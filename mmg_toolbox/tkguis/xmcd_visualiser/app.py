import tkinter as tk

from ..misc.config import get_config, C
from ..misc.functions import topmenu, select_folder
from ..misc.styles import RootWithStyle, create_root


def create_xmcd_visualiser(data_directory: str | None = None, scan_range_str: str = None,
                           pairs: list[tuple[int, int]] = None,
                           parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a Data Viewer showing all scans in an experiment folder
    """
    from .widget import XMCDVisualiser
    from ..apps.experiment import create_title_window

    root = create_root(parent=parent, window_title='XMCD Visualiser')
    config = config or get_config()
    if data_directory:
        config[C.current_dir] = data_directory

    widget = XMCDVisualiser(root, scan_range_str=scan_range_str,
                            pairs=pairs, config=config)

    def set_data_path():
        folder = select_folder(root, config[C.current_dir])
        if folder:
            config[C.current_dir] = folder
            widget.average.add_exp_path(folder)

    def set_save_dir():
        folder = select_folder(root, config[C.current_proc])
        if folder:
            config[C.current_proc] = folder

    menu = {
        'File': {
            'New': lambda: create_xmcd_visualiser(parent=root, config=config, data_directory=data_directory),
            'Experiment UI': create_title_window,
            'Set Data path': set_data_path,
            'Set Save path': set_save_dir,
            'Load from Processed file': widget.average.pair_selector.btn_load_file,
        },
    }

    topmenu(root, menu, add_themes=True, add_about=True, config=config)
    root.update()

    if parent is None:
        root.mainloop()
    return root
