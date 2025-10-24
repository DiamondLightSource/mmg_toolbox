import os
import tkinter as tk
from mmg_toolbox.tkguis.misc.styles import create_root


def create_log_viewer(filename: str, parent: tk.Misc | None = None):
    """Log Viewer Window"""
    from ..widgets.log_viewer import LogViewerWidget
    from mmg_toolbox.utils.file_reader import read_gda_terminal_log

    root = create_root(window_title='Log Viewer', parent=parent)
    log_tabs = read_gda_terminal_log(filename)
    LogViewerWidget(root, log_tabs)
    root.mainloop()
    return root


def create_gda_terminal_log_viewer(data_directory: str, parent: tk.Misc | None = None):
    """Create Log Viewer window using data directory"""
    gda_terminal_log = os.path.join(data_directory, 'gdaterminal.log')
    if os.path.isfile(gda_terminal_log):
        create_log_viewer(gda_terminal_log, parent=parent)
    else:
        raise OSError(f"{gda_terminal_log} does not exist!")
