"""
mmg_toolbox example
Example script to read XAS scans from i16
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment
from mmg_toolbox.xas import average_polarised_scans, average_scans


exp = Experiment('/dls/i16/data/2026/cm44164-9', instrument='i16')

spectra = exp.load_xas(1145818)

for spectrum in spectra:
    m = spectrum.metadata
    print(f"Spectrum: {spectrum.name} T={m.temp:.1f} K, B={m.mag_field:+3.1f} T, pol='{m.pol}'")

# Processing
spectra = [
    spectrum.trim(1000, 30000).remove_background('flat')
    for spectrum in spectra
]

av = average_scans(*spectra)

print(repr(av))

av.create_figure()
plt.show()


