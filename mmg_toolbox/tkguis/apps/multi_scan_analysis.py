import tkinter as tk

from mmg_toolbox.tkguis.misc.config import get_config
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_multi_scan_analysis(parent: tk.Misc | None = None, config: dict | None = None,
                               exp_directory: str | None = None, proc_directory: str | None = None,
                               scan_numbers: list[int] | None = None, metadata: str | None = None,
                               x_axis: str | None = None, y_axis: str | None = None) -> RootWithStyle:
    """
    Create a range selector
    """
    from ..widgets.multi_scan_analysis import MultiScanAnalysis

    root = create_root(parent=parent, window_title='Multi-Scan Analysis')
    config = get_config() if config is None else config

    MultiScanAnalysis(root, config, exp_directory=exp_directory,
                      proc_directory=proc_directory, scan_numbers=scan_numbers,
                      metadata=metadata, x_axis=x_axis, y_axis=y_axis)

    if parent is None:
        root.mainloop()
    return root
