import os
import tkinter as tk

from mmg_toolbox.utils.env_functions import get_notebook_directory, open_terminal, get_scan_number, check_file_access
from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root
from mmg_toolbox.tkguis.misc.jupyter import launch_jupyter_notebook, terminate_notebooks
from mmg_toolbox.scripts.scripts import create_script, create_notebook, SCRIPTS, NOTEBOOKS


def create_data_viewer(initial_folder: str | None = None,
                       parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from ..widgets.nexus_data_viewer import NexusDataViewer
    from .log_viewer import create_gda_terminal_log_viewer
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .multi_scan_analysis import create_multi_scan_analysis
    from .scans import create_range_selector
    from .python_editor import create_python_editor

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = config or get_config()

    widget = NexusDataViewer(root, initial_folder=initial_folder, config=config)

    def get_filepath():
        filename, folder = widget.selector_widget.get_filepath()
        return folder

    def get_replacements():
        filename, folder = widget.selector_widget.get_filepath()
        filenames = widget.selector_widget.get_multi_filepath()
        scan_numbers = [get_scan_number(f) for f in filenames]
        return {
            # {{template}}: replacement
            'description': 'an example script',
            'filepaths': ', '.join(f"'{f}'" for f in filenames),
            'experiment_dir': folder,
            'scan_numbers': str(scan_numbers),
            'title': f"Example Script: {os.path.basename(filename)}",
            'x-axis': widget.plot_widget.axes_x.get(),
            'y-axis': widget.plot_widget.axes_y.get(),
            'beamline': config.get(C.beamline),
        }

    def create_script_template(template='example'):
        filename, folder = widget.selector_widget.get_filepath()
        new_file = check_file_access(folder + '/processing/example_script.py')
        create_script(new_file, template, **get_replacements())
        create_python_editor(open(new_file).read(), root, config),

    def create_notebook_template(template='example'):
        filename, folder = widget.selector_widget.get_filepath()
        new_file = check_file_access(folder + '/processing/example.ipynb')
        create_notebook(new_file, template, **get_replacements(filename))
        launch_jupyter_notebook('notebook', file=new_file)

    def start_multi_scan_plot():
        filename, folder = widget.selector_widget.get_filepath()
        filenames = widget.selector_widget.get_multi_filepath()
        scan_numbers = [get_scan_number(f) for f in filenames]
        create_multi_scan_analysis(root, config, exp_directory=folder, scan_numbers=scan_numbers)

    menu = {
        'File': {
            'New Data Viewer': lambda: create_data_viewer(parent=root, config=config),
            'Add Folder': widget.selector_widget.browse_folder,
            'File Browser': lambda: create_file_browser(root, config.get(C.default_directory, None)),
            'NeXus File Browser': lambda: create_nexus_file_browser(root, config.get(C.default_directory, None)),
            'Jupyter Browser': lambda: create_jupyter_browser(root, get_notebook_directory(get_filepath())),
            'Range selector': lambda: create_range_selector(initial_folder, root, config),
            'Log viewer': lambda: create_gda_terminal_log_viewer(get_filepath(), root)
        },
        'Processing': {
            'Multi-Scan': start_multi_scan_plot,
            'Script Editor': lambda: create_python_editor(None, root, config),
            'Open a terminal': lambda: open_terminal(f"cd {get_filepath()}"),
            'Start Jupyter (processing)': lambda: launch_jupyter_notebook('notebook', get_filepath() + '/processing'),
            'Start Jupyter (notebooks)': lambda: launch_jupyter_notebook('notebook', get_filepath() + '/processed/notebooks'),
            'Stop Jupyter servers': terminate_notebooks,
            'Scripts:': {name: lambda n=name: create_script_template(n) for name in SCRIPTS},
            'Notebooks:': {name: lambda n=name: create_notebook_template(n) for name in NOTEBOOKS},
        }
    }
    menu.update(widget.plot_widget.options_menu())

    topmenu(root, menu, add_themes=True, add_about=True, config=config)

    root.update()

    if parent is None:
        root.mainloop()
    return root
