

import hdfmap
from hdfmap import NexusMap
from hdfmap.eval_functions import dataset2data, dataset2str, generate_identifier
import h5py
import numpy as np
import datetime

from mmg_toolbox.utils.misc_functions import DataHolder, shorten_string
from mmg_toolbox.utils.file_functions import get_scan_number
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapMMGMetadata as Md


class NexusScan(hdfmap.NexusLoader):
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
        return hdfmap.load_hdf(self.filename)

    def datasets(self, *args) -> list[h5py.Dataset]:
        """Return HDF5 datasets from NeXus file (leaves file in open state)"""
        with self.load_hdf() as hdf:
            return [hdf[self.map.combined[name]] for name in args]

    def arrays(self, *args) -> list[np.ndarray]:
        """Return Numpy array"""
        with self.load_hdf() as hdf:
            return [hdf[self.map.combined[name]][...] for name in args]

    def values(self, *args, value_func=np.mean) -> list[float]:
        """Return float values"""
        with self.load_hdf() as hdf:
            return [value_func(hdf[self.map.combined[name]]) for name in args]

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

    def labels(self, *args) -> list[str]:
        """Return labels"""
        return [generate_identifier(self.map[arg]) for arg in args]

    def table(self, delimiter=', ', string_spec='', format_spec='f', default_decimals=8) -> str:
        """Return data table"""
        with self.load_hdf() as hdf:
            return self.map.create_scannables_table(hdf, delimiter, string_spec, format_spec, default_decimals)

    def get_plot_data(self, x_axis: str = 'axes0', y_axis: str = 'signal0') -> dict:
        with self.load_hdf() as hdf:
            cmd = self.map.eval(hdf, Md.cmd)
            if len(cmd) > self.MAX_STR_LEN:
                cmd = shorten_string(cmd)
            ydata = self.map.eval(hdf, y_axis)
            yerror = self._error_function(ydata)
            return {
                'x': self.map.eval(hdf, x_axis),
                'y': ydata,
                'yerror': yerror,
                'xlabel': generate_identifier(self.map[x_axis]) if x_axis in self.map else x_axis,
                'ylabel': generate_identifier(self.map[y_axis]) if y_axis in self.map else y_axis,
                'title': f"#{self.scan_number()}\n{cmd}"
            }


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
    map: hdfmap.NexusMap
    metadata: DataHolder

    def __init__(self, filename: str | None, hdf_map: hdfmap.NexusMap | None = None, flatten_scannables: bool = True):
        NexusScan.__init__(self, filename, hdf_map)

        with hdfmap.load_hdf(filename) as hdf:
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
