import tkinter as tk

from mmg_toolbox.tkguis.misc.config import get_config
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_script_runner(parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Create a range selector
    """
    from ..widgets.script_runner import ScriptRunner

    root = create_root(parent=parent, window_title='Script Runner')
    config = get_config() if config is None else config

    ScriptRunner(root, config)

    if parent is None:
        root.mainloop()
    return root
