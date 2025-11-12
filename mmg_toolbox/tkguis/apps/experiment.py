
from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import create_root
from mmg_toolbox.tkguis.misc.jupyter import launch_jupyter_notebook, terminate_notebooks
from mmg_toolbox.utils.env_functions import open_terminal


def create_title_window(beamline: str | None = None):
    """Title Window"""
    from ..widgets.title_window import TitleWindow
    from .log_viewer import create_gda_terminal_log_viewer
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .scans import create_range_selector
    from .data_viewer import create_data_viewer
    from .python_editor import create_python_editor
    from .visit_viewer import create_visit_viewer


    root = create_root(window_title='Beamline Data Viewer')
    config = get_config(beamline=beamline)

    widget = TitleWindow(root, config)

    menu = {
        'File': {
            'File Browser': lambda: create_file_browser(root, config.get(C.default_directory, None)),
            'NeXus File Browser': lambda: create_nexus_file_browser(root, config.get('default_directory')),
            'Jupyter Browser': lambda: create_jupyter_browser(root, widget.notebook_dir.get()),
            'Data Viewer': lambda: create_data_viewer(widget.data_dir.get(), root, config),
            'Range selector': lambda: create_range_selector(widget.data_dir.get(), root, config),
            'Log viewer': lambda: create_gda_terminal_log_viewer(widget.data_dir.get(), root),
            'Visit Viewer': lambda: create_visit_viewer(config),
        },
        'Processing': {
            'Script Editor': lambda: create_python_editor(None, root, config),
            'Open a terminal': lambda: open_terminal(f"cd {widget.data_dir.get()}"),
            'Start Jupyter (processing)': lambda: launch_jupyter_notebook('notebook', widget.proc_dir.get()),
            'Start Jupyter (notebooks)': lambda: launch_jupyter_notebook('notebook', widget.notebook_dir.get()),
            'Stop Jupyter servers': terminate_notebooks,
        }
    }
    menu.update(widget.menu_items())

    topmenu(root, menu, add_themes=True, add_about=True, config=config)

    root.mainloop()
    return root
