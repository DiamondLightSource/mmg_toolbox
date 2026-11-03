"""
mmg_toolbox example
Example script to read XAS scans from i16
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment
from mmg_toolbox.xas import average_polarised_scans


exp = Experiment('/dls/science/groups/das/ExampleData/i16/vortex_2026', instrument='i16')

### Single Energy Vortex spectrum ###
spectrum, = exp.load_xas(1146115, element_edge='Ir L32')  # scan x 1 3 1 xsp3 1
m = spectrum.metadata
print(f"Spectrum: {spectrum.name} T={m.temp:.1f} K, B={m.mag_field:+3.1f} T, pol='{m.pol}'")

# Processing
processed_spectrum = spectrum.trim(1000, 20000).remove_background('flat')
fig = processed_spectrum.create_figure()

### Incident Energy Scan with Vortex ###
scan, = exp.scans(1146116)
# Add ROI window - xsp3 has 2 channels, 4096 bins. create window around bin 915 == 9150 eV
scan.map.add_roi('new_window', 1, 915, 2, 100, 'xsp3')
spectrum = scan.xas_spectra()

fig2 = spectrum.create_figure()  # show the different Windows


### Merge and compare scans
exp.add_roi('my_window', 1, 915, 2, 100, 'xsp3')  # Add ROI to exp so it is added to every scan
spectra = exp.load_xas(*range(1146116, 1146124))

# Processing
spectra = [
    spectrum.trim(5, 0).remove_background('flat')
    for spectrum in spectra
]

# Find opposite polarisations, sum similar polarisations
pol1, pol2 = average_polarised_scans(*spectra)
print(f"Found {len(pol1.parents)} spectra with '{pol1.metadata.pol}' polarisation," +
      " and {len(pol2.parents)} spectra with '{pol2.metadata.pol}' polarisation")

# Align spectra using cross-correlation
pol1 = pol1.align_spectra('my_window')
pol2 = pol2.align_spectra('my_window')

# Calculate subtraction
xmld = pol1 - pol2

fig3 = xmld.create_sum_rules_figure(figsize=[12, 10], dpi=100)

plt.show()


