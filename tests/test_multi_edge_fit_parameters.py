"""
mmg_toolbox tests
Test XAS Multi-Edge Fit Parameters
"""

from pytest import approx
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox.xas.multi_edge_fit_parameters import edge_energy, get_atomic_system, get_spin_orbit
from mmg_toolbox.xas.multi_edge_fit_parameters import (preedge_slope, midedge_slope, postedge_slope,
                                                       energy_reference, transition_points, edge_jump)
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

DATA_DIR = Path('/dls/science/groups/das/ExampleData/xmcd/virtual_beamline_app/')
INIT_PARAMS = json.load(open(DATA_DIR / 'vba_init_params.json'))
FIT_PARAMS = json.load(open(DATA_DIR / 'vba_fit_params.json'))


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
    jump = edge_jump(energy, signal, p0, p1, p2, l3, l2, signal[0])

    assert p0 == approx(0)
    assert p1 == approx(0)
    assert p2 == approx(0)
    assert jump == approx(30 / 1.5)

    background = background_three_region(energy, p0, p1, p2, l3, l2, energy[1], signal[1])
    rm_bkg = signal - background
    assert rm_bkg[0] == approx(0, abs=0.0001)
    edge = double_l_edge(energy, jump, l3, 8.2, 0, 0.01, 0.01)
    rm_edge = rm_bkg - edge

    assert rm_edge[0] == approx(0, abs=0.01)
    assert rm_edge[-1] == approx(0, abs=0.01)

    # fig, ax = plt.subplots()
    # ax.plot(energy, signal, label='signal')
    # ax.plot(energy, background, label='background')
    # ax.plot(energy, edge, label='edge')
    # ax.plot(energy, rm_edge, label='rm_background')
    # ax.legend()
    # plt.show()


@only_dls_file_system
def test_against_matlab_parameters():
    # data written by mmg_toolbox (loaded by VBA)
    c1 = np.loadtxt(DATA_DIR / 'mmg_37436_pc_1T.csv', delimiter=',')
    # c2 = np.loadtxt(DATA_DIR / 'mmg_37439_nc_1T.csv', delimiter=',')

    energy = c1[:, 0]
    signal = c1[:, 1] / c1[:, 2]

    e0 = edge_energy(energy, signal)
    atsym = get_atomic_system(energy)
    soc, nd = get_spin_orbit(atsym)
    e_shift = energy[:5].mean()
    intercept = signal[:5].mean()
    slope1 = preedge_slope(energy, signal, e0)
    slope2 = midedge_slope(energy, signal, e0, soc)
    slope3 = postedge_slope(energy, signal, e0, soc)
    if atsym[:2] not in ['Cu', 'Co', 'Ni']:
        slope2 = slope1
    l3_en, l2_en = transition_points(e0, soc)
    jump = edge_jump(energy, signal, slope1, slope2, slope3, l3_en, l2_en, intercept)

    assert slope1 == approx(INIT_PARAMS['m11']['Current'], abs=0.0001)
    assert slope2 == approx(INIT_PARAMS['m12']['Current'], abs=0.0001)
    assert slope3 == approx(INIT_PARAMS['m13']['Current'], abs=0.0001)
    assert jump == approx(INIT_PARAMS['Int1']['Current'], abs=0.0001)

    background = background_three_region(energy, slope1, slope2, slope3, l3_en, l2_en, e_shift, intercept)
    rm_bkg = signal - background

    fig, ax = plt.subplots()
    ax.plot(energy, signal, label='signal')
    ax.plot(energy, background, label='background')
    ax.plot(energy, rm_bkg, label='rm_background')
    ax.legend()
    plt.show()

    assert rm_bkg[0] == approx(0, abs=0.01)


@only_dls_file_system
def test_lmfit_models():
    # data written by mmg_toolbox (loaded by VBA)
    c1 = np.loadtxt(DATA_DIR / 'mmg_37436_pc_1T.csv', delimiter=',')
    # c2 = np.loadtxt(DATA_DIR / 'mmg_37439_nc_1T.csv', delimiter=',')

    energy = c1[:, 0]
    signal = c1[:, 1] / c1[:, 2]

    model = BackgroundThreeRegionModel()
    params = model.guess(signal, x=energy)  # Fitting is performed here
    bkg = model.eval(params, energy=energy)
    rem_bkg = signal - bkg

    assert params['m1'].value == approx(INIT_PARAMS['m11']['Current'], abs=0.0001)
    assert params['m2'].value == approx(INIT_PARAMS['m12']['Current'], abs=0.0001)
    assert params['m3'].value == approx(INIT_PARAMS['m13']['Current'], abs=0.0001)
    assert params['t1'].value == approx(INIT_PARAMS['T11']['Current'], abs=0.0001)
    assert params['t2'].value == approx(INIT_PARAMS['T12']['Current'], abs=0.0001)
    assert abs(rem_bkg[0]) < 0.01

    model2 = DoubleLEdgeModel()
    params2 = model2.guess(rem_bkg, x=energy)
    edge = model2.eval(params2, energy=energy)
    rem_bkg = rem_bkg - edge

    assert params2['e0_l3'].value == approx(INIT_PARAMS['E0']['Current'], abs=0.0001)
    assert params2['intensity_l3'].value == approx(INIT_PARAMS['Int1']['Current'], abs=0.0004)
    assert params2['spin_orbit_2p'].value == approx(INIT_PARAMS['SOC2p']['Current'], abs=0.0001)
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



