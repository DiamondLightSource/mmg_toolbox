"""
mmg_toolbox tests
Test lmfit functions
"""
import pytest
import numpy as np
from lmfit.models import GaussianModel

from mmg_toolbox import data_file_reader
from mmg_toolbox.fitting import FitResults, peakfit, multipeakfit, gauss, Peak

from . import only_dls_file_system
from .example_files import DIR

@pytest.fixture
def example_peak():
    x = np.linspace(-3, 2, 100)
    y = gauss(x, height=10, cen=-0.5, fwhm=0.8, bkg=0.1)
    yield x, y


def test_gauss():
    x = np.linspace(-1, 1, 100)
    h, c, w, b = 10, 0, 0.2, 0
    amplitude = h * w * 1.064467  # area
    sigma = w / 2.348200
    g = gauss(x, height=h, cen=c, fwhm=w, bkg=b)

    g_area = np.trapezoid(g, x)
    g_height = np.max(g)
    assert pytest.approx(g_area, abs=1e-2) == amplitude
    assert pytest.approx(g_height, abs=0.1) == h

    g_model = GaussianModel()
    pars = g_model.make_params(amplitude=amplitude, center=c, sigma=sigma)
    g_lmfit = g_model.eval(pars, x=x)

    g_lm_area = np.trapezoid(g_lmfit, x)
    g_lm_height = np.max(g_lmfit)
    assert pytest.approx(g_lm_area, abs=1e-2) == amplitude
    assert pytest.approx(g_lm_height, abs=0.1) == h

    # Check integration
    area = np.sum(g) * np.mean(np.diff(x))
    assert pytest.approx(area, abs=1e-2) == amplitude

    # Check Gauss2D
    y = np.linspace(-1, 1, 100)
    g2d = gauss(x, y, height=h, cen=c, fwhm=w, bkg=b)
    amplitude2 = h * w * w * (np.pi / (4*np.log(2)))
    integral2 = np.trapezoid(np.trapezoid(g2d, y, axis=0), x, axis=0)
    assert g2d.shape == (100, 100)
    area_2d = np.sum(g2d) * np.mean(np.diff(x))  * np.mean(np.diff(y))
    height_2d = np.max(g2d)
    assert pytest.approx(area_2d, abs=1e-2) == amplitude2
    assert pytest.approx(area_2d, abs=1e-2) == integral2
    assert pytest.approx(height_2d, abs=0.15) == h

    # Check Gauss2D with different values
    y = np.linspace(-10, -2, 300)
    h, c, c2, w, w2, b = 10, -0.1, -5, 0.2, 0.5, 0
    g2d = gauss(x, y, height=h, cen=c, fwhm=w, bkg=b, cen_y=c2, fwhm_y=w2)
    amplitude2 = h * w * w2 * (np.pi / (4 * np.log(2)))
    integral2 = np.trapezoid(np.trapezoid(g2d, y, axis=0), x, axis=0)
    assert g2d.shape == (300, 100)
    area_2d = np.sum(g2d) * np.mean(np.diff(x)) * np.mean(np.diff(y))
    height_2d = np.max(g2d)
    assert pytest.approx(area_2d, abs=1e-2) == amplitude2
    assert pytest.approx(area_2d, abs=1e-2) == integral2
    assert pytest.approx(height_2d, abs=0.15) == h





def test_peak_fit(example_peak):
    x, y = example_peak
    result = peakfit(x, y)
    print(result)
    assert isinstance(result, FitResults)
    assert abs(result.height - 10) < 1
    assert abs(result.center + 0.5) < 0.01
    assert abs(result.fwhm - 0.8) < 0.1
    assert abs(result.background - 0.1) < 1
    assert result.amplitude > 3 * result.stderr_amplitude


def test_multipeakfit(example_peak):
    x, y = example_peak
    result = multipeakfit(x, y)
    assert isinstance(result, FitResults)
    assert result.npeaks == 1
    assert abs(result.height - 10) < 1
    assert abs(result.center + 0.5) < 0.01
    assert abs(result.fwhm - 0.8) < 0.1
    assert abs(result.background - 0.1) < 1
    assert result.amplitude > 3 * result.stderr_amplitude

    for peak in result:
        print(peak)
        assert isinstance(peak, Peak)
        assert result.amplitude == pytest.approx(8.52, abs=0.01)


@only_dls_file_system
def test_scan_fit():
    file = DIR + f'/i16/777777.nxs'
    scan = data_file_reader(file)

    result = scan.fit.multi_peak_fit('eta', 'sum', model='pVoight')
    assert result.npeaks == len(result) == 5
    assert result.amplitude == pytest.approx(1.3493e6, abs=1e3)
