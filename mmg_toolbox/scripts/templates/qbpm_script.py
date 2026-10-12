"""
{{title}}
{{description}}

Determination of phase plate offsets using QBPM6 device
{{date}}
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment
from mmg_toolbox.misc.phase_plates import scan_phaseplate_normalisation


data_dir = '{{experiment_dir}}'
scan_number = {{scan_number}}

exp = Experiment(data_dir, instrument='{{beamline}}')
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
