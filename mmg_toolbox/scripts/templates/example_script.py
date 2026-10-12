"""
{{title}}
{{description}}
"""

import matplotlib.pyplot as plt
import hdfmap

filenames = [
    {{filepaths}}
]

fig, ax = plt.subplots()

for file in filenames:
    m = hdfmap.NexusMap()
    with hdfmap.load_hdf(file) as nxs:
        m.populate(nxs)
        data = m.get_plot_data(nxs)
        label = m.format_hdf(nxs, "{filename}: {__axes}")
    ax.plot(data['xdata'], data['ydata'], label=label)

ax.set_xlabel(data['xlabel'])
ax.set_ylabel(data['ylabel'])
ax.set_title(data['title'])

plt.show()
