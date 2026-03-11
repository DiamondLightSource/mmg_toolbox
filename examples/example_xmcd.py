"""
mmg_toolbox example
Example script to read XAS scans from i06 or i10
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment


exp = Experiment('/dls/science/groups/das/ExampleData/hdfmap_tests/i10', instrument='i10-1')

spectra = exp.load_xas(37436, 37437, 37438, 37439, dls_loader=True, mode='tey')

for spectrum in spectra:
    m = spectrum.metadata
    print(f"Spectrum: {spectrum.name} T={m.temp:.1f} K, B={m.mag_field:+3.1f} T, pol='{m.pol}'")

# Processing
spectra = [
    spectrum.divide_by_preedge(ev_from_start=5).remove_background('linear')
    for spectrum in spectra
]

up_right, down_right, down_left, up_left = spectra
xmcd_field1 = up_right - down_right
xmcd_field2 = up_left - down_left
xmcd_pol1 = up_left - up_right
xmcd_pol2 = down_left - down_right

# xmcd_field1.create_sum_rules_figure()
# xmcd_field2.create_sum_rules_figure()
# xmcd_pol1.create_sum_rules_figure()
# xmcd_pol2.create_sum_rules_figure()

from mmg_toolbox.xas import average_polarised_scans

print(xmcd_pol1)

pol1, pol2 = average_polarised_scans(*spectra)

pol1.create_background_figure()

plt.show()