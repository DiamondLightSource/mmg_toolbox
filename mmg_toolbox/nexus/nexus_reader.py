import os

from mmg_toolbox.beamline_metadata.config import beamline_config
import hdfmap
from hdfmap import load_hdf, create_nexus_map

from mmg_toolbox.nexus.nexus_scan import NexusDataHolder, NexusScan
from mmg_toolbox.utils.file_functions import get_scan_number, replace_scan_number


def read_nexus_file(filename: str, flatten_scannables: bool = True, beamline: str | None = None) -> NexusDataHolder:
    """
    Read Nexus file as DataHolder
    """
    config = beamline_config(beamline)
    return NexusDataHolder(filename, flatten_scannables=flatten_scannables, config=config)


def read_nexus_files(*filenames: str, beamline: str | None = None) -> list[NexusScan]:
    """
    Read Nexus files as NexusScan
    """
    hdf_map = create_nexus_map(filenames[0])
    config = beamline_config(beamline)
    return [NexusScan(f, hdf_map, config=config) for f in filenames]


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


def find_similar_scans(filename: str, *files: str, metadata: list[str | tuple[str, float]]) -> list[str]:
    """
    Find scan files with similar metadata

        metadata = [
            'name',  # match scans with file2['name'] == file1['name']
            ('name', tol)  # match scans with abs(file2['name'] - file1['name']) < tol
        ]
        match_files = find_similar_scans(*filenames, metadata=metadata)

    :param filename: nexus scan file to compare others with
    :praam files: list of additional nexus files
    :param metadata: list of nexus metadata fields to compare
    :returns: list of scan files that match all requirements
    """
    nexus_map = create_nexus_map(filename)
    names = [n if isinstance(n, str) else n[0] for n in metadata]
    with hdfmap.load_hdf(filename) as hdf:
        initial_parameters = [
            nexus_map.eval(hdf, name)
            for name in names
        ]
    similar_files = []
    for file in files:
        if file == filename:
            continue
        with hdfmap.load_hdf(file) as hdf:
            new_parameters = [
                nexus_map.eval(hdf, name)
                for name in names
            ]
        match = all(
            ini == new if isinstance(par, str) else abs(ini - new) < par[1]
            for par, ini, new in zip(metadata, initial_parameters, new_parameters)
        )
        if match:
            similar_files.append(file)
    return similar_files


def find_scans(filename: str, *files: str, hdf_map: hdfmap.NexusMap | None = None, first_only: bool = False,
               **matches: str | float | tuple[float, float]) -> list[str]:
    """
    Find scans files with matching parameters

        matches = {
            'name1': 'scan', # matches if 'scan' in file['name1']
            'name2': value, # matches if file['name2'] ~= value
            'name3': (value, tol), # matches if abs(file['name3'] - value) < tol
        }
        match_files = find_scans(*filenames, **matches)

    :param filename: nexus filename (used to create hdfmap)
    :param files: list of additional nexus files
    :param hdf_map: if given, uses this hdfmap rather than generating one.
    :param first_only: if true, returns on the first result
    :param matches: keyword arguments for matching parameters
    :returns: list of scan files that match all requirements
    """
    nexus_map = hdf_map or create_nexus_map(filename)
    matching_files = []
    for file in (filename,) + files:
        with hdfmap.load_hdf(file) as hdf:
            all_ok = True
            for name, match_value in matches.items():
                file_value = nexus_map.eval(hdf, name)
                if isinstance(match_value, str):
                    chk = match_value in file_value
                elif isinstance(match_value, (float, int)):
                    chk = abs(match_value - file_value) < 0.01
                else:
                    chk = abs(match_value[0] - file_value) < match_value[1]
                if not chk:
                    all_ok = False
                    break
        if all_ok:
            matching_files.append(file)
            if first_only:
                break
    return matching_files

