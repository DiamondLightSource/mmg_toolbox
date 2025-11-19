import os
import tkinter as tk

from mmg_toolbox.utils.env_functions import get_notebook_directory, get_scan_number
from ..misc.config import get_config, C
from ..misc.functions import topmenu
from ..misc.styles import RootWithStyle, create_root
from ..misc.processing_options import generate_replacement_getter, generate_processing_menu


def create_data_viewer(initial_folder: str | None = None,
                       parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from ..widgets.nexus_data_viewer import NexusDataViewer
    from .log_viewer import create_gda_terminal_log_viewer
    from .file_browser import create_nexus_file_browser, create_file_browser, create_jupyter_browser
    from .scans import create_range_selector

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = config or get_config()

    widget = NexusDataViewer(root, initial_folder=initial_folder, config=config)

    def get_filepath():
        filename, folder = widget.selector_widget.get_filepath()
        return folder

    def get_scannos():
        return [get_scan_number(f) for f in widget.selector_widget.get_multi_filepath()]

    getter = generate_replacement_getter(
        scanno_getter=get_scannos,
        x_getter=widget.plot_widget.axes_x.get,
        y_getter=widget.plot_widget.axes_y.get,
        title_getter=lambda: f"Example Script: {os.path.basename(get_filepath())}"
    )
    processing_menu = generate_processing_menu(
        parent=root,
        config=config,
        directory=initial_folder,
        scan_files_getter=widget.selector_widget.get_multi_filepath,
        replacement_getter=getter
    )

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
        'Processing': processing_menu
    }
    menu.update(widget.plot_widget.options_menu())

    topmenu(root, menu, add_themes=True, add_about=True, config=config)

    root.update()

    if parent is None:
        root.mainloop()
    return root
