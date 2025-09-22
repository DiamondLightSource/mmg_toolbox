
from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import create_root
from mmg_toolbox.env_functions import open_terminal, open_jupyter_lab


def create_title_window():
    """Title Window"""
    from ..widgets.title_window import TitleWindow
    from .config_editor import ConfigEditor
    from .log_viewer import create_gda_terminal_log_viewer
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .scans import create_range_selector
    from .data_viewer import create_data_viewer
    from .python_editor import create_python_editor


    root = create_root(window_title='Beamline Data Viewer')
    config = get_config()

    widget = TitleWindow(root, config)

    menu = {
        'File': {
            'File Browser': lambda: create_file_browser(root, config.get(C.default_directory, None)),
            'NeXus File Browser': lambda: create_nexus_file_browser(root, config.get('default_directory')),
            'Jupyter Browser': lambda: create_jupyter_browser(root, widget.notebook_dir.get()),
            'Data Viewer': lambda: create_data_viewer(widget.data_dir.get(), root, config),
            'Range selector': lambda: create_range_selector(widget.data_dir.get(), root, config),
            'Log viewer': lambda: create_gda_terminal_log_viewer(widget.data_dir.get(), root)
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        },
        'Processing': {
            'Start Jupyter': open_jupyter_lab,
            'Script Editor': lambda: create_python_editor(None, root, config),
            'Open terminal': lambda: open_terminal(f"cd {widget.data_dir.get()}"),
        }
    }
    menu.update(widget.menu_items())

    topmenu(root, menu, add_themes=True, add_about=True)

    root.mainloop()
    return root
