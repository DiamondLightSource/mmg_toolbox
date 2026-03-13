"""
mmg_toolbox example
Example script to read XAS scans from i06 or i10
"""

import hdfmap
import matplotlib.pyplot as plt
from mmg_toolbox import data_file_reader


filename = '/dls/science/groups/das/ExampleData/hdfmap_tests/i06/i06-1-372210.nxs'

scan =  data_file_reader(filename)
spectra = scan.xas_spectra(dls_loader=True, mode='tey')

print(scan)
print(spectra)

spectra = spectra.trim(ev_from_start=2., ev_from_end=None)
norm = spectra.divide_by_preedge(ev_from_start=5)
rembk = norm.remove_background('exp')
# rembk = norm.auto_edge_background()

# Plot Spectra and background
rembk.create_background_figure()

# Print processes
print(rembk)

# Save Nexus file
rembk.write_nexus('output_xas.nxs')

print('\n\n######################### output_xas.nxs ###################################')
print(hdfmap.hdf_tree_string('output_xas.nxs'))

plt.show()