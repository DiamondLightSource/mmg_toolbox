"""
mmg_toolbox tests
Test experiment folder functions
"""

import mmg_toolbox.beamline_metadata.config as config
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapXASMetadata as Md
from . import only_dls_file_system
from .example_files import DIR


def test_config():
    cfg = config.beamline_config('i16')
    assert cfg[config.C.beamline] == 'i16'
    assert 'Atten' in cfg[config.C.metadata_string]

    cfg = config.beamline_config('i06-1')
    assert cfg[config.C.beamline] == 'i06-1'
    assert 'field =' in cfg[config.C.metadata_string]
    assert cfg[config.C.default_directory].startswith('/dls/i06-1/data/')

    cfg = config.beamline_config('i32')
    assert cfg[config.C.beamline] == 'i32'

    cfg = config.beamline_config()
    assert len(cfg[config.C.roi]) == 0


@only_dls_file_system
def test_metadata_names():
    import hdfmap
    f = DIR + 'i10/i10-1-26851.nxs'
    m = hdfmap.NexusMap()
    expressions = (name for name in dir(Md) if not name.startswith('_'))
    with hdfmap.load_hdf(f) as h:
        m.populate(h)
        for expression in expressions:
            print(expression, getattr(Md, expression))
            value = m.eval(h, getattr(Md, expression), default=None)
            print(expression, getattr(Md, expression), value)
            assert value is not None

