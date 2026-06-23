"""
mmg_toolbox example
Example edge detection from energy range
"""

import numpy as np
from mmg_toolbox.xas import xray_edges_in_range, energy_range_edge_label, get_edge_energies

energy_ev = np.arange(770, 800, 0.5)

# Automatic determination of edge
auto_edge_label = ' '.join(energy_range_edge_label(energy_ev.min(), energy_ev.max()))

print(f"Absorption edges between: {energy_ev.min()}, {energy_ev.max()} eV")
available_edges = xray_edges_in_range(energy_ev.min(), energy_ev.max(), search_edges=None)
print('\n'.join(
    f"{en} eV : {lab}" for lab, en in available_edges.items()
))

# search L edges only
available_l_edges = xray_edges_in_range(energy_ev.min(), energy_ev.max(), search_edges=['L3', 'L2'])
edge_label = ' '.join(energy_range_edge_label(energy_ev.min(), energy_ev.max(), search_edges=['L3', 'L2']))
print('\nAutomatically determined absorption edge:')
print('\n'.join(f"{en} eV : {lab}" for lab, en in available_l_edges.items()))
print(f"Edge label: {edge_label}")

print('\n\nVarious edges:')
edges = get_edge_energies('Ni L23', 'Mn L3, L2', 'O K', 'FeL2', 'Um4', edge_label)
for lab, en in edges.items():
    print(f"{lab:6} : {en} eV")

energies_ev = [720, 560, 540, 1235, 2838, 3552, 7112, 11215]
en_range_ev = 30

print('\n\nVarious energy ranges:')
for en in energies_ev:
    element, edges = energy_range_edge_label(en, energy_range_ev=en_range_ev)
    print(f"{en-en_range_ev/2:.0f}-{en+en_range_ev/2:.0f} eV : {element} {edges}")

