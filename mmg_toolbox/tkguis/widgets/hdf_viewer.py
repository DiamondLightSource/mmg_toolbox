"""
tk widget for viewing tree structure of HDF files
"""

import tkinter as tk
from tkinter import ttk

import h5py
import hdfmap

from mmg_toolbox.utils.file_functions import hdfobj_string
from ..misc.functions import open_close_all_tree, select_hdf_file
from ..misc.search import search_tree
from ..misc.styles import update_text_style
from .nexus_string_views import HdfNexusStr, HdfTreeStr, Nexus2SrsStr, NxTransformationsStr
from .nexus_treeview import HdfTreeview, HdfNameSpace


DETAILS_TAB_WIDTH = 30


class HDFViewer:
    """
    HDF Viewer - display cascading hierarchical data within HDF file in ttk GUI
        HDFViewer("filename.h5")
    Simple ttk interface for browsing HDF file structures.
     - Click Browse or File>Select File to pick an HDF, H5 or NeXus file
     - Collapse and expand the tree to view the file structure
     - Search for addresses using the search bar
     - Click on a dataset or group to view stored attributes and data

    :param root: tk root
    :param hdf_filename: str or None*, if str opens this file initially
    """

    def __init__(self, root: tk.Misc, hdf_filename: str = None, config: dict | None = None):
        self.map: hdfmap.NexusMap | None = None
        self.root = root
        self.config = config

        # Variables
        self.filepath = tk.StringVar(self.root, '')
        self.expandall = tk.BooleanVar(self.root, False)
        self.expression_box = tk.StringVar(self.root, '')
        self.expression_path = tk.StringVar(self.root, 'path = ')
        self.search_box = tk.StringVar(self.root, '')
        self.search_matchcase = tk.BooleanVar(self.root, False)
        self.search_wholeword = tk.BooleanVar(self.root, True)

        "------- Build Elements -----"
        # filepath
        self.ini_browse(self.root)

        main = ttk.Frame(self.root)
        main.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(main)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        # Tabs
        self.view_tabs = ttk.Notebook(frm)
        tab1 = ttk.Frame(self.view_tabs)
        tab2 = ttk.Frame(self.view_tabs)
        tab3 = ttk.Frame(self.view_tabs)
        tab4 = ttk.Frame(self.view_tabs)
        tab5 = ttk.Frame(self.view_tabs)
        tab6 = ttk.Frame(self.view_tabs)
        self.view_tabs.bind('<<NotebookTabChanged>>', self.tab_change)

        self.view_tabs.add(tab1, text='HDF Tree')
        self.view_tabs.add(tab2, text='NeXus')
        self.view_tabs.add(tab3, text='HdfMap')
        self.view_tabs.add(tab4, text='Tree String')
        self.view_tabs.add(tab5, text='NeXus2SRS')
        self.view_tabs.add(tab6, text='NXtransformations')
        self.view_tabs.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        # treeviews
        self.hdf_tree = HdfTreeview(tab1)
        self.nexus = HdfNexusStr(tab2)
        self.hdf_map = HdfNameSpace(tab3)
        self.hdf_text = HdfTreeStr(tab4)
        self.nexus2srs = Nexus2SrsStr(tab5)
        self.transformations = NxTransformationsStr(tab6)

        self.hdf_tree.tree.bind('<<TreeviewSelect>>', self.tree_select)
        self.hdf_map.tree.bind('<<TreeviewSelect>>', self.tree_select)

        frm = ttk.Frame(main)
        frm.pack(side=tk.LEFT, expand=tk.NO, fill=tk.BOTH)
        # notebook
        tab_detail, tab_search, tab_expr = self.ini_notebook(frm)

        self.text = self.ini_details(tab_detail)
        self.ini_search(tab_search)
        self.text2 = self.ini_expression(tab_expr)

        if hasattr(self.root, 'style'):
            update_text_style(self.text, self.root.style)
            update_text_style(self.text2, self.root.style)

        "-------- Start Mainloop ------"
        if hdf_filename:
            self.filepath.set(hdf_filename)
            self.populate_from_file()

    "======================================================"
    "================= init functions ====================="
    "======================================================"

    def ini_browse(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Button(frm, text='Browse', command=self.select_file, width=10)
        var.pack(side=tk.LEFT)

        var = ttk.Entry(frm, textvariable=self.filepath)
        var.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        var.bind('<Return>', self.populate_from_file)
        var.bind('<KP_Enter>', self.populate_from_file)

        var = ttk.Checkbutton(frm, variable=self.expandall, text='Expand', command=self.check_expand)
        var.pack(side=tk.LEFT)

    def ini_notebook(self, frame: tk.Misc) -> tuple[ttk.Frame, ttk.Frame, ttk.Frame]:

        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        tab_control = ttk.Notebook(frm)
        tab1 = ttk.Frame(tab_control)
        tab2 = ttk.Frame(tab_control)
        tab3 = ttk.Frame(tab_control)

        tab_control.add(tab1, text='Details')
        tab_control.add(tab2, text='Search')
        tab_control.add(tab3, text='Expression')
        tab_control.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        return tab1, tab2, tab3

    def ini_details(self, frame: tk.Misc) -> tk.Text:
        frm = ttk.Frame(frame)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        text = tk.Text(frm, wrap=tk.NONE, width=DETAILS_TAB_WIDTH)
        text.pack(fill=tk.BOTH, expand=tk.YES)

        var = tk.Scrollbar(frm, orient=tk.HORIZONTAL, command=text.xview)
        var.pack(side=tk.BOTTOM, fill=tk.X)
        text.configure(xscrollcommand=var.set)
        return text

    def ini_search(self, frame: tk.Misc):
        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)

        var = ttk.Entry(frm, textvariable=self.search_box)
        var.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        # var.bind('<KeyRelease>', self.fun_search)
        var.bind('<Return>', self.fun_search)
        var.bind('<KP_Enter>', self.fun_search)
        var = ttk.Button(frm, text='Search', command=self.fun_search, width=10)
        var.pack(side=tk.TOP)

        line = ttk.Frame(frm)
        line.pack(side=tk.TOP)
        var = ttk.Checkbutton(line, variable=self.search_matchcase, text='Case')
        var.pack(side=tk.LEFT)
        var = ttk.Checkbutton(line, variable=self.search_wholeword, text='Word')
        var.pack(side=tk.LEFT)

    def ini_expression(self, frame: tk.Misc) -> tk.Text:
        frm = ttk.Frame(frame)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Entry(frm, textvariable=self.expression_box)
        var.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.fun_expression)
        var.bind('<KP_Enter>', self.fun_expression)

        var = ttk.Label(frm, textvariable=self.expression_path)
        var.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)

        var = ttk.Button(frm, text='Evaluate Expression', command=self.fun_expression)
        var.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)

        text = tk.Text(frm, wrap=tk.NONE, width=DETAILS_TAB_WIDTH)
        text.pack(fill=tk.BOTH, expand=tk.YES)

        var = tk.Scrollbar(frm, orient=tk.HORIZONTAL, command=text.xview)
        var.pack(side=tk.BOTTOM, fill=tk.X)
        text.configure(xscrollcommand=var.set)
        return text

    "======================================================"
    "================ general functions ==================="
    "======================================================"

    def check_expand(self):
        selected = self.view_tabs.select()
        tab_name = self.view_tabs.tab(selected)['text']
        if tab_name == 'HDF Tree':
            open_close_all_tree(self.hdf_tree.tree, "", self.expandall.get())
        elif tab_name == 'HdfMap':
            open_close_all_tree(self.hdf_map.tree, "", self.expandall.get())

    def _delete_tree(self):
        self.hdf_tree.delete()
        self.hdf_map.delete()

    def populate_from_file(self, event=None):
        filename = self.filepath.get()
        self.map = hdfmap.create_nexus_map(filename)
        with hdfmap.load_hdf(filename) as hdf:
            self.populate(hdf, self.map)

    def populate(self, hdf_obj: h5py.File, hdf_map: hdfmap.NexusMap):
        self._delete_tree()
        self.hdf_tree.populate(hdf_obj, openstate=self.expandall.get())
        self.hdf_map.populate(hdf_obj, hdf_map)

    "======================================================"
    "================= event functions ===================="
    "======================================================"

    def tab_change(self, event):
        # Selected tab:
        selected = self.view_tabs.select()
        tab_name = self.view_tabs.tab(selected)['text']
        if tab_name == 'NeXus':
            self.nexus.populate(self.map)
        if tab_name == 'Tree String':
            self.hdf_text.populate(self.map.filename)
        if tab_name == 'NeXus2SRS':
            self.nexus2srs.populate(self.map)
        if tab_name == 'NXtransformations':
            self.transformations.populate(self.map.filename)

    def tree_select(self, event):
        self.text.delete('1.0', tk.END)
        tree = event.widget
        item = tree.focus()
        if 'path' in tree['columns']:  # hdfmap tab
            path = tree.set(item, column='path')
        else:
            path = tree.item(item, 'text')
        out = hdfobj_string(self.filepath.get(), path)
        self.text.insert('1.0', out)

    def select_file(self, event=None):
        filename = select_hdf_file(self.root)
        if filename:
            self.filepath.set(filename)
            self.populate_from_file()

    def fun_search(self, event=None):
        """Search currently active tab"""
        if self.view_tabs.index(self.view_tabs.select()) == 0:
            self.hdf_tree.tree.selection_remove(self.hdf_tree.tree.selection())
            search_tree(
                treeview=self.hdf_tree.tree,
                branch="",
                query=self.search_box.get(),
                match_case=self.search_matchcase.get(),
                whole_word=self.search_wholeword.get()
            )
        else:
            self.hdf_map.tree.selection_remove(self.hdf_map.tree.selection())
            search_tree(
                treeview=self.hdf_map.tree,
                branch="",
                query=self.search_box.get(),
                match_case=self.search_matchcase.get(),
                whole_word=self.search_wholeword.get()
            )

    def fun_expression(self, event=None):
        if self.map is None:
            return
        # self.text2.delete('1.0', tk.END)
        expression = self.expression_box.get()
        self.expression_path.set(f"path = {self.map.get_path(expression)}")
        out_str = f">>> {expression}\n"
        try:
            # out = hdfmap.hdf_eval(self.filepath.get(), expression)
            out = self.map.eval(self.map.load_hdf(), expression)
        except NameError as ne:
            out = ne
        out_str += f"{out}\n\n"
        # self.text2.insert('1.0', out_str)
        self.text2.insert(tk.END, out_str)

