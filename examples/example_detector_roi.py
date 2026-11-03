"""
mmg_toolbox example
Example script using the Experiment class to get files from data folders
"""

import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment, data_file_reader

# Example 1: Single File
scan = data_file_reader('/dls/science/groups/das/ExampleData/i16/2dscans_2026/1144250.nxs')

# Define ROI
# scans with the pilatus have shape (n, i, j), where n in the number of points,
# i is the fast (short) axis and j is the slow (long axis)
# see help(scan.map.add_roi)
scan.map.add_roi(
    name='nroi1',
    cen_i='pil3_centre_j',  # pil3_centre_j is a value inside the NeXus file defining the detector centre
    cen_j='pil3_centre_i',  # can also be given as integers
    wid_i=80,
    wid_j=20,
    image_name='pil3_100k'  # detector name, use 'IMAGE' if you're not sure.
)

# 'nroi1' defines a set of parameters in the scan object, accessible the the eval interface
roi_total, roi_max, roi_min, roi_mean = scan('nroi1_total, nroi1_max, nroi1_min, nroi1_mean')
roi_bkg, roi_rmbkg = scan('nroi1_bkg, nroi1_rmbkg')  # background definition and removal from nroi1
roi_box, roi_bkg_box = scan('nroi1_box, nroi1_bkg_box')  # coordinates of the box
roi_volume = scan('nroi1')  # returns (n,80,20) array
print(f"roi_total: {roi_total.shape}")
print(f"roi_volume: {roi_volume.shape}")

# Plot the ROI on an image
fig1, ax = plt.subplots(figsize=(12, 4), dpi=100)
ax = scan.plot.image(index=None, log=True, colorbar=True, axes=ax)
ax.plot(roi_box[:, 1], roi_box[:, 0], 'w-', lw=2, label='nroi1')
ax.plot(roi_bkg_box[:, 1], roi_bkg_box[:, 0], 'r-', lw=1, label='nroi1_bkg')
ax.legend()

# Plot the scan
ax = scan.plot.plot('axes', ['nroi1_total', 'nroi1_bkg', 'nroi1_rmbkg'])
plt.show()

# Example 2: Multiple Files
exp = Experiment('/dls/science/groups/das/ExampleData/i16/2dscans_2026/1144250.nxs')

# add ROI to all scans
exp.add_roi('nroi1', 'pil3_centre_j', 'pil3_centre_i+20', 100, 30)
exp.add_roi('nroi2', 'pil3_centre_j', 'pil3_centre_i-20', 100, 30)

# Load ROI values
scan, = exp.scans(1144250)
roi1_total, roi2_total = scan('nroi1_total, nroi2_total')

# Plot ROI values for range of scans
fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=100)
exp.plot.multi_lines(*range(1144250, 1144260), yaxis='nroi1_total / Transmission', value='sx', axes=ax1)
exp.plot.multi_lines(*range(1144250, 1144260), yaxis='nroi2_total / Transmission', value='sx', axes=ax2)
fig2.tight_layout()
plt.show()