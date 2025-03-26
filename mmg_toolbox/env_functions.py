"""
Environment functions
"""

import os
import re
import subprocess
from datetime import datetime

# environment variables on beamline computers
BEAMLINE = 'BEAMLINE'
USER = ['USER', 'USERNAME']
DLS = '/dls'
MMG_BEAMLINES = ['i06', 'i06-1', 'i06-2', 'i10', 'i10-1', 'i16', 'i21']

regex_scan_number = re.compile(r'\d{3,}')


# Initialise available beamlines
YEAR = str(datetime.now().year)
AVAILABLE_EXPIDS = {
    beamline: {
        os.path.basename(path): path for path in sorted(
            (file.path for file in os.scandir(os.path.join(DLS, beamline, 'data', YEAR))
             if file.is_dir() and os.access(file.path, os.R_OK)),
            key=lambda x: os.path.getmtime(x)
        )
    } for beamline in MMG_BEAMLINES
} if os.path.isdir(DLS) else {}


def get_beamline():
    """Return current beamline from environment variable"""
    return os.environ.get(BEAMLINE, '')


def get_user():
    """Return current user from environment variable"""
    return next((os.environ[u] for u in USER if u in os.environ), '')


def get_data_directory():
    """Return the default data directory"""
    beamline = get_beamline()
    year = datetime.now().year
    if beamline:
        return f"/dls/{beamline}/data/{year}"
    return os.path.expanduser('~')


def get_dls_visits(instrument: str | None = None, year: str | int | None = None) -> dict[str, ...]:
    """Return list of visits"""
    if instrument is None:
        instrument = get_beamline()
    if year is None:
        year = datetime.now().year

    dls_dir = os.path.join('/dls', instrument.lower(), 'data', str(year))
    if os.path.isdir(dls_dir):
        return {p.name: p.path for p in os.scandir(dls_dir) if p.is_dir()}
    return {}


def get_scan_number(filename: str) -> int:
    """Return scan number from scan filename"""
    filename = os.path.basename(filename)
    match = regex_scan_number.search(filename)
    if match:
        return int(match[0])
    return 0


def replace_scan_number(filename: str, new_number: int) -> str:
    """Replace scan number in filename"""
    path, filename = os.path.split(filename)
    new_filename = regex_scan_number.sub(str(new_number), filename)
    return os.path.join(path, new_filename)


def run_command(command):
    """
    Run shell command, print output to terminal
    """
    print('\n\n\n################# Starting ###################')
    print(f"Running command:\n{command}\n\n\n")
    output = subprocess.run(command, shell=True, capture_output=True)
    print(output.stdout.decode())
    print('\n\n\n################# Finished ###################\n\n\n')