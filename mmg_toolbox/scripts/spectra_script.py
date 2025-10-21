"""
Example Script
{{description}}
"""

import os
import matplotlib.pyplot as plt

from mmg_toolbox.xas.nxxas_loader import load_xas_scans
from mmg_toolbox.xas.spectra_container import average_polarised_scans


scan_files = [
    # {{filenames}}
    'file.nxs'
]
output_folder = '{{output_path}}'

# Load spectra from scans
scans = load_xas_scans(*scan_files)

# Plot raw spectra
fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=80)
fig.suptitle('raw scan files')
for scan in scans:
    for n, (mode, spectra) in enumerate(scan.spectra.items()):
        spectra.plot(ax=axes[n], label=scan.name)
        axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

print('Normalise by pre-edge')
for scan in scans:
    scan.divide_by_preedge()
    print(scan)

# plot scan normalised scan files
fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=80)
fig.suptitle('Normalise by pre-edge')
for scan in scans:
    for n, (mode, spectra) in enumerate(scan.spectra.items()):
        spectra.plot(ax=axes[n], label=scan.name)
        axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

print('Fit and subtract background')
for scan in scans:
    scan.auto_edge_background(peak_width_ev=3.)
    print(scan)
    new_filename = f"{os.path.splitext(scan.metadata.filename)[0]}_auto_edge_background.nxs"
    scan.write_nexus(os.path.join(output_folder, new_filename))

# Plot background subtracted scans
for scan in scans:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=80)
    fig.suptitle(scan.name)
    for n, (mode, spectra) in enumerate(scan.spectra.items()):
        spectra.plot_parents(ax=axes[0, n])
        spectra.plot_bkg(ax=axes[0, n])
        axes[0, n].set_ylabel(mode)

        spectra.plot(ax=axes[1, n], label=scan.name)
        axes[1, n].set_ylabel(mode)

    for ax in axes.flat:
        ax.set_xlabel('E [eV]')
        ax.legend()

print('\n\nAverage polarised scans')
# Scan polarisations
for scan in scans:
    print(f"{scan.name}: {scan.metadata.pol}")
pol1, pol2 = average_polarised_scans(*scans)
print(pol1)
print(pol2)

# Plot averaged scans
fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=80)
fig.suptitle('Averaged polarised scans')
for scan in [pol1, pol2]:
    for n, (mode, spectra) in enumerate(scan.spectra.items()):
        spectra.plot(ax=axes[n], label=scan.name)
        axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()


print('\n\nCalculate XMCD')
xmcd = pol1 - pol2
print(xmcd)

for name, spectra in xmcd.spectra.items():
    print(spectra)
    print(spectra.process)
    print(spectra.sum_rules_report(1))

# Save xmcd file
xmcd_filename = f"{scans[0].metadata.scan_no}-{scans[-1].metadata.scan_no}_{xmcd.name}.nxs"
xmcd.write_nexus(os.path.join(output_folder, xmcd_filename))

fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=80)
fig.suptitle(xmcd.name.upper())
for n, (mode, spectra) in enumerate(xmcd.spectra.items()):
    spectra.plot(ax=axes[n])
    axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

plt.show()
