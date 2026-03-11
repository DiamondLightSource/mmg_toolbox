"""
mmg_toolbox tests
Test experiment folder functions
"""

import os
import subprocess

from . import only_dls_file_system
from .example_files import FILES_DICT

@only_dls_file_system
def test_cli_create_notebooks():
    directory = os.path.dirname(FILES_DICT['i10 scan'])
    command = f"python -c \"from mmg_toolbox import create_notebooks; create_notebooks()\"  -d {directory} -q"

    print(f"Running: {command}")
    output = subprocess.run(command, shell=True, capture_output=True)
    print('Output:')
    print(output.stdout.decode())

    assert os.path.isfile(f"{directory}/example.py")
    assert os.path.isfile(f"{directory}/peak fitting.py")
    assert os.path.isfile(f"{directory}/plot multi-line.py")
    assert os.path.isfile(f"{directory}/example.ipynb")

    os.remove(f"{directory}/example.py")
    os.remove(f"{directory}/peak fitting.py")
    os.remove(f"{directory}/plot multi-line.py")
    os.remove(f"{directory}/example.ipynb")

