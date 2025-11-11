"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
import numpy as np

import hdfmap
from hdfmap import create_nexus_map

from mmg_toolbox.utils.file_functions import read_tiff
from ..misc.styles import create_hover, create_root
from ..misc.screen_size import get_figure_size
from ..misc.matplotlib import ini_image, COLORMAPS, DEFAULT_COLORMAP, add_rectangle
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from .roi_editor import RoiEditor

logger = create_logger(__file__)


class NexusDetectorImage:
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = hdf_filename
        self.parent = root
        self.map = hdf_map
        self.config = config or get_config()

        self.detector_name = tk.StringVar(root, 'NXdetector')
        self.view_index = tk.IntVar(root, 0)
        self.axis_name = tk.StringVar(root, 'axis = ')
        self.axis_value = tk.DoubleVar(root, 0)
        self.logplot = tk.BooleanVar(root, False)
        self.difplot = tk.BooleanVar(root, False)
        self.mask = tk.DoubleVar(root, 0)
        self.cmin = tk.DoubleVar(root, 0)
        self.cmax = tk.DoubleVar(root, 1)
        self.fixclim = tk.BooleanVar(root, False)
        self.colormap = tk.StringVar(root, self.config.get(C.default_colormap, DEFAULT_COLORMAP))
        self.image_error = tk.StringVar(root, '')
        self.extra_plot_callbacks = []  # calls any function in this list on update_image
        self.roi_names = []

        section = ttk.Frame(root)
        section.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        ttk.Button(frm, text='Window', command=self.new_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(frm, text='ROIs', command=self.roi_frame).pack(side=tk.LEFT)
        ttk.Button(frm, text='Draw new ROI', command=self.mouse_select_roi).pack(side=tk.LEFT)
        self.detector_menu = ttk.OptionMenu(frm, self.detector_name, None, 'NXdetector', command=self.update_image_plot)
        self.detector_menu.pack(side=tk.RIGHT)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        self.im_fig, self.im_ax, self._im_lines, self.ax_image, self.colorbar, self.toolbar = ini_image(
            frame=frm,
            figure_size=get_figure_size(root, self.config, C.image_size),
            figure_dpi=self.config.get(C.plot_dpi),
        )
        self.im_ax.set_xlabel(None)
        self.im_ax.set_ylabel(None)
        self.rectangle = self.im_ax.axvspan(0, 0, alpha=0.2)

        # Error message
        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        self.error_label = ttk.Label(frm, textvariable=self.image_error)  # only pack this on error

        self.slider = self.ini_slider(root)

        if hdf_filename:
            self.update_image_data_from_file(hdf_filename, hdf_map)

    def ini_slider(self, root: tk.Misc):
        frm = ttk.Frame(root)
        frm.pack(expand=tk.NO, pady=2, padx=5)

        def inc():
            new_val = self.view_index.get() + 1
            if new_val < self.map.scannables_length():
                self.view_index.set(new_val)
                self.update_image()

        def dec():
            new_val = self.view_index.get() - 1
            if new_val >= 0:
                self.view_index.set(new_val)
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

        # axis mode
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
        window, fun_close = create_hover(self.parent)

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

        var = ttk.OptionMenu(frm, self.colormap, self.colormap.get(), *COLORMAPS,
                             command=self.update_colormap_details)
        var.pack(side=tk.LEFT)

        var = ttk.Label(frm, text='clim:')
        var.pack(side=tk.LEFT, expand=tk.NO)
        var = ttk.Entry(frm, textvariable=self.cmin, width=6)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.update_colormap_details)
        var.bind('<KP_Enter>', self.update_colormap_details)
        var = ttk.Entry(frm, textvariable=self.cmax, width=6)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.update_colormap_details)
        var.bind('<KP_Enter>', self.update_colormap_details)
        var = ttk.Checkbutton(frm, text='Fix', variable=self.fixclim)
        var.pack(side=tk.LEFT)

        frm = ttk.Frame(window)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        var = ttk.Button(frm, text='Close', command=fun_close)
        var.pack(fill=tk.X)

    def roi_frame(self):
        """a hovering frame with ROIs"""
        # window, fun_close = create_hover(root)
        window = create_root('Regions of Interest (ROIs)', self.parent)

        def on_close():
            window.destroy()
            self.add_config_rois()
            self.plot_config_rois()

        RoiEditor(window, self.config, on_close)

    def options_menu(self) -> dict:
        """Return a dict of options for menu structure"""
        menu = {
            "Image": {
                "Change options": self.options_frame,
            }
        }
        return menu

    def new_window(self):
        window = create_root(self.filename, self.parent)
        widget = NexusDetectorImage(window, self.filename, self.config, self.map)
        return widget

    def _clear_error(self):
        self.error_label.pack_forget()

    def _show_error(self, message):
        self.image_error.set(message)
        self.error_label.pack()

    def im_line(self, *args, **kwargs):
        lines = self.im_ax.plot(*args, **kwargs)
        self._im_lines.extend(lines)

    def text(self, *args, **kwargs):
        text = self.im_ax.text(*args, **kwargs)
        self._im_lines.append(text)

    def remove_im_lines(self):
        for obj in self._im_lines:
            obj.remove()
        self._im_lines.clear()

    def update_image_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self._clear_error()
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
        # TODO add axis_name and value
        self.add_config_rois()
        self.view_index.set(0)
        self.update_image_plot()

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
            elif image.ndim != 2:
                raise Exception(f"detector image[{index}] is the wrong shape: {image.shape}")
        except Exception as e:
            self._show_error(f'Error loading image: {e}')
            image = np.zeros([10, 10])
            value = np.nan
        return image, value

    def update_image_plot(self, event=None):
        """replace plot instance (e.g. on loading new file)"""
        self._clear_error()
        if self.filename is None:
            return
        image, value = self._get_image()

        # Options
        if self.logplot.get():
            image = np.log10(image)
        if self.difplot.get():
            raise Warning('Not implemented yet')
        if self.mask.get():
            raise Warning('Not implemented yet')

        cmap = self.colormap.get()
        cmin, cmax = self._get_clim()
        if not self.fixclim.get():
            cmax = 1 + image.max() / 2
            self.cmax.set(cmax)
        # Add plot by removing old one
        self.ax_image.remove()
        self.rectangle.remove()
        self.ax_image = self.im_ax.pcolormesh(image, shading='auto', clim=[cmin, cmax], cmap=cmap)
        self.im_ax.set_xlim([0, image.shape[1]])
        self.im_ax.set_ylim([0, image.shape[0]])
        # self.rectangle = self.ax.axvspan(0, 0, alpha=0.9, facecolor='k', zorder=2)
        self.rectangle = add_rectangle(self.im_ax, 0, 0, 0, 0)
        self.plot_config_rois()
        self.colorbar.update_normal(self.ax_image)
        self.toolbar.update()
        self.im_fig.canvas.draw()
        # Load axis mode
        self.axis_value.set(value)
        # Run additional callbacks
        for function in self.extra_plot_callbacks:
            function()

    def update_image(self, event=None):
        """replace array in plot (e.g. on changing slider)"""
        self._clear_error()
        if self.filename is None:
            return
        image, value = self._get_image()

        if self.logplot.get():
            image = np.log10(image)

        self.ax_image.set_array(image)
        self.axis_value.set(value)
        self.update_colormap_details()
        # Run additional callbacks
        for function in self.extra_plot_callbacks:
            function()

    def _get_clim(self):
        cmin, cmax = self.cmin.get(), self.cmax.get()
        if self.logplot.get():
            cmin, cmax = np.log10([cmin + 1, cmax])
        return cmin, cmax

    def update_colormap_details(self, event=None):
        """Update plot colormap details (e.g. on changing colormap)"""
        cmap = self.colormap.get()
        self.ax_image.set_clim(self._get_clim())
        self.ax_image.set_cmap(cmap)
        self.colorbar.update_normal(self.ax_image)
        self.toolbar.update()
        self.im_fig.canvas.draw()

    def add_roi(self, name: str, cen_i: int | str, cen_j: int | str,
                wid_i: int = 30, wid_j: int = 30, image_name: str = 'IMAGE'):
        """add region of interest to config"""
        if C.roi in self.config:
            self.config[C.roi].append((name, cen_i, cen_j, wid_i, wid_j, image_name))
        self.add_config_rois()
        self.plot_config_rois()
        print(f"ROI created: {name}, {cen_i}, {cen_j}, {wid_i}, {wid_j}")

    def add_config_rois(self):
        """add config rois to hdfmap"""
        self.roi_names.clear()
        rois = self.config.get(C.roi)
        detector_names = list(self.map.image_data.keys())
        if rois:
            for name, cen_i, cen_j, wid_i, wid_j, det_name in rois:
                if det_name in detector_names:
                    self.map.add_roi(name, cen_i, cen_j, wid_i, wid_j, det_name)
                    self.roi_names.extend([
                        f"{name}_total",
                        f"{name}_max",
                        f"{name}_min",
                        f"{name}_mean",
                        f"{name}_bkg",
                        f"{name}_rmbkg",
                        # f"{name}_box",
                        # f"{name}_bkg_box",
                    ])

    def plot_config_rois(self):
        """plot config rois on image"""
        self.remove_im_lines()
        rois = self.config.get(C.roi)
        detector = self.detector_name.get()
        if rois:
            #TODO: replace with roi_box from hdfmap
            try:
                with hdfmap.load_hdf(self.filename) as hdf:
                    for n, (name, cen_i, cen_j, wid_i, wid_j, det_name) in enumerate(rois):
                        if det_name == detector:
                            cen_i, cen_j, wid_i, wid_j = self.map.eval(hdf, f"{cen_i},{cen_j},{wid_i},{wid_j}")
                            roi_square = np.array([
                                # x, y
                                [cen_i - wid_i // 2, cen_j - wid_j // 2],
                                [cen_i - wid_i // 2, cen_j + wid_j // 2],
                                [cen_i + wid_i // 2, cen_j + wid_j // 2],
                                [cen_i + wid_i // 2, cen_j - wid_j // 2],
                                [cen_i - wid_i // 2, cen_j - wid_j // 2],
                            ])
                            self.im_line(roi_square[:, 1], roi_square[:, 0], 'k-', lw=2)
                            self.text(cen_j + wid_j // 2, cen_i + wid_i // 2, str(n))
            except Exception as e:
                self._show_error(f'Error plotting ROIs: {e}')
        self.im_fig.canvas.draw()

    def mouse_select_roi(self):
        """Select a roi with the mouse"""
        x_start = [0]
        y_start = [0]
        ipress = [False]

        def disconnect():
            self.im_fig.canvas.mpl_disconnect(press)
            self.im_fig.canvas.mpl_disconnect(move)
            self.im_fig.canvas.mpl_disconnect(release)
            self.im_fig.canvas._tkcanvas.master.config(cursor="arrow")

        def mouse_press(event):
            if event.inaxes:
                x_start[0] = event.xdata
                y_start[0] = event.ydata
                ipress[0] = True
            else:
                disconnect()

        def mouse_move(event):
            if event.inaxes and ipress[0]:
                x_end = event.xdata
                y_end = event.ydata
                self.rectangle.set_bounds(x_start[0], y_start[0], x_end - x_start[0], y_end - y_start[0])
                self.im_fig.canvas.draw()

        def mouse_release(event):
            x_end = event.xdata
            y_end = event.ydata
            x_wid = x_end - x_start[0]
            y_wid = y_end - y_start[0]
            x_cen = x_start[0] + x_wid/2
            y_cen = y_start[0] + y_wid/2
            detector = self.detector_name.get()
            name = f"{detector}_roi"
            roi_count = 1
            roi_names = [roi[0] for roi in self.config.get(C.roi)]
            while f"{name}{roi_count}" in roi_names:
                roi_count += 1
            self.add_roi(
                name=f"{name}{roi_count}",
                cen_i=int(y_cen),
                cen_j=int(x_cen),
                wid_i=int(y_wid),
                wid_j=int(x_wid),
                image_name=detector
            )
            self.rectangle.set_bounds(0, 0, 0, 0)
            self.im_fig.canvas.draw()
            disconnect()

        press = self.im_fig.canvas.mpl_connect('button_press_event', mouse_press)
        move = self.im_fig.canvas.mpl_connect('motion_notify_event', mouse_move)
        release = self.im_fig.canvas.mpl_connect('button_release_event', mouse_release)
        self.im_fig.canvas._tkcanvas.master.config(cursor="crosshair")
