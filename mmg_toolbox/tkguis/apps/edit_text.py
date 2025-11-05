"""
Simple window with editable text box
"""

from mmg_toolbox.tkguis.misc.styles import tk, ttk, create_root
from mmg_toolbox.tkguis.misc.logging import create_logger

logger = create_logger(__file__)


class EditText:
    """
    Simple text edit box
        next_text = EditText(old_text, tkframe).show()
    :param expression: str expression to edit
    :param parent: tk root
    """

    def __init__(self, expression: str, parent: tk.Misc | None = None, textwidth=30, title="Edit text"):
        self.output = expression
        self.root = create_root(title, parent=parent)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        self.text = tk.Text(frm, wrap=tk.NONE, width=textwidth)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.text.insert('1.0', expression)

        var = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        self.text.configure(yscrollcommand=var.set)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Button(self.root, text='Update', command=self.fun_update)
        var.pack(side=tk.TOP, fill=tk.X)

    def fun_update(self, event=None):
        """Launches window, returns selection"""
        self.output = self.text.get('1.0', tk.END)
        self.root.destroy()  # trigger wait_window

    def show(self):
        """Launches window, returns selection"""
        self.root.wait_window()  # wait for window
        self.root.destroy()
        return self.output