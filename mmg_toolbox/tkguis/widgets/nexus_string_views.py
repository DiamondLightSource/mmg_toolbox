"""
tk widgets for viewing text based nexus data
"""

import tkinter as tk
from tkinter import ttk

import hdfmap

from mmg_toolbox.tkguis.misc.styles import update_text_style


class _StringView:
    """
    String viewer widget for NeXus file viewer
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

    def _populate(self, string):
        self.delete()
        self.text.insert('1.0', string)

    def populate(self, **kwargs):
        pass

    def delete(self):
        self.text.delete('1.0', tk.END)


class HdfTreeStr(_StringView):
    """
    HDF Tree String object
    """
    def populate(self, hdf_filename: str):
        """Load HDF file, populate ttk.treeview object"""
        tree_str = hdfmap.hdf_tree_string(hdf_filename)
        self._populate(tree_str)


class HdfNexusStr(_StringView):
    """
    Nexus Info String object
    """

    def populate(self, hdf_map: hdfmap.NexusMap):
        """Load HDF file, populate ttk.treeview object"""
        tree_str = hdf_map.info_nexus()
        self._populate(tree_str)


class Nexus2SrsStr(_StringView):
    """
    Display output of NeXus2SRS
    """

    def populate(self, hdf_map: hdfmap.NexusMap):
        """Load HDF file, populate ttk.treeview object"""
        from nexus2srs.nexus2srs import generate_datafile
        with hdf_map.load_hdf() as hdf:
            outstr, detector_image_paths = generate_datafile(hdf, hdf_map)
        self._populate(outstr)


class NxTransformationsStr(_StringView):
    """
    Display output of NeXus2Transformations
    """
    def populate(self, hdf_filename: str):
        from mmg_toolbox.nexus.nexus_transformations import generate_nxtranformations_string
        outstr = generate_nxtranformations_string(hdf_filename)
        self._populate(outstr)
