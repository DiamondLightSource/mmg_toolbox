"""
Main MMG Runscript
"""

import sys
from . import start_gui


if __name__ == '__main__':
    if 'gui' in sys.argv:
        start_gui()

    # Start up interactive console
    import sys
    import numpy as np
    import matplotlib.pyplot as plt
    import mmg_toolbox as mmg

    print(f"""
    {mmg.version_info()}
    By Dan Porter, Diamond Light Source Ltd.
    
    See help(mmg) for info, or mmg.start_gui() to get started!
    """)


