"""
mmg_toolbox tests
Test Spectra Analysis Functions
"""

from pytest import approx
import numpy as np

from mmg_toolbox.xas import spectra_analysis as spa


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