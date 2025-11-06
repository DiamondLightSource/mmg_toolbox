"""
mmg_toolbox example
Example script using the Experiment class to get files from data folders
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

datadir = '/dls/science/groups/das/ExampleData/i16/azimuths'
datadir = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/cm37262-1'
exp = Experiment(datadir)
all_scans = exp.all_scan_numbers()

# print('\n'.join(exp.scans_str(*exp.all_scans().values())))

rng = range(1032510, 1032521)
# exp.plot(*rng)
exp.plot.surface_3d(*rng)

# exp.plot(1108746, 1108747, 1108748)

# exp.plot.detail(-1)

# exp.plot.surface_2d(*all_scans[:5], xaxis='eta_fly', signal='signal', values='psi')
# exp.plot.surface_3d(*all_scans[:5], xaxis='eta_fly', signal='signal', values='psi')

#exp.plot.lines_3d(*all_scans[:5], xaxis='eta_fly', signal='signal', values='psi')

plt.show()
