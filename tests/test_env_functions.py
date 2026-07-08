"""
mmg_toolbox tests
Test utils.misc_functions
"""

from mmg_toolbox.beamline_metadata.config import BEAMLINE_CONFIG
from mmg_toolbox.utils.env_functions import get_dls_visits

from . import only_dls_file_system

@only_dls_file_system
def test_dls_visits():
    for beamline in BEAMLINE_CONFIG:
        visits = get_dls_visits(beamline, omit_empty=True, max_visits=3)
        print(beamline, visits)
        assert len(visits) > 0