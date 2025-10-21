

import hdfmap
from hdfmap.eval_functions import dataset2data, dataset2str, generate_identifier
import h5py
import numpy as np
import datetime

from mmg_toolbox.utils.misc_functions import DataHolder, shorten_string
from mmg_toolbox.utils.file_functions import get_scan_number
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapMMGMetadata as Md


class NexusDataHolder(DataHolder):
    """Nexus data holder class"""
    filename: str
    map: hdfmap.NexusMap
    metadata: DataHolder
    MAX_STR_LEN: int = 100

    def __init__(self, filename: str | None, hdf_map: hdfmap.NexusMap | None = None, flatten_scannables: bool = True):
        if filename is None:
            filename = hdf_map.filename
        if hdf_map is None:
            hdf_map = hdfmap.create_nexus_map(filename)
        self.filename = filename
        self.map = hdf_map

        with hdfmap.load_hdf(filename) as hdf:
            metadata = hdf_map.get_metadata(hdf)
            scannables = hdf_map.get_scannables(hdf, flatten=flatten_scannables)
        super().__init__(**scannables)
        self.metadata = DataHolder(**metadata)

        from mmg_toolbox.utils.fitting import ScanFitManager, poisson_errors
        self.fit = ScanFitManager(self)
        self._error_function = poisson_errors

    def __repr__(self):
        return f"NexusDataHolder('{self.filename}')"

    def __str__(self):
        return str(self.map)

    def __call__(self, *args, **kwargs):
        return self.eval(*args, **kwargs)

    def eval(self, expression: str, default='-', raise_errors: bool = True):
        """
        Evaluate an expression using the namespace of the hdf file
        :param expression: str expression to be evaluated
        :param default: returned if varname not in namespace
        :param raise_errors: raise exceptions if True, otherwise return str error message as result and log the error
        :return: eval(expression)
        """
        with hdfmap.load_hdf(self.filename) as hdf:
            return self.map.eval(hdf, expression, default=default, raise_errors=raise_errors)

    def format(self, expression: str, default='-', raise_errors: bool = True) -> str:
        """
        Evaluate a formatted string expression using the namespace of the hdf file
        :param expression: str expression using {name} format specifiers
        :param default: returned if varname not in namespace
        :param raise_errors: raise exceptions if True, otherwise return str error message as result and log the error
        :return: eval_hdf(f"expression")
        """
        with hdfmap.load_hdf(self.filename) as hdf:
            return self.map.format_hdf(hdf, expression, default=default, raise_errors=raise_errors)

    def scan_number(self) -> int:
        return get_scan_number(self.filename)

    def title(self) -> str:
        return f"#{self.scan_number()}"

    def datasets(self, *args) -> list[h5py.Dataset]:
        """Return HDF5 datasets from NeXus file (leaves file in open state)"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return [hdf[self.map.combined[name]] for name in args]

    def arrays(self, *args) -> list[np.ndarray] :
        """Return Numpy array"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return [hdf[self.map.combined[name]][...] for name in args]

    def values(self, *args, value_func=np.mean) -> list[float]:
        """Return float values"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return [np.mean(hdf[self.map.combined[name]]) for name in args]

    def times(self, *args) -> list[datetime.datetime]:
        """Return datetime object"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return [dataset2data(hdf[self.map.combined[name]]) for name in args]

    def strings(self, *args, units=False) -> list[str]:
        """Return string value"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return [dataset2str(hdf[self.map.combined[name]], units=units) for name in args]

    def image(self, index:  int | tuple | slice | None = None) -> np.ndarray:
        """Return image or selection from default detector"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return self.map.get_image(hdf, index)

    def labels(self, *args) -> list[str]:
        """Return labels"""
        return [generate_identifier(self.map[arg]) for arg in args]

    def table(self, delimiter=', ', string_spec='', format_spec='f', default_decimals=8) -> str:
        """Return data table"""
        with hdfmap.load_hdf(self.filename) as hdf:
            return self.map.create_scannables_table(hdf, delimiter, string_spec, format_spec, default_decimals)

    def get_plot_data(self, x_axis: str = 'axes0', y_axis: str = 'signal0') -> dict:
        with hdfmap.load_hdf(self.filename) as hdf:
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
    
    def plot(self, x_axis: str = 'axes0', y_axis: str = 'signal0', axes=None):
        """Plot data using matplotlib"""
        import matplotlib.pyplot as plt
        plot_data = self.get_plot_data(x_axis, y_axis)

        if axes is None:
            fig, axes = plt.subplots()

        axes.plot(plot_data['x'], plot_data['y'], label=plot_data['title'])
        axes.set_xlabel(plot_data['xlabel'])
        axes.set_ylabel(plot_data['ylabel'])
        axes.set_title(plot_data['title'])


def read_nexus_file(filename: str) -> NexusDataHolder:
    """
    Read Nexus file as DataHolder
    """
    return NexusDataHolder(filename, flatten_scannables=True)


def add_roi(hdf_map: hdfmap.NexusMap, name: str, cen_i: int | str, cen_j: int | str,
                wid_i: int = 30, wid_j: int = 30, image_name: str = 'IMAGE'):
    """
    Add an image ROI (region of interest) to the named expressions
    The ROI operates on the default IMAGE dataset, loading only the required region from the file.
    The following expressions will be added, for use in self.eval etc.
        *name* -> returns the whole ROI array
        *name*_total -> returns the sum of each image in the ROI array
        *name*_max -> returns the max of each image in the ROI array
        *name*_min -> returns the min of each image in the ROI array
        *name*_mean -> returns the mean of each image in the ROI array
        *name*_bkg -> returns the background ROI array (area around ROI)
        *name*_rmbkg -> returns the total with background subtracted
    """
    wid_i = abs(wid_i) // 2
    wid_j = abs(wid_j) // 2
    islice = f"{cen_i}-{wid_i:.0f} : {cen_i}+{wid_i:.0f}"
    jslice = f"{cen_j}-{wid_j:.0f} : {cen_j}+{wid_j:.0f}"
    roi_array = f"d_{image_name}[..., {islice}, {jslice}]"
    roi_total = f"{roi_array}.sum(axis=(-1, -2))"
    roi_max = f"{roi_array}.max(axis=(-1, -2))"
    roi_min = f"{roi_array}.min(axis=(-1, -2))"
    roi_mean = f"{roi_array}.mean(axis=(-1, -2))"

    islice = f"{cen_i}-{wid_i*2:.0f} : {cen_i}+{wid_i*2:.0f}"
    jslice = f"{cen_j}-{wid_j*2:.0f} : {cen_j}+{wid_j*2:.0f}"
    bkg_array = f"d_{image_name}[..., {islice}, {jslice}]"
    bkg_total = f"{bkg_array}.sum(axis=(-1, -2))"
    roi_bkg_total = f"({bkg_total} - {roi_total})"
    roi_bkg_mean = f"{roi_bkg_total}/(12*{wid_i * wid_j})"
    # Transpose array to broadcast bkg_total
    roi_rmbkg = f"({roi_array}.T - {roi_bkg_mean}).sum(axis=(0, 1))"
    alternate_names = {
        f"{name}_total": roi_total,
        f"{name}_max": roi_max,
        f"{name}_min": roi_min,
        f"{name}_mean": roi_mean,
        f"{name}_bkg": roi_bkg_total,
        f"{name}_rmbkg": roi_rmbkg,
        name: roi_array,
    }
    hdf_map.add_named_expression(**alternate_names)

