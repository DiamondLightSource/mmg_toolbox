"""
Example Script
{{description}}
"""

import sys, os
import numpy as np
import matplotlib.pyplot as plt

import hdfmap
from mmg_toolbox.spectra_scan import SpectraScan, find_pol_pairs, is_nxxas
from mmg_toolbox.nexus_writer import create_xmcd_nexus

hdfmap.set_all_logging_level('error')

scan_files = [
    # {{filenames}}
    'file.nxs'
]

# Load spectra from scans
scans = [SpectraScan(file) for file in scan_files]

# Plot raw spectra
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6], dpi=100)
for scan in scans:
    print(scan, '\n')
    scan.tey.plot(ax1)
    scan.tfy.plot(ax2)

ax1.set_xlabel('E [eV]')
ax1.set_ylabel('TEY / monitor')
ax2.set_xlabel('E [eV]')
ax2.set_ylabel('TFY / monitor')
ax1.legend()
ax2.legend()

# Subtract background and normalise
# background options: flat, norm, linear, curve, exp
# normalisation option: .norm_to_jump(), .norm_to_peak()
rem_bkg = [s.remove_background('flat').norm_to_jump() for s in scans]
pairs = find_pol_pairs(*rem_bkg)

for pair in pairs:
    # pair.create_figure()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6], dpi=100)
    fig.suptitle(pair.description)

    pair.spectra1.tey.plot_parents(ax1)  # background subtracted spectra
    pair.spectra2.tey.plot_parents(ax1)
    pair.tey.plot(ax1)  # XMCD/XMLD

    pair.spectra1.tey.plot_parents(ax2)
    pair.spectra2.tey.plot_parents(ax2)
    pair.tey.plot(ax2)

    ax1.set_xlabel('E [eV]')
    ax1.set_ylabel('TEY / monitor')
    ax2.set_xlabel('E [eV]')
    ax2.set_ylabel('TFY / monitor')
    ax1.legend()
    ax2.legend()

# Average each polarisation of all scans
pol1 = [pair.spectra1 for pair in pairs]
pol2 = [pair.spectra2 for pair in pairs]
av_pol1 = sum(pol1[1:], pol1[0])
av_pol2 = sum(pol2[1:], pol2[0])
diff = av_pol1 - av_pol2
print(diff)

# diff.create_figure()
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6], dpi=100)
fig.suptitle(diff.description)

diff.spectra1.tey.plot_parents(ax1)
diff.spectra2.tey.plot_parents(ax1)
diff.tey.plot(ax1)

diff.spectra1.tey.plot_parents(ax2)
diff.spectra2.tey.plot_parents(ax2)
diff.tey.plot(ax2)

ax1.set_xlabel('E [eV]')
ax1.set_ylabel('TEY / monitor')
ax2.set_xlabel('E [eV]')
ax2.set_ylabel('TFY / monitor')
ax1.legend()
ax2.legend()

plt.show()
