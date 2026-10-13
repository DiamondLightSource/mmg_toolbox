"""
{{title}}
{{description}}
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

data_dir = '{{experiment_dir}}'
scan_numbers = {{scan_numbers}}

exp = Experiment(data_dir, instrument='{{beamline}}')
exp.plot.set_plot_defaults()

fig, ax = plt.subplots()
exp.plot.multi_lines(
    *scan_numbers,
    xaxis='{{x-axis}}',
    yaxis='{{y-axis}}',
    value='{{value}}',
    axes=ax
)

plt.show()
