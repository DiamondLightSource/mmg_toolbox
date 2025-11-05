"""
Command line interface for Dataviewer
"""

import sys
import os

from mmg_toolbox.utils.env_functions import get_beamline
from .misc.config import BEAMLINE_CONFIG, get_config
from .apps.experiment import create_title_window
from .apps.data_viewer import create_data_viewer
from .apps.nexus import create_nexus_viewer


def doc():
    from mmg_toolbox import tkguis
    help(tkguis)


def run(*args):
    """
    Command line interface for Dataviewer
    """
    if any(arg.lower() in ['-h', '--help', 'man'] for arg in args):
        doc()
        return

    beamline = next((bm for bm in BEAMLINE_CONFIG if bm in args), get_beamline())
    config = get_config(beamline=beamline)

    for n, arg in enumerate(args):
        if os.path.isdir(arg):
            create_data_viewer(arg, config=config)
            return
        elif os.path.isfile(arg):
            create_nexus_viewer(arg, config=config)
            return
    create_title_window(beamline)
    return


def cli_run():
    run(*sys.argv[1:])
