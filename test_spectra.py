"""
Example spectra analysis
"""

import matplotlib.pyplot as plt
from mmg_toolbox.spectra_scan import Scan, SubtractPolarisations, split_polarisations

files = [
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26822.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26823.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26824.nxs',
    '/dls/i10-1/data/2025/cm40624-2/i10-1-26825.nxs',
]

scans = [Scan(file) for file in files]

pol1, pol2 = split_polarisations(*scans)

raw = SubtractPolarisations(pol1, pol2)
proc = SubtractPolarisations(pol1.fit_bkg_then_norm_to_jump(), pol2.fit_bkg_then_norm_to_peak())

raw.create_figure()
proc.create_figure()

# fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6])
# proc.tey.plot(ax1, label='TEY')
# proc.tfy.plot(ax2, label='TFY')
#
# ax1.set_xlabel('E [eV]')
# ax1.set_ylabel('TEY / monitor')
# ax2.set_xlabel('E [eV]')
# ax2.set_ylabel('TEY / monitor')

# fig.show()
plt.show()
