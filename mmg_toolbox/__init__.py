"""
Magnetic Materials Group Toolbox
"""

__version__ = '0.2.0'
__date__ = '19/06/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui']


def start_gui():
    from .tkguis import create_title_window
    create_title_window()

