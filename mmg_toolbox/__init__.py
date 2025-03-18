"""
Magnetic Materials Group Toolbox
"""

__version__ = '0.1'
__date__ = '18/03/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui']


def start_gui():
    from .tkguis import create_data_viewer
    create_data_viewer()

