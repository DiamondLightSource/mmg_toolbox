"""
Example Script for XAS Spectra Analysis
{{date}}
{{description}}
"""

import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment, module_info, xas
from mmg_toolbox.plotting.matplotlib import set_plot_defaults

set_plot_defaults()  # set nice defaults for matplotlib plots

# Filenames - Polarisation 1
files_pol1 = [
    {{xas_files1}}
]
files_pol2 = [
    {{xas_files2}}
]
mode = '{{xas_mode}}'
background = '{{xas_background}}'

pol1_spectra = xas.load_xas_scans(*files_pol1, mode=mode, dls_loader=True)
pol2_spectra = xas.load_xas_scans(*files_pol2, mode=mode, dls_loader=True)

# Process the spectra
pol1_spectra = [spectra.divide_by_preedge().remove_background(background) for spectra in pol1_spectra]
pol2_spectra = [spectra.divide_by_preedge().remove_background(background) for spectra in pol2_spectra]

# average spectra
pol1 = xas.average_scans(*pol1_spectra)
pol2 = xas.average_scans(*pol2_spectra)

# subtract spectra
diff = pol1 - pol2

# Plotting
fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
for spectra in diff.spectra1.parents:
    spectrum = spectra.spectra[mode]
    axes[0].plot(spectrum.energy, spectrum.signal)
pol1.add_edge_lines(axes[0])
axes[0].legend()
axes[0].set_xlabel('E [eV]')
axes[0].set_ylabel(mode)
axes[0].set_title(diff.spectra1.name)

for spectra in diff.spectra2.parents:
    spectrum = spectra.spectra[mode]
    axes[1].plot(spectrum.energy, spectrum.signal)
pol1.add_edge_lines(axes[1])
axes[1].legend()
axes[1].set_xlabel('E [eV]')
axes[1].set_ylabel(mode)
axes[1].set_title(diff.spectra1.name)

# Plot XMCD / XMLD
diff.create_sum_rules_figure(figsize=(12, 6), dpi=100)
plt.tight_layout(h_pad=0.1, w_pad=0.1)

# create processed nexus file
scan_numbers = list(diff.get_raw_metadata('scan_no').values())
xmcd_filename = f"{scan_numbers[0]}-{scan_numbers[-1]}_{diff.name}.nxs"
diff.write_nexus('{{processing_dir}}/' + xmcd_filename)

