"""
Show plots
"""

import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D

from mmg_toolbox import Experiment, data_file_reader
from tests.example_files import DIR, FILES_DICT

exp = Experiment(DIR + '/i16/cm37262-1', instrument='i16')

ax = exp.plot(-1)

rng = range(1032510, 1032521)
exp.plot(*rng)

fig_ax = exp.plot.multi_plot(*rng)

exp.plot.surface_2d(*rng)
exp.plot.lines_3d(*rng)
exp.plot.surface_3d(*rng)

plt.show()

# Old file types
scan = data_file_reader(FILES_DICT['i16 pilatus eta scan, tiff files, no defaults'])
scan.plot()

scan = data_file_reader(FILES_DICT['i16 pilatus eta scan, old nexus format'])
scan.plot()

scan = data_file_reader(FILES_DICT['i16 pilatus hkl scan, new nexus format'])
scan.plot()

plt.show()

# Plotting methods
scan = data_file_reader(FILES_DICT['i16 pilatus hkl scan, new nexus format'])
scan.plot.plot('axes', 'signal')

scan = data_file_reader(FILES_DICT['i10 pimte new scan'])
scan.plot.image()

scan = data_file_reader(FILES_DICT['i16 merlin 2d delta gam calibration'])
scan.plot.map2d('delta', 'gamma')

plt.show()