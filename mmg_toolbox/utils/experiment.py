"""
Experiment Folder Monitor
"""

import os
import numpy as np
import hdfmap

from ..utils.misc_functions import numbers2string
from ..utils.env_functions import scan_number_mapping, last_folder_update, get_beamline_from_directory
from ..beamline_metadata.config import beamline_config, C
from ..nexus.nexus_scan import NexusScan, NexusDataHolder
from ..nexus.nexus_reader import find_scans
from ..xas import load_xas_scans, SpectraContainer


class Experiment:
    """
    Experiment class
    Monitors data folders for scan files and provies a
    convenient way to load scan data using only a scan number.

    E.G.
        from mmg_toolbox import Experiment
        exp = Experiment('path/to/folder1', 'path/to/folder2', instrument='i06')
        print(scan)
        scan = exp.scan(-1)  # latest scan
        scan_list = exp.scans(*range(12345, 12355))
        data = exp.join_scan_data(*range(-100, 0), data_fields=['cmd', 'Ta'])  # returns dict of arrays

    :param folder_paths: file directories containing .nxs files
    :param instrument: instrument name for configuration.
    """

    def __init__(self, *folder_paths: str, instrument: str | None = None):
        self.folder_paths = folder_paths
        self.scan_list = {}
        self._scan_list_update = None
        self.instrument = instrument or get_beamline_from_directory(folder_paths[0], None)
        self.config = beamline_config(self.instrument)
        from ..plotting.exp_plot_manager import ExperimentPlotManager
        self.plot = ExperimentPlotManager(self)

    def __repr__(self):
        paths = ', '.join(f"'{p}'" for p in self.folder_paths)
        return f"Experiment({paths}, instrument={self.instrument})"

    def __str__(self):
        self._update_scan_list()
        scan_numbers = self._scan_numbers()
        lines = ['Instrument: ' + self.instrument]
        lines.extend(self.folder_paths)
        if scan_numbers:
            lines.extend([
                f"    Files: {len(scan_numbers)}",
                f"    Scans: {scan_numbers[0]}-{scan_numbers[-1]}",
            ])
        else:
            lines.extend(["  No NeXus files found."])
        return '\n'.join(lines)

    def __getitem__(self, item: int | slice) -> NexusScan | list[NexusScan]:
        if isinstance(item, slice):
            scan_numbers = self.all_scan_numbers()[item]
            return self.scans(*scan_numbers)
        else:
            scan_numbers = self.all_scan_numbers()[item]
            return self.scans(scan_numbers)[0]

    def __len__(self) -> int:
        return len(self.all_scan_numbers())

    def _update_scan_list(self):
        mod_times = [last_folder_update(folder) for folder in self.folder_paths]
        folders = [
            folder for folder, time in zip(self.folder_paths, mod_times)
            if self._scan_list_update is None or time > self._scan_list_update
        ]
        self._scan_list_update = max(mod_times)  # datetime.now()?
        self.scan_list.update(scan_number_mapping(*folders))

    def _scan_numbers(self) -> list[int]:
        self._update_scan_list()
        return list(self.scan_list.keys())

    def add_data_paths(self, *folder_paths: str):
        """Add additional paths"""
        new_paths = tuple(
            path for path in folder_paths
            if path not in self.folder_paths and os.path.isdir(path)
        )
        self.folder_paths = self.folder_paths + new_paths
        self._update_scan_list()

    def all_scans(self) -> dict[int, str]:
        self._update_scan_list()
        return self.scan_list.copy()

    def all_scan_numbers(self) -> list[int]:
        self._update_scan_list()
        return list(self.scan_list.keys())

    def all_scan_files(self) -> list[str]:
        self._update_scan_list()
        return list(self.scan_list.values())

    def get_scan_filename(self, scan_file: int | str = -1) -> str:
        """Return the full filename of a scan number"""
        if isinstance(scan_file, int):
            if scan_file < 1:
                scan_numbers = self._scan_numbers()
                return self.scan_list[scan_numbers[scan_file]]
            self._update_scan_list()
            return self.scan_list[scan_file]

        if os.path.isfile(scan_file):
            return os.path.abspath(scan_file)
        raise FileNotFoundError(f"scan file {scan_file} not found")

    def scan(self, scan_file: int | str = -1) -> NexusDataHolder:
        """read Nexus file as NexusDataHolder"""
        return NexusDataHolder(self.get_scan_filename(scan_file), config=self.config)

    def scans(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None) -> list[NexusScan]:
        """Read Nexus files as lazy NexusScan. All files use the same HdfMap, based on the first scan"""
        filenames = [self.get_scan_filename(scan_file) for scan_file in scan_files]
        if not filenames:
            filenames = list(self.all_scans().values())
        if filenames and hdf_map is None:
            hdf_map = hdfmap.create_nexus_map(filenames[0])
        return [NexusScan(file, hdf_map, config=self.config) for file in filenames]

    def find_scans(self, *scan_files: int | str,  hdf_map: hdfmap.NexusMap | None = None, first_only: bool = False,
                   **matches: str | float | tuple[float, float]) -> list[NexusScan]:
        """
        Find scans files with matching metadata

            matches = {
                'name1': 'scan', # matches if 'scan' in file['name1']
                'name2': value, # matches if file['name2'] ~= value
                'name3': (value, tol), # matches if abs(file['name3'] - value) < tol
            }
            match_files = find_scans(*filenames, **matches)

        :param scan_files: set of scan numbers or filenames, if not given will search all scans in folder.
        :param hdf_map: if given, uses this hdfmap rather than generating one.
        :param first_only: if true, returns on the first result
        :param matches: keyword arguments for matching parameters
        :returns: list of scan files that match all requirements
        """
        filenames = [self.get_scan_filename(scan_file) for scan_file in scan_files]
        if not filenames:
            filenames = list(self.all_scans().values())
        if hdf_map is None:
            hdf_map = hdfmap.create_nexus_map(filenames[0])
        matches = find_scans(*filenames, hdf_map=hdf_map, first_only=first_only, **matches)
        return self.scans(*matches, hdf_map=hdf_map)

    def join_scan_data(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                       data_fields: list[str] | None = None, default: np.ndarray = np.array([0.0])) -> dict[str, list]:
        """
        Join data from scans
        """
        scans = self.scans(*scan_files, hdf_map=hdf_map)
        data_fields = [self.config[C.scan_description]] if data_fields is None else data_fields
        data = {name: [] for name in data_fields}
        for scan in scans:
            with scan.load_hdf() as hdf:
                for name in data_fields:
                    data[name].append(scan.map.eval(hdf, name, default=default))
        return data

    def get_all_data(self, *fields: str, default: np.ndarray = np.array([0.0])) -> dict[str, list]:
        """
        Return dict of data for all files
        """
        return self.join_scan_data(data_fields=list(fields), default=default)

    def generate_mesh(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                      axes: str | tuple[str, str] = 'axes', signal: str = 'axes',
                      values: str | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate 2D mesh from scan or scans

            x, y, z = generate_mesh(*range(-10, 0), axes='eta', signal='roi2_sum', values='Tsample')
            # or, if scan 12345 is a 2D grid scan
            x, y, z = generate_mesh(12345, axes=('sx', 'sy'), signal='roi2_sum')

        :param scan_files: multiple files or single 2D grid scan
        :param hdf_map: hdfmap.NeXus map, or None to generate
        :param axes: x-axis name, or for grid scans the names of ('xaxis', 'yaxis')
        :param signal: signal name
        :param values: name of the value that changes between multiple files
        :returns: X, Y, IMAGE rank 2 arrays
        """
        scans = self.scans(*scan_files, hdf_map=hdf_map)
        if len(scan_files) == 1:
            # Single 2D Grid scan
            scan = scans[0]
            try:
                x_axis, y_axis = axes
            except ValueError:
                raise Exception("axes should be specified as axes=('axes0', 'axes1')")
            with scan.load_hdf() as hdf:
                x_data = scan.map.eval(hdf, x_axis, default=0.0).squeeze()
                y_data = scan.map.eval(hdf, y_axis, default=0.0).squeeze()
                z_data = scan.map.eval(hdf, signal, default=0.0).squeeze()
            if x_data.size != y_data.size:
                raise Exception(f"arrays '{x_axis}'[{x_data.size}] and '{y_axis}'[{y_data.size}] have different sizes")
            if x_data.ndim == 1 and y_data.ndim == 1:
                y_data, x_data = np.meshgrid(y_data, x_data)
            if z_data.shape != x_data.shape or z_data.shape != y_data.shape:
                raise Exception(
                    f"{repr(scan)} '{x_axis}', '{y_axis}' and '{signal}' shapes are not consistent: " +
                    f"x: {x_data.shape}, y: {y_data.shape}, im: {z_data.shape}"
                )
            return x_data, y_data, z_data
        else:
            x_data, y_data, z_data = [], [], []
            for n, scan in enumerate(scans):
                with scan.load_hdf() as hdf:
                    x = np.reshape(scan.map.eval(hdf, axes, default=0.0), -1)
                    y = np.reshape(scan.map.eval(hdf, signal, default=0.0), -1)
                    val = np.reshape(scan.map.eval(hdf, values, default=0.0), -1) if values is not None else np.array([n])
                if val.size == 1:
                    val = np.tile(val, x.size)
                if y.size != x.size or val.size != x.size:
                    raise Exception(
                        f"{repr(scan)} '{axes}', '{signal}' and '{values}' shapes are not consistent: " +
                        f"x, y, val = ({x.size}, {y.size}, {val.size})"
                    )
                x_data.append(x)
                y_data.append(val)
                z_data.append(y)
            # create a regular sized array
            min_len = min(len(x) for x in x_data)
            # array size [len(scan_files), min_len]
            x_array = np.array([x[:min_len] for x in x_data])
            y_array = np.array([y[:min_len] for y in y_data])
            z_array = np.array([z[:min_len] for z in z_data])
            return x_array, y_array, z_array

    def scan_str(self, scan_file: int | str = 0, metadata_str: str | None = None,
                 hdf_map: hdfmap.NexusMap | None = None) -> str:
        """Read scan file and return metadata string"""
        if metadata_str is None:
            from ..tkguis.misc.beamline_metadata import META_STRING, BEAMLINE_META
            if self.instrument in BEAMLINE_META:
                metadata_str = BEAMLINE_META[self.instrument]
            else:
                metadata_str = META_STRING

        scan_file = self.get_scan_filename(scan_file)

        if hdf_map is None:
            hdf_map = hdfmap.create_nexus_map(scan_file)

        with hdfmap.load_hdf(self.get_scan_filename(scan_file)) as hdf:
            return hdf_map.format_hdf(hdf, metadata_str, raise_errors=True)

    def scans_str(self, *scan_files: int | str, metadata_str: str | None = None,
                  hdf_map: hdfmap.NexusMap | None = None) -> list[str]:
        """Return string description for multiple files"""
        if metadata_str is None:
            metadata_str = " : {str(start_time):30} : " + self.config[C.scan_description]
        filenames = [self.get_scan_filename(scan_file) for scan_file in scan_files]
        if hdf_map is None:
            hdf_map = hdfmap.create_nexus_map(filenames[0])
        folder_file = ['/'.join(filename.split(os.sep)[-2:]) for filename in filenames]
        return [
            name + self.scan_str(file, metadata_str, hdf_map)
            for file, name in zip(filenames, folder_file)
        ]

    def _generate_scans_title(self, *scans: NexusScan, metadata_str: str | None = None) -> str:
        """Generate title from multiple scan files"""
        if metadata_str is None:
            metadata_str = "\n" + self.config[C.scan_description]
        first_scan = scans[0]
        folder = first_scan.filename.split(os.sep)[-2]
        meta = first_scan.format(metadata_str)
        scan_numbers = [scan.scan_number() for scan in scans]
        number_range = numbers2string(scan_numbers)
        return f"{folder} {number_range} {meta}"

    def generate_scans_title(self, *scan_files: int | str, metadata_str: str | None = None,
                             hdf_map: hdfmap.NexusMap | None = None) -> str:
        """Generate title from multiple scan files"""
        scans = self.scans(*scan_files, hdf_map=hdf_map)
        return self._generate_scans_title(*scans, metadata_str=metadata_str)

    def load_xas(self, *scan_files: int | str, sample_name: str | None = '') -> list[SpectraContainer]:
        """Read XAS spectra containers"""
        filenames = [self.get_scan_filename(file) for file in scan_files]
        return load_xas_scans(*filenames, sample_name=sample_name)

