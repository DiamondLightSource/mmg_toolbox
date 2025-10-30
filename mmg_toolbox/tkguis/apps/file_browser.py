import tkinter as tk

from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_file_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from ..widgets.folder_treeview import FolderTreeViewFrame

    root = create_root(parent=parent, window_title='File Browser')
    topmenu(root, {}, add_themes=True, add_about=True)
    FolderTreeViewFrame('Any', root, initial_directory)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_file_browser(parent: tk.Misc | None = None, initial_directory: str | None = None,
                              hdf_path: str = '/entry/scan_command') -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from ..widgets.folder_treeview import NexusFolderTreeViewFrame

    root = create_root(parent=parent, window_title='NeXus File Browser')
    topmenu(root, {}, add_themes=False, add_about=True)
    NexusFolderTreeViewFrame(root, initial_directory, hdf_path)
    if parent is None:
        root.mainloop()
    return root


def create_jupyter_browser(parent: tk.Misc | None = None, initial_directory: str | None = None) -> RootWithStyle:
    """
    File Browser - Browse directories and open NeXus files
    """
    from ..widgets.folder_treeview import JupyterFolderTreeViewFrame

    root = create_root(parent=parent, window_title='Jupyter Notebook Browser')
    topmenu(root, {}, add_themes=True, add_about=True)
    JupyterFolderTreeViewFrame(root, initial_directory)
    if parent is None:
        root.mainloop()
    return root
