import os
import tkinter as tk

from mmg_toolbox.env_functions import get_notebook_directory, open_terminal
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
    from mmg_toolbox.tkguis.apps.log_viewer import create_gda_terminal_log_viewer
    from mmg_toolbox.tkguis.apps.config_editor import ConfigEditor
    from ..misc.matplotlib import SMALL_FIGURE_DPI
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .scans import create_range_selector
    from .python_editor import create_python_editor

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config
    if root.winfo_screenheight() <= 800:
        config[C.plot_dpi] = SMALL_FIGURE_DPI

    widget = NexusDataViewer(root, initial_folder=initial_folder, config=config)

    def get_filepath():
        filename, folder = widget.selector_widget.get_filepath()
        return folder

    def get_replacements(*filenames):
        return {
            # {{template}}: replacement
            'description': 'an example script',
            'filepaths': ', '.join(f"'{f}'" for f in filenames),
            'title': f"Example Script: {os.path.basename(filenames[0])}",
            'x-axis': widget.plot_widget.axes_x.get(),
            'y-axis': widget.plot_widget.axes_y.get(),
        }

    def create_script_template(template='example'):
        filename, folder = widget.selector_widget.get_filepath()
        new_file = folder + '/processing/example_script.py'
        create_script(new_file, template, **get_replacements(filename))
        create_python_editor(open(new_file).read(), root, config),

    def create_notebook_template(template='example'):
        filename, folder = widget.selector_widget.get_filepath()
        new_file = folder + '/processing/example.ipynb'
        create_notebook(new_file, template, **get_replacements(filename))
        launch_jupyter_notebook('notebook', file=new_file)

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
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        },
        'Processing': {
            'Script Editor': lambda: create_python_editor(None, root, config),
            'Open a terminal': lambda: open_terminal(f"cd {get_filepath()}"),
            'Start Jupyter (processing)': lambda: launch_jupyter_notebook('notebook', get_filepath() + '/processing'),
            'Start Jupyter (notebooks)': lambda: launch_jupyter_notebook('notebook', get_filepath() + '/processed/notebooks'),
            'Stop Jupyter servers': terminate_notebooks,
            'Scripts:': {name: lambda n=name: create_script_template(n) for name in SCRIPTS},
            'Notebooks:': {name: lambda n=name: create_notebook_template(n) for name in NOTEBOOKS},
        }
    }
    menu.update(widget.image_widget.options_menu())

    topmenu(root, menu, add_themes=True, add_about=True)

    root.update()
    print(f"Window size (wxh): {root.winfo_reqwidth()}x{root.winfo_reqheight()}")

    if parent is None:
        root.mainloop()
    return root
