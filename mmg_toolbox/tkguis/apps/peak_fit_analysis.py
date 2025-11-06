import tkinter as tk

from mmg_toolbox.tkguis.misc.config import get_config
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_peak_fit(parent: tk.Misc | None = None, config: dict | None = None,
                    exp_directory: str | None = None, proc_directory: str | None = None,
                    scan_numbers: list[int] | None = None, metadata: str | None = None,
                    x_axis: str | None = None, y_axis: str | None = None) -> RootWithStyle:
    """
    Create window for peak fitting
    """
    from ..widgets.peak_fit_analysis import PeakFitAnalysis

    root = create_root(parent=parent, window_title='Peak Fitting')
    config = config or get_config()

    PeakFitAnalysis(root, config, exp_directory=exp_directory,
                    proc_directory=proc_directory, scan_numbers=scan_numbers,
                    metadata=metadata, x_axis=x_axis, y_axis=y_axis)

    if parent is None:
        root.mainloop()
    return root
