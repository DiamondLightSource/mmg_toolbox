"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
import numpy as np

import hdfmap
from hdfmap import create_nexus_map

from ...file_functions import read_tiff
from ..misc.functions import show_error
from ..misc.styles import create_hover
from ..misc.matplotlib import ini_image, COLORMAPS, DEFAULT_COLORMAP
from ..misc.logging import create_logger
from ..misc.config import get_config

logger = create_logger(__file__)


class NexusDetectorImage:
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = hdf_filename
        self.map: hdfmap.NexusMap | None = None
        self.config = get_config() if config is None else config

        self.detector_name = tk.StringVar(self.root, 'NXdetector')
        self.view_index = tk.IntVar(self.root, 0)
        self.axis_name = tk.StringVar(self.root, 'axis = ')
        self.axis_value = tk.DoubleVar(self.root, 0)
        self.logplot = tk.BooleanVar(self.root, False)
        self.difplot = tk.BooleanVar(self.root, False)
        self.mask = tk.DoubleVar(self.root, 0)
        self.cmin = tk.DoubleVar(self.root, 0)
        self.cmax = tk.DoubleVar(self.root, 1)
        self.fixclim = tk.BooleanVar(self.root, False)
        self.colormap = tk.StringVar(self.root, self.config.get('default_colormap', DEFAULT_COLORMAP))

        section = ttk.Frame(self.root)
        section.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        self.detector_menu = ttk.OptionMenu(frm, self.detector_name, None, 'NXdetector', command=self.update_image)
        self.detector_menu.pack(side=tk.RIGHT)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        self.fig, self.ax, self.ax_image, self.colorbar, self.toolbar = ini_image(frm)
        self.ax.set_xlabel(None)
        self.ax.set_ylabel(None)

        self.slider = self.ini_slider()

        if hdf_filename:
            self.update_data_from_file(hdf_filename)

    def ini_slider(self):
        frm = ttk.Frame(self.root)
        frm.pack(expand=tk.NO, pady=2, padx=5)

        def inc():
            self.view_index.set(self.view_index.get() + 1)
            self.update_image()

        def dec():
            self.view_index.set(self.view_index.get() - 1)
            self.update_image()

        var = ttk.Label(frm, text='Index:', width=8)
        var.pack(side=tk.LEFT)
        var = ttk.Button(frm, text='-', command=dec)
        var.pack(side=tk.LEFT)
        tkscale = ttk.Scale(frm, from_=0, to=100, variable=self.view_index, orient=tk.HORIZONTAL,
                            command=self.update_image, length=300)
        # var.bind("<ButtonRelease-1>", callback)
        tkscale.pack(side=tk.LEFT, expand=tk.YES)
        var = ttk.Button(frm, text='+', command=inc)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.view_index, width=6)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)

        # axis label
        var = ttk.Label(frm, textvariable=self.axis_name)
        var.pack(side=tk.LEFT)
        var = ttk.Label(frm, textvariable=self.axis_value)
        var.pack(side=tk.LEFT)

        # Options button
        var = ttk.Button(frm, text='Options', command=self.options_frame)
        var.pack(side=tk.LEFT, padx=3)
        return tkscale

    def options_frame(self):
        """A hovering frame with options"""
        window, fun_close = create_hover(self.root)

        frm = ttk.LabelFrame(window, text='Options', relief=tk.RIDGE)
        frm.pack(expand=tk.NO, pady=2, padx=5)

        var = ttk.Checkbutton(frm, text='Log', variable=self.logplot, command=self.update_image)
        var.pack(side=tk.LEFT, padx=6)
        var = ttk.Checkbutton(frm, text='Diff', variable=self.difplot, command=self.update_image)
        var.pack(side=tk.LEFT, padx=6)

        var = ttk.Label(frm, text='Mask <')
        var.pack(side=tk.LEFT, expand=tk.NO, padx=6)
        var = ttk.Entry(frm, textvariable=self.mask, width=6)
        var.pack(side=tk.LEFT, padx=6)
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)

        var = ttk.OptionMenu(frm, self.colormap, *COLORMAPS, command=self.update_image)
        var.pack(side=tk.LEFT)

        var = ttk.Label(frm, text='clim:')
        var.pack(side=tk.LEFT, expand=tk.NO)
        var = ttk.Entry(frm, textvariable=self.cmin, width=6)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)
        var = ttk.Entry(frm, textvariable=self.cmax, width=6)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)
        var = ttk.Checkbutton(frm, text='Fix', variable=self.fixclim)
        var.pack(side=tk.LEFT)

        frm = ttk.Frame(window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        var = ttk.Button(frm, text='Close', command=fun_close)
        var.pack(fill=tk.X)

    def options_menu(self) -> dict:
        """Return a dict of options for menu structure"""
        menu = {
            "Image": {
                "Change options": self.options_frame,
            }
        }
        return menu

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = filename
        self.map = create_nexus_map(self.filename) if hdf_map is None else hdf_map
        self.slider.config(to=self.map.scannables_length() - 1)  # set slider max
        detector_names = list(self.map.image_data.keys())
        # self.detector_menu['values'] = detector_names if detector_names else ['No 2D NXdetectors']
        self.detector_menu.set_menu(
            *detector_names
        )
        if not detector_names:
            return
        self.view_index.set(0)
        self.update_image()

    def _get_image(self):
        try:
            detector = self.detector_name.get()
            axis_name = self.axis_name.get()
            index = int(self.view_index.get())
            self.view_index.set(index)

            self.map.set_image_path(self.map.image_data[detector])
            with hdfmap.load_hdf(self.filename) as hdf:
                image = self.map.get_image(hdf, index)
                value = self.map.get_data(hdf, axis_name, index=index, default=index)

            if issubclass(type(image), str):
                # TIFF image
                file_directory = os.path.dirname(self.filename)
                image_filename = os.path.join(file_directory, image)
                # print(f"directory: {file_directory}\nstring: {image}\nfilename: {image_filename}")
                if not os.path.isfile(image_filename):
                    raise FileNotFoundError(f"File not found: {image_filename}")
                image = read_tiff(image_filename)
        except Exception as e:
            show_error(
                message=f'Error loading image from file {os.path.basename(self.filename)}:\n{e}',
                parent=self.root,
                raise_exception=False
            )
            image = np.zeros([10, 10])
        return image, value

    def update_image(self, event=None):
        """Plot image data"""
        if self.filename is None:
            return
        image, value = self._get_image()

        # Options
        cmin, cmax = self.cmin.get(), self.cmax.get()
        if self.logplot.get():
            image = np.log10(image)
            cmax = np.log10(cmax)
        if self.difplot.get():
            raise Warning('Not implemented yet')
        if self.mask.get():
            raise Warning('Not implemented yet')
        # Add plot
        self.ax_image.remove()
        colormap = self.colormap.get()
        blah = 5
        # clim = [image.max()/(blah * 5), image.max()/blah]# [cmin, cmax]
        clim = [0, image.max()/2]
        self.ax_image = self.ax.pcolormesh(image, shading='auto', clim=clim, cmap=colormap)
        self.ax_image.set_clim(clim)
        self.ax.set_xlim([0, image.shape[1]])
        self.ax.set_ylim([0, image.shape[0]])
        self.colorbar.update_normal(self.ax_image)
        self.toolbar.update()
        self.fig.canvas.draw()
        # Load axis label
        self.axis_value.set(value)

