"""
Command line interface for mmg_toolbox Dataviewer

    $ dataviewer

Open an experiment selection window for the default beamline by default,
however other options are available.

CLI Options:
    -h, --help              show this help message and exit
    experiment/directory    open a specific folder containing nexus files
    scan/file.nxs           open a specific NeXus file to view the tree
    beamline                open a experiment selection window for beamline
"""

import sys
import os

from mmg_toolbox.utils.env_functions import get_beamline, get_beamline_from_directory
from .misc.config import BEAMLINE_CONFIG, get_config
from .apps.experiment import create_title_window
from .apps.data_viewer import create_data_viewer
from .apps.nexus import create_nexus_viewer


def doc():
    print(__doc__)
    print(f"Available beamlines: {list(BEAMLINE_CONFIG.keys())}")


def run(*args):
    """
    Command line interface for Dataviewer
    """
    if any(arg.lower() in ['-h', '--help', 'man'] for arg in args):
        doc()
        return

    beamline = next((bm for bm in BEAMLINE_CONFIG if bm in args), get_beamline())

    for n, arg in enumerate(args):
        if os.path.isdir(arg):
            beamline = get_beamline_from_directory(os.path.abspath(arg), beamline)
            config = get_config(beamline=beamline)
            create_data_viewer(arg, config=config)
            return
        elif os.path.isfile(arg):
            beamline = get_beamline_from_directory(os.path.abspath(arg), beamline)
            config = get_config(beamline=beamline)
            create_nexus_viewer(arg, config=config)
            return
        elif arg in BEAMLINE_CONFIG:
            beamline = arg
    create_title_window(beamline)
    return


def cli_run():
    run(*sys.argv[1:])
