"""
mmg_toolbox tests
Test lmfit functions
"""
import pytest
import numpy as np

from mmg_toolbox import data_file_reader
from mmg_toolbox.utils.fitting import FitResults, peakfit, multipeakfit, gauss, Peak

from . import only_dls_file_system
from .example_files import DIR

@pytest.fixture
def example_peak():
    x = np.linspace(-3, 2, 100)
    y = gauss(x, height=10, cen=-0.5, fwhm=0.8, bkg=0.1)
    yield x, y


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
    assert result.amplitude == pytest.approx(1349267.96, abs=0.01)
