"""
Magnetic Materials Group Toolbox
"""

__version__ = '0.1'
__date__ = '11/10/2025'
__author__ = 'Dan Porter'

__all__ = ['start_gui']


def start_gui():
    from .env_functions import get_data_directory
    from .tkguis import create_file_browser
    create_file_browser(initial_directory=get_data_directory())

