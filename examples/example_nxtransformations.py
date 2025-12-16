"""
Example file reading NXtransformation chains from a NeXus file
"""

import matplotlib.pyplot as plt
from mmg_toolbox import data_file_reader
from mmg_toolbox.nexus.nexus_transformations import generate_nxtranformations_string

# filename = 'i16_12345.nxs'
filename = '/dls/i16/data/2025/nt43883-1/1112922.nxs'
# filename = '/dls/i16/data/2025/mm41697-1/1116348.nxs'

print(generate_nxtranformations_string(filename))

scan = data_file_reader(filename)

instrument = scan.instrument_model()

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
instrument.plot_wavevectors(ax)

plt.show()