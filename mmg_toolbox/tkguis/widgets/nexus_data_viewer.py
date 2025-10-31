"""
a tkinter frame with a single plot
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
from .nexus_plot import NexusMultiAxisPlot
from .nexus_image import NexusDetectorImage

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
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        window = ttk.Frame(self.root)
        window.pack()

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

        # TOP-RIGHT
        frm = ttk.LabelFrame(window, text='Plot')
        frm.grid(column=1, row=0, **grid_options)
        sec = ttk.Frame(frm)
        sec.pack(side=tk.TOP, fill=tk.BOTH)
        self.plot_widget = NexusMultiAxisPlot(sec, config=self.config)
        self.index_line, = self.plot_widget.ax1.plot([], [], ls='--', c='k', scaley=False, label=None)

        # BOTTOM-RIGHT
        frm = ttk.LabelFrame(window, text='Image')
        frm.grid(column=1, row=1, **grid_options)
        self.image_frame = ttk.Frame(frm)  # image frame will be packed when required
        self.image_widget = NexusDetectorImage(self.image_frame, config=self.config)

        # update image_widget update_image to add plot line
        def update_index_line():
            xvals, yvals = self.plot_widget.line.get_data()
            index = self.image_widget.view_index.get()
            ylim = self.plot_widget.ax1.get_ylim()
            xval = xvals[index]
            self.index_line.set_data([xval, xval], ylim)
            self.plot_widget.update_axes()
        self.image_widget.extra_plot_callbacks.append(update_index_line)  # runs on update_image

        if initial_folder and len(self.selector_widget.tree.get_children()) > 0:
            # Open first scan
            first_folder = next(iter(self.selector_widget.tree.get_children()))
            if len(self.selector_widget.tree.get_children(first_folder)) > 0:
                first_scan = next(iter(self.selector_widget.tree.get_children(first_folder)))
                self.selector_widget.tree.item(first_folder, open=True)
                self.selector_widget.tree.selection_set(first_scan)

        # self._log_size()

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

        if self.map.image_data:
            self.image_widget.update_data_from_file(filename, self.map)
            xvals, yvals = self.plot_widget.line.get_data()
            index = np.nanargmax(yvals)
            xval = xvals[index]
            ylim = self.plot_widget.ax1.get_ylim()
            self.index_line.set_data([xval, xval], ylim)
            self.plot_widget.update_axes()
            self.image_widget.view_index.set(index)
            self.image_widget.update_image()
            self.image_frame.pack(side=tk.TOP, fill=tk.BOTH)
            # add rois to signal drop-down
            for item in self.image_widget.roi_names:
                self.plot_widget.listbox.insert("", tk.END, text=item)
        else:
            self.image_frame.pack_forget()
            self.index_line.set_data([], [])
            self.plot_widget.update_axes()

    def _log_size(self):
        self.root.update()
        logger.info(f"Geometry: {self.root.winfo_geometry()}")
        logger.info(f"Screen Width x Height: {self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
