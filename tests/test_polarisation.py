"""
mmg_toolbox tests
Test polarisation functions
"""

import pytest
import numpy as np
import hdfmap

from mmg_toolbox.utils import polarisation as pol
from . import only_dls_file_system
from .example_files import FILES_DICT


def test_polarisation():
    assert pol.check_polarisation(pol.PolLabels.linear_horizontal) == 'lh'
    assert pol.check_polarisation(pol.PolLabels.linear_vertical) == 'lv'
    assert pol.check_polarisation(pol.PolLabels.circular_left) == 'cl'
    assert pol.check_polarisation(pol.PolLabels.circular_right) == 'cr'
    assert pol.check_polarisation(pol.PolLabels.circular_negative) == 'cl'
    assert pol.check_polarisation(pol.PolLabels.circular_positive) == 'cr'
    assert pol.check_polarisation(pol.PolLabels.linear_arbitrary, 0) == 'lh'
    assert pol.check_polarisation(pol.PolLabels.linear_arbitrary, 90) == 'lv'
    assert pol.check_polarisation(pol.PolLabels.linear_arbitrary, 30) == 'la'
    assert pol.check_polarisation(np.array([1,1,0,0])) == 'lh'
    assert pol.check_polarisation(None, 60) == 'la'
    assert pol.pol_subtraction_label('pc') == 'xmcd'
    assert pol.pol_subtraction_label('lv') == 'xmld'


@only_dls_file_system
def test_read_polarisation():
    filename = FILES_DICT['i16 pilatus eta scan, new nexus format']
    with hdfmap.load_hdf(filename) as hdf:
        polarisation = pol.get_polarisation(hdf)

    assert polarisation == pol.PolLabels.linear_horizontal

    filename = FILES_DICT['i10-1 la pol']

    with hdfmap.load_hdf(filename) as hdf:
        polarisation = pol.get_polarisation(hdf)

    assert polarisation == pol.PolLabels.linear_arbitrary


def test_arbitrary_polarisation():
    p0, p1, p2, p3 = pol.stokes_from_vector(30)
    assert pol.polarisation_label_from_stokes(p0, p1, p2, p3) == 'la'