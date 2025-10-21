"""
tk widget for editing the Config file
"""

from ..misc.styles import tk, ttk
from ..misc.logging import create_logger
from ..misc.config import get_config, C

logger = create_logger(__file__)


class RoiEditor:
    """
    Edit the Configuration File in an inset window
    """

    def __init__(self, root: tk.Misc, config: dict | None = None, close_func = None):
        self.root = root
        self.close_func = close_func
        if config is None:
            self.config = get_config()
        else:
            self.config = config

        window = ttk.Frame(root, borderwidth=2, relief=tk.RIDGE)
        window.pack(expand=tk.NO, pady=2, padx=5)

        self.roi_table = ttk.Frame(window, borderwidth=20, relief=tk.RAISED)
        self.roi_table.pack(side=tk.TOP, fill=tk.BOTH)

        frm = ttk.Frame(self.roi_table)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        ttk.Label(frm, text='Image ROIs', style="title.TLabel").pack(expand=tk.YES, fill=tk.X, padx=10, pady=10)

        self.roi_values: list[tuple] = []
        self.roi_lines: list[tuple[bool, ttk.Frame]] = []
        rois = self.config.get(C.roi)
        if rois:
            for name, cen_i, cen_j, wid_i, wid_j, det_name in rois:
                self.add_roi(name, cen_i, cen_j, wid_i, wid_j, det_name)

        ln = ttk.Frame(window, borderwidth=2)
        ln.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(ln, text='Add ROI', command=self.add_roi).pack()

        ln = ttk.Frame(window, borderwidth=6)
        ln.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(ln, text='Close', command=self.close).pack(fill=tk.X, expand=tk.YES)

    def add_roi(self, name: str = '', cen_i: int | str = '', cen_j: int | str = '',
                wid_i: int = 30, wid_j: int = 30, det_name: str = 'IMAGE'):
        tkvars = (
            # label, tkVar, width
            ('Name:', tk.StringVar(self.root, name), 8),
            ('Centre_i:', tk.StringVar(self.root, cen_i), 6),
            ('Centre_j:', tk.StringVar(self.root, cen_j), 6),
            ('Width_i', tk.IntVar(self.root, wid_i), 6),
            ('Width_j', tk.IntVar(self.root, wid_j), 6),
            ('Detector', tk.StringVar(self.root, det_name), 10)
        )
        def copy_roi():
            self.add_roi(*(var[1].get() for var in tkvars))

        self.roi_values.append(tkvars)
        ln = ttk.Frame(self.roi_table, borderwidth=2)
        ln.pack(side=tk.TOP, fill=tk.X)
        self.roi_lines.append((True, ln))
        for label, tkvar, width in tkvars:
            ttk.Label(ln, text=label).pack(side=tk.LEFT, padx=2)
            ttk.Entry(ln, textvariable=tkvar, width=width).pack(side=tk.LEFT, padx=2)
        ttk.Button(ln, text='X', command=lambda index=len(self.roi_lines)-1: self.remove_roi(index)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ln, text='Copy', command=copy_roi).pack(side=tk.LEFT, padx=2)

    def remove_roi(self, index: int):
        check, frame = self.roi_lines[index]
        frame.pack_forget()
        self.roi_lines[index] = (False, frame)

    def create_config_rois(self):
        rois = [
            tuple(var[1].get() for var in roi_values)
            for index, roi_values in enumerate(self.roi_values)
            if self.roi_lines[index][0] is True and roi_values[0][1].get()
        ]
        return rois

    def update_config(self):
        self.config[C.roi] = self.create_config_rois()

    def close(self):
        self.update_config()
        if self.close_func:
            self.close_func()
        else:
            self.root.destroy()

