"""
A python editor
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from mmg_toolbox.tkguis.misc.config import get_config, C
from mmg_toolbox.tkguis.misc.functions import topmenu
from mmg_toolbox.tkguis.misc.styles import create_root, RootWithStyle
from mmg_toolbox.tkguis.misc.logging import create_logger


logger = create_logger(__file__)


def create_python_editor(script_string: str | None = None, parent: tk.Misc | None = None,
                         config: dict | None = None, filename: str | None = None) -> RootWithStyle:
    """
    ScriptGenerator GUI
    Python code editor with special features for I16 scripts

    :param script_string: string to display
    :param parent: tkinter parent object
    :param config: config dict
    :param filename: initial filename
    """
    from ..widgets.python_editor import PythonEditorFrame

    title = filename or 'Python Editor'
    root = create_root(title, parent=parent)
    config = get_config() if config is None else config

    widget = PythonEditorFrame(root, script_string, config, filename=filename)

    menu = {
        'File': {
            'New script': widget.new,
            'Open': widget.open,
            'Save As...': widget.saveas,
            'Save': widget.save,
            'Quit': root.destroy,
        },
    }
    topmenu(root, menu, add_about=True)

    if parent is None:
        root.mainloop()
    return root

