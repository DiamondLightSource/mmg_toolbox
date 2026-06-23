"""
mmg_toolbox tests
Test Spectra Analysis Functions
"""

from pytest import approx
import numpy as np
import os
import h5py

from mmg_toolbox import data_file_reader
from mmg_toolbox.xas import (
    Spectra, SpectraContainer, SpectraContainerSubtraction, load_xas_scans,
    average_polarised_scans, polarised_pairs, pair_scans, average_scans
)
from mmg_toolbox.xas.nxxas_loader import is_nxxas, is_processed
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

    en2, sig2 = container.get_arrays()
    assert sig2.shape == signal.shape
    en3, tey, tfy = container.get_all_arrays()
    assert tfy.shape == energy.shape

    container2 = container.divide_by_preedge().remove_background('linear')
    assert container2.spectra['tey'].signal.max() == approx(0)

    container3 = container + container + container
    assert container3.spectra['tey'].signal.max() == approx(3)
    assert len(container3.parents) == 2  # TODO: find a way to flatten identical processes as parents

    pol1 = container3.copy('pc')
    pol1.metadata.pol = 'pc'
    pol2 = container3.copy('nc')
    pol2.metadata.pol = 'nc'
    container4 = pol1 - pol2
    assert container4.spectra['tey'].signal.max() == approx(0)
    steps = container4.analysis_steps()
    assert len(steps) == 3
    steps_string = container4.analysis_steps_str()
    assert len(steps_string) == approx(569, abs=50)
    assert 'xmcd' in steps_string


def test_average_spectra():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra = {mode: Spectra(energy, signal, label='test', mode=mode) for mode in ['tey', 'tfy']}
    container1 = SpectraContainer('scan1', spectra)
    container2 = SpectraContainer('scan2', spectra)
    container3 = SpectraContainer('scan3', spectra)

    av_scan = average_scans(container1, container2, container3)
    assert len(av_scan.parents) == 3
    assert repr(av_scan) == "SpectraContainer('scan1+scan2+scan3', 'average', ['tey', 'tfy'])"
    av_scan = average_scans(container1, container2, container3, container2)
    assert len(av_scan.parents) == 4
    assert av_scan.parents[0].parents == ()
    assert repr(av_scan) == "SpectraContainer('scan1+..+scan2', 'average', ['tey', 'tfy'])"
    assert repr(av_scan.spectra['tey']) == "SpectraAverage('test+test+test+test', 'tey', energy=array(300,), signal=array(300,), process_label='average')"


@only_dls_file_system
def test_load_xas_scans():
    assert is_nxxas(FILES_DICT['i06-1 zacscan'])
    spectra, = load_xas_scans(FILES_DICT['i06-1 zacscan'], dls_loader=True)
    assert spectra.metadata.pol == 'cr'
    assert spectra.metadata.mag_field == approx(0)

    spectra = spectra.trim(ev_from_start=2., ev_from_end=None)
    norm = spectra.divide_by_preedge(ev_from_start=5)
    rembk = norm.remove_background('exp')

    assert rembk.spectra['tey'].signal.max() == approx(2.82, abs=0.03)

    # Write nexus
    rembk.write_nexus('test_spectra.nxs')
    assert os.path.isfile('test_spectra.nxs')
    assert is_processed('test_spectra.nxs')

    with h5py.File('test_spectra.nxs', 'r') as hdf:
        assert isinstance(hdf['/processed/tey/absorbed_beam'], h5py.Dataset)
    check, = load_xas_scans('test_spectra.nxs')
    assert len(check.spectra) == 2
    assert len(check.parents) == 0
    assert isinstance(check, SpectraContainer)
    scan = data_file_reader('test_spectra.nxs')
    assert all(scan('signal') == rembk.spectra['tey'].signal)


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
    assert xmcd.parents[0].parents[0].parents[0].parents[0].parents == ()
    assert xmcd.get_raw_filename() == FILES_DICT['i10-1 Fe L3,2 +1T pc']
    orbital, spin = xmcd.calculate_sum_rules()
    assert orbital == approx(-0.088, abs=0.001)
    assert spin == approx(0.008, abs=0.001)
    report = xmcd.sum_rules_report()
    assert ' n_holes = 4\nL = -0.088 μB\nS = 0.008 μB' in report

    # Write nexus
    xmcd.write_nexus('test_xmcd.nxs')
    assert os.path.isfile('test_xmcd.nxs')
    assert is_processed('test_xmcd.nxs')

    with h5py.File('test_xmcd.nxs', 'r') as hdf:
        assert isinstance(hdf['/xmcd/tey/absorbed_beam'], h5py.Dataset)
    check, = load_xas_scans('test_xmcd.nxs')
    assert len(check.spectra) == 2
    assert len(check.parents) == 2
    assert check.parents[0].parents == ()  # TODO: read full history
    assert isinstance(check, SpectraContainerSubtraction)
    scan = data_file_reader('test_xmcd.nxs')
    assert all(scan('signal') == xmcd.spectra['tey'].signal)

    os.remove('test_xmcd.nxs')


@only_dls_file_system
def test_find_pairs():
    files = [
        FILES_DICT['i10-1 Fe L3,2 +1T pc'],
        FILES_DICT['i10-1 Fe L3,2 -1T pc'],
        FILES_DICT['i10-1 Fe L3,2 +1T nc'],
        FILES_DICT['i10-1 Fe L3,2 -1T nc'],
    ]
    all_spectra = load_xas_scans(*files, dls_loader=True)
    pol_pairs = polarised_pairs(*all_spectra)
    assert len(pol_pairs) == 2
    scan1, scan2 = pol_pairs[0]
    assert scan1.metadata.pol != scan2.metadata.pol

    pairs = pair_scans(*all_spectra)
    assert len(pairs) == 2
    scan1, scan2 = pairs[0]
    assert scan1.metadata.pol == scan2.metadata.pol
    assert scan1.metadata.mag_field == approx(-scan2.metadata.mag_field)

def test_write_outputs():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra = {mode: Spectra(energy, signal, label='test', mode=mode) for mode in ['tey', 'tfy']}
    container = SpectraContainer('test', spectra)

    container = container.divide_by_preedge()
    container.write_nexus('test_xas.nxs')
    assert os.path.isfile('test_xas.nxs')
    assert is_processed('test_xas.nxs')

    with h5py.File('test_xas.nxs', 'r') as hdf:
        assert isinstance(hdf['/test/divide_by_preedge/tey/absorbed_beam'], h5py.Dataset)
        assert isinstance(hdf['/test/tey/absorbed_beam'], h5py.Dataset)
    check, = load_xas_scans('test_xas.nxs')
    assert len(check.spectra) == 2
    assert len(check.parents) == 0

    os.remove('test_xas.nxs')

    container.write_csv('test_xas.csv')
    assert os.path.isfile('test_xas.csv')

    energy2, tey, tfy = np.loadtxt('test_xas.csv', delimiter=',').T
    assert tey.shape == signal.shape

    os.remove('test_xas.csv')


def test_write_average_outputs():
    from mmg_toolbox.fitting.functions import gauss
    energy = np.arange(700, 730, 0.1)
    signal = gauss(energy, height=30, cen=715, fwhm=3, bkg=6)
    scans = []
    for n in range(5):
        spectra = {mode: Spectra(energy, signal, label=f'test{n}', mode=mode) for mode in ['tey', 'tfy']}
        container = SpectraContainer(f'test{n}', spectra)
        container = container.divide_by_preedge()
        container = container.remove_background('flat')
        scans.append(container)
    av_spectra = average_scans(*scans)

    av_spectra.write_nexus('test_av_xas.nxs')
    assert os.path.isfile('test_av_xas.nxs')
    assert is_processed('test_av_xas.nxs')

    with h5py.File('test_av_xas.nxs', 'r') as hdf:
        assert isinstance(hdf['/test0+..+test4/tey/absorbed_beam'], h5py.Dataset)
    check, = load_xas_scans('test_av_xas.nxs')
    assert len(check.spectra) == 2
    assert len(check.parents) == 5

    os.remove('test_av_xas.nxs')

def test_write_subtracted_outputs():
    energy = np.arange(700, 730, 0.1)
    signal = 3 * np.ones(len(energy))
    spectra1 = {mode: Spectra(energy, signal, label='test1', mode=mode) for mode in ['tey', 'tfy']}
    container1 = SpectraContainer('test1', spectra1)
    container1 = container1.divide_by_preedge()
    container1.metadata.pol = 'cr'
    spectra2 = {mode: Spectra(energy, signal * 1.2, label='test2', mode=mode) for mode in ['tey', 'tfy']}
    container2 = SpectraContainer('test2', spectra2)
    container2 = container2.divide_by_preedge()
    container2.metadata.pol = 'cl'

    subtracted = container1 - container2
    subtracted.write_nexus('test_subtracted.nxs')
    assert os.path.isfile('test_subtracted.nxs')

    with h5py.File('test_subtracted.nxs', 'r') as hdf:
        assert isinstance(hdf['/xmcd/tey/absorbed_beam'], h5py.Dataset)
        assert isinstance(hdf['/xmcd/tfy/absorbed_beam'], h5py.Dataset)
        assert isinstance(hdf['/xmcd/sum_rules/tey/data'], h5py.Dataset)
    check, = load_xas_scans('test_subtracted.nxs')
    assert len(check.spectra) == 2
    assert len(check.parents) == 2
    assert isinstance(check, SpectraContainerSubtraction)

    os.remove('test_subtracted.nxs')

    subtracted.write_csv('test_subtracted.csv')
    assert os.path.isfile('test_subtracted.csv')

    energy2, tey1, tfy1, tey2, tfy2, tey_xmcd, tfy_xmcd = np.loadtxt('test_subtracted.csv', delimiter=',').T
    assert tey_xmcd.shape == signal.shape

    os.remove('test_subtracted.csv')

