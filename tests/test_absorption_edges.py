"""
Test absorption_edges.py functions
"""

import numpy as np
from pytest import approx
from . import only_dls_file_system
from mmg_toolbox.xas.absorption_edges import (split_element_edge, split_element_oxidation, xray_edges_in_range,
                                              Element, Edge, MultiEdge, find_spectra_edge, get_edges)


def test_split_element_edge():
    element, edges = split_element_edge('Co L23')
    assert (element, edges) == ('Co', ['L3', 'L2'])
    element, edges = split_element_edge('O K')
    assert (element, edges) == ('O', ['K'])
    element, edges = split_element_edge('Sm   M4,5')
    assert (element, edges) == ('Sm', ['M5', 'M4'])
    element, edges = split_element_edge('U   L2, L3')
    assert (element, edges) == ('U', ['L3', 'L2'])
    element, edges = split_element_edge('Fe3+L32')
    assert (element, edges) == ('Fe', ['L3', 'L2'])


def test_split_element_oxidation():
    element, oxidation = split_element_oxidation('Co3+ L23')
    assert (element, oxidation) == ('Co', 3)
    element, oxidation = split_element_oxidation('O2-K')
    assert (element, oxidation) == ('O', -2)
    element, oxidation = split_element_oxidation('Ar')
    assert (element, oxidation) == ('Ar', 0)


def test_element():
    element = Element('Co3+')
    assert element.symbol == 'Co'
    assert str(element) == 'Co'
    assert element.oxidation == 3
    assert element.d_electrons(0) == 7
    assert element.d_holes() == 4

    assert Element('Fe') > Element('Mn')
    assert Element('O') < Element('Mn')
    assert Element('Na2+') == Element('Na')


def test_d_electrons():
    assert Element('Ni2+').d_electrons() == 8, 'Ni2+'
    assert Element('Co2+').d_electrons() == 7, 'Co2+'
    assert Element('Fe2+').d_electrons() == 6, 'Fe2+'
    assert Element('Pd2+').d_electrons() == 8, 'Pd2+'
    assert Element('Rh2+').d_electrons() == 7, 'Rh2+'
    assert Element('Pt2+').d_electrons() == 8, 'Pt2+'
    assert Element('Ir2+').d_electrons() == 7, 'Ir2+'
    assert Element('Fe3+').d_holes() == 5, 'Fe3+'
    assert Element('Co3+').d_holes() == 4, 'Co3+'
    assert Element('Fe').d_holes() == 4, 'Fe'


def test_edge():
    edge = Edge('Co L3')
    assert edge.element.symbol == 'Co'
    assert edge.edge == 'L3'
    assert edge.energy == approx(778)
    assert len(edge.element.edges()) == 7
    assert edge.element.is_d() == True
    assert edge.element.d_holes(3) == 4
    assert edge.element.weight == approx(58.933195)
    assert edge.element.atomic_number == 27
    assert edge.element.name == 'Cobalt'

    assert edge == Edge('Co L3')
    assert Edge('O K') < edge
    assert Edge('U M5') > edge


def test_multi_edge():
    edge1, edge2 = Edge('IrL3'), Edge('IrL2')
    edges = MultiEdge(edge1, edge2)
    assert edges.element.symbol == 'Ir'
    assert str(edges) == 'Ir L3,2'
    assert len(edges) == 2
    assert edges[0] == edge1

    edges = MultiEdge.from_symbol('Co L32')
    assert edges.element.symbol == 'Co'
    assert len(edges.edges) == 2
    assert str(edges) == 'Co L3,2'

    _edge = Edge('O K')
    energy = np.linspace(_edge.energy-25, _edge.energy+25, 100)
    signal = np.ones_like(energy)
    signal[energy > _edge.energy] = 10.0
    edges = MultiEdge.from_spectra(energy, signal)
    assert str(edges) == 'O K'

def test_energy_range_edges():

    edges = xray_edges_in_range(770, 800, search_edges=('L3', 'L2'))
    assert edges == [Edge('Co L3'), Edge('Co L2')]

    edges = MultiEdge.from_range(720, energy_range_ev=30)
    assert str(edges) == 'Fe L3,2'

    edges = MultiEdge.from_range(850, 875)
    assert str(edges) == 'Ni L3,2'

    edges = MultiEdge.from_range(523, 560)
    assert str(edges) == 'O K'

    edges = MultiEdge.from_range(1225, 1250)
    assert str(edges) == 'Tb M5'


def test_get_edges():
    check = {
        'Co L2': 793.0,
        'Co L3': 778.0,
        'Fe L2': 720.0,
        'Mn L2': 650.0,
        'Mn L3': 639.0,
        'O K': 543.0,
        'U M4': 3728.0
    }
    symbols = ('Co L23', 'Mn L3, L2', 'O K', 'FeL2', 'Um4', 'Co L32')
    edges = get_edges(*symbols)
    edge_dict = {repr(edge): edge.energy for edge in edges}
    assert edge_dict == check


def test_find_spectra_edge():
    energy = np.arange(1055, 1135, 1)
    edges = find_spectra_edge(energy)
    assert edges.element.symbol == 'Sm'
    assert len(edges.edges) == 2
    assert str(edges) == 'Sm M5,4'


@only_dls_file_system
def test_find_spectra_edge():
    from mmg_toolbox import data_file_reader
    inpath = "/dls/science/groups/das/ExampleData/i10-1/sm_edge/i10-1-77203.nxs"
    scan = data_file_reader(inpath)
    xas_scan = scan.xas_spectra(dls_loader=True)
    edges = find_spectra_edge(xas_scan.tey.energy, xas_scan.tey.signal)
    assert edges.element.symbol == 'Sm'
    assert len(edges.edges) == 2
    assert str(edges) == 'Sm M5,4'

    inpath = "/dls/science/groups/das/ExampleData/hdfmap_tests/i10/i10-1-37436.nxs"
    scan = data_file_reader(inpath)
    xas_scan = scan.xas_spectra(dls_loader=True)
    edges = find_spectra_edge(xas_scan.tey.energy, xas_scan.tey.signal)
    assert edges.element.symbol == 'Fe'
    assert len(edges.edges) == 2
    assert str(edges) == 'Fe L3,2'

    inpath = "/dls/science/groups/das/ExampleData/hdfmap_tests/i06/i06-1-353226.nxs"
    scan = data_file_reader(inpath)
    xas_scan = scan.xas_spectra(dls_loader=True)
    edges = find_spectra_edge(xas_scan.tey.energy, xas_scan.tey.signal)
    assert edges.element.symbol == 'Co'
    assert len(edges.edges) == 2
    assert str(edges) == 'Co L3,2'

    inpath = '/dls/science/groups/das/ExampleData/hdfmap_tests/i06/i06-1-372210.nxs'
    scan = data_file_reader(inpath)
    xas_scan = scan.xas_spectra(dls_loader=True)
    spectra = xas_scan.spectra[next(iter(xas_scan.spectra))]
    edges = find_spectra_edge(spectra.energy, spectra.signal)
    assert edges.element.symbol == 'Cu'
    assert len(edges.edges) == 2
    assert str(edges) == 'Cu L3,2'

    inpath = "/dls/science/groups/das/ExampleData/hdfmap_tests/i16/1146116.nxs"
    scan = data_file_reader(inpath)
    xas_scan = scan.xas_spectra(dls_loader=True)
    spectra = xas_scan.spectra[next(iter(xas_scan.spectra))]
    edges = find_spectra_edge(spectra.energy, spectra.signal)
    assert edges.element.symbol == 'Ir'
    assert len(edges.edges) == 1
    assert str(edges) == 'Ir L3'


