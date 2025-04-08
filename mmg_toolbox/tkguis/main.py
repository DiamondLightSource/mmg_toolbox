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


def create_jupyter_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from .widgets.folder_treeview import JupyterFolderTreeViewFrame

    root = create_root(parent=parent, window_title='Jupyter Notebook Browser')
    topmenu(root, {}, add_themes=True, add_about=True)
    JupyterFolderTreeViewFrame(root, initial_directory)
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


def select_scans(folder: str, parent: tk.Misc | None = None, config: dict | None = None,
                 metadata_list: list[str] | None = None) -> list[str]:
    """
    Create a selection box for scans in a folder
    """
    from .widgets.scan_selector import ScanSelector

    root = create_root(parent=parent, window_title='Select Files')
    config = get_config() if config is None else config
    if metadata_list:
        # replace config
        config = {'metadata_list': {name: f"{{{name}}}" for name in metadata_list}}
    return ScanSelector(root, folder, config).show()


def list_scans(*file_list: str, parent: tk.Misc | None = None, config: dict | None = None,
               metadata_list: list[str] | None = None) -> list[str]:
    """
    Create a selection box for scans in a folder
    """
    from .widgets.scan_selector import ScanViewer

    root = create_root(parent=parent, window_title='Select Files')
    config = get_config() if config is None else config
    if metadata_list:
        # replace config
        config = {'metadata_list': {name: f"{{{name}}}" for name in metadata_list}}
    return ScanViewer(root, *file_list, config=config).show()


def create_range_selector(initial_folder: str | None = None,
                          parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a range selector
    """
    from .widgets.scan_range_selector import ScanRangeSelector

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config

    ScanRangeSelector(root, initial_folder, config)

    if parent is None:
        root.mainloop()
    return root


def create_script_runner(parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a range selector
    """
    from .widgets.script_runner import ScriptRunner

    root = create_root(parent=parent, window_title='Script Runner')
    config = get_config() if config is None else config

    ScriptRunner(root, config)

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
    from .widgets.size_tester import WindowSize

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config

    widget = NexusScanDetailsPlot(root, initial_folder=initial_folder, config=config)

    def get_processed():
        item = widget.selector_widget.tree.selection()
        if not item:
            item = next(iter(widget.selector_widget.tree.get_children()))
        if item:
            filepath = widget.selector_widget.tree.set(item, 'filepath')
            print(item, filepath)
            filepath += '/processed'
        else:
            filepath = config.get('default_directory', None)
        return filepath

    menu = {
        'File': {
            'Add Folder': widget.selector_widget.browse_folder,
            'Folder Browser': lambda: create_file_browser(root, config.get('default_directory', None)),
            'Jupyter Browser': lambda: create_jupyter_browser(root, get_processed()),
            'Size widget': lambda: WindowSize(root),
            'Range selector': lambda: create_range_selector(initial_folder, root, config)
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


def create_title_window():
    """Title Window"""
    from .widgets.title_window import TitleWindow
    from .widgets.config_editor import ConfigEditor

    root = create_root(window_title='Beamline Data Viewer')
    config = get_config()

    widget = TitleWindow(root, config)

    menu = {
        'File': {
            'Folder Browser': lambda: create_file_browser(root, config.get('default_directory')),
            'Jupyter Browser': lambda: create_jupyter_browser(root, widget.notebook_dir.get()),
            'Data Viewer': lambda: create_data_viewer(widget.data_dir.get(), root, config),
            'Range selector': lambda: create_range_selector(widget.data_dir.get(), root, config)
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }

    topmenu(root, menu, add_themes=True, add_about=True)

    root.mainloop()
    return root