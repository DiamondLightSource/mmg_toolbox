"""
a tkinter frame combining 2D line plots and images from a NeXus file
"""
import tkinter as tk
from tkinter import ttk

import hdfmap

from ..misc.styles import create_root
from ..misc.logging import create_logger
from .nexus_plot import NexusMultiAxisPlot
from .nexus_image import NexusDetectorImage

logger = create_logger(__file__)


class NexusPlotAndImage(NexusMultiAxisPlot, NexusDetectorImage):
    """
    tkinter widget containing 2D line plot and image plot

    widget = NexusPlotAndImage(root, 'path/to/file.nxs', config=config)

    """
    def __init__(self, root: tk.Misc, *hdf_filenames: str,
                 config: dict | None = None, horizontal_alignment: bool = False):
        grid_options = dict(padx=5, pady=5, sticky='nsew')
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        # 2D Plot
        frm = ttk.LabelFrame(root, text='Plot')
        frm.grid(column=0, row=0, **grid_options)
        sec = ttk.Frame(frm)
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        # super().__init__(sec, *hdf_filenames, config=config)
        NexusMultiAxisPlot.__init__(self, sec, config=config)

        # Image
        frm = ttk.LabelFrame(root, text='Image')
        if horizontal_alignment:
            frm.grid(column=1, row=0, **grid_options)
        else:
            frm.grid(column=0, row=1, **grid_options)
        self.image_frame = ttk.Frame(frm)  # image frame will be packed when required
        NexusDetectorImage.__init__(self, self.image_frame, config=config)

        # Index line (used by both components)
        self.index_line, = self.ax1.plot([], [], ls='--', c='k', scaley=False, label=None)

        if hdf_filenames:
            self.update_data_from_files(*hdf_filenames)

    def pack_image(self):
        self.image_frame.pack(fill=tk.BOTH, expand=tk.YES)

    def remove_image(self):
        self.image_frame.pack_forget()

    def update_index_line(self):
        """update image_widget update_image to add plot line"""
        xvals, yvals = self.line.get_data()
        index = self.view_index.get()
        ylim = self.ax1.get_ylim()
        xval = xvals[index]
        self.index_line.set_data([xval, xval], ylim)
        self.update_axes()

    def update_data_from_files(self, *filenames: str, hdf_map: hdfmap.NexusMap | None = None):
        hdf_map = hdf_map or hdfmap.create_nexus_map(filenames[0])
        NexusMultiAxisPlot.update_data_from_files(self, *filenames, hdf_map=hdf_map)
        if hdf_map.image_data:
            NexusDetectorImage.update_image_data_from_file(self, filenames[0], hdf_map=hdf_map)
            self.update_index_line()
            self.pack_image()
        else:
            self.index_line.set_data([], [])
            self.remove_image()

    def update_image(self, event=None):
        super().update_image(event)
        self.update_index_line()

    def add_config_rois(self):
        super().add_config_rois()
        # add rois to signal drop-down
        for item in self.roi_names:
            self.listbox.insert("", tk.END, text=item)

    def new_window(self):
        window = create_root(self.filename, self.parent)
        widget = NexusPlotAndImage(window, config=self.config, horizontal_alignment=True)
        widget.update_data_from_files(self.filename, hdf_map=self.map)
        return widget
