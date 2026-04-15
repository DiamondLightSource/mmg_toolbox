"""
a tkinter frame combining 2D line plots and images from a NeXus file
"""
import tkinter as tk
from tkinter import ttk
from threading import Thread

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
    GRID_OPTIONS = dict(padx=5, pady=5, sticky='nsew')

    def __init__(self, root: tk.Misc, *hdf_filenames: str,
                 config: dict | None = None, horizontal_alignment: bool = False):
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        self.horizontal_alignment = horizontal_alignment

        # 2D Plot
        self.plot_frame = ttk.LabelFrame(root, text='Plot')
        self.plot_frame.grid(row=0, column=0, **self.GRID_OPTIONS)
        NexusMultiAxisPlot.__init__(self, self.plot_frame, config=config)

        # Image
        self.image_frame = ttk.LabelFrame(root, text='Image')
        if self.horizontal_alignment:
            self.image_frame.grid(row=0, column=1, **self.GRID_OPTIONS)
        else:
            self.image_frame.grid(row=1, column=0, **self.GRID_OPTIONS)
        NexusDetectorImage.__init__(self, self.image_frame, config=config)

        # Index line (used by both components)
        self.index_line, = self.ax1.plot([], [], ls='--', c='k', scaley=False, label=None)

        if hdf_filenames:
            self.update_data_from_files(*hdf_filenames)

    def pack_frames(self, hdf_map: hdfmap.NexusMap):
        if hdf_map.image_data and hdf_map.scannables_length() == 1:
            logger.info('Packing image only')
            # Detector image only
            self.plot_frame.grid_forget()
            self.image_frame.grid(row=0, column=0, **self.GRID_OPTIONS)
        elif hdf_map.image_data:
            # Detector image and plot
            self.plot_frame.grid(row=0, column=0, **self.GRID_OPTIONS)
            if self.horizontal_alignment:
                logger.info('Packing plot and image horizontally')
                self.image_frame.grid(row=0, column=1, **self.GRID_OPTIONS)
            else:
                logger.info('Packing plot and image vertically')
                self.image_frame.grid(row=1, column=0, **self.GRID_OPTIONS)
        else:
            logger.info('Packing plot only')
            self.plot_frame.grid(row=0, column=0, **self.GRID_OPTIONS)
            self.image_frame.grid_forget()

    def update_index_line(self):
        """update image_widget update_image to add plot line"""
        xvals, yvals = self.line.get_data()
        index = self.view_index.get()
        ylim = self.ax1.get_ylim()
        xval = xvals[index]
        self.index_line.set_data([xval, xval], ylim)
        self.update_axes()

    def _update_image(self, filename: str, hdf_map: hdfmap.NexusMap):
        self.axis_name.set(self.axes_x.get())
        NexusDetectorImage.update_image_data_from_file(self, filename, hdf_map=hdf_map)

    def update_data_from_files(self, *filenames: str, hdf_map: hdfmap.NexusMap | None = None):
        hdf_map = hdf_map or hdfmap.create_nexus_map(filenames[0])
        NexusMultiAxisPlot.update_data_from_files(self, *filenames, hdf_map=hdf_map)
        self.pack_frames(hdf_map)
        if hdf_map.image_data:
            self.update_index_line()
            th = Thread(target=self._update_image, args=(filenames[0], hdf_map))
            th.daemon = True
            th.start()
        else:
            self.index_line.set_data([], [])

    def update_image(self, event=None):
        NexusDetectorImage.update_image(self, event)
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
