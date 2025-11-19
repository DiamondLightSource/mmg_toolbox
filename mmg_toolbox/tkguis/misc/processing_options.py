"""
Menu options for processing tasks
"""
import os
import tkinter as tk

from mmg_toolbox.utils.env_functions import (get_notebook_directory, open_terminal, get_scan_number,
                                             get_processing_directory)
from mmg_toolbox.scripts.scripts import (generate_script, create_notebook,
                                         SCRIPTS, NOTEBOOKS, R)
from .config import get_config, C
from .functions import check_new_file
from .jupyter import launch_jupyter_notebook, terminate_notebooks
from ..apps.multi_scan_analysis import create_multi_scan_analysis
from ..apps.python_editor import create_python_editor


def create_script_from_template(root: tk.Misc, template: str = 'example', directory: str | None = None,
                                config: dict | None = None, **replacements):
    proc_dir = directory or config[C.current_proc]
    script_name = os.path.join(proc_dir, f"{template}.py")
    new_file = check_new_file(root, script_name)
    script = generate_script(template, **replacements)
    create_python_editor(script, root, config, filename=new_file)


def create_notebook_from_template(root: tk.Misc, template: str = 'example', directory: str | None = None,
                                  config: dict | None = None, **replacements):
    proc_dir = directory or config[C.current_proc]
    script_name = os.path.join(proc_dir, f"{template}.ipynb")
    new_file = check_new_file(root, script_name)
    create_notebook(new_file, template, **replacements)
    launch_jupyter_notebook('notebook', file=new_file)


def generate_replacement_getter(scanno_getter, title_getter, x_getter = None,
                                y_getter = None, metadata_getter = None):
    def getter() -> dict:
        replacements = {
            R.scannos: str(scanno_getter()),
            R.description: 'Created by  MultiScanAnalysis',
        }
        if title_getter:
            replacements[R.title] = str(title_getter())
        if x_getter:
            replacements[R.xaxis] = str(x_getter())
        if y_getter:
            replacements[R.yaxis] = str(y_getter())
        if metadata_getter:
            replacements[R.value] = str(metadata_getter())
        return replacements
    return getter


def generate_processing_menu(parent, config: dict, directory: str | None = None, scan_files_getter=None,
                             replacement_getter=None) -> dict:
    """Generate processing menu options"""

    directory = directory or config[C.current_dir]
    proc_dir = config.get(C.current_proc) or get_processing_directory(directory)
    nb_dir = config.get(C.current_nb) or get_notebook_directory(directory)

    if scan_files_getter is None:
        scan_files_getter = lambda: []
    if replacement_getter is None:
        replacement_getter = lambda: {}

    def start_multi_scan_plot():
        filenames = scan_files_getter()
        scan_numbers = [get_scan_number(f) for f in filenames]
        create_multi_scan_analysis(parent, config, exp_directory=directory, scan_numbers=scan_numbers)

    def replacements():
        values = {
            R.exp: directory,
            R.proc: proc_dir,
            R.filepaths: ', '.join(f"'{f}'" for f in scan_files_getter()),
            R.beamline: config.get(C.beamline, ''),
            R.value: config.get(C.default_metadata, ''),
        }
        values.update(replacement_getter())
        return values

    scripts = {
        name: lambda n=name: create_script_from_template(parent, n, directory, config, **replacements())
        for name in SCRIPTS
    }
    notebooks = {
        name: lambda n=name: create_notebook_from_template(parent, n, directory, config, **replacements())
        for name in NOTEBOOKS
    }
    menu = {
        'Multi-Scan': start_multi_scan_plot,
        'Script Editor': lambda: create_python_editor(None, parent, config),
        'Open a terminal': lambda: open_terminal(f"cd {directory}"),
        'Start Jupyter (processing)': lambda: launch_jupyter_notebook('notebook', proc_dir),
        'Start Jupyter (notebooks)': lambda: launch_jupyter_notebook('notebook', nb_dir),
        'Stop Jupyter servers': terminate_notebooks,
        'Create Script:': scripts,
        'Create Notebook:': notebooks,
    }
    return menu
