"""
mmg_toolbox tests
Test Spectra Analysis Functions
"""

from pytest import approx
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

    element, edges = spa.energy_range_edge_label(850, 875)
    assert element + edges == 'NiL3, L2'

    element, edges = spa.energy_range_edge_label(523, 560)
    assert element + edges == 'OK'

    # element, edges = spa.energy_range_edge_label(1225, 1250)
    # assert element + edges == 'TbM5'  # currently gives GeL2


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


def test_find_shift():
    from mmg_toolbox.fitting.functions import gauss
    en1 = np.arange(600, 700, 0.1)
    sig1 = gauss(en1, cen=645.3, fwhm=12.6, height=60, bkg=0)
    en2 = np.arange(598, 698, 0.1)
    sig2 = gauss(en2, cen=646.2, fwhm=12.6, height=60, bkg=0)
    en3 = np.arange(602, 705, 0.1)
    sig3 = gauss(en3, cen=643.1, fwhm=12.6, height=60, bkg=0) + gauss(en3, cen=655, fwhm=14, height=20)

    from scipy.signal import correlate
    av_en = np.linspace(
        max(en1.min(), en2.min()),
        min(en1.max(), en2.max()),
        len(en1) * 10
    )
    en_step = av_en[1] - av_en[0]
    i_sig1 = np.interp(av_en, en1, sig1)
    i_sig2 = np.interp(av_en, en2, sig2)
    corr = correlate(i_sig1, i_sig2, mode='full')

    lag = np.argmax(corr) - (len(av_en) - 1)
    shift = lag * en_step
    assert shift == approx(645.3 - 646.2, 0.001)

    shifts = spa.find_shifts((en1, sig1), (en2, sig2), (en3, sig3))
    assert shifts == approx([-0.02, shift, 0.76], abs=0.03)  # manual shift slightly different due to interpolation
    shifts_d = spa.find_shifts((en1, sig1), (en2, sig2), (en3, sig3), differentiate=True)
    assert shifts_d == approx([-0.02, -0.92, 1.86], abs=0.01)

    # check peaks are aligned
    peak1 = en1[np.argmax(sig1)] + shifts_d[0]
    peak2 = en2[np.argmax(sig2)] + shifts_d[1]
    peak3 = en3[np.argmax(sig3)] + shifts_d[2]
    assert  peak1 == approx(peak2, 0.001) == approx(peak3, 0.001)