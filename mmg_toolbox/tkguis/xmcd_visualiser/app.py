import tkinter as tk

from ..misc.config import get_config, C
from ..misc.functions import topmenu
from ..misc.styles import RootWithStyle, create_root


def create_xmcd_visualiser(data_directory: str | None = None, scan_range_str: str = None,
                           pairs: list[tuple[int, int]] = None,
                           parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from .widget import XMCDVisualiser

    root = create_root(parent=parent, window_title='XMCD Visualiser')
    config = config or get_config()
    if data_directory:
        config[C.current_dir] = data_directory

    widget = XMCDVisualiser(root, scan_range_str=scan_range_str,
                            pairs=pairs, config=config)

    menu = {
        'File': {
            'New': lambda: create_xmcd_visualiser(parent=root, config=config, data_directory=data_directory),
        },
    }

    topmenu(root, menu, add_themes=True, add_about=True, config=config)
    root.update()

    if parent is None:
        root.mainloop()
    return root
