"""
mmg_toolbox tests
Test polarisation functions
"""

import pytest
import hdfmap

from mmg_toolbox.utils import polarisation as pol
from . import only_dls_file_system
from .example_files import FILES


def test_polarisation():
    assert pol.check_polarisation(pol.PolLabels.linear_horizontal) == 'lh'
    assert pol.check_polarisation(pol.PolLabels.linear_vertical) == 'lv'
    assert pol.check_polarisation(pol.PolLabels.circular_left) == 'cl'
    assert pol.check_polarisation(pol.PolLabels.circular_right) == 'cr'
    assert pol.check_polarisation(pol.PolLabels.circular_negative) == 'cl'
    assert pol.check_polarisation(pol.PolLabels.circular_positive) == 'cr'
    assert pol.pol_subtraction_label('pc') == 'xmcd'
    assert pol.pol_subtraction_label('lv') == 'xmld'


@only_dls_file_system
def test_read_polarisation():
    filename, description = FILES[4]
    with hdfmap.load_hdf(filename) as hdf:
        polarisation = pol.get_polarisation(hdf)

    assert polarisation == pol.PolLabels.linear_horizontal