"""
mmg_toolbox example
Example script to read XAS scans from i06 or i10
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import hdfmap
from mmg_toolbox import xas


inpath = '/dls/science/groups/das/ExampleData/hdfmap_tests/i06/i06-1-372210.nxs'

nxs_map = hdfmap.create_nexus_map(inpath)

with nxs_map.load_hdf() as nxs:
    def rd(expr, default=''):
        return nxs_map.format_hdf(nxs, expr, default=default)

    # currently accounts for i06-1 and i10-1 metadata
    metadata = {
        "scan": rd('{filename}'),
        "cmd": rd('{(cmd|user_command|scan_command)}'),
        "title": rd('{title}', os.path.basename(inpath)),
        "endstation": rd('{end_station}', 'unknown'),
        "sample": rd('{sample_name}', ''),
        "energy": rd('{mean((fastEnergy|pgm_energy|energye|energyh)):.2f} eV'),
        "pol": rd('{polarisation?("lh")}'),
        "height": rd('{(em_y|hfm_y):.2f}', 0),
        "pitch": rd('{(em_pitch|hfm_pitch):.2f}', 0),
        "temperature": rd('{(T_sample|sample_temperature|lakeshore336_cryostat|lakeshore336_sample|itc3_device_sensor_temp?(300)):.2f} K'),
        "field": rd('{(field_z|sample_field|magnet_field|ips_demand_field?(0)):.2f} T'),
    }
    # scannables - selects the first available of the options separated by |
    ENERGY = '(fastEnergy|pgm_energy|energye|energyh)'
    MONITOR = '(i0|C2|ca62sr|mcs16_data|mcse16_data|mcsh16_data)'
    TEY = '(tey|C1|ca61sr|mcs17_data|mcse17_data|mcsh17_data)'
    TFY = '(fdu|C3|ca63sr|mcs18_data|mcse18_data|mcsh18_data|mcsd18_data)'

    print('Scan data paths:')
    print('energy: ', nxs_map.eval(nxs, '_' + ENERGY))
    print('monitor: ', nxs_map.eval(nxs, '_' + MONITOR))
    print('tey: ', nxs_map.eval(nxs, '_' + TEY))
    print('tfy: ', nxs_map.eval(nxs, '_' + TFY))

    energy = nxs_map.eval(nxs, ENERGY)
    monitor = nxs_map.eval(nxs, MONITOR, default=1.0)
    tey = nxs_map.eval(nxs, TEY, default=np.ones(nxs_map.scannables_shape())) / monitor
    tfy = nxs_map.eval(nxs, TFY, default=np.ones(nxs_map.scannables_shape())) / monitor

print('\nMetadata:')
print('\n'.join(f"{n:12}: {d}" for n, d in metadata.items()))

title = "{endstation} {sample} {scan}\nE = {energy}, pol = {pol}, T = {temperature}, B = {field}".format(**metadata)
print('\ntitle: ', title)

###

print(f"Absorption edges between: {energy.min()}, {energy.max()} eV")
print('\n'.join(f"{en} eV : {lab}" for en, lab in xas.xray_edges_in_range(energy.min(), energy.max(), search_edges=None)))

# search L edges only, returns single element edge or set
available_l_edges = xas.xray_edges_in_range(energy.min(), energy.max())
edge_label = ' '.join(xas.energy_range_edge_label(energy.min(), energy.max()))
print('\nAutomatically determined absorption edge:')
print('\n'.join(f"{en} eV : {lab}" for en, lab in available_l_edges))
print(f"Edge label: {edge_label}")

###

scan, = xas.load_xas_scans(inpath)
scan_title = f"#{scan.metadata.scan_no} {edge_label} T={scan.metadata.temp:.0f}K B={scan.metadata.mag_field:.3g}T {scan.metadata.pol}"
print(scan_title)
print(scan)

###

# Plot raw spectra
fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
fig.suptitle(scan_title)
for n, (mode, spectra) in enumerate(scan.spectra.items()):
    spectra.plot(ax=axes[n], label=scan.name)
    axes[n].set_ylabel(mode)
    for lab, en in available_l_edges:
        axes[n].axvline(en, c='k', linestyle='-')
        axes[n].text(en+1, 0.98 * spectra.signal.max(), lab)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

###

# 1. Normalise by pre-edge
scan.divide_by_preedge()

# plot scan normalised scan files
fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
fig.suptitle('Normalise by pre-edge')
for n, (mode, spectra) in enumerate(scan.spectra.items()):
    spectra.plot(ax=axes[n], label=scan.name)
    axes[n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

# 2. Fit and subtract background
# scan.auto_edge_background(peak_width_ev=10.)

# Plot background subtracted scans
fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=80)
fig.suptitle(scan_title)
for n, (mode, spectra) in enumerate(scan.spectra.items()):
    spectra.plot_parents(ax=axes[0, n])
    spectra.plot_bkg(ax=axes[0, n])
    axes[0, n].set_ylabel(mode)

    spectra.plot(ax=axes[1, n], label=scan.name)
    axes[1, n].set_ylabel(mode)

for ax in axes.flat:
    ax.set_xlabel('E [eV]')
    ax.legend()

# 4. Save Nexus file
scan.write_nexus('output_xas.nxs')

print('\n\n######################### output_xas.nxs ###################################')
print(hdfmap.hdf_tree_string('output_xas.nxs'))

plt.show()