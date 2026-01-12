"""
mmg_toolbox tests
Test utils.misc_functions
"""

import numpy as np
from mmg_toolbox.utils.misc_functions import (stfm, consolidate_numeric_strings, findranges, numbers2string,
                                              round_string_floats, shorten_string, data_holder)


def test_stfm():
    assert '35.25 (1)' == stfm(35.25, 0.01)
    assert '110 (5)' == stfm(110.25, 5)
    assert '0.0015300 (5)' == stfm(0.00153, 0.0000005)
    assert '1.56(2)E+6' == stfm(1.5632e6, 1.53e4)
    assert '0.00 (1)' == stfm(0, 0.01)


def test_consolidate_numeric_strings():
    my_range = list(range(12345, 12355)) + list(range(12357, 12365, 2))
    filenames = [f"i06-{n}.nxs" for n in my_range] + [f"i06-1-{n}.nxs" for n in my_range[:10]]
    strings = consolidate_numeric_strings(*filenames)
    assert len(strings) == 2
    assert strings == ['i06-####.nxs .. [123[45:54,57:2:63]]', 'i06-1-####.nxs .. [123[45:54]]']


def test_find_ranges():
    assert findranges([1, 2, 3, 4, 5]) == '1:5'
    assert findranges([1, 2, 3, 4, 5, 10, 12, 14, 16]) == '1:5,10:2:16'


def test_numbers2string():
    assert numbers2string([50001, 50002, 50003]) == '5000[1:3]'
    assert numbers2string([51020, 51030, 51040]) == '510[20:10:40]'


def test_round_string_floats():
    s = '#810002 scan eta 74.89533603616637 76.49533603616636 0.02 pil3_100k 1 roi2'
    assert round_string_floats(s) == '#810002 scan eta 74.895 76.495 0.02 pil3_100k 1 roi2'


def test_shorten_string():
    s = '\n #810002 scan eta 74.89533603616637 76.49533603616636 0.02 pol hkl checkbeam msmapper euler pil3_100k 1 roi2 \n other commands'
    assert shorten_string(s) == '#810002 scan eta 74.895 76.495 0.02 pol hkl checkbeam msmapper euler pil3_100k 1 roi2'
    out = shorten_string(s, 40, 10)
    assert len(out) == 40
    assert out == '#810002 scan eta 74.895 7 ... 00k 1 roi2'


def test_data_holder():
    scans = {'eta': np.arange(10), 'sum': np.arange(10)}
    metadata = {'a': 10, 'b': 20, 'c': 'hello'}
    d = data_holder(scans, metadata)
    assert hasattr(d, 'eta')
    assert hasattr(d, 'sum')
    assert hasattr(d.metadata, 'a')
    assert d.metadata.c == 'hello'


