import tkinter as tk

from mmg_toolbox.env_functions import get_notebook_directory
from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_data_viewer(initial_folder: str | None = None,
                       parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from ..widgets.nexus_data_viewer import NexusDataViewer
    from ..widgets.log_viewer import create_gda_terminal_log_viewer
    from mmg_toolbox.tkguis.apps.config_editor import ConfigEditor
    from ..misc.matplotlib import FIGURE_SIZE, IMAGE_SIZE, FIGURE_DPI, SMALL_FIGURE_DPI
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .scans import create_range_selector

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config
    config[C.plot_dpi] = FIGURE_DPI if root.winfo_screenheight() >= 800 else SMALL_FIGURE_DPI

    widget = NexusDataViewer(root, initial_folder=initial_folder, config=config)

    def get_filepath():
        filename, folder = widget.selector_widget.get_filepath()
        return folder

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
        }
    }
    menu.update(widget.image_widget.options_menu())

    topmenu(root, menu, add_themes=True, add_about=True)

    root.update()
    print(f"Window size (wxh): {root.winfo_reqwidth()}x{root.winfo_reqheight()}")

    if parent is None:
        root.mainloop()
    return root
