"""
Environment functions
"""

import os
import subprocess
from datetime import datetime

# environment variables on beamline computers
BEAMLINE = 'BEAMLINE'
USER = ['USER', 'USERNAME']


def get_beamline():
    """Return current beamline from environment variable"""
    return os.environ.get(BEAMLINE, '')


def get_user():
    """Return current user from environment variable"""
    return next((os.environ[u] for u in USER if u in os.environ), '')


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


def run_command(command):
    """
    Run shell command, print output to terminal
    """
    print('\n\n\n################# Starting ###################')
    print(f"Running command:\n{command}\n\n\n")
    output = subprocess.run(command, shell=True, capture_output=True)
    print(output.stdout.decode())
    print('\n\n\n################# Finished ###################\n\n\n')