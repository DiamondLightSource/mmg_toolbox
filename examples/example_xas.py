"""
mmg_toolbox example
Example script to read XAS scans from i06 or i10
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import hdfmap
from mmg_toolbox import xas, data_file_reader


inpath = '/dls/science/groups/das/ExampleData/hdfmap_tests/i06/i06-1-372210.nxs'


scan =  data_file_reader(inpath)
spectra = scan.xas_spectra(dls_loader=True)

print(spectra)

###

# scan, = xas.load_xas_scans(inpath)
# scan.metadata.edge
# scan_title = f"#{scan.metadata.scan_no} {edge_label} T={scan.metadata.temp:.0f}K B={scan.metadata.mag_field:.3g}T {scan.metadata.pol}"
# print(scan_title)
# print(scan)
#
# ###
#
# # Plot raw spectra
# fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
# fig.suptitle(scan_title)
# for n, (mode, spectra) in enumerate(scan.spectra.items()):
#     spectra.plot(ax=axes[n], label=scan.name)
#     axes[n].set_ylabel(mode)
#     for lab, en in available_l_edges:
#         axes[n].axvline(en, c='k', linestyle='-')
#         axes[n].text(en+1, 0.98 * spectra.signal.max(), lab)
#
# for ax in axes.flat:
#     ax.set_xlabel('E [eV]')
#     ax.legend()
#
# ###
#
# # 1. Normalise by pre-edge
# scan.divide_by_preedge()
#
# # plot scan normalised scan files
# fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=100)
# fig.suptitle('Normalise by pre-edge')
# for n, (mode, spectra) in enumerate(scan.spectra.items()):
#     spectra.plot(ax=axes[n], label=scan.name)
#     axes[n].set_ylabel(mode)
#
# for ax in axes.flat:
#     ax.set_xlabel('E [eV]')
#     ax.legend()
#
# # 2. Fit and subtract background
# # scan.auto_edge_background(peak_width_ev=10.)
#
# # Plot background subtracted scans
# fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=80)
# fig.suptitle(scan_title)
# for n, (mode, spectra) in enumerate(scan.spectra.items()):
#     spectra.plot_parents(ax=axes[0, n])
#     spectra.plot_bkg(ax=axes[0, n])
#     axes[0, n].set_ylabel(mode)
#
#     spectra.plot(ax=axes[1, n], label=scan.name)
#     axes[1, n].set_ylabel(mode)
#
# for ax in axes.flat:
#     ax.set_xlabel('E [eV]')
#     ax.legend()
#
# # 4. Save Nexus file
# scan.write_nexus('output_xas.nxs')
#
# print('\n\n######################### output_xas.nxs ###################################')
# print(hdfmap.hdf_tree_string('output_xas.nxs'))
#
# plt.show()