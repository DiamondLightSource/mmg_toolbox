"""
Script to create notebooks at start of experiment
"""

import os
import argparse

from mmg_toolbox.utils.env_functions import (get_beamline_from_directory, get_processing_directory,
                                             get_dls_visits, open_jupyter_lab)
from mmg_toolbox.beamline_metadata.default_scripts import create_beamline_scripts


def create_notebooks(directory: str | None = None, beamline: str | None = None, start_jupyter: bool | None = None):
    """
    Create notebooks at start of experiment
    """
    print(f"Creating experiment notebooks for mmg_toolbox")
    if beamline is None:
        if directory is None:
            beamline = input("Which beamline? e.g. i06-1:")
        else:
            beamline = get_beamline_from_directory(directory, default='')

    visits = get_dls_visits(beamline)
    current_visit = next(iter(visits.keys()))
    if directory is None:
        directory = input(f"Which visit or directory? [default: {current_visit}]:")
        if directory is None:
            directory = current_visit

    if directory in visits:
        directory = visits[directory]
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory {directory} does not exist")
    processing_directory = get_processing_directory(directory)
    if os.path.isdir(get_processing_directory(directory)):
        use_processing = input("Use the processing directory? [Y/n]:")
        if use_processing.lower() == 'y':
            directory = processing_directory

    if beamline is None:
        beamline = get_beamline_from_directory(directory, default='')

    print(f"Creating notebooks for {beamline} in {directory}")
    title = f"{beamline} {os.path.basename(directory)} mmg_toolbox Example Script"
    create_beamline_scripts(beamline, directory, title=title)

    # Start Jupyter
    if start_jupyter is None:
        start_jupyter = input("Would you like to start Jupyter? [Y/n]:")
    if start_jupyter == True or str(start_jupyter).lower() == 'y':
        open_jupyter_lab(directory)


def cli_create_notebooks():
    parser = argparse.ArgumentParser(
        prog='mmg_toolbox',
        description='Create notebooks at start of experiment'
    )
    parser.add_argument("-b", "--beamline", help='Beamline to use', type=str)
    parser.add_argument("-d", "--directory", help='Working directory', type=str)
    parser.add_argument("-v", "--visit", help='Visits to use as working directory', type=str)
    parser.add_argument("-j", "--jupyter", action='store_true', help='Start Jupyter lab in working directory')
    parser.add_argument("-q", "--quiet", action='store_true', help='Do not start Jupyter lab on startup')
    args = parser.parse_args()

    if args.quiet:
        start_jupyter = False
    elif args.jupyter:
        start_jupyter = True
    else:
        start_jupyter = None

    create_notebooks(
        directory=args.directory or args.visit,
        beamline=args.beamline,
        start_jupyter=start_jupyter,
    )
