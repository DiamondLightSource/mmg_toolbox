"""
mmg_toolbox example
Example script to load multiple files from a 2D grid scan
"""

import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment


exp = Experiment('/dls/science/groups/das/ExampleData/i16/2dscans_2026/', instrument='i16')

# Add custom ROI
exp.add_roi('new_roi', cen_i=110, cen_j=240, wid_i=100, wid_j=60, image_name='pil3_100k')

scan_numbers = range(1144247, 1144272)
scans = exp.scans(*scan_numbers)
ttl = exp.generate_scans_title(*scan_numbers)

print(scans[10].map.image_data)
scans[10].plot.image(rois=True, log=True)
plt.show()

# Generate 2D mesh from scans in sx, sy
xx, yy, image = exp.generate_mesh(*scans, signal='max(new_roi_total)', values=('sx', 'sy'))

plt.figure()
plt.pcolormesh(xx, yy, image, shading='nearest')  # use shading='gouraud' for interpolation
plt.axis('image')
cb = plt.colorbar(label='Intensity')
plt.xlabel('sx')
plt.ylabel('sy')
plt.title(ttl)
plt.tight_layout()
plt.show()


# Perform fits
for scan in scans:
    # Multi-peak fit on each scan
    result = scan.fit.multi_peak_fit(
        xaxis='axes',  # default scan axes
        yaxis='new_roi_total / Transmission / (rc / 300)',  # 'signal',  # default scan values
        npeaks=None,  # determine the number of peaks automatically
        min_peak_power=None,
        peak_distance_idx=6,
        model='Gaussian',
        background='Slope',
        plot_result=False  #  set True to make see fit plots
    )
    # the result object contains all the fit data, but this is also stored in the scan namespace
    print(scan.format('{scan_number}: sx={sx:.2f}, sy={sy:.2f}, amplitude={amplitude:.0f}, centre={center:.2f}, fwhm={fwhm:.2g}'),)

# Generate 2D mesh from scans in sx, sy using fit data
xx, yy, image = exp.generate_mesh(*scans, signal='amplitude', values=('sx', 'sy'))

plt.figure()
plt.pcolormesh(xx, yy, image)
plt.axis('image')
cb = plt.colorbar(label='amplitude')
plt.xlabel('sx')
plt.ylabel('sy')
plt.title(ttl)
plt.tight_layout()
plt.show()
