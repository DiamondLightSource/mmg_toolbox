import os

from hdfmap import load_hdf, create_nexus_map

from mmg_toolbox.nexus.nexus_scan import NexusDataHolder, NexusScan
from mmg_toolbox.utils.file_functions import get_scan_number, replace_scan_number


def read_nexus_file(filename: str, flatten_scannables: bool = True) -> NexusDataHolder:
    """
    Read Nexus file as DataHolder
    """
    return NexusDataHolder(filename, flatten_scannables=flatten_scannables)


def read_nexus_files(*filenames: str) -> list[NexusScan]:
    """
    Read Nexus files as NexusScan
    """
    hdf_map = create_nexus_map(filenames[0])
    return [NexusScan(f, hdf_map) for f in filenames]


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

