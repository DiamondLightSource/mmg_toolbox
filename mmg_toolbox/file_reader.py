"""
Automatic data file reader
"""

from mmg_toolbox.misc_functions import DataHolder
from mmg_toolbox.dat_file_reader import read_dat_file
from mmg_toolbox.nexus_reader import read_nexus_file


def data_file_reader(filename: str) -> DataHolder:
    """
    Read Nexus or dat file as DataHolder
    """
    if filename.endswith('.dat'):
        return read_dat_file(filename)
    return read_nexus_file(filename)
