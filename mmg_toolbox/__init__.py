"""
Magnetic Materials Group Toolbox
"""

import sys
from mmg_toolbox.utils.file_reader import data_file_reader
from mmg_toolbox.utils.experiment import Experiment

__version__ = '0.4.2'
__date__ = '12/11/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui', 'version_info', 'title', 'module_info', 'data_file_reader', 'Experiment']


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
    import tkinter
    out += '\n   tkinter version: %s' % tkinter.TkVersion
    out += '\n'
    return out
