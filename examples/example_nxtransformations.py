"""
Example file reading NXtransformation chains from a NeXus file
"""

import hdfmap
from mmg_toolbox.nexus_functions import nx_find_all
from mmg_toolbox.nexus_transformations import generate_nxtranformations_string

# filename = 'i16_12345.nxs'
filename = '/dls/i16/data/2025/nt43883-1/1112922.nxs'

print(generate_nxtranformations_string(filename))
