"""
Script to create notebooks at start of experiment
"""

import os
import argparse

from mmg_toolbox.utils.env_functions import (get_beamline_from_directory, get_processing_directory,
                                             get_dls_visits, open_jupyter_lab)
from mmg_toolbox.beamline_metadata.default_scripts import create_beamline_scripts


def create_notebooks(directory: str | None = None, beamline: str | None = None,
                     start_jupyter: bool | None = None, prefix: str = '', quiet: bool = False):
    """
    Create notebooks at start of experiment

    :param directory: directory where to create notebooks, or visit ID for current beamline
    :param beamline: Beamline name, e.g. i06-1
    :param start_jupyter: start jupyter lab
    :param prefix: prefix for notebook/ script filenames
    :param quiet: quiet mode (no user inputs)
    """
    print("Creating experiment notebooks for mmg_toolbox")
    print(f"Directory: {directory}, Beamline: {beamline}")
    # Beamline
    if beamline is None:
        if directory is None and not quiet:
            beamline = input("Which beamline? e.g. i06-1:")
        else:
            beamline = get_beamline_from_directory(directory or '', default='')

    # Visits (from beamline)
    visits = get_dls_visits(beamline)
    current_visit = next(iter(visits.keys()), os.getcwd())
    if directory is None and not quiet:
        if visits:
            print(f"Visits for beamline {beamline}:\n  " + "\n  ".join(visits))
        directory = input(f"Which visit or directory? [default: {current_visit}]:")
    if not directory:
        directory = current_visit
    if directory in visits:
        directory = visits[directory]

    # Directory (from visits)
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory {directory} does not exist")
    processing_directory = get_processing_directory(directory)
    if not quiet and os.path.isdir(get_processing_directory(directory)):
        use_processing = input("Use the processing directory? [Y/n]:")
        if use_processing.lower() == 'y':
            directory = processing_directory

    # Beamline (again, from directory)
    if not beamline:
        beamline = get_beamline_from_directory(directory, default='')

    print(f"Creating notebooks for {beamline} in {directory}")
    title = f"{beamline} {os.path.basename(directory)} mmg_toolbox Example Script"
    create_beamline_scripts(beamline, directory, prefix=prefix, title=title)

    # Start Jupyter
    if not quiet and start_jupyter is None:
        start_jupyter = input("Would you like to start Jupyter? [Y/n]:")
        start_jupyter = start_jupyter.lower() == 'y'
    if start_jupyter:
        open_jupyter_lab(directory)


def cli() -> dict[str, str | None]:
    parser = argparse.ArgumentParser(
        prog='mmg_toolbox',
        description='Create notebooks at start of experiment'
    )
    parser.add_argument("directory", nargs='?', default=None,
                        help="The working directory (if ./processing exists, this will be chosen)", type=str)
    parser.add_argument("-b", "--beamline", help='Beamline to use', type=str)
    parser.add_argument("-v", "--visit", help='Visits to use as working directory', type=str)
    parser.add_argument("-p", "--prefix", type=str, default='', help="Prefix for script filenames")
    parser.add_argument("-j", "--jupyter", action='store_true', default=None,
                        help='Start Jupyter lab in working directory')
    parser.add_argument("-q", "--quiet", action='store_true', help='Do not start Jupyter lab on startup')
    args = parser.parse_args()
    print('input args:', args)

    return dict(
        directory=args.directory or args.visit,
        beamline=args.beamline,
        start_jupyter=args.jupyter,
        prefix=args.prefix,
        quiet=args.quiet
    )


def cli_create_notebooks():
    create_notebooks(**cli())
