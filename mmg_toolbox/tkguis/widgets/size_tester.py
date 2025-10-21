"""
Simple frame widget that returns the current screen size and window position
"""

from ..misc.styles import tk, ttk, create_root
from ..misc.logging import create_logger

logger = create_logger(__file__)


class WindowSize:
    """
    Simple text edit box
        next_text = EditText(old_text, tkframe).show()
    :param parent: tk root
    """

    def __init__(self, parent: tk.Misc | None = None):
        self.root = create_root('Size Widget', parent=parent)

        frm = ttk.LabelFrame(self.root, text='Size')
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        self.text = tk.Text(frm, wrap=tk.NONE, width=100, height=10)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Button(self.root, text='Update', command=self.fun_update)
        var.pack(side=tk.TOP, fill=tk.X)
        var = ttk.Button(self.root, text='Close', command=self.root.destroy)
        var.pack(side=tk.TOP, fill=tk.X)

    def fun_update(self, event=None):
        """Launches window, returns selection"""
        self.root.update()
        self.root.update_idletasks()
        # self.root.attributes('-fullscreen', True)
        # self.root.state('iconic')
        # geometry = self.root.winfo_geometry()
        s = f"Screen size (w x h): {self.root.winfo_screenwidth()} x {self.root.winfo_screenheight()}\n"
        s += f"Geometry: {self.root.geometry()}\n"
        s += f"winfo_reqwidth x winfo_reqhight: {self.root.winfo_reqwidth()} x {self.root.winfo_reqheight()}\n"
        # s += f"current display geometry: {self.get_curr_screen_geometry()}"
        self.text.replace("1.0", tk.END, s)

