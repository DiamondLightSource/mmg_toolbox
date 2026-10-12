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

# Create experiment object - monitors one or more data folders for files
exp = Experiment('{{experiment_dir}}', instrument='{{beamline}}')

print(exp)

# Load scan data and plot raw spectra
scans = exp.scans(*{{scan_numbers}})  # loads Scan objects that can access NeXus data file
spectras = exp.load_xas(*{{scan_numbers}}, sample_name='mysample', mode='tey', dls_loader=True)  # only loads NXxas spectra (energy scans) and creates a Spectra object

for scan in spectras:
    print(scan)

# Process the spectra
spectras = [spectra.divide_by_preedge().remove_background('linear') for spectra in spectras]
n_spectra = len(spectras[0].spectra)

# Plot each spectra
fig, axes = plt.subplots(1, n_spectra, figsize=[6 * n_spectra, 6], dpi=100, squeeze=False)
for scan in spectras:
    for ax, (mode, spectra) in zip(axes.flat, scan.spectra.items()):
        spectra.plot(ax)
        ax.set_title(spectra.process_label)
        ax.set_ylabel(mode)
        ax.set_xlabel('E [eV]')
        ax.legend()

fig.tight_layout()

plt.show()

# Average polarised scans
for xas_scan in spectras:
    print(f"{xas_scan.name}: {xas_scan.metadata.pol}")
pol1, pol2 = xas.average_polarised_scans(*scans)
print(pol1)
print(pol2)

if pol2 is None:
    raise  ValueError(f"No opposite polarisations found: {[s.metadata.pol for s in spectras]}")

# Plot averaged scans
fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
fig.suptitle('Averaged polarised scans')
for xas_scan in [pol1, pol2]:
    for n, (mode, spectra) in enumerate(xas_scan.spectra.items()):
        spectra.plot(ax=axes[n], label=xas_scan.name)
        axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

plt.show()

# Calculate XMCD
xmcd = pol1 - pol2
print(xmcd)

# Plot XMCD
xmcd.create_sum_rules_figure(figsize=(5 * n_spectra, 6), dpi=100)
plt.tight_layout(h_pad=0.1, w_pad=0.1)

# create processed nexus file
xmcd_filename = f"{spectras[0].metadata.scan_no}-{spectras[-1].metadata.scan_no}_{xmcd.name}.nxs"
xmcd.write_nexus('{{experiment_dir}}/' + xmcd_filename)

