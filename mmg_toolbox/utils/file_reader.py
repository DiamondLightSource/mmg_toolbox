"""
Automatic data file reader
"""

from mmg_toolbox.utils.misc_functions import DataHolder
from mmg_toolbox.utils.dat_file_reader import read_dat_file
from mmg_toolbox.nexus.nexus_reader import read_nexus_file


def data_file_reader(filename: str) -> DataHolder:
    """
    Read Nexus or dat file as DataHolder
    """
    if filename.endswith('.dat'):
        return read_dat_file(filename)
    return read_nexus_file(filename)
