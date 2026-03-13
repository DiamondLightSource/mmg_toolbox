"""
mmg_toolbox tests
Test Spectra Analysis Functions
"""

import pytest
import numpy as np

from mmg_toolbox.xas import spectra_analysis as spa

def test_edge_labels():
    check = {
        'Co L2': 793.0,
        'Co L3': 778.0,
        'Fe L2': 720.0,
        'Mn L2': 650.0,
        'Mn L3': 639.0,
        'O K': 543.0,
        'U M4': 3728.0
    }
    assert spa.get_edge_energies('Co L23', 'Mn L3, L2', 'O K', 'FeL2', 'Um4') == check

    edges = spa.xray_edges_in_range(770, 800)
    assert edges == {'Co L2': 793.0, 'Co L3': 778.0}

    element, edges = spa.energy_range_edge_label(720, energy_range_ev=30)
    assert element+edges == 'FeL3, L2'


def test_n_holes():
    assert spa.d_electron_count('Ni2+') == 8
    assert spa.d_electron_count('Co2+') == 7
    assert spa.d_electron_count('Fe2+') == 6
    assert spa.d_electron_count('Pd2+') == 8
    assert spa.d_electron_count('Rh2+') == 7
    assert spa.d_electron_count('Pt2+') == 8
    assert spa.d_electron_count('Ir2+') == 7
    assert spa.d_electron_holes('Fe3+') == 5
    assert spa.d_electron_holes('Co3+') == 4
    assert spa.d_electron_holes('Fe') == 4


