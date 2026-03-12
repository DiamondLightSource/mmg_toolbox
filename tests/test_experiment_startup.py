"""
mmg_toolbox tests
Test experiment folder functions
"""

import os
import subprocess

from . import only_dls_file_system
from .example_files import FILES_DICT

def test_cli_inputs():
    py_cmd = "python -c \"from mmg_toolbox.scripts.experiment_startup import cli; print(cli())\" "

    def run(cmd):
        print(f"Running: {py_cmd+cmd}")
        output = subprocess.run(py_cmd+cmd, shell=True, capture_output=True)
        return output.stdout.decode()

    command = '.'
    out = run(command)
    assert "{'directory': '.', 'beamline': None, 'start_jupyter': None, 'prefix': '', 'quiet': False}" in out

    command = '-v mm12345-1 -b i16 -j'
    out = run(command)
    assert "{'directory': 'mm12345-1', 'beamline': 'i16', 'start_jupyter': True, 'prefix': '', 'quiet': False}" in out


@only_dls_file_system
def test_cli_create_notebooks():
    directory = os.path.dirname(FILES_DICT['i10 scan'])
    command = f"python -c \"from mmg_toolbox.scripts.experiment_startup import cli_create_notebooks; cli_create_notebooks()\" -b i10-1 -q {directory}"

    print(f"Running: {command}")
    output = subprocess.run(command, shell=True, capture_output=True)
    print('Output:')
    print(output.stdout.decode())

    assert os.path.isfile(f"{directory}/example.py")
    assert os.path.isfile(f"{directory}/example.ipynb")
    # assert os.path.isfile(f"{directory}/peak fitting.py")
    # assert os.path.isfile(f"{directory}/plot multi-line.py")
    assert os.path.isfile(f"{directory}/spectra.py")
    assert os.path.isfile(f"{directory}/xmcd.ipynb")

    os.remove(f"{directory}/example.py")
    os.remove(f"{directory}/example.ipynb")
    # os.remove(f"{directory}/peak fitting.py")
    # os.remove(f"{directory}/plot multi-line.py")
    os.remove(f"{directory}/spectra.py")
    os.remove(f"{directory}/xmcd.ipynb")


