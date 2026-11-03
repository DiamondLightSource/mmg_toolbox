"""
mmg_toolbox example
Example script using the Experiment class to get files from data folders
"""

import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

datadir1 = '/dls/science/groups/das/ExampleData/i16/azimuths'
datadir2 = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/cm37262-1'
exp = Experiment(datadir1, datadir2)
all_scan_nos = exp.all_scan_numbers()

# Print information - all scans
print('\n'.join(exp.scans_str(*all_scan_nos)))
# single scan
print(exp.scan_str(-1))  # -1 is a shortcut for the latest scan, 0 is the first scan

# Load scans
scan = exp.scan(1032510)  # NexusDataHolder object (loads data)
print(repr(scan))
scan1, scan2, scan3 = exp.scans(*range(-3, 0))  # NexusScan object (lazy loader)

# Search for scans
scan_nos = exp.get_nearby_scan_numbers(1032510)
scans = exp.find_scans(*scan_nos, **{'_cmd': 'scan energy'})

# Find values that change between scans
values = exp.get_value_changes(*scan_nos)
print('\n'.join(f"{name} : {np.std(array):.2f}" for name, array in values.items()))


# Plotting
rng = range(1032510, 1032521)
# exp.plot(*rng)
exp.plot.surface_3d(*rng)

exp.plot(1108746, 1108747, 1108748)

exp.plot.detail(-1)

exp.plot.surface_2d(*all_scan_nos[:5], xaxis='eta_fly', signal='signal', values='psi')
exp.plot.surface_3d(*all_scan_nos[:5], xaxis='eta_fly', signal='signal', values='psi')

exp.plot.lines_3d(*all_scan_nos[:5], xaxis='eta_fly', signal='signal', values='psi')

plt.show()
