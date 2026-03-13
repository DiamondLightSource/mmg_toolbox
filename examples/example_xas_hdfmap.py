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
print('\n'.join(f"{en} eV : {lab}" for lab, en in xas.xray_edges_in_range(energy.min(), energy.max(), search_edges=None).items()))

# search L edges only, returns single element edge or set
available_l_edges = xas.xray_edges_in_range(energy.min(), energy.max())
edge_label = ' '.join(xas.energy_range_edge_label(energy.min(), energy.max()))
print('\nAutomatically determined absorption edge:')
print('\n'.join(f"{en} eV : {lab}" for lab, en in available_l_edges.items()))
print(f"Edge label: {edge_label}")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle(title)
ax1.plot(energy, tey, label='TEY')
ax1.set_xlabel('Energy (eV)')
ax1.set_ylabel('signal')
ax1.legend()

ax2.plot(energy, tfy, label='TFY')
ax2.set_xlabel('Energy (eV)')
ax2.set_ylabel('signal')
ax2.legend()

plt.show()