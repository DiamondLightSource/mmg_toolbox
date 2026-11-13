"""
mmg_toolbox example
Example edge detection from energy range
"""

import numpy as np
from mmg_toolbox.xas import xray_edges_in_range, find_spectra_edge, Edge

energy_ev = np.arange(770, 800, 0.5)

# Automatic determination of edge
auto_edge = find_spectra_edge(energy_ev)
print(f"Edge label: {auto_edge}")

print(f"Absorption edges between: {energy_ev.min()}, {energy_ev.max()} eV")
available_edges = xray_edges_in_range(energy_ev.min(), energy_ev.max(), search_edges=None)
print(available_edges)
print('\n'.join(str(edge) for edge in available_edges))

print('\nAutomatically determined absorption edge:')
edge_label = find_spectra_edge(energy_ev)
print(f"Edge label: {edge_label}")

print('\n\nVarious edges:')
edges = [Edge(s) for s in ('Ni L23', 'Mn L3, L2', 'O K', 'FeL2', 'Um4', str(edge_label))]
print('\n'.join(str(edge) for edge in edges))

energies_ev = [720, 560, 540, 1235, 2838, 3552, 7112, 11215]
en_range_ev = 30

print('\n\nVarious energy ranges:')
for en in energies_ev[5:]:
    rng = np.linspace(en-en_range_ev/2, en+en_range_ev/2, 10)
    edges = find_spectra_edge(rng)
    print(f"{en-en_range_ev/2:.0f}-{en+en_range_ev/2:.0f} eV : {edges}")

