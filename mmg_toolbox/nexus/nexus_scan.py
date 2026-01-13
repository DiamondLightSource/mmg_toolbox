"""
NeXus Scan Classes

NexusScan - NeXus Scan class, lazy loader of scan files
NexusDataHolder - Loads scan data and meta data into attributes
"""

import os
import datetime

import h5py
import numpy as np
from hdfmap import NexusLoader, NexusMap, load_hdf
from hdfmap.eval_functions import dataset2data, dataset2str

from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapMMGMetadata as Md
from mmg_toolbox.beamline_metadata.config import beamline_config, C
from mmg_toolbox.nexus.instrument_model import NXInstrumentModel
from mmg_toolbox.nexus.nexus_functions import get_dataset_value
from mmg_toolbox.utils.file_functions import get_scan_number, read_tiff
from mmg_toolbox.utils.misc_functions import shorten_string, DataHolder
from mmg_toolbox.xas import SpectraContainer, load_xas_scans


class NexusScan(NexusLoader):
    """
    Light-weight NeXus file reader

    Example:
        scan = NexusScan('scan.nxs')
        scan('scan_command') -> returns value

    :param nxs_filename: path to nexus file
    :param hdf_map: NexusMap object or None
    :param config: configuration dict
    """
    MAX_STR_LEN: int = 100

    def __init__(self, nxs_filename: str, hdf_map: NexusMap | None = None, config: dict | None = None):
        super().__init__(nxs_filename, hdf_map)
        self.config: dict = config or beamline_config()
        self.beamline = self.config.get('beamline', None)

        # add scan number to eval namespace
        self.map.add_local(scan_number=self.scan_number())

        from mmg_toolbox.fitting import ScanFitManager, poisson_errors
        self.fit = ScanFitManager(self)
        self._error_function = poisson_errors
        from mmg_toolbox.plotting.scan_plot_manager import ScanPlotManager
        self.plot = ScanPlotManager(self)

    def __repr__(self):
        if self.beamline:
            return f"NexusScan<{self.beamline}>({self.scan_number()}: '{self.filename}')"
        return f"NexusScan('{self.filename}')"

    def __str__(self):
        try:
            return self.metadata_str()
        except Exception as ex:
            return f"{repr(self)}\n  Metadata failed with: \n{ex}\n"

    def metadata_str(self, expression: str | None = None):
        """Generate metadata string from beamline config"""
        if expression is None:
            expression = self.config.get(C.metadata_string, '')
        return self.format(expression)

    def scan_number(self) -> int:
        return get_scan_number(self.filename)

    def title(self) -> str:
        return f"#{self.scan_number()}"

    def label(self) -> str:
        return f"#{self.scan_number()}"

    def load_hdf(self) -> h5py.File:
        """Load the Hdf file"""
        return load_hdf(self.filename)

    def datasets(self, *args) -> list[h5py.Dataset]:
        """Return HDF5 datasets from NeXus file (leaves file in open state)"""
        with self.load_hdf() as hdf:
            return [hdf[self.map.combined[name]] for name in args]

    def arrays(self, *args, units: str = '', default: np.ndarray = np.array([np.nan])) -> list[np.ndarray]:
        """Return Numpy arrays"""
        with self.load_hdf() as hdf:
            return [
                get_dataset_value(self.map.combined[name], hdf, units=units, default=default)
                for name in args
            ]

    def values(self, *args, value_func=np.mean,
               units: str = '', default: np.ndarray = np.array(np.nan)) -> list[np.floating]:
        """Return float values"""
        with self.load_hdf() as hdf:
            return [
                value_func(get_dataset_value(self.map.combined[name], hdf, units=units, default=default))
                for name in args
            ]

    def times(self, *args) -> list[datetime.datetime]:
        """Return datetime object"""
        with self.load_hdf() as hdf:
            data = [dataset2data(hdf[self.map.combined[name]]) for name in args]
            dt = [
                obj if isinstance(obj, datetime.datetime)
                else datetime.datetime.fromisoformat(obj) if isinstance(obj, str)
                else datetime.datetime.fromtimestamp(float(obj))
                for obj in data
            ]
        return dt

    def strings(self, *args, units=False) -> list[str]:
        """Return string value"""
        with self.load_hdf() as hdf:
            return [dataset2str(hdf[self.map.combined[name]], units=units) for name in args]

    def image(self, index: int | tuple | slice | None = None) -> np.ndarray:
        """Return image or selection from default detector"""
        if not self.map.image_data:
            raise ValueError(f'{repr(self)} contains no image data')
        with self.load_hdf() as hdf:
            image = self.map.get_image(hdf, index)

            if issubclass(type(image), str):
                # TIFF image, NXdetector/image_data -> array('file.tif')
                file_directory = os.path.dirname(self.filename)
                image_filename = os.path.join(file_directory, image)
                if not os.path.isfile(image_filename):
                    raise FileNotFoundError(f"File not found: {image_filename}")
                image = read_tiff(image_filename)
            elif image.ndim == 0:
                # image is file path number, NXdetector/path -> arange(n_points)
                scan_number = get_scan_number(self.filename)
                file_directory = os.path.dirname(self.filename)
                detector_names = list(self.map.image_data.keys())
                for detector_name in detector_names:
                    image_filename = os.path.join(file_directory, f"{scan_number}-{detector_name}-files/{image:05.0f}.tif")
                    if os.path.isfile(image_filename):
                        break
                if not os.path.isfile(image_filename):
                    raise FileNotFoundError(f"File not found: {image_filename}")
                image = read_tiff(image_filename)
            elif image.ndim != 2:
                raise Exception(f"detector image[{index}] is the wrong shape: {image.shape}")
            return image

    def volume(self) -> np.ndarray:
        """Return complete stack of images"""
        return self.image(index=())

    def table(self, delimiter=', ', string_spec='', format_spec='f', default_decimals=8) -> str:
        """Return data table"""
        with self.load_hdf() as hdf:
            return self.map.create_scannables_table(hdf, delimiter, string_spec, format_spec, default_decimals)

    def get_plot_data(self, x_axis: str | None = None, y_axis: str | None = None) -> dict:
        """Return dict of plottable data"""
        # TODO: improve docs
        # TODO: add multiple y_axis, z_axis, see scan_plot_manager
        x_defaults = [None, 'axes', 'axes0']
        y_defaults = [None, 'signal', 'signal0']
        if x_axis in x_defaults or y_axis in y_defaults:
            axes_names, signal_names = self.map.nexus_default_names()
            x_axis = next(iter(axes_names)) if x_axis in x_defaults else x_axis
            y_axis = next(iter(signal_names)) if y_axis in y_defaults else y_axis

        with self.load_hdf() as hdf:
            data = self.map.get_plot_data(hdf)
            cmd = self.map.eval(hdf, Md.cmd)
            if len(cmd) > self.MAX_STR_LEN:
                cmd = shorten_string(cmd)
            xdata = self.map.eval(hdf, x_axis)
            ydata = self.map.eval(hdf, y_axis)
            yerror = self._error_function(ydata)
            x_lab, y_lab = self.map.generate_ids(x_axis, y_axis, modify_missing=False)
            additional = {
                'x': xdata,
                'y': ydata,
                'xdata': xdata,
                'ydata': ydata,
                'yerror': yerror,
                'xlabel': x_lab,
                'ylabel': y_lab,
                'title': f"#{self.scan_number()}\n{cmd}"
            }
            if 'grid_xlabel' in data and ydata.ndim == 2:
                additional['grid_label'] = y_lab
                additional['grid_data'] = ydata
            data.update(additional)
            return data

    def xas_scan(self) -> SpectraContainer:
        """Load XAS Spectra"""
        return load_xas_scans(self.filename)[0]

    def instrument_model(self) -> NXInstrumentModel:
        """return instrument model"""
        with self.load_hdf() as hdf:
            return NXInstrumentModel(hdf)


class NexusDataHolder(DataHolder, NexusScan):
    """
    Nexus data holder class
     - Automatically reads scannable and metadata from file
     - acts like the old .dat DataHolder class
     - has additional functions to read data from NeXus file

    Example:
        scan = NexusDataHolder('12345.nxs')
        scan.eta -> returns array
        scan.metadata.metadata -> returns value
        scan('signal') -> evaluate expression

    :param filename: path to Nexus file
    :param hdf_map: NexusMap object or None to generate
    :param flatten_scannables: if True, flattens all scannable arrays to 1D
    """
    filename: str
    map: NexusMap
    metadata: DataHolder

    def __init__(self, filename: str | None, hdf_map: NexusMap | None = None, flatten_scannables: bool = True,
                 config: dict | None = None):
        NexusScan.__init__(self, filename, hdf_map, config)

        with load_hdf(filename) as hdf:
            metadata = self.map.get_metadata(hdf)
            scannables = self.map.get_scannables(hdf, flatten=flatten_scannables)
        DataHolder.__init__(self, **scannables)
        self.metadata = DataHolder(**metadata)

    def __repr__(self):
        return f"NexusDataHolder('{self.filename}')"
