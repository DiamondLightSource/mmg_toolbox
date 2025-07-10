"""
Main front ends
"""

import tkinter as tk
from ..env_functions import get_notebook_directory
from .misc.styles import create_root, RootWithStyle
from .misc.functions import topmenu, select_hdf_file
from .misc.config import get_config, C


def create_file_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from .widgets.folder_treeview import FolderTreeViewFrame

    root = create_root(parent=parent, window_title='File Browser')
    topmenu(root, {}, add_themes=True, add_about=True)
    FolderTreeViewFrame('Any', root, initial_directory)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_file_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from .widgets.folder_treeview import NexusFolderTreeViewFrame

    root = create_root(parent=parent, window_title='NeXus File Browser')
    topmenu(root, {}, add_themes=False, add_about=True)
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

    widget = HDFViewer(root, filename)

    menu = {
        'File': {
            'Open': widget.select_file
        },
    }
    topmenu(root, menu, add_themes=False, add_about=True)

    if parent is None:
        root.mainloop()
    return root


def create_nexus_plotter(filename: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 1D line data from a NeXus file
    """
    from .widgets.nexus_plot import NexusDefaultPlot
    from .widgets.config_editor import ConfigEditor

    root = create_root('NeXus File Default Plot', parent=parent)
    widget = NexusDefaultPlot(root, filename, config)

    def load_file():
        new_filename = select_hdf_file(root)
        if new_filename:
            widget.update_data_from_file(new_filename)

    menu = {
        'File': {
            'Open': load_file,
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }

    topmenu(root, menu, add_themes=False, add_about=True)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_image_plotter(filename: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 2D images from detectors in a NeXus file, including a slider
    """
    from .widgets.nexus_image import NexusDetectorImage

    root = create_root(parent=parent, window_title='NeXus File Image Plot')

    widget = NexusDetectorImage(root, filename, config)

    def load_file():
        new_filename = select_hdf_file(root)
        if new_filename:
            widget.update_data_from_file(new_filename)

    menu = {
        'File': {
            'Open': load_file,
        },
    }
    topmenu(root, menu, add_themes=False, add_about=True)

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
        config = {C.metadata_list: {name: f"{{{name}}}" for name in metadata_list}}
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
        config = {C.metadata_list: {name: f"{{{name}}}" for name in metadata_list}}
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
    from .widgets.nexus_data_viewer import NexusDataViewer
    from .widgets.log_viewer import create_gda_terminal_log_viewer
    from .widgets.config_editor import ConfigEditor
    from .misc.matplotlib import FIGURE_SIZE, IMAGE_SIZE, FIGURE_DPI, SMALL_FIGURE_DPI

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config
    config['figure_size'] = FIGURE_SIZE
    config['image_size'] = IMAGE_SIZE
    config['figure_dpi'] = FIGURE_DPI if root.winfo_screenheight() >= 800 else SMALL_FIGURE_DPI

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


def create_title_window():
    """Title Window"""
    from .widgets.title_window import TitleWindow
    from .widgets.config_editor import ConfigEditor
    from .widgets.log_viewer import create_gda_terminal_log_viewer

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
        }
    }
    menu.update(widget.menu_items())

    topmenu(root, menu, add_themes=True, add_about=True)

    root.mainloop()
    return root
