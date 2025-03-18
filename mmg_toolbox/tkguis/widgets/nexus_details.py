"""
a tkinter frame with a single plot
"""
import tkinter as tk
from tkinter import ttk
import h5py

import hdfmap
from hdfmap import create_nexus_map

from ..misc.functions import post_right_click_menu, show_error
from ..misc.logging import create_logger
from ..misc.config import get_config
from .edit_text import EditText

logger = create_logger(__file__)

TEXTWIDTH = 50  # characters, width of textboxes


class NexusDetails:
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = hdf_filename
        self.map: hdfmap.NexusMap | None = None
        self.config = get_config() if config is None else config

        self._text_expression = self.config.get('metadata_string', '')
        self.terminal_entry = tk.StringVar(self.root, '')

        self.textbox, self.terminal = self.ini_textbox(self.root)

        if hdf_filename:
            self.update_data_from_file(hdf_filename)

    def ini_textbox(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.LEFT)

        xfrm = ttk.Frame(frm)
        xfrm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        text = tk.Text(xfrm, state=tk.DISABLED, wrap=tk.NONE, width=TEXTWIDTH)
        text.pack(fill=tk.BOTH, expand=tk.YES)
        # text.bind("<Double-1>", self.text_double_click)

        var = ttk.Scrollbar(xfrm, orient=tk.HORIZONTAL)
        var.pack(side=tk.BOTTOM, fill=tk.X)
        var.config(command=text.xview)
        text.configure(xscrollcommand=var.set)

        # Terminal
        tfrm = tk.Frame(frm, relief=tk.RIDGE)
        tfrm.pack(side=tk.TOP, fill=tk.BOTH)

        terminal = tk.Text(tfrm, state=tk.DISABLED, wrap=tk.NONE, height=3, width=TEXTWIDTH)
        terminal.pack(side=tk.LEFT, fill=tk.X, expand=tk.NO)

        var = ttk.Scrollbar(tfrm, orient=tk.VERTICAL)
        var.pack(side=tk.LEFT, fill=tk.Y)
        var.config(command=terminal.yview)
        terminal.configure(yscrollcommand=var.set)

        efrm = tk.Frame(frm, relief=tk.GROOVE)
        efrm.pack(side=tk.TOP, fill=tk.BOTH)

        var = ttk.Label(efrm, text='>>')
        var.pack(side=tk.LEFT)
        var = ttk.Entry(efrm, textvariable=self.terminal_entry)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.fun_terminal)
        var.bind('<KP_Enter>', self.fun_terminal)

        var = ttk.Button(efrm, text='CLS', command=self.fun_terminal_cls)
        var.pack(side=tk.LEFT)

        # right-click menu
        m = tk.Menu(frame, tearoff=0)
        m.add_command(label="edit Text", command=self.edit_expression)
        # m.add_command(label="open Namespace", command=self.view_namespace)

        def menu_popup(event):
            post_right_click_menu(m, event.x_root, event.y_root)
        text.bind("<Button-3>", menu_popup)
        return text, terminal

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = filename
        self.map = create_nexus_map(self.filename) if hdf_map is None else hdf_map
        self.update_text()

    def update_text(self):
        try:
            with hdfmap.load_hdf(self.filename) as hdf:
                txt = self.map.format_hdf(hdf, self._text_expression)
            self.textbox.configure(state=tk.NORMAL)
            self.textbox.delete('1.0', tk.END)
            self.textbox.insert('1.0', txt)
            self.textbox.configure(state=tk.DISABLED)
        except Exception as e:
            show_error(f"Error:\n{e}", parent=self.root)

    def edit_expression(self):
        """Double-click on text display => open config str"""
        self._text_expression = EditText(self._text_expression, self.root).show()
        self.update_text()

    def view_namespace(self, event=None):
        """Open HDFMapView gui"""
        pass
        # HDFMapView(self.filename, parent=self.root)

    def fun_terminal(self, event=None):
        if self.filename is None:
            return
        expression = self.terminal_entry.get()
        out_str = f"\n>>> {expression}\n"
        try:
            with hdfmap.load_hdf(self.filename) as hdf:
                out = self.map.eval(hdf, expression)
            self.terminal_entry.set('')
        except NameError as ne:
            out = ne
        out_str += f"{out}\n"
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.insert(tk.END, out_str)
        self.terminal.see(tk.END)
        self.terminal.configure(state=tk.DISABLED)

    def fun_terminal_cls(self, event=None):
        # print('deleting')
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.delete('1.0', tk.END)
        self.terminal.configure(state=tk.DISABLED)
