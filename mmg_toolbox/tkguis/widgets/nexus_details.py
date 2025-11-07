"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesnocancel

import hdfmap
from hdfmap import create_nexus_map

from mmg_toolbox.utils.env_functions import get_scan_notebooks, TMPDIR
from ..misc.functions import post_right_click_menu, show_error
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from ..misc.screen_size import get_text_size
from ..apps.edit_text import EditText

logger = create_logger(__file__)


class NexusDetails:
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = hdf_filename
        self.map: hdfmap.NexusMap | None = None
        self.config = config or get_config()

        self.terminal_history = ['']
        self.terminal_history_index = 0
        self._text_expression = self.config.get(C.metadata_string, '')
        self.terminal_entry = tk.StringVar(self.root, self.terminal_history[self.terminal_history_index])
        self.notebook = tk.StringVar(self.root, 'None')
        self.notebooks = {}  # notebook: filepath

        self.terminal = self.ini_terminal(self.root)  # pack from bottom
        self.combo_notebook = self.ini_notebooks(self.root)  # pack from bottom
        self.textbox = self.ini_textbox(self.root)

        if hdf_filename:
            self.update_data_from_file(hdf_filename)

    def ini_textbox(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        xfrm = ttk.Frame(frm)
        xfrm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        # reduce text height if screen is small
        text_chars, text_lines = get_text_size(self.root, self.config)
        text = tk.Text(xfrm, state=tk.DISABLED, wrap=tk.NONE, width=text_chars, height=text_lines)
        text.pack(fill=tk.BOTH, expand=tk.YES)
        # text.bind("<Double-1>", self.text_double_click)

        var = ttk.Scrollbar(xfrm, orient=tk.HORIZONTAL)
        var.pack(side=tk.BOTTOM, fill=tk.X)
        var.config(command=text.xview)
        text.configure(xscrollcommand=var.set)

        # right-click menu
        m = tk.Menu(frame, tearoff=0)
        m.add_command(label="edit Text", command=self.edit_expression)
        m.add_command(label="view Metadata", command=self.view_metadata)

        def menu_popup(event):
            post_right_click_menu(m, event.x_root, event.y_root)
        text.bind("<Button-3>", menu_popup)
        return text

    def ini_terminal(self, frame: tk.Misc):
        # Terminal
        frm = ttk.Frame(frame)
        frm.pack(side=tk.BOTTOM, fill=tk.X, expand=tk.YES)

        tfrm = ttk.Frame(frm, relief=tk.RIDGE)
        tfrm.pack(side=tk.TOP, fill=tk.BOTH)

        text_chars, text_lines = get_text_size(self.root, self.config)
        terminal = tk.Text(tfrm, state=tk.DISABLED, wrap=tk.NONE, height=3, width=text_chars)
        terminal.pack(side=tk.LEFT, fill=tk.X, expand=tk.NO)

        var = ttk.Scrollbar(tfrm, orient=tk.VERTICAL)
        var.pack(side=tk.LEFT, fill=tk.Y)
        var.config(command=terminal.yview)
        terminal.configure(yscrollcommand=var.set)

        efrm = ttk.Frame(frm, relief=tk.GROOVE)
        efrm.pack(side=tk.TOP, fill=tk.BOTH)

        var = ttk.Label(efrm, text='>>')
        var.pack(side=tk.LEFT)
        var = ttk.Entry(efrm, textvariable=self.terminal_entry)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.fun_terminal)
        var.bind('<KP_Enter>', self.fun_terminal)
        var.bind('<Up>', self.fun_terminal_history_up)
        var.bind('<Down>', self.fun_terminal_history_down)

        var = ttk.Button(efrm, text='CLS', command=self.fun_terminal_cls)
        var.pack(side=tk.LEFT)
        return terminal

    def ini_notebooks(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.BOTTOM, fill=tk.X, expand=tk.YES, padx=6)

        menu = ttk.OptionMenu(frm, self.notebook)
        menu.pack(side=tk.LEFT)
        ttk.Button(frm, text='Open', command=self.run_notebook).pack(side=tk.LEFT)
        ttk.Button(frm, text='Reprocess', command=self.reprocess_notebook).pack(side=tk.LEFT)
        return menu

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = filename
        self.map = create_nexus_map(self.filename) if hdf_map is None else hdf_map
        self.update_text()
        self.notebooks = {
            os.path.basename(file): file
            for file in get_scan_notebooks(filename)
        }
        if self.notebooks:
            first_notebook = next(iter(self.notebooks))
            self.combo_notebook.set_menu(first_notebook, *self.notebooks)
        else:
            self.combo_notebook.set_menu('None')

    def update_text(self):
        try:
            with hdfmap.load_hdf(self.filename) as hdf:
                txt = self.map.format_hdf(hdf, self._text_expression)
            self.textbox.configure(state=tk.NORMAL)
            self.textbox.delete('1.0', tk.END)
            self.textbox.insert('1.0', txt)
            self.textbox.configure(state=tk.DISABLED)
        except Exception as e:
            show_error(f"Error:\n{e}", parent=self.root, raise_exception=False)

    def edit_expression(self):
        """Double-click on text display => open config str"""
        self._text_expression = EditText(self._text_expression, self.root).show()
        self.update_text()

    def view_metadata(self):
        from ..apps.namespace_select import create_metadata_selector
        hdf_map = self.map or create_nexus_map(self.filename)
        create_metadata_selector(hdf_map, self.root, self.config)

    def run_notebook(self):
        from mmg_toolbox.utils.nb_runner import view_jupyter_notebook, view_notebook_html
        notebook = self.notebook.get()
        if notebook not in self.notebooks:
            return
        filename = self.notebooks[notebook]
        html = filename.replace('.ipynb', '.html')
        if os.path.isfile(html):
            view_jupyter_notebook(html)
        else:
            # generate html in TMP
            view_notebook_html(filename)

    def reprocess_notebook(self):
        """Copy notebook to processing folder"""
        from mmg_toolbox.utils.nb_runner import reprocess_notebook
        notebook = self.notebook.get()
        if notebook not in self.notebooks:
            return
        filename = self.notebooks[notebook]

        response = askyesnocancel(
            title="NeXus Data Viewer",
            message=f"This will copy {notebook} and start a jupyter server\nYes will copy to processing, No to TMP",
            parent=self.root,
        )
        if response:
            print('Yes')
            reprocess_notebook(filename)
        elif response is None:
            print('Cancel')
            return
        else:
            print('No')
            reprocess_notebook(filename, output_folder=TMPDIR)

    def set_terminal(self):
        self.terminal_entry.set(self.terminal_history[self.terminal_history_index])

    def fun_terminal(self, event=None):
        if self.filename is None:
            return
        expression = self.terminal_entry.get()
        out_str = f"\n>>> {expression}\n"
        try:
            # TODO: replace with asteval.Interpreter (maybe in hdfmap V1.1)
            with hdfmap.load_hdf(self.filename) as hdf:
                out = self.map.eval(hdf, expression)
            self.terminal_history.insert(1, expression)
            self.terminal_history_index = 0
            self.set_terminal()
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

    def fun_terminal_history_up(self, event=None):
        if len(self.terminal_history) > self.terminal_history_index:
            self.terminal_history_index += 1
            self.set_terminal()

    def fun_terminal_history_down(self, event=None):
        self.terminal_history_index -= 1
        self.set_terminal()
