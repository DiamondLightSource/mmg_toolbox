"""
A treeview tkinter frame for displaying the hierachical structure of HDF and Nexus files
"""

import os
import h5py
import tkinter as tk
from tkinter import ttk

import hdfmap
from hdfmap.eval_functions import generate_identifier

from ..misc.functions import post_right_click_menu
from ..misc.logging import create_logger

logger = create_logger(__file__)

# TODO: make this more general, add to _Treeview
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


class _Treeview:
    """
    Treeview  widget for NeXus file viewer

    params
     root: tk frame
    """
    def __init__(self, root: tk.Misc, *columns: str):
        frm = ttk.Frame(root)
        frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        tree = ttk.Treeview(frm, columns=columns, selectmode='browse')
        tree.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        var = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        tree.configure(yscrollcommand=var.set)

        # tree.bind("<<TreeviewSelect>>", self.tree_select)
        # tree.bind("<Double-1>", self.on_double_click)
        tree.bind("<Button-3>", right_click_menu(frm, tree))
        self.tree = tree

    def populate(self, **kwargs):
        pass

    def delete(self):
        self.tree.delete(*self.tree.get_children())


class HdfTreeview(_Treeview):
    """
    HDF Treeview object
    """
    def __init__(self, root: tk.Misc):
        super().__init__(root, 'type', 'name', 'value')
        # Populate tree
        self.tree.heading("#0", text="HDF Address")
        self.tree.column("#0", minwidth=50, width=400)
        self.tree.column("type", width=100, anchor='c')
        self.tree.column("name", width=100, anchor='c')
        self.tree.column("value", width=200, anchor='c')
        self.tree.heading("type", text="Type")
        self.tree.heading("name", text="Name")
        self.tree.heading("value", text="Value")

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


class HdfNameSpace(_Treeview):
    """
    HDF Namespace object
    """

    def __init__(self, root: tk.Misc):
        super().__init__(root, 'path', 'value')

        # Populate tree
        self.tree.heading("#0", text="Name")
        self.tree.column("#0", minwidth=50, width=100)
        self.tree.column("path", width=300, anchor='c')
        self.tree.column("value", width=200, anchor='c')
        self.tree.heading("path", text="Path")
        self.tree.heading("value", text="Value")

    def populate(self, hdf_obj: h5py.File, hdf_map: hdfmap.NexusMap,
                 all: bool = True, group: bool = False, combined: bool = False, values: bool = False,
                 arrays: bool = False, scannables: bool = False, metadata: bool = False, image_data: bool = False):
        """Load HDF file, populate ttk.treeview object"""

        data = {
            name: hdf_map.get_string(hdf_obj, name)
            for name, path in hdf_map.combined.items()
        }

        if all or group:
            datasets = self.tree.insert("", tk.END, text='Groups', values=('', ''))
            for name, path_list in hdf_map.classes.items():
                # path_list = list(set(path_list))  # remove duplicates
                if len(path_list) == 1:
                    self.tree.insert(datasets, tk.END, text=name, values=(path_list[0], ''))
                else:
                    grp = self.tree.insert(datasets, tk.END, text=name, values=('', ''))
                    for path in path_list:
                        self.tree.insert(grp, tk.END, text=name, values=(path, ''))

        if all or combined:
            datasets = self.tree.insert("", tk.END, text='Combined', values=('', ''))
            for name, path in hdf_map.combined.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        if all or values:
            datasets = self.tree.insert("", tk.END, text='Values', values=('', ''))
            for name, path in hdf_map.values.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        if all or arrays:
            datasets = self.tree.insert("", tk.END, text='Arrays', values=('', ''))
            for name, path in hdf_map.arrays.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        if all or scannables:
            datasets = self.tree.insert("", tk.END, text='Scannables', values=('', ''))
            for name, path in hdf_map.scannables.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        if all or metadata:
            datasets = self.tree.insert("", tk.END, text='Metadata', values=('', ''))
            for name, path in hdf_map.metadata.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

        if all or image_data:
            datasets = self.tree.insert("", tk.END, text='Image Data', values=('', ''))
            for name, path in hdf_map.image_data.items():
                value = data.get(name, 'NOT IN MAP')
                self.tree.insert(datasets, tk.END, text=name, values=(path, value))

