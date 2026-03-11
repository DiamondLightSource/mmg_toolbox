"""
mmg_toolbox tests
Test Spectra Analysis Functions
"""

from pytest import approx
import numpy as np
import os
import h5py

from mmg_toolbox.xas import Spectra, SpectraContainer, load_xas_scans, average_polarised_scans
from . import only_dls_file_system
from .example_files import FILES_DICT


def test_create_spectra():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra1 = Spectra(energy, signal, label='test', mode='tey')
    spectra2 = Spectra(energy, signal, label='test', mode='tey')
    spectra3 = Spectra(energy + 1, signal, label='test', mode='tey')
    spectra4 = Spectra(energy - 1, signal, label='test', mode='tey')
    average = spectra1 + spectra2 + spectra3 + spectra4
    diff = spectra1 - spectra2

    assert average.signal.max() == approx(3)
    assert average.process_label == 'average'
    assert len(average.process) > 200
    assert diff.signal.max() == approx(0)
    assert diff.process_label == 'subtraction'
    assert len(diff.process) > 200

    edges = spectra1.edges()
    assert len(edges) == 2
    assert 'Fe L3' in edges

    spectra5 = spectra1.divide_by_preedge()
    assert spectra5.signal.max() == approx(1)
    spectra6 = spectra1.trim(ev_from_start=5, ev_from_end=1)
    assert spectra6.signal.shape == (240, )
    spectra7 = spectra1.remove_background('flat')
    assert spectra7.signal.max() == approx(0)
    assert spectra7.process_label == 'flat'


def test_spectra_container():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra = {mode: Spectra(energy, signal, label='test', mode=mode) for mode in ['tey', 'tfy']}
    container = SpectraContainer('test', spectra)
    s = str(container)
    assert 'E = 714.95 eV -> Fe L3, L2' in s
    assert len(container.spectra) == 2

    edges = container.get_edges()
    assert len(edges) == 2

    container2 = container.divide_by_preedge().remove_background('linear')
    assert container2.spectra['tey'].signal.max() == approx(0)

    container3 = container + container + container
    assert container3.spectra['tey'].signal.max() == approx(3)

    pol1 = container3.copy('pc')
    pol1.metadata.pol = 'pc'
    pol2 = container3.copy('nc')
    pol2.metadata.pol = 'nc'
    container4 = pol1 - pol2
    assert container4.spectra['tey'].signal.max() == approx(0)
    steps = container4.analysis_steps()
    assert len(steps) == 2
    steps_string = container4.analysis_steps_str()
    assert len(steps_string) == approx(569, abs=50)
    assert 'xmcd' in steps_string


@only_dls_file_system
def test_load_xas_scans():
    spectra, = load_xas_scans(FILES_DICT['i06-1 zacscan'], dls_loader=True)
    assert spectra.metadata.pol == 'cr'
    assert spectra.metadata.mag_field == approx(0)

    spectra = spectra.trim(ev_from_start=2., ev_from_end=None)
    norm = spectra.divide_by_preedge(ev_from_start=5)
    rembk = norm.remove_background('exp')

    assert rembk.spectra['tey'].signal.max() == approx(2.82, abs=0.03)


@only_dls_file_system
def test_average_polarised_scans():
    files = [
        FILES_DICT['i10-1 Fe L3,2 +1T pc'],
        FILES_DICT['i10-1 Fe L3,2 -1T pc'],
        FILES_DICT['i10-1 Fe L3,2 +1T nc'],
        FILES_DICT['i10-1 Fe L3,2 -1T nc'],
    ]
    all_spectra = load_xas_scans(*files, dls_loader=True)
    assert all_spectra[0].metadata.pol == 'cr'
    assert all_spectra[0].metadata.mag_field == approx(1)

    all_spectra = [
        spectrum.divide_by_preedge(ev_from_start=5).remove_background('flat')
        for spectrum in all_spectra
    ]

    pol1, pol2 = average_polarised_scans(*all_spectra)
    xmcd = pol1 - pol2
    assert xmcd.spectra['tey'].signal.max() == approx(0.145, abs=0.001)
    assert 'xmcd' == xmcd.name
    assert 'xmcd' in xmcd.analysis_steps_str()
    orbital, spin = xmcd.calculate_sum_rules()
    assert orbital == approx(-0.088, abs=0.001)
    assert spin == approx(0.008, abs=0.001)
    report = xmcd.sum_rules_report()
    assert ' n_holes = 4\nL = -0.088 μB\nS = 0.008 μB' in report


def test_write_nexus():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra = {mode: Spectra(energy, signal, label='test', mode=mode) for mode in ['tey', 'tfy']}
    container = SpectraContainer('test', spectra)

    container = container.divide_by_preedge()
    container.write_nexus('test_xas.nxs')
    assert os.path.isfile('test_xas.nxs')

    with h5py.File('test_xas.nxs', 'r') as hdf:
        assert isinstance(hdf['/entry/divide_by_preedge/tey'], h5py.Dataset)

    os.remove('test_xas.nxs')

