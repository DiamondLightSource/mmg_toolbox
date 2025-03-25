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

        # scroll = ttk.Scrollbar(self.root, orient=tk.VERTICAL)
        # scroll.pack(side=tk.RIGHT, fill=tk.Y)
        # canvas = tk.Canvas(self.root)#, #yscrollcommand=scroll.set)
        # canvas.pack()
        # scroll.config(command=canvas.yview)
        # window = ttk.Frame(canvas)
        # canvas.create_window(0, 0, window=window)
        # # var.config(command=terminal.yview)
        # # terminal.configure(yscrollcommand=var.set)
        # canvas.config(yscrollcommand=scroll.set,
        #               scrollregion=(0, 0, 100, 100))

        window = tk.Frame()
        window.pack()
        frm = ttk.LabelFrame(window, text='Files', width=50)
        frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.NO, padx=2, pady=2)
        self.selector_widget = FolderScanSelector(frm, initial_directory=initial_folder)
        self.selector_widget.tree.bind("<<TreeviewSelect>>", self.on_file_select)

        # frm = ttk.LabelFrame(self.root, text='Details')
        # frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.YES, padx=2, pady=2)
        self.detail_widget = NexusDetails(frm, config=self.config)

        frm = ttk.LabelFrame(window, text='Plot')
        frm.pack(side=tk.LEFT, fill=tk.Y, expand=tk.NO, padx=2, pady=2)
        sec = ttk.Frame(frm)
        sec.pack(side=tk.TOP, fill=tk.X)
        self.plot_widget = NexusDefaultPlot(sec, config=self.config)
        self.index_line = self.plot_widget.ax1.axvline(0, ls='--', c='k')
        sec = ttk.Frame(frm)
        sec.pack(side=tk.TOP, fill=tk.X)
        self.image_widget = NexusDetectorImage(sec, config=self.config)

        self._log_size()

    def on_file_select(self, event=None):
        filename, folder = self.selector_widget.get_filepath()
        if filename:
            logger.info(f"Updating widgets for file: {filename}")
            self.filename = filename
            self.map = create_nexus_map(filename)
            self.detail_widget.update_data_from_file(filename, self.map)
            self.plot_widget.update_data_from_file(filename, self.map)
            self.image_widget.update_data_from_file(filename, self.map)

            xvals, yvals = self.plot_widget.line.get_data()
            print(f"nanargmax: {np.nanargmax(yvals)}")
            index = np.nanargmax(yvals)
            self.image_widget.view_index.set(index)
            self.image_widget.update_image()
            ylim = self.plot_widget.ax1.get_ylim()
            self.index_line.set_data([xvals[index], xvals[index]], ylim)
            self.plot_widget.update_axes()

    def _log_size(self):
        self.root.update()
        logger.info(f"Geometry: {self.root.winfo_geometry()}")
        logger.info(f"Screen Width x Height: {self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
