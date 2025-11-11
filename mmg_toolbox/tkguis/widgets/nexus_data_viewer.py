"""
a tkinter frame with 4 sections:
    NW: File selection treeview
    SW: NeXus metadata viewer
    NE: 2D Line plot
    SE: Image plot
"""
import tkinter as tk
from tkinter import ttk
import numpy as np

from hdfmap import create_nexus_map

from mmg_toolbox.utils.env_functions import get_scan_number
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from .scan_selector import FolderScanSelector
from .nexus_details import NexusDetails
from .nexus_plot_and_image import NexusPlotAndImage

logger = create_logger(__file__)


class NexusDataViewer:
    """
    tkinter widget containing scan selector, details,
    line plot and image plot - the main frame in the data viewer.

    widget = NexusDataViewer(root, 'initial/folder', config)


    """
    def __init__(self, root: tk.Misc, initial_folder: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.map = None
        self.config = config or get_config()

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        window = ttk.Frame(self.root)
        # window.pack(fill=tk.BOTH, expand=tk.YES)
        window.grid(column=0, row=0, **grid_options)
        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        window.columnconfigure(0, weight=0)
        window.columnconfigure(1, weight=1)

        # TOP-LEFT
        frm = ttk.LabelFrame(window, text='Files')
        frm.grid(column=0, row=0, **grid_options)
        self.selector_widget = FolderScanSelector(frm, initial_directory=initial_folder, config=self.config)
        self.selector_widget.tree.bind("<<TreeviewSelect>>", self.on_file_select)

        # BOTTOM-LEFT
        frm = ttk.LabelFrame(window, text='Details')
        # frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.YES, padx=2, pady=2)
        frm.grid(column=0, row=1, **grid_options)
        self.detail_widget = NexusDetails(frm, config=self.config)

        # RIGHT-SIDE
        frm = ttk.Frame(window)
        frm.grid(column=1, row=0, rowspan=2, **grid_options)
        self.plot_widget = NexusPlotAndImage(frm, config=self.config)

        # select first file if it exists
        self.root.after(100, self.select_first_file, None)

    def select_first_file(self, _event=None):
        if len(self.selector_widget.tree.get_children()) > 0:
            first_folder = next(iter(self.selector_widget.tree.get_children()))
            if len(self.selector_widget.tree.get_children(first_folder)) > 0:
                first_scan = next(iter(self.selector_widget.tree.get_children(first_folder)))
                self.selector_widget.tree.item(first_folder, open=True)
                self.selector_widget.tree.selection_set(first_scan)

    def on_file_select(self, event=None):
        filename, folder = self.selector_widget.get_filepath()
        filenames = self.selector_widget.get_multi_filepath()
        if len(filenames) == 0:
            return
        self.config[C.current_dir] = folder

        logger.info(f"Updating widgets for file: {filename}")
        # TODO: time and speed up this part
        self.selector_widget.select_box.set(get_scan_number(filename))
        self.map = create_nexus_map(filename)
        self.detail_widget.update_data_from_file(filename, self.map)
        self.plot_widget.update_data_from_files(*filenames, hdf_map=self.map)
