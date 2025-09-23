"""
A treeview tkinter frame for displaying the hierachical structure of HDF and Nexus files
"""

import os
import h5py
import tkinter as tk
from tkinter import ttk

import hdfmap
from hdfmap.eval_functions import generate_identifier

from ...file_functions import hdfobj_string
from ..misc.styles import update_text_style
from ..misc.functions import post_right_click_menu, open_close_all_tree, select_hdf_file
from ..misc.search import search_tree
from ..misc.logging import create_logger

logger = create_logger(__file__)

DETAILS_TAB_WIDTH = 30


def right_click_menu(frame, tree):
    """
    Create right-click context menu for hdf_tree objects
    :param frame: tkinter frame
    :param tree: ttk.Treeview object
    :return: menu_popup function
    """

    def copy_address():
        for iid in tree.selection():
            frame.master.clipboard_clear()
            frame.master.clipboard_append(tree.item(iid)['text'])

    def copy_name():
        for iid in tree.selection():
            frame.master.clipboard_clear()
            frame.master.clipboard_append(tree.item(iid)['values'][-2])

    def copy_value():
        for iid in tree.selection():
            frame.master.clipboard_clear()
            frame.master.clipboard_append(tree.item(iid)['values'][-1])

    # right-click menu - file options
    m = tk.Menu(frame, tearoff=0)
    m.add_command(label="Copy address", command=copy_address)
    m.add_command(label="Copy name", command=copy_name)
    m.add_command(label="Copy value", command=copy_value)

    def menu_popup(event):
        # select item
        iid = tree.identify_row(event.y)
        if iid:
            tree.selection_set(iid)
            post_right_click_menu(m, event.x_root, event.y_root)
    return menu_popup


class HdfTreeview:
    """
    HDF Treeview object
    """
    def __init__(self, root: tk.Misc):

        frm = ttk.Frame(root)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        tree = ttk.Treeview(frm, columns=('type', 'name', 'value'), selectmode='browse')
        tree.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        tree.configure(yscrollcommand=var.set)

        # Populate tree
        tree.heading("#0", text="HDF Address")
        tree.column("#0", minwidth=50, width=400)
        tree.column("type", width=100, anchor='c')
        tree.column("name", width=100, anchor='c')
        tree.column("value", width=200, anchor='c')
        tree.heading("type", text="Type")
        tree.heading("name", text="Name")
        tree.heading("value", text="Value")
        # tree.bind("<<TreeviewSelect>>", self.tree_select)
        # tree.bind("<Double-1>", self.on_double_click)
        tree.bind("<Button-3>", right_click_menu(frm, tree))
        self.tree = tree

    def populate(self, hdf_obj: h5py.File, openstate=True):
        """Load HDF file, populate ttk.treeview object"""

        def recur_func(hdf_group, tree_group="", top_address='/'):
            for key in hdf_group:
                obj = hdf_group.get(key)
                link = hdf_group.get(key, getlink=True)
                address = top_address + key
                name = generate_identifier(address)
                if isinstance(obj, h5py.Group):
                    try:
                        nx_class = obj.attrs['NX_class'].decode() if 'NX_class' in obj.attrs else 'Group'
                    except AttributeError:
                        nx_class = obj.attrs['NX_class']
                    except OSError:
                        nx_class = 'Group'  # if object doesn't have attrs
                    values = (nx_class, name, "")
                    new_tree_group = self.tree.insert(tree_group, tk.END, text=address, values=values)
                    # add attributes
                    for attr, val in obj.attrs.items():
                        self.tree.insert(new_tree_group, tk.END, text=f"@{attr}", values=('Attribute', attr, val))
                    recur_func(obj, new_tree_group, address + '/')
                    self.tree.item(new_tree_group, open=openstate)
                elif isinstance(obj, h5py.Dataset):
                    if isinstance(link, h5py.ExternalLink):
                        link_type = 'External Link'
                    elif isinstance(link, h5py.SoftLink):
                        link_type = 'Soft Link'
                    else:
                        link_type = 'Dataset'
                    if obj.shape:
                        val = f"{obj.dtype} {obj.shape}"
                    else:
                        val = str(obj[()])
                    values = (link_type, name, val)
                    # datasets.append(address)
                    new_tree_group = self.tree.insert(tree_group, tk.END, text=address, values=values)
                    for attr, val in obj.attrs.items():
                        self.tree.insert(new_tree_group, tk.END, text=f"@{attr}", values=('Attribute', attr, val))
                    self.tree.item(new_tree_group, open=False)

        # add top level file group
        hdf_filename = hdf_obj.filename
        self.tree.insert("", tk.END, text='/', values=('File', os.path.basename(hdf_filename), ''))
        recur_func(hdf_obj, "")

    def delete(self):
        self.tree.delete(*self.tree.get_children())


class HdfNameSpace:
    """
    HDF Namespace object
    """

    def __init__(self, root: tk.Misc):

        frm = ttk.Frame(root)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        tree = ttk.Treeview(frm, columns=('path', 'value'), selectmode='browse')
        tree.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        tree.configure(yscrollcommand=var.set)

        # Populate tree
        tree.heading("#0", text="Name")
        tree.column("#0", minwidth=50, width=100)
        tree.column("path", width=300, anchor='c')
        tree.column("value", width=200, anchor='c')
        tree.heading("path", text="Path")
        tree.heading("value", text="Value")
        # tree.bind("<<TreeviewSelect>>", self.tree_select)
        # tree.bind("<Double-1>", self.on_double_click)
        tree.bind("<Button-3>", right_click_menu(frm, tree))
        self.tree = tree

    def populate(self, hdf_obj: h5py.File, hdf_map: hdfmap.NexusMap):
        """Load HDF file, populate ttk.treeview object"""

        data = {
            name: hdf_map.get_string(hdf_obj, name)
            for name, path in hdf_map.combined.items()
        }

        datasets = self.tree.insert("", tk.END, text='Groups', values=('', ''))
        for name, path_list in hdf_map.classes.items():
            # path_list = list(set(path_list))  # remove duplicates
            if len(path_list) == 1:
                self.tree.insert(datasets, tk.END, text=name, values=(path_list[0], ''))
            else:
                grp = self.tree.insert(datasets, tk.END, text=name, values=('', ''))
                for path in path_list:
                    self.tree.insert(grp, tk.END, text=name, values=(path, ''))

        datasets = self.tree.insert("", tk.END, text='Combined', values=('', ''))
        for name, path in hdf_map.combined.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        datasets = self.tree.insert("", tk.END, text='Values', values=('', ''))
        for name, path in hdf_map.values.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        datasets = self.tree.insert("", tk.END, text='Arrays', values=('', ''))
        for name, path in hdf_map.arrays.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        datasets = self.tree.insert("", tk.END, text='Scannables', values=('', ''))
        for name, path in hdf_map.scannables.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        datasets = self.tree.insert("", tk.END, text='Metadata', values=('', ''))
        for name, path in hdf_map.metadata.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        datasets = self.tree.insert("", tk.END, text='Image Data', values=('', ''))
        for name, path in hdf_map.image_data.items():
            value = data.get(name, 'NOT IN MAP')
            self.tree.insert(datasets, tk.END, text=name, values=(path, value))

    def delete(self):
        self.tree.delete(*self.tree.get_children())


class HdfTreeStr:
    """
    HDF Tree String object
    """

    def __init__(self, root: tk.Misc):

        frm = ttk.Frame(root)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        self.text = tk.Text(frm, wrap=tk.NONE)

        vbar = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        hbar = ttk.Scrollbar(frm, orient=tk.HORIZONTAL, command=self.text.xview)
        self.text.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        if hasattr(root, 'style'):
            update_text_style(self.text, root.style)

    def populate(self, hdf_filename: str):
        """Load HDF file, populate ttk.treeview object"""
        tree_str = hdfmap.hdf_tree_string(hdf_filename)
        self.delete()
        self.text.insert('1.0', tree_str)

    def delete(self):
        self.text.delete('1.0', tk.END)


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

    def __init__(self, root: tk.Misc, hdf_filename: str = None):
        self.map = None
        self.root = root

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

        self.view_tabs.add(tab1, text='HDF Tree')
        self.view_tabs.add(tab2, text='HdfMap')
        self.view_tabs.add(tab3, text='Tree String')
        self.view_tabs.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        # treeviews
        self.hdf_tree = HdfTreeview(tab1)
        self.hdf_map = HdfNameSpace(tab2)
        self.hdf_text = HdfTreeStr(tab3)

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
        open_close_all_tree(self.hdf_tree, "", self.expandall.get())

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
        self.hdf_text.populate(hdf_obj.filename)

    "======================================================"
    "================= event functions ===================="
    "======================================================"

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