"""
{{title}}
{{description}}
"""

import matplotlib.pyplot as plt
from mmg_toolbox import data_file_reader

filenames = [
    {{filepaths}}
]

fig, ax = plt.subplots()

for file in filenames:
    scan = data_file_reader(file, '{{beamline}}')
    data = scan.get_plot_data('{{x-axis}}', '{{y-axis}}')
    label = scan.label()
    ax.plot(data['xdata'], data['ydata'], label=label)

ax.set_xlabel(data['xlabel'])
ax.set_ylabel(data['ylabel'])
ax.set_title(data['title'])

plt.show()
