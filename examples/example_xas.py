"""
mmg_toolbox example
Example script to read XAS scans from i06 or i10
"""

import os
import numpy as np
import hdfmap
from mmg_toolbox.xas.spectra_analysis import energy_range_edge_label, xray_edges_in_range
from mmg_toolbox.xas.nxxas_loader import load_from_nxs_using_hdfmap


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
print('\n'.join(f"{en} eV : {lab}" for en, lab in xray_edges_in_range(energy.min(), energy.max(), search_edges=None)))

edge_label = energy_range_edge_label(energy.min(), energy.max())
print('Automatically determined absorption edge:')
print(f"\nEdge label: {' '.join(edge_label)}")

###

scan = load_from_nxs_using_hdfmap(inpath)
print(scan)