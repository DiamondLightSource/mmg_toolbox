"""
tk window to select HDF paths from files
"""

import tkinter as tk
from tkinter import ttk
import hdfmap

from ..misc.functions import open_close_all_tree
from ..misc.config import get_config
from ..misc.styles import create_root


def create_metadata_selector(hdf_map: hdfmap.NexusMap,
                             parent: tk.Misc | None = None, config: dict | None = None) -> list[str]:
    """
    Create a hdfmap namespace selector
    """
    from ..widgets.nexus_treeview import HdfNameSpace

    root = create_root(parent=parent, window_title='Select Metadata')
    config = get_config() if config is None else config

    widget = HdfNameSpace(root)
    with hdf_map.load_hdf() as hdf:
        widget.populate(hdf, hdf_map, all=False, metadata=True)
    open_close_all_tree(widget.tree, "", True)

    output_names = []

    def select():
        output_names.extend([
            widget.tree.item(iid, 'text')
            for iid in widget.tree.selection()
        ])
        root.destroy()

    ttk.Button(root, text='Select', command=select).pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=5)

    root.wait_window()
    return output_names


def create_scannable_selector(hdf_map: hdfmap.NexusMap,
                              parent: tk.Misc | None = None, config: dict | None = None) -> list[str]:
    """
    Create a hdfmap namespace selector
    """
    from ..widgets.nexus_treeview import HdfNameSpace

    root = create_root(parent=parent, window_title='Select Scannable')
    config = get_config() if config is None else config

    widget = HdfNameSpace(root)
    with hdf_map.load_hdf() as hdf:
        widget.populate(hdf, hdf_map, all=False, scannables=True)
    open_close_all_tree(widget.tree, "", True)

    output_names = []

    def select(event=None):
        output_names.extend([
            widget.tree.item(iid, 'text')
            for iid in widget.tree.selection()
        ])
        root.destroy()

    widget.tree.bind("<Double-1>", select)
    ttk.Button(root, text='Select', command=select).pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=5)

    root.wait_window()
    return output_names