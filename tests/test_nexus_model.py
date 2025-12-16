"""
mmg_toolbox tests
Test nx transformations
"""

from mmg_toolbox.nexus.instrument_model import NXInstrumentModel
from mmg_toolbox.nexus.nexus_reader import read_nexus_file
from . import only_dls_file_system
from .example_files import DIR

@only_dls_file_system
def test_read_nexus_file():
    f = DIR + 'i16/1116988.nxs'
    scan = read_nexus_file(f)
    model = scan.instrument_model()
    assert isinstance(model, NXInstrumentModel)

