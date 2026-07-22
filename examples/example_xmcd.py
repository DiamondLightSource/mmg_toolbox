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

av_pol1 = up_right + down_left
av_pol2 = up_left + down_left
xmcd_av = av_pol1 - av_pol2

# xmcd_field1.create_sum_rules_figure()
# xmcd_field2.create_sum_rules_figure()
# xmcd_pol1.create_sum_rules_figure()
# xmcd_pol2.create_sum_rules_figure()
# xmcd_av.create_sum_rules_figure()
# plt.show()

print(xmcd_av.get_raw_metadata('filename'))

xmcd_av.write_nexus('test.nxs')
