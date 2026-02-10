"""
NeXus Scan Classes

NexusScan - NeXus Scan class, lazy loader of scan files
NexusDataHolder - Loads scan data and meta data into attributes
"""

import os
import datetime
import re

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

    def _get_plot_axis(self, hdf: h5py.File | h5py.Group, axis_name: str,
                       reduce_shape: bool = True, flatten: bool = False) -> tuple[np.ndarray, str]:
        """
        Return plot axis data and label for given axis name

        E.G.
            data, label = scan.get_plot_axis('axes', flatten=True)

        :param hdf: h5py.File or h5py.Group
        :param axis_name: axis name as given in self.map
        :param reduce_shape: reduces shape (summing additional axes) of >2D arrays to self.map.scannables_shape
        :param flatten: flatten data array if True
        :return: (data, label) tuple
        """
        # Default scannables if not generated by hdfmap
        if ('axes' in axis_name or 'signal' in axis_name) and axis_name not in self.map:
            axes_names, signal_names = self.map.nexus_default_names()
            if re.match(r"axes\d?", axis_name):
                index = int(axis_name.strip('axes') or 0)
                axis_name = list(axes_names)[index]
            elif re.match(r"signal\d?", axis_name):
                index = int(axis_name.strip('signal') or 0)
                axis_name = list(signal_names)[index]
        label, = self.map.generate_ids(axis_name, modify_missing=False)
        data = self.map.eval(hdf, axis_name)
        if np.ndim(data) > 1 and reduce_shape:
            # reduce high dimensional arrays to the default scannable shape
            shape = self.map.scannables_shape()
            if np.ndim(data) == len(shape) + 2:
                # Image data
                data = np.sum(data, axis=(-1, -2))
            if np.shape(data) != shape:
                raise ValueError(f"2+D Arrays must have same shape: {axis_name}{np.shape(data)} != {shape}")
        if flatten:
            data = np.reshape(data, -1)
        return data, label

    def get_plot_axis(self, axis_name: str, reduce_shape: bool = True, flatten: bool = False) -> tuple[np.ndarray, str]:
        """
        Return plot axis data and label for given axis name

        E.G.
            data, label = scan.get_plot_axis('axes', flatten=True)

        :param axis_name: axis name as given in self.map
        :param reduce_shape: reduces shape (summing additional axes) of >2D arrays to self.map.scannables_shape
        :param flatten: flattens output if True
        :return: (data, label) tuple
        """
        with self.load_hdf() as hdf:
            return self._get_plot_axis(hdf, axis_name, reduce_shape=reduce_shape, flatten=flatten)

    def get_plot_data(self, x_axis: str | None = None, *y_axis: str | None, z_axis: str | None = None) -> dict:
        """
        Return dict of plottable data

        E.G.
            data = scan.get_plot_data('axes', 'signal')

            plt.plot(data['x'], data['y'])
            plt.xlabel(data['xlabel'])
            plt.ylabel(data['ylabel'])
            plt.title(data['title'])
            plt.legend(data['legend'])

        :param x_axis: axis name as given in self.map
        :param y_axis: axis name as given in self.map
        :param z_axis: axis name as given in self.map
        :returns: {
            'xlabel': str label of first axes
            'ylabel': str label of first signal
            'xdata': flattened array of first axes
            'ydata': flattened array of first signal
            'axes_names': list of axes names,
            'signal_names': list of signal + auxiliary signal names,
            'axes_data': list of ND arrays of data for axes,
            'signal_data': list of ND array of data for signal + auxiliary signals,
            'axes_labels': list of axes labels as 'name [units]',
            'signal_labels': list of signal labels,
            'data': dict of all scannables axes,
            'title': str title as 'filename\nNXtitle'
        if dataset is a 2D grid scan, additional rows:
            'grid_xlabel': str label of grid x-axis
            'grid_ylabel': str label of grid y-axis
            'grid_label': str label of height or colour
            'grid_xdata': 2D array of x-coordinates
            'grid_ydata': 2D array of y-coordinates
            'grid_data': 2D array of height or colour
        }
        """
        with self.load_hdf() as hdf:
            data = self.map.get_plot_data(hdf)
            cmd = self.map.eval(hdf, Md.cmd)
            if len(cmd) > self.MAX_STR_LEN:
                cmd = shorten_string(cmd)
            x_data, x_lab = self.get_plot_axis(x_axis or 'axes', reduce_shape=True, flatten=True)

            y_data, y_labs = [], []
            y_axis = y_axis or [None]
            for n, _y_axis in enumerate(y_axis):
                _y_data, _y_lab = self.get_plot_axis(_y_axis or f"signal{n}", reduce_shape=True, flatten=True)
                y_data.append(_y_data)
                y_labs.append(_y_lab)
            y_data = np.array(y_data)
            y_error = self._error_function(y_data)

            additional = {
                'x': x_data,
                'y': y_data[0],
                'xdata': x_data,
                'ydata': y_data.T,
                'yerror': y_error.T,
                'xlabel': x_lab,
                'ylabel': y_labs[0],
                'title': f"#{self.scan_number()}\n{cmd}",
                'legend': y_labs
            }
            if z_axis is not None:
                z_data, z_lab = self.get_plot_axis(z_axis, reduce_shape=True, flatten=True)
                additional['zdata'] = z_data
                additional['zlabel'] = z_lab
            # 2+D data
            shape = self.map.scannables_shape()
            if len(shape) >= 2:
                x_data = x_data.reshape(shape)
                y_data, y_lab = self.get_plot_axis(y_axis[0] or 'axes1')
                z_data, z_lab = self.get_plot_axis(
                    y_axis[1] if len(y_axis) > 1 else z_axis or 'signal',
                )
                # reduce dimensions to 2
                #TODO: taking the first dimension might not always be right
                x_data = x_data[(..., ) + (0, ) * (x_data.ndim - 2)]
                y_data = y_data[(..., ) + (0, ) * (y_data.ndim - 2)]
                z_data = z_data.sum(axis=tuple(range(2, z_data.ndim)))

                if y_data.shape != x_data.shape:
                    raise ValueError(f"Shape of '{y_lab}' {y_data.shape} != '{x_lab}' {x_data.shape}")
                if z_data.shape != x_data.shape:
                    raise ValueError(f"Shape of '{z_lab}' {z_data.shape} != '{x_lab}' {x_data.shape}")

                additional['grid_xlabel'] = x_lab
                additional['grid_ylabel'] = y_lab
                additional['grid_label'] = z_lab
                additional['grid_xdata'] = x_data
                additional['grid_ydata'] = y_data
                additional['grid_data'] = z_data
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
