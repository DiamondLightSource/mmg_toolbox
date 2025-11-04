"""
A treeview tkinter frame for displaying the hierachical structure of HDF and Nexus files
"""

import os
import h5py
import tkinter as tk

import hdfmap
from hdfmap.eval_functions import generate_identifier

from .treeview import CanvasTreeview
from ..misc.logging import create_logger

logger = create_logger(__file__)


class HdfTreeview(CanvasTreeview):
    """
    HDF Treeview object
    """
    def __init__(self, root: tk.Misc, width: int | None = None, height: int | None = None):
        columns = [
            ('#0', 'HDF Address', 400, False, None),
            ('type', 'Type', 100, False, None),
            ('name', 'Name', 100, False, None),
            ('value', 'Value', 200, False, None),
        ]
        super().__init__(root, *columns, width=width, height=height)


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


class HdfNameSpace(CanvasTreeview):
    """
    HDF Namespace object
    """

    def __init__(self, root: tk.Misc, width: int | None = None, height: int | None = None):
        columns = [
            ('#0', 'Name', 100, False, None),
            ('path', 'Path', 300, False, None),
            ('value', 'Value', 200, False, None),
        ]
        super().__init__(root, *columns, width=width, height=height)

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

