"""
Magnetic Materials Group Toolbox
"""

__version__ = '0.1'
__date__ = '08/04/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui']


def start_gui():
    from .tkguis import create_title_window
    create_title_window()

