import os

from hdfmap import NexusMap, NexusLoader, load_hdf, create_nexus_map
from hdfmap.eval_functions import dataset2data, dataset2str
import h5py
import numpy as np
import datetime

from mmg_toolbox.utils.misc_functions import DataHolder, shorten_string
from mmg_toolbox.utils.file_functions import get_scan_number, replace_scan_number
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapMMGMetadata as Md
from mmg_toolbox.nexus.nexus_functions import get_dataset_value
from mmg_toolbox.nexus.instrument_model import NXInstrumentModel
from mmg_toolbox.xas.nxxas_loader import load_xas_scans, SpectraContainer


class NexusScan(NexusLoader):
    """
    Light-weight NeXus file reader

    Example:
        scan = NexusScan('scan.nxs')
        scan('scan_command') -> returns value

    :param nxs_filename: path to nexus file
    :param hdf_map: NexusMap object or None
    """
    MAX_STR_LEN: int = 100

    def __init__(self, nxs_filename: str, hdf_map: NexusMap | None = None):
        super().__init__(nxs_filename, hdf_map)

        from mmg_toolbox.utils.fitting import ScanFitManager, poisson_errors
        self.fit = ScanFitManager(self)
        self._error_function = poisson_errors
        from mmg_toolbox.plotting.scan_plot_manager import ScanPlotManager
        self.plot = ScanPlotManager(self)

    def __repr__(self):
        return f"NexusScan('{self.filename}')"

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
            return [dataset2data(hdf[self.map.combined[name]]) for name in args]

    def strings(self, *args, units=False) -> list[str]:
        """Return string value"""
        with self.load_hdf() as hdf:
            return [dataset2str(hdf[self.map.combined[name]], units=units) for name in args]

    def image(self, index: int | tuple | slice | None = None) -> np.ndarray:
        """Return image or selection from default detector"""
        with self.load_hdf() as hdf:
            return self.map.get_image(hdf, index)

    def table(self, delimiter=', ', string_spec='', format_spec='f', default_decimals=8) -> str:
        """Return data table"""
        with self.load_hdf() as hdf:
            return self.map.create_scannables_table(hdf, delimiter, string_spec, format_spec, default_decimals)

    #TODO: Remove this?
    def get_plot_data(self, x_axis: str = 'axes0', y_axis: str = 'signal0') -> dict:
        with self.load_hdf() as hdf:
            cmd = self.map.eval(hdf, Md.cmd)
            if len(cmd) > self.MAX_STR_LEN:
                cmd = shorten_string(cmd)
            xdata = self.map.eval(hdf, x_axis)
            ydata = self.map.eval(hdf, y_axis)
            yerror = self._error_function(ydata)
            x_lab, y_lab = self.map.generate_ids(x_axis, y_axis, modify_missing=False)
            return {
                'x': xdata,
                'y': ydata,
                'yerror': yerror,
                'xlabel': x_lab,
                'ylabel': y_lab,
                'title': f"#{self.scan_number()}\n{cmd}"
            }

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

    def __init__(self, filename: str | None, hdf_map: NexusMap | None = None, flatten_scannables: bool = True):
        NexusScan.__init__(self, filename, hdf_map)

        with load_hdf(filename) as hdf:
            metadata = self.map.get_metadata(hdf)
            scannables = self.map.get_scannables(hdf, flatten=flatten_scannables)
        DataHolder.__init__(self, **scannables)
        self.metadata = DataHolder(**metadata)

    def __repr__(self):
        return f"NexusDataHolder('{self.filename}')"


def read_nexus_file(filename: str, flatten_scannables: bool = True) -> NexusDataHolder:
    """
    Read Nexus file as DataHolder
    """
    return NexusDataHolder(filename, flatten_scannables=flatten_scannables)


def find_matching_scans(filename: str, match_field: str = 'scan_command',
                        search_scans_before: int = 10, search_scans_after: int | None = None) -> list[str]:
    """
    Find scans with scan numbers close to the current file with matching scan command

    :param filename: nexus file to start at (must include scan number in filename)
    :param match_field: nexus field to compare between scan files
    :param search_scans_before: number of scans before current scan to look for
    :param search_scans_after: number of scans after current scan to look for (None==before)
    :returns: list of scan files that exist and have matching field values
    """
    nexus_map = create_nexus_map(filename)
    field_value = nexus_map.eval(nexus_map.load_hdf(), match_field)
    scanno = get_scan_number(filename)
    if search_scans_after is None:
        search_scans_after = search_scans_before
    matching_files = []
    for scn in range(scanno - search_scans_before, scanno + search_scans_after):
        new_filename = replace_scan_number(filename, scn)
        if os.path.isfile(new_filename):
            new_field_value = nexus_map.eval(load_hdf(new_filename), match_field)
            if field_value == new_field_value:
                matching_files.append(new_filename)
    return matching_files

