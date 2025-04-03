"""
Environment functions
"""

import os
import re
import subprocess
import tempfile
from datetime import datetime

# environment variables on beamline computers
BEAMLINE = 'BEAMLINE'
USER = ['USER', 'USERNAME']
DLS = '/dls'
MMG_BEAMLINES = ['i06', 'i06-1', 'i06-2', 'i10', 'i10-1', 'i16', 'i21']

regex_scan_number = re.compile(r'\d{3,}')

# Find writable directory
TMPDIR = tempfile.gettempdir()
if not os.access(TMPDIR, os.W_OK):
    TMPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if not os.access(TMPDIR, os.W_OK):
        TMPDIR = os.path.expanduser('~')


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

    dls_dir = os.path.join(DLS, instrument.lower(), 'data', str(year))
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


def get_first_file(folder: str, extension='.nxs') -> str:
    """Return first scan in folder"""
    from mmg_toolbox.file_functions import list_files
    return next(iter(list_files(folder, extension=extension)))


def get_scan_numbers(folder: str) -> list[int]:
    """Return ordered list of scans numbers from nexus files in directory"""
    from mmg_toolbox.file_functions import list_files
    return sorted(
        number for filename in list_files(folder, extension='.nxs')
        if (number := get_scan_number(filename)) > 0
    )


def get_last_scan_number(folder: str) -> int:
    """Return latest scan number"""
    return get_scan_numbers(folder)[-1]


def run_command(command: str):
    """
    Run shell command, print output to terminal
    """
    print('\n\n\n################# Starting ###################')
    print(f"Running command:\n{command}\n\n\n")
    output = subprocess.run(command, shell=True, capture_output=True)
    print(output.stdout.decode())
    print('\n\n\n################# Finished ###################\n\n\n')


def open_terminal(command: str):
    """
    Open a new terminal window (linux only) and run a command
    """
    shell_cmd = f"gnome-terminal -- bash -c \"{command}; exec bash\""
    subprocess.Popen(shell_cmd, shell=True)


def run_python_script(script_filename: str):
    """
    Run shell command, print output to terminal
    """
    command = f"python {script_filename}"
    run_command(command)


def run_jupyter_notebook(notebook_filename: str):
    """
    Run a jupyter notebook
    """
    pass