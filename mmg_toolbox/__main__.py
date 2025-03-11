"""
Main MMG Runscript
"""

import sys
from . import start_gui


if __name__ == '__main__':
    if 'gui' in sys.argv:
        start_gui()

