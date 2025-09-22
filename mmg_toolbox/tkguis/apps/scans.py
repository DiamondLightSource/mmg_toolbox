import tkinter as tk

from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.styles import create_root, RootWithStyle


def select_scans(folder: str, parent: tk.Misc | None = None, config: dict | None = None,
                 metadata_list: list[str] | None = None) -> list[str]:
    """
    Create a selection box for scans in a folder
    """
    from ..widgets.scan_selector import ScanSelector

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
    from ..widgets.scan_selector import ScanViewer

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
    from ..widgets.scan_range_selector import ScanRangeSelector

    root = create_root(parent=parent, window_title='NeXus Data Viewer')
    config = get_config() if config is None else config

    ScanRangeSelector(root, initial_folder, config)

    if parent is None:
        root.mainloop()
    return root
