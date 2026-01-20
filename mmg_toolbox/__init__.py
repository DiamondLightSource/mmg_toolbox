"""
Magnetic Materials Group Toolbox
"""

import sys
from mmg_toolbox.utils.file_reader import data_file_reader
from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.beamline_metadata import metadata, xas_metadata, nexus_metadata

__version__ = '0.5.1'
__date__ = '20/01/2026'
__author__ = 'Dan Porter'

__all__ = ['start_gui', 'version_info', 'title', 'module_info',
           'data_file_reader', 'Experiment', 'metadata', 'xas_metadata', 'nexus_metadata']


def start_gui(*args: str):
    from mmg_toolbox.tkguis import run
    run(*args)


def version_info():
    return 'mmg_toolbox version %s (%s)' % (__version__, __date__)


def title():
    return 'mmg_toolbox  version %s' % __version__


def module_info():
    out = 'Python version %s' % sys.version
    out += '\n%s' % version_info()
    # Modules
    import numpy
    out += '\n     numpy version: %s' % numpy.__version__
    try:
        import matplotlib
        out += '\nmatplotlib version: %s' % matplotlib.__version__
    except ImportError:
        out += '\nmatplotlib version: None'
    try:
        import hdfmap
        out += '\nhdfmap version: %s (%s)' % (hdfmap.__version__, hdfmap.__date__)
    except ImportError:
        out += '\nhdfmap version: Not available'
    try:
        import tkinter
        out += '\n   tkinter version: %s' % tkinter.TkVersion
    except ImportError:
        out += '\ntkinter version: Not available'
    out += '\n'
    return out
