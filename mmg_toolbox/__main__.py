"""
Main MMG Runscript
"""

import sys

if __name__ == '__main__':
    # Start up interactive console
    import sys
    import numpy as np
    import matplotlib.pyplot as plt
    import mmg_toolbox as mmg

    print(f"""
    {mmg.version_info()}
    By Dan Porter, Diamond Light Source Ltd.
    
    See help(mmg) for info, or scan = mmg.data_file_reader('file.nxs') to get started!
    """)


