"""
a tkinter frame with a single plot
"""
import tkinter as tk
from tkinter import ttk
import numpy as np
import h5py

import hdfmap
from hdfmap import create_nexus_map

from ..misc.logging import create_logger
from ..misc.config import get_config
from .scan_selector import FolderScanSelector
from .nexus_details import NexusDetails
from .nexus_plot import NexusDefaultPlot
from .nexus_image import NexusDetectorImage

logger = create_logger(__file__)


class NexusScanDetailsPlot:
    def __init__(self, root: tk.Misc, initial_folder: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = ''
        self.map = None
        self.config = get_config() if config is None else config

        frm = ttk.LabelFrame(self.root, text='Files')
        frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.NO, padx=2, pady=2)
        self.selector_widget = FolderScanSelector(frm, initial_directory=initial_folder)
        self.selector_widget.tree.bind("<<TreeviewSelect>>", self.on_file_select)

        # frm = ttk.LabelFrame(self.root, text='Details')
        # frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.YES, padx=2, pady=2)
        self.detail_widget = NexusDetails(frm, config=self.config)

        frm = ttk.LabelFrame(self.root, text='Plot')
        frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.NO, padx=2, pady=2)
        self.plot_widget = NexusDefaultPlot(frm, config=self.config)
        self.image_widget = NexusDetectorImage(frm, config=self.config)

    def on_file_select(self, event=None):
        filename, folder = self.selector_widget.get_filepath()
        if filename:
            logger.info(f"Updating widgets for file: {filename}")
            self.filename = filename
            self.map = create_nexus_map(filename)
            self.detail_widget.update_data_from_file(filename, self.map)
            self.plot_widget.update_data_from_file(filename, self.map)
            self.image_widget.update_data_from_file(filename, self.map)
