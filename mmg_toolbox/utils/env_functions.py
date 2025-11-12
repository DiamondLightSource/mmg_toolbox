"""
Environment functions
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime

from mmg_toolbox.utils.file_functions import get_scan_number, list_files

# environment variables on beamline computers
BEAMLINE = 'BEAMLINE'
USER = ['USER', 'USERNAME']
DLS = '/dls'
MMG_BEAMLINES = ['i06', 'i06-1', 'i06-2', 'i10', 'i10-1', 'i16', 'i21']

# Find writable directory
TMPDIR = tempfile.gettempdir()
if not os.access(TMPDIR, os.W_OK):
    TMPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if not os.access(TMPDIR, os.W_OK):
        TMPDIR = os.path.expanduser('~')


# Initialise available beamlines
YEAR = str(datetime.now().year)


def check_file_access(filepath: str, append: str = '_new') -> str:
    """Check path has write access, if not, return appended path with write access"""
    # return filepath if it already exists and is writable
    if os.path.exists(filepath) and os.access(filepath, os.W_OK):
        return filepath
    tries = 0
    max_tries = 3

    path, name = os.path.split(filepath)
    if not os.access(path, os.W_OK):
        raise OSError(f"new file cannot be written as path is not writable: '{path}'")

    if os.path.exists(filepath):
        # filepath is not writeable, amend name
        name, ext = os.path.splitext(name)
        while os.path.exists(filepath) and not os.access(filepath, os.W_OK):
            if tries > max_tries:
                raise Exception(f"File is not writable: {filepath}")
            name += append
            filepath = os.path.join(path, name + ext)
            tries += 1
    return filepath


def get_beamline(default=''):
    """Return current beamline from environment variable"""
    return os.environ.get(BEAMLINE, default)


def get_user(default=''):
    """Return current user from environment variable"""
    return next((os.environ[u] for u in USER if u in os.environ), default)


def get_data_directory():
    """Return the default data directory"""
    beamline = get_beamline()
    year = datetime.now().year
    if beamline:
        return f"/dls/{beamline}/data/{year}"
    return os.path.expanduser('~')


def get_processing_directory(data_directory: str):
    """Return the processing directory of the visit"""
    return os.path.join(data_directory, 'processing')


def get_notebook_directory(data_directory: str):
    """Return the notebook directory of the visit"""
    return os.path.join(data_directory, 'processed', 'notebooks')


def get_dls_visits(instrument: str | None = None, year: str | int | None = None) -> dict[str, str]:
    """Return dict of {visit: path} for each visible visit in the beamline directory"""
    if instrument is None:
        instrument = get_beamline()
    if year is None:
        year = datetime.now().year

    dls_dir = os.path.join(DLS, instrument.lower(), 'data', str(year))
    if os.path.isdir(dls_dir):
        return {
            os.path.basename(path): path
            for path in sorted(
                (file.path for file in os.scandir(os.path.join(DLS, instrument, 'data', YEAR))
                 if file.is_dir() and os.access(file.path, os.R_OK)),
                key=lambda x: os.path.getmtime(x), reverse=True
            )
        }
    return {}


def get_first_file(folder: str, extension='.nxs') -> str:
    """Return first scan in folder"""
    return next(iter(list_files(folder, extension=extension)))


def get_scan_numbers(folder: str, extension: str = '.nxs') -> list[int]:
    """Return ordered list of scans numbers from nexus files in directory"""
    return sorted(
        number for filename in list_files(folder, extension=extension)
        if (number := get_scan_number(filename)) > 0
    )


def scan_number_mapping(*folders: str, extension: str = '.nxs') -> dict[int, str]:
    """Build mapping of scan number to scan file"""
    mapping = {
        number: filename
        for folder in folders
        for filename in list_files(folder, extension=extension)
        if (number := get_scan_number(filename)) > 0
    }
    return dict(sorted(mapping.items()))


def get_last_scan_number(folder: str) -> int:
    """Return latest scan number"""
    return get_scan_numbers(folder)[-1]


def last_folder_update(folder: str) -> datetime:
    """Returns datetime timestamp of last folder update"""
    modified = os.path.getmtime(folder)
    return datetime.fromtimestamp(modified)


def get_scan_notebooks(scan: int | str, data_directory: str | None = None) -> list[str]:
    """Return list of processed jupyter notebooks for scan"""
    try:
        data_directory, filename = os.path.split(scan)
        scan = get_scan_number(filename)
    except TypeError:
        pass
    notebook_directory = get_notebook_directory(data_directory)
    if os.path.isdir(notebook_directory):
        notebooks = list_files(notebook_directory, '.ipynb')
        return [notebook for notebook in notebooks if str(scan) in os.path.basename(notebook)]
    return []


def run_command(command: str):
    """
    Run shell command, print output to terminal
    """
    print('\n\n\n################# Starting ###################')
    print(f"Running command:\n{command}\n\n\n")
    output = subprocess.run(command, shell=True, capture_output=True)
    print(output.stdout.decode())
    print(output.stderr.decode())
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
    command = f"{sys.executable} {script_filename}"
    run_command(command)


def run_python_string(script: str):
    """
    Run shell command, print output to terminal
    """
    # command = f"{sys.executable} -c {script}"
    # run_command(command)
    subprocess.run([sys.executable, '-c', script])


def run_jupyter_notebook(notebook_filename: str):
    """
    Run a jupyter notebook
    """
    command = f"jupyter notebook {notebook_filename}"
    run_command(command)


def open_jupyter_lab():
    """
    Open a new terminal and start a Jupyter lab terminal (linux only)
    """
    shell_cmd = f"gnome-terminal -- bash -c \"jupyter lab; exec bash\""
    subprocess.Popen(shell_cmd, shell=True)