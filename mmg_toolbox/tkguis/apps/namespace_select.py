"""
tk window to select HDF paths from files
"""

import tkinter as tk
from tkinter import ttk
import hdfmap

from mmg_toolbox.tkguis.misc.config import get_config
from mmg_toolbox.tkguis.misc.styles import create_root


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
        widget.populate(hdf, hdf_map, group=False, combined=False, values=False, arrays=False,
                        scannables=False, image_data=False, metadata=True)

    output_names = []

    def select():
        output_names.extend([
            widget.tree.set(iid, column='#0')
            for iid in widget.tree.selection()
        ])
        root.destroy()

    ttk.Button(root, text='Select', command=select).pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=5)

    root.wait_window()
    return output_names

