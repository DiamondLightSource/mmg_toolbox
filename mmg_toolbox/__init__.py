"""
Magnetic Materials Group Toolbox
"""

import sys
from file_reader import data_file_reader

__version__ = '0.2.1'
__date__ = '30/07/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui', 'version_info', 'title', 'module_info', 'data_file_reader']


def start_gui():
    from .tkguis import create_title_window
    create_title_window()


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
