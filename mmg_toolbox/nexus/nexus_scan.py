"""
NeXus Scan Classes

NexusScan - NeXus Scan class, lazy loader of scan files
NexusDataHolder - Loads scan data and meta data into attributes
"""

import os
import datetime
import json

import h5py
import hdfmap
import numpy as np
from hdfmap import NexusLoader, NexusMap, load_hdf
from hdfmap.eval_functions import dataset2data, dataset2str

from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapMMGMetadata as Md
from mmg_toolbox.beamline_metadata.hdfmap_generic import ROI_SUFFIXES
from mmg_toolbox.beamline_metadata.config import beamline_config, C
from mmg_toolbox.nexus.instrument_model import NXInstrumentModel
from mmg_toolbox.nexus.nexus_functions import get_dataset_value, nx_find, nx_find_all
from mmg_toolbox.nexus.nexus_names import NX_START, NX_END
from mmg_toolbox.nexus import nexus_writer as nw
from mmg_toolbox.utils.file_functions import get_scan_number, read_tiff, get_file_time
from mmg_toolbox.utils.misc_functions import shorten_string, multiple_replace, DataHolder
from mmg_toolbox.xas.spectra_container import SpectraContainer
from mmg_toolbox.xas.nxxas_loader import load_xas_scans


class NexusScan(NexusLoader):
    """
    Light-weight NeXus file reader

        >>> scan = NexusScan('scan.nxs')
        >>> scan('scan_command')
         'scan x ...'
        >>> x, y = scan('axes, signal / monitor')
        >>> scan.plot()  # default plot
        >>> scan.plot.image()  # other plot options
        >>> result = scan.fit.multi_peak_fit()
        >>> print(scan)  # print scan default metadata
        >>> print(scan.info())  # print scan namespace
        >>> scan.map.add_roi('name', ...)  # add ROI to namespace
        >>> scan.image(0)  # return first detector image as array
        >>> scan.volume()  # return image stack
        >>> data = scan.get_plot_data()  # return dict of plot data

    :param nxs_filename: path to nexus file
    :param hdf_map: NexusMap object or None
    :param config: configuration dict
    """
    MAX_STR_LEN: int = 100

    def __init__(self, nxs_filename: str, hdf_map: NexusMap | None = None, config: dict | None = None):
        super().__init__(nxs_filename, hdf_map)
        self.config: dict = config or beamline_config()
        self.beamline = self.config.get(C.beamline, None)

        # add scan number to eval namespace
        self.add_local(scan_number=self.scan_number(), beamline=self.beamline)
        # add alternate names
        self.map.add_named_expression(**self.config.get(C.replace_names, {}))
        # add ROIs
        for (name, cen_i, cen_j, wid_i, wid_j, det_name) in self.config.get(C.roi, []):
            self.map.add_roi(name, cen_i, cen_j, wid_i, wid_j, det_name)

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

    def info(self, arrays=False, values=False, combined=False,
             metadata=False, scannables=True, image_data=True,
             local=False, alternate=True) -> str:
        """Return string of namespace information"""
        map_data = self.map.info_names(arrays=arrays, values=values, combined=combined,
                                       metadata=metadata, scannables=scannables,
                                       image_data=image_data, local=local, alternate=alternate)
        return map_data

    def rois(self, append: str = '_total') -> list[str]:
        """
        Return ROI expressions available in scan namespace

            rois = [scan.eval(roi) for roi in scan.rois('_total')]

        :param append: str to append to each ROI name, e.g. '_total', '_max', '_min', '_mean'
        :return: list of ROI names that can be used in eval.
        """
        # search for ROIs in HdfMap expressions
        alternate_name_rois = {
            next((name.removesuffix(sfx) for sfx in ROI_SUFFIXES if name.endswith(sfx)), name)
            for name, expression in self.map.alternate_names.items()
            if expression.startswith('d_')
        }
        return [roi + append for roi in alternate_name_rois]

    def scan_number(self) -> int:
        return get_scan_number(self.filename)

    def title(self) -> str:
        return f"#{self.scan_number()}"

    def label(self) -> str:
        return f"#{self.scan_number()}"

    def start_end_duration(self) -> tuple[datetime.datetime, datetime.datetime, datetime.timedelta]:
        """Return start and end times of scan, plus duration as datetime and timedelta objects"""
        scan_start, scan_end = self.times(NX_START, NX_END, default=None)
        if scan_start is None:
            raise KeyError(f"scan start time not found in {self.filename}")
        if scan_end is None:
            scan_end = get_file_time(self.filename)
        return scan_start, scan_end, scan_end - scan_start

    def load_hdf(self) -> h5py.File:
        """Load the Hdf file"""
        return load_hdf(self.filename)

    def hdf_tree_string(self, group: str = '/', all_links: bool = True, attributes: bool = True) -> str:
        """
        Generate string of the hdf file structure, similar to h5ls. Uses h5py.visititems

        :param all_links: bool, if True, also show links
        :param group: only display tree structure of this group (default root)
        :param attributes: if True, display the attributes of groups and datasets
        :return: str
        """
        return hdfmap.hdf_tree_string(self.filename, all_links=all_links, group=group, attributes=attributes)

    def hdf_find(self, *field_or_class: str | list[str], find_all: bool = False) -> (h5py.Dataset | h5py.Group) | list[h5py.Dataset | h5py.Group]:
        """
        Find datasets and groups within hdf file

            HdfDataset = scan.hdf_find('NXentry', ['NXdata', 'measurement'], 'signal')

        Warning: HDF file stays in open state while Dataset or Group objects exist.

        :param field_or_class: names to search for, in hierarchical order. Lists treated as OR
        :param find_all: whether to return all datasets or only the first match
        :returns: matching Dataset or Group, or list of matching Datasets or Groups
        """
        with self.load_hdf() as hdf:
            if find_all:
                return nx_find_all(hdf, *field_or_class)
            return nx_find(hdf, *field_or_class)

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

    def times(self, *args, default: datetime.datetime | None = None) -> list[datetime.datetime | None]:
        """Return datetime object"""
        with self.load_hdf() as hdf:
            data = [
                dataset2data(hdf[self.map.combined[name]])
                if name in self.map.combined else default
                for name in args
            ]
            dt = [
                obj if obj is None or isinstance(obj, datetime.datetime) else
                datetime.datetime.fromisoformat(obj) if isinstance(obj, str) else
                datetime.datetime.fromtimestamp(float(obj))
                for obj in data
            ]
        return dt

    def strings(self, *args, units=False) -> list[str]:
        """Return string value"""
        with self.load_hdf() as hdf:
            return [dataset2str(hdf[self.map.combined[name]], units=units) for name in args]

    def image(self, index: int | str | None = None) -> np.ndarray:
        """
        Return image or selection from default detector

            im = scan.image(0)  # First image
            im = scan.image(None)  # middle image
            im = scan.image('sum')  # sum of all images

        :param index: point in the scan to show the image, 'sum' gives sum over all images, None gives the middle image
        :return: (n,m) array
        """
        if not self.map.image_data:
            raise ValueError(f'{repr(self)} contains no image data')
        with self.load_hdf() as hdf:
            if index == 'sum':
                volume = self.map.get_image(hdf, ())
                image = volume.sum(axis=tuple(range(volume.ndim-2)))  # this will fail for filenames
            else:
                image = self.map.get_image(hdf, index)

            if issubclass(type(image), str) or np.issubdtype(image.dtype, str):
                # TIFF image, NXdetector/image_data -> array('file.tif')
                file_directory = os.path.dirname(self.filename)
                image_filename = os.path.join(file_directory, str(image))
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
        return self.map.get_image(self.load_hdf(), ())

    def image_background(self, index: int | tuple | slice | str | None = (), n_bins: int  = 100) -> np.ndarray:
        """
        Return the modal value of the detector image,
        which usually gives the background value.

        The modal value is determined by histograming the image (or image stack) and taking
        the value of the largest bin.

        :param index: index of image to return, use () for full image stack.
        :param n_bins: number of histogram bins
        :return: modal value or values per image
        """
        image = self.map.get_image(self.load_hdf(), index)  # hdf data only
        n, bins = np.histogram(np.log10(image[image>0].flatten()), bins=n_bins)
        return 10 ** bins[np.argmax(n)]

    def get_max_index(self, expression: str = 'IMAGE') -> tuple[float, tuple[int, ...]]:
        """Return the index and value of the maximum pixel in a detector image or volume"""
        data = self.eval(expression)
        max_idx = tuple(int(v) for v in np.unravel_index(np.argmax(data), data.shape))
        return float(data[max_idx]), max_idx

    def table(self, delimiter=', ', string_spec='', format_spec='f', default_decimals=8) -> str:
        """Return data table"""
        with self.load_hdf() as hdf:
            return self.map.create_scannables_table(hdf, delimiter, string_spec, format_spec, default_decimals)

    def get_scan_time(self) -> np.ndarray:
        """Return array of datetimes for each scan point"""
        start, stop, duration = self.start_end_duration()
        count_time = self.eval('_t', default=None)  # '_t' is an alternate for count_time and others
        if count_time is None:
            # assume regular spacing in time
            shape = self.map.scannables_shape()
            time_per_point = duration.total_seconds() / np.prod(*shape)
            count_time = np.full(shape, time_per_point)
        return np.array([start + datetime.timedelta(seconds=x) for x in np.cumsum(count_time)])

    def replace_default_names(self, expression: str) -> str:
        """Replace 'axes', 'signal' and 'IMAGE' in expression with correct values"""
        return self.map.merge_default_names(expression)

    def _get_plot_axis(self, hdf: h5py.File | h5py.Group, axis_name: str,
                       reduce_shape: bool = True, flatten: bool = False) -> tuple[np.ndarray, str]:
        """
        Return plot axis data and label for given axis name

            data, label = scan.get_plot_axis('axes', flatten=True)

        :param hdf: h5py.File or h5py.Group
        :param axis_name: axis name as given in self.map
        :param reduce_shape: reduces shape (summing additional axes) of >2D arrays to self.map.scannables_shape
        :param flatten: flatten data array if True
        :return: (data, label) tuple
        """
        # Default scannables if not generated by hdfmap
        label = axis_name = self.replace_default_names(axis_name)
        data = self.map.eval(hdf, axis_name, local_data=self._local_data)
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

            data = scan.get_plot_data('axes', 'signal')
            plt.plot(data['x'], data['y'])
            plt.xlabel(data['xlabel'])
            plt.ylabel(data['ylabel'])
            plt.title(data['title'])
            plt.legend(data['legend'])

        :param x_axis: axis name or expression as given in self.map
        :param y_axis: axis name or expression as given in self.map
        :param z_axis: axis name or expression as given in self.map
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
            x_data, x_lab = self._get_plot_axis(hdf, x_axis or 'axes', reduce_shape=True, flatten=True)

            y_data, y_labs = [], []
            y_axis = y_axis or [None]
            for n, _y_axis in enumerate(y_axis):
                _y_data, _y_lab = self._get_plot_axis(hdf, _y_axis or f"signal{n}", reduce_shape=True, flatten=True)
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
                z_data, z_lab = self._get_plot_axis(hdf, z_axis, reduce_shape=True, flatten=True)
                additional['zdata'] = z_data
                additional['zlabel'] = z_lab
            # 2+D data
            shape = self.map.scannables_shape()
            if len(shape) >= 2:
                x_data = x_data.reshape(shape)
                y_data, y_lab = self._get_plot_axis(hdf, y_axis[0] or 'axes1')
                z_data, z_lab = self._get_plot_axis(hdf,
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

    def xas_spectra(self, sample_name: str | None = None, element_edge: str | None = None, mode: str | list[str] = 'all',
                    dls_loader: bool = False) -> SpectraContainer:
        """
        Load XAS Spectra from the scan file

            >>> spectra = scan.xas_spectra()
            >>> spectra = spectra.remove_background('slope')
            >>> spectra.plot()

        :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
        :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
        :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
        :param dls_loader: bool, if True uses explicit loading of metadata from DLS MMG beamlines
        :return: SpectraContainer
        """
        return load_xas_scans(self.filename, sample_name=sample_name, element_edge=element_edge,
                              mode=mode, dls_loader=dls_loader, hdfmap=self.map)[0]

    def instrument_model(self) -> NXInstrumentModel:
        """Build and instrument model from NeXus file"""
        with self.load_hdf() as hdf:
            return NXInstrumentModel(hdf)

    def copy_file(self, new_filename: str, merge_links: bool = False, copy_linked_files: bool = False,
                  merge_compression: str = 'gzip'):
        """
        Copy NeXus file to a new location, also copy the linked files
        :param new_filename: new filename
        :param merge_links: if True, copies any data from externally linked data files into the new file
        :param copy_linked_files: if True, copies linked files to keep the same relative path.
        :param merge_compression: compression algorithm for merged datasets, default is 'gzip'
        :return: None
        """
        links = self.map.find_links()
        with h5py.File(new_filename, 'w') as new_file, h5py.File(self.filename) as old_file:
            for name, obj in old_file.items():
                old_file.copy(name, new_file, name)

            for link_path, link_filename in links.items():
                if link_path in old_file:
                    old_obj = old_file[link_path]
                    link = old_file.get(link_path, getlink=True)
                    if isinstance(link, h5py.ExternalLink):
                        if merge_links:
                            del new_file[link_path]
                            dataset = new_file.create_dataset(link_path, data=old_obj[()],
                                                              compression=merge_compression, compression_opts=7)
                            dataset.attrs.update(old_obj.attrs)
                        elif copy_linked_files:
                            if not os.path.isabs(link_filename):
                                old_link_filename = os.path.join(os.path.dirname(self.filename), link_filename)
                                new_link_filename = os.path.join(os.path.dirname(new_filename), link_filename)
                                if os.path.isfile(old_link_filename):
                                    from shutil import copyfile
                                    copyfile(old_link_filename, new_link_filename)
                                    print(f"Copied '{new_link_filename}'.")
                                else:
                                    print(f"Linked file {old_link_filename} does not exist")
                            else:
                                print(f"Linked file '{link_filename}' has absolute path, skipping")
                        else:
                            # check link works
                            if new_file.get(link_path) is None:
                                print(f"Warning: path '{link_path}' can't find external file '{link.filename}'.",
                                      "use copy_file(..., merge_links=True) instead.")

    def save(self, filename: str):
        """Save object as HDF5 file"""
        from mmg_toolbox import __version__
        date = str(datetime.datetime.now())

        # Write new file
        with h5py.File(filename, 'w') as f:
            nw.add_entry_links(f, self.filename)
            entry = nw.add_nxentry(f, 'NexusScan', default=False)
            # Filename
            nw.add_nxfield(entry, 'filename', self.filename)
            # LocalData
            nw.add_nxprocess(
                root=entry,
                name='local_data',
                program='mmg_toolbox.nexus.nexus_scan',
                version=__version__,
                date=date,
                **self._local_data  # save local_data as NXparameters
            )
            nw.add_nxnote(
                root=entry,
                name='config',
                description='NexusScan configuration',
                data=self.config,
            )
            nw.add_nxnote(
                root=entry,
                name='hdfmap',
                description='HdfMap json blob',
                data=self.map.generate_json_str()
            )

    def load_local_data(self):
        """If the scan file contains previously saved NexusScan information, the local data and config will be loaded."""

        with self.load_hdf() as hdf:
            orig_filename, hdf_map, local_data, config = _load_local_data(hdf)

        self.__init__(orig_filename, hdf_map, config=config)
        self.add_local(**local_data)

    def save_nxdata(self, root: h5py.Group, name: str = 'data', x_axis: str | None = None, *y_axis: str | None,
                    z_axis: str | None = None, default: bool = False):
        """Save scan data as NXdata group"""
        plot_data = self.get_plot_data(x_axis, *y_axis, z_axis=z_axis)
        nx_data = nw.add_nxdata(
            root=root,
            name=name,
            axes=plot_data['axes_names'],
            signal=plot_data['signal_names'][0],
            default=default
        )
        for name, data in zip(plot_data['axes_names'], plot_data['axes_data']):
            nw.add_nxfield(nx_data, name, data)
        for name, data in zip(plot_data['signal_names'], plot_data['signal_data']):
            nw.add_nxfield(nx_data, name, data)

    def save_csv(self, filename: str, *scannables: str):
        """Save axes and signal as CSV file"""
        # Load scannables data
        names = (self.replace_default_names(scannable) for scannable in scannables)
        header = '# mmg_toolbox.nexus.nexus_scan\n'
        header += '# ' + ', '.join(names)
        scannable_arrays = self.eval(','.join(scannables))
        array_len = max(len(array) for array in scannable_arrays)
        scannable_arrays = [
            np.tile(array, array_len) if array.size == 1 else array
            for array in scannable_arrays
        ]
        with open(filename, 'w') as f:
            f.write(header)
            f.write('\n')
            for values in zip(*scannable_arrays):
                f.write(', '.join(map(str, values)))
                f.write('\n')


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

    def __init__(self, filename: str, hdf_map: NexusMap | None = None, flatten_scannables: bool = True,
                 config: dict | None = None):
        NexusScan.__init__(self, filename, hdf_map, config)

        with load_hdf(filename) as hdf:
            metadata = self.map.get_metadata(hdf)
            scannables = self.map.get_scannables(hdf, flatten=flatten_scannables)
        DataHolder.__init__(self, **scannables)
        self.metadata = DataHolder(**metadata)

    def __repr__(self):
        return f"NexusDataHolder('{self.filename}')"


def _load_local_data(hdf: h5py.File) -> tuple[str, NexusMap, dict, dict]:
    """Load saved data from Nexus file saved by NexusScan.save"""
    def h5value(ds):
        return ds.asstr()[()] if h5py.check_string_dtype(ds.dtype) else ds[()]

    nexus_scan_entry = hdf.get('NexusScan', None)
    if nexus_scan_entry is None:
        print(f"File {hdf.filename} does not contain a NexusScan entry")
        return "", NexusMap(), {}, {}
    orig_filename = str(h5value(nexus_scan_entry.get('filename')))
    hdfmap_json = nexus_scan_entry['hdfmap/data'].asstr()[()]
    hdf_map = NexusMap(hdfmap_json)
    local_data = {name: h5value(ds) for name, ds in nexus_scan_entry['local_data/parameters'].items()}
    config = json.loads(h5value(nexus_scan_entry.get('config/data')))
    return orig_filename, hdf_map, local_data, config


def load_nexus_scan(filename: str) -> NexusScan:
    """Loads a NexusScan object from a NeXus file, if it includes the NexusScan entry"""
    with load_hdf(filename) as hdf:
        if 'NexusScan' not in hdf:
            print(f"File {filename} does not contain a NexusScan entry, loading NexusScan as normal")
            hdf_map = NexusMap(hdf)  # save re-opening the file
            return NexusScan(filename, hdf_map)

        orig_filename, hdf_map, local_data, config = _load_local_data(hdf)

    # create NexusScan
    nexus_scan = NexusScan(orig_filename, hdf_map, config=config)
    nexus_scan.add_local(**local_data)
    return nexus_scan

