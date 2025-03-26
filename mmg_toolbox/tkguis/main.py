"""
Main front ends
"""

import tkinter as tk
from .misc.styles import create_root, RootWithStyle
from .misc.functions import topmenu
from .misc.config import get_config


def create_file_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from .widgets.folder_treeview import NexusFolderTreeViewFrame

    root = create_root(parent=parent, window_title='NeXus File Browser')
    topmenu(root, {}, add_themes=True, add_about=True)
    NexusFolderTreeViewFrame(root, initial_directory)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_viewer(filename: str, parent: tk.Misc | None = None) -> RootWithStyle:
    """
    File Viewer of the NeXus structure
    """
    from .widgets.nexus_treeview import HDFViewer

    root = create_root(parent=parent, window_title='NeXus File Viewer')
    topmenu(root, {}, add_themes=True, add_about=True)
    HDFViewer(root, filename)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_plotter(filename: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 1D line data from a NeXus file
    """
    from .widgets.nexus_plot import NexusDefaultPlot
    from .widgets.config_editor import ConfigEditor

    root = create_root(parent=parent, window_title='NeXus File Plotter')
    menu = {
        'File': {
            'Open': lambda: print('Not available')
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }

    topmenu(root, menu, add_themes=True, add_about=True)
    NexusDefaultPlot(root, filename)
    if parent is None:
        root.mainloop()
    return root


def create_data_viewer(initial_folder: str | None = None,
                       parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from .widgets.nexus_scan_plot import NexusScanDetailsPlot
    from .widgets.config_editor import ConfigEditor

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config

    widget = NexusScanDetailsPlot(root, initial_folder=initial_folder, config=config)

    menu = {
        'File': {
            'Add Folder': widget.selector_widget.browse_folder,
            'Folder Browser': lambda: create_file_browser(root, config.get('default_directory', None)),
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }
    menu.update(widget.image_widget.options_menu())

    topmenu(root, menu, add_themes=True, add_about=True)

    if parent is None:
        root.mainloop()
    return root
