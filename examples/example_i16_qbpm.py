"""
mmg_toolbox example
Example script to read QBPM6 scans from i16 for phase plate offsets
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment
from mmg_toolbox.misc.phase_plates import scan_phaseplate_normalisation


data_dir = '/dls/i16/data/2026/mm43750-1'
scan_number = 1146049

exp = Experiment(data_dir, instrument='i16')
exp.plot.set_plot_defaults()

scan, = exp.scans(scan_number)

neg, pos, avmid, posoff = scan_phaseplate_normalisation(
    scan=scan,
    x_data='axes',
    sigma_data='(C1+C3)/2',
    pi_data='(C2+C4)/2',
    monitor='ic1monitor',
    normalise_type='left',
    show_difference=False,
    plot=True
)

plt.show()

