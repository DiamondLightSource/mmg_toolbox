"""
mmg_toolbox tests
Test XAS Multi-Edge Fit Parameters
"""

from pytest import approx, fixture
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox.xas import MultiEdge
from mmg_toolbox.xas.multi_edge_fit_parameters import (preedge_slope, midedge_slope, postedge_slope,
                                                       transition_points, l3_edge_jump)
from mmg_toolbox.xas.multi_edge_fit_functions import background_three_region, double_l_edge
from mmg_toolbox.xas.multi_edge_fit_models import BackgroundThreeRegionModel, DoubleLEdgeModel
from . import only_dls_file_system

# Matlab data
# Captured by loading test files:
#  Component 1: VBA_37436_pc_1T.csv
#  Component 2: VBA_37439_nc_1T.csv
# Init are defaults on first loading data
# Fit values are returned after 1 round of fitting from defaults, then clicking Accept
# TODO: these aren't used yet
VBA = {
    'Atomic System': 'Fe2+',
    'init_component1_file': 'vbl_init_component1_37436.dat',
    'init_component2_file': 'vbl_init_component2_37439.dat',
    'init_dichroism_file': 'vbl_init_dichroism.dat',
    'fit_component1_file': 'vbl_fit_component1_37436.dat',
    'fit_component2_file': 'vbl_fit_component2_37439.dat',
    'fit_dichroism_file': 'vbl_fit_dichroism.dat',
    'init_parameters': {
        'SSE': 2.149e+04,
        'mS(eff)': 0.05949,
        'mL': -0.001509,
    },
    'fit_parameters': {
        'SSE': 2393,
        'mS(eff)': -0.0395,
        'mL': 0.03103,
    }
}


@fixture
def matlab_data():
    data_dir = Path('/dls/science/groups/das/ExampleData/xmcd/virtual_beamline_app/')
    init_params = json.load(open(data_dir / 'vba_init_params.json')) 
    fit_params = json.load(open(data_dir / 'vba_fit_params.json'))
    yield data_dir, init_params, fit_params


def test_edge_slope():
    energy = np.arange(690, 750, 0.5)
    signal = np.ones_like(energy) * 60.
    signal[35:50] += 100
    signal[40:] += 30
    signal[60:70] += 40

    l3, l2 = energy[35], energy[61]

    p0 = preedge_slope(energy, signal)
    p1 = midedge_slope(energy, signal)
    p2 = postedge_slope(energy, signal)
    background = background_three_region(energy, p0, p1, p2, l3, l2, energy[1], signal[1])
    jump = l3_edge_jump(energy, signal - background, l3, l2)

    fig, ax = plt.subplots()
    ax.plot(energy, signal, label='signal')
    ax.plot(energy, background, label='background')
    ax.legend()
    plt.show()

    assert p0 == approx(0)
    assert p1 == approx(0)
    assert p2 == approx(0)
    assert jump == approx(30 / 1.5)

    rm_bkg = signal - background
    assert rm_bkg[0] == approx(0, abs=0.0001)
    edge = double_l_edge(energy, jump, l3, 8.2, 0, 0.01, 0.01)
    rm_edge = rm_bkg - edge

    assert rm_edge[0] == approx(0, abs=0.01)
    assert rm_edge[-1] == approx(0, abs=0.01)

    fig, ax = plt.subplots()
    ax.plot(energy, signal, label='signal')
    ax.plot(energy, background, label='background')
    ax.plot(energy, edge, label='edge')
    ax.plot(energy, rm_edge, label='rm_background')
    ax.legend()
    plt.show()


@only_dls_file_system
def test_against_matlab_parameters(matlab_data):
    data_dir, init_params, fit_params = matlab_data
    # data written by mmg_toolbox (loaded by VBA)
    c1 = np.loadtxt(data_dir / 'mmg_37436_pc_1T.csv', delimiter=',')
    # c2 = np.loadtxt(data_dir / 'mmg_37439_nc_1T.csv', delimiter=',')

    energy = c1[:, 0]
    signal = c1[:, 1] / c1[:, 2]

    edge = MultiEdge.from_spectra(energy, signal)
    e0 = edge.energies()[0]
    soc = edge.element.spin_orbit
    e_ref = energy[:5].mean()
    intercept = signal[:5].mean()
    slope1 = preedge_slope(energy, signal, e0)
    slope2 = midedge_slope(energy, signal, e0, soc)
    slope3 = postedge_slope(energy, signal, e0, soc)
    if edge.element.symbol not in ['Cu', 'Co', 'Ni']:
        slope2 = slope1
    l3_en, l2_en = transition_points(e0, soc)
    background = background_three_region(energy, slope1, slope2, slope3, l3_en, l2_en, e_ref, intercept)
    rm_bkg = signal - background
    jump = l3_edge_jump(energy, rm_bkg, l3_en, l2_en)

    assert slope1 == approx(init_params['m11']['Current'], abs=0.0001)
    assert slope2 == approx(init_params['m12']['Current'], abs=0.0001)
    assert slope3 == approx(init_params['m13']['Current'], abs=0.0001)
    assert jump == approx(init_params['Int1']['Current'], abs=0.0001)

    fig, ax = plt.subplots()
    ax.plot(energy, signal, label='signal')
    ax.plot(energy, background, label='background')
    ax.plot(energy, rm_bkg, label='rm_background')
    ax.legend()
    plt.show()

    assert rm_bkg[0] == approx(0, abs=0.01)


@only_dls_file_system
def test_lmfit_models(matlab_data):
    data_dir, init_params, fit_params = matlab_data
    # data written by mmg_toolbox (loaded by VBA)
    c1 = np.loadtxt(data_dir / 'mmg_37436_pc_1T.csv', delimiter=',')
    # c2 = np.loadtxt(data_dir / 'mmg_37439_nc_1T.csv', delimiter=',')

    energy = c1[:, 0]
    signal = c1[:, 1] / c1[:, 2]

    model = BackgroundThreeRegionModel()
    params = model.guess(signal, x=energy)  # Fitting is performed here
    bkg = model.eval(params, energy=energy)
    rem_bkg = signal - bkg

    assert params['m1'].value == approx(init_params['m11']['Current'], abs=0.0001)
    assert params['m2'].value == approx(init_params['m12']['Current'], abs=0.0001)
    assert params['m3'].value == approx(init_params['m13']['Current'], abs=0.0001)
    assert params['t1'].value == approx(init_params['T11']['Current'], abs=0.0001)
    assert params['t2'].value == approx(init_params['T12']['Current'], abs=0.0001)
    assert abs(rem_bkg[0]) < 0.01

    model2 = DoubleLEdgeModel()
    params2 = model2.guess(rem_bkg, x=energy)
    edge = model2.eval(params2, energy=energy)
    rem_bkg = rem_bkg - edge

    assert params2['e0_l3'].value == approx(init_params['E0']['Current'], abs=0.0001)
    assert params2['intensity_l3'].value == approx(init_params['Int1']['Current'], abs=0.0004)
    assert params2['spin_orbit_2p'].value == approx(init_params['SOC2p']['Current'], abs=0.0001)
    assert abs(rem_bkg[0]) < 0.01
    assert abs(rem_bkg[-1]) < 0.01

    fig, ax = plt.subplots()
    ax.plot(energy, signal, label='signal')
    ax.plot(energy, bkg, label='background')
    ax.plot(energy, edge, label='edge')
    ax.plot(energy, rem_bkg, label='rm_background')
    ax.legend()
    plt.show()

    # assert False



