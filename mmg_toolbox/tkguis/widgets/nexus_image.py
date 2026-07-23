"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
import numpy as np

import hdfmap
from hdfmap import create_nexus_map

from mmg_toolbox.utils.file_functions import read_tiff, get_scan_number
from ..misc.styles import create_hover, create_root
from ..misc.screen_size import get_figure_size
from ..misc.matplotlib import ini_image, add_rectangle
from ..misc.logging import create_logger
from ..misc.config import get_config, C, COLORMAPS, DEFAULT_COLORMAP
from .roi_editor import RoiEditor

logger = create_logger(__file__)


class NexusDetectorImage:
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = hdf_filename
        self.parent = root
        self.map = hdf_map
        self.config = config or get_config()

        self.PLOT_OPTIONS = ['Image', 'sum axis 0', 'sum axis 1']
        self.detector_name = tk.StringVar(root, 'NXdetector')
        self.plot_option = tk.StringVar(root, self.PLOT_OPTIONS[0])
        self.view_index = tk.IntVar(root, 0)
        self.axis_name = tk.StringVar(root, 'axis')
        self.axis_value = tk.StringVar(root, '')
        self.flip_y = tk.BooleanVar(root, self.config.get(C.image_flip_y, True))
        self.flip_x = tk.BooleanVar(root, self.config.get(C.image_flip_x, False))
        self.logplot = tk.BooleanVar(root, False)
        self.difplot = tk.BooleanVar(root, False)
        self.mask = tk.DoubleVar(root, 0)
        self.cmin = tk.DoubleVar(root, 0)
        self.cmax = tk.DoubleVar(root, 1)
        self.fixclim = tk.BooleanVar(root, False)
        self.colormap = tk.StringVar(root, self.config.get(C.default_colormap, DEFAULT_COLORMAP))
        self.sum_x_scale = tk.DoubleVar(root, 1)
        self.sum_x_offset = tk.DoubleVar(root, 0)
        self.sum_x_label = tk.StringVar(root, '')
        self.image_error = tk.StringVar(root, '')
        self.extra_plot_callbacks = []  # calls any function in this list on update_image
        self.roi_names = []

        section = ttk.Frame(root)
        section.pack(side='top', expand=True, fill='both')

        frm = ttk.Frame(section)
        frm.pack(side='top', expand=False, fill='x')
        ttk.Button(frm, text='Window', command=self.new_window).pack(side='left', padx=5)
        ttk.Button(frm, text='ROIs', command=self.roi_frame).pack(side='left')
        ttk.Button(frm, text='Draw new ROI', command=self.mouse_select_roi).pack(side='left')
        self.detector_menu = ttk.OptionMenu(frm, self.detector_name, None, 'NXdetector', command=self.update_image_plot)
        self.detector_menu.pack(side='right')
        self.plot_option_menu = ttk.OptionMenu(frm, self.plot_option, None, *self.PLOT_OPTIONS, command=self.update_image_plot)
        self.plot_option_menu.pack(side='right')

        frm = ttk.Frame(section)
        frm.pack(side='top', expand=True, fill='both')

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
        frm.pack(side='top', expand=False, fill='x')
        self.error_label = ttk.Label(frm, textvariable=self.image_error, style='error.TLabel')  # only pack this on error

        self.slider = self.ini_slider(root)

        if hdf_filename:
            self.update_image_data_from_file(hdf_filename, hdf_map)

    def ini_slider(self, root: tk.Misc):
        frm = ttk.Frame(root)
        frm.pack(expand=False, fill='x', pady=2, padx=5)

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
        var.pack(side='left')
        var = ttk.Button(frm, text='-', command=dec, width=2)
        var.pack(side='left')
        tkscale = ttk.Scale(frm, from_=0, to=100, variable=self.view_index, orient='horizontal',
                            command=self.update_image)
        # var.bind("<ButtonRelease-1>", callback)
        tkscale.pack(side='left', expand=True, fill='x')
        var = ttk.Button(frm, text='+', command=inc, width=2)
        var.pack(side='left')
        var = ttk.Entry(frm, textvariable=self.view_index, width=3)
        var.pack(side='left')
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)

        # axis mode
        var = ttk.Label(frm, textvariable=self.axis_value, width=12)
        var.pack(side='left')

        # Options button
        var = ttk.Button(frm, text='Options', command=self.options_frame)
        var.pack(side='left', padx=3)
        return tkscale

    def options_frame(self):
        """A hovering frame with options"""
        window, fun_close = create_hover(self.parent, top_left=(0, 0.1))

        frm = ttk.LabelFrame(window, text='Options', relief='ridge')
        frm.pack(expand=False, pady=2, padx=5)
        line = ttk.Frame(frm)
        line.pack(side='top', pady=2)
        var = ttk.Checkbutton(line, text='Flip-y', variable=self.flip_y, command=self.update_image)
        var.pack(side='left', padx=6)
        var = ttk.Checkbutton(line, text='Flip-x', variable=self.flip_x, command=self.update_image)
        var.pack(side='left', padx=6)
        var = ttk.Checkbutton(line, text='Log', variable=self.logplot, command=self.update_image)
        var.pack(side='left', padx=6)
        var = ttk.Checkbutton(line, text='Diff', variable=self.difplot, command=self.update_image)
        var.pack(side='left', padx=6)

        var = ttk.Label(line, text='Mask <')
        var.pack(side='left', expand=False, padx=6)
        var = ttk.Entry(line, textvariable=self.mask, width=6)
        var.pack(side='left', padx=6)
        var.bind('<Return>', self.update_image)
        var.bind('<KP_Enter>', self.update_image)

        line = ttk.Frame(frm)
        line.pack(side='top', pady=2)
        var = ttk.OptionMenu(line, self.colormap, self.colormap.get(), *COLORMAPS,
                             command=self.update_colormap_details)
        var.pack(side='left')

        var = ttk.Label(line, text='clim:')
        var.pack(side='left', expand=False)
        var = ttk.Entry(line, textvariable=self.cmin, width=6)
        var.pack(side='left')
        var.bind('<Return>', self.update_colormap_details)
        var.bind('<KP_Enter>', self.update_colormap_details)
        var = ttk.Entry(line, textvariable=self.cmax, width=6)
        var.pack(side='left')
        var.bind('<Return>', self.update_colormap_details)
        var.bind('<KP_Enter>', self.update_colormap_details)
        var = ttk.Checkbutton(line, text='Fix', variable=self.fixclim)
        var.pack(side='left')

        line = ttk.Frame(frm)
        line.pack(side='top', pady=2)
        ttk.Label(line, text='Sum Axis Label').pack(side='left', padx=2)
        ttk.Entry(line, textvariable=self.sum_x_label, width=12).pack(side='left', padx=2)
        ttk.Label(line, text='Scale').pack(side='left', padx=2)
        ttk.Entry(line, textvariable=self.sum_x_scale, width=4).pack(side='left', padx=2)
        ttk.Label(line, text='Offset').pack(side='left', padx=2)
        ttk.Entry(line, textvariable=self.sum_x_offset, width=4).pack(side='left', padx=2)

        frm = ttk.Frame(window)
        frm.pack(side='top', expand=True, fill='x')
        var = ttk.Button(frm, text='Close', command=fun_close)
        var.pack(fill='x')

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
        title = self.map.format_hdf(self.map.load_hdf(), self.config.get(C.scan_title, '')) or self.filename
        window = create_root(title, self.parent)
        widget = NexusDetectorImage(window, self.filename, self.config, self.map)
        return widget

    def _clear_image_error(self):
        self.error_label.pack_forget()

    def _show_image_error(self, message):
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
            if obj.axes:
                obj.remove()
        self._im_lines.clear()

    def update_image_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        logger.debug(f'update image from filename: {filename}')
        self._clear_image_error()
        self.filename = filename
        self.map = create_nexus_map(self.filename) if hdf_map is None else hdf_map
        self.slider.config(to=self.map.scannables_length() - 1)  # set slider max
        detector_names = list(self.map.image_data.keys())
        # self.detector_menu['values'] = detector_names if detector_names else ['No 2D NXdetectors']
        self.detector_menu.set_menu(
            detector_names[0],
            *detector_names
        )
        if not detector_names:
            return
        # shape = self.map.datasets[self.map.image_data[detector_names[0]]].shape
        shape = self.map.get_image_shape()
        if shape[0] / shape[1] < 0.01:
            self.plot_option.set(self.PLOT_OPTIONS[1])
        elif shape[1] / shape[0] < 0.01:
            self.plot_option.set(self.PLOT_OPTIONS[2])
        else:
            self.plot_option.set(self.PLOT_OPTIONS[0])
        self.add_config_rois()
        self.view_index.set(0)
        self.update_image_plot()

    def _get_image(self):
        try:
            detector = self.detector_name.get()
            axis_name = self.axis_name.get()
            index = int(self.view_index.get())
            self.view_index.set(index)
            logger.debug(f"load image: {detector} [{index}] with axis '{axis_name}'")

            self.map.set_image_path(self.map.image_data[detector])
            with hdfmap.load_hdf(self.filename) as hdf:
                image = self.map.get_image(hdf, index)
                value = self.map.get_data(hdf, axis_name, index=index, default=index)

            if issubclass(type(image), str):
                # TIFF image, NXdetector/image_data -> array('file.tif')
                file_directory = os.path.dirname(self.filename)
                image_filename = os.path.join(file_directory, image)
                # print(f"directory: {file_directory}\nstring: {image}\nfilename: {image_filename}")
                logger.info(f"load tiff image from '{image}': {image_filename}")
                if not os.path.isfile(image_filename):
                    raise FileNotFoundError(f"File not found: {image_filename}")
                image = read_tiff(image_filename)
            elif image.ndim == 0:
                # image is file path number, NXdetector/path -> arange(n_points)
                scan_number = get_scan_number(self.filename)
                file_directory = os.path.dirname(self.filename)
                image_filename = os.path.join(file_directory, f"{scan_number}-{detector}-files/{image:05.0f}.tif")
                logger.info(f"load tiff image from {image}: {image_filename}")
                if not os.path.isfile(image_filename):
                    raise FileNotFoundError(f"File not found: {image_filename}")
                image = read_tiff(image_filename)
            elif image.ndim != 2:
                raise Exception(f"detector image[{index}] is the wrong shape: {image.shape}")
        except Exception as e:
            self._show_image_error(f'Error loading image: {e}')
            image = np.zeros([10, 10])
            value = np.nan

        # Options
        if self.flip_y.get():
            image = np.flipud(image)
        if self.flip_x.get():
            image = np.fliplr(image)
        if self.logplot.get():
            image = np.log10(image + 1)
        if self.difplot.get():
            raise Warning('Not implemented yet')
        if self.mask.get():
            raise Warning('Not implemented yet')
        return image, value

    def update_value(self, value: float):
        self.axis_value.set(f"{self.axis_name.get()} = {value:.3f}")

    def update_image_plot(self, event=None):
        """replace plot instance (e.g. on loading new file)"""
        self._clear_image_error()
        if self.filename is None:
            return
        image, value = self._get_image()

        # clear previous plot
        self.im_ax.clear()
        self.rectangle = add_rectangle(self.im_ax, 0, 0, 0, 0)
        option = self.PLOT_OPTIONS.index(self.plot_option.get())
        if option == 0:  # Image
            cmap = self.colormap.get()
            cmin, cmax = self._get_clim()
            if not self.fixclim.get():
                cmax = 1 + image.max() / 2
                self.cmax.set(cmax)
            self.ax_image = self.im_ax.pcolormesh(image, shading='auto', clim=[cmin, cmax], cmap=cmap)
            self.im_ax.set_xlim((0, image.shape[1]))
            self.im_ax.set_ylim((0, image.shape[0]))
            self.im_ax.axis('image')
            self.plot_config_rois()
            self.colorbar.update_normal(self.ax_image)
        elif 1 <= option <= 2:  # sum axis 0/1
            line = image.sum(axis=option-1)
            xdata = (self.sum_x_scale.get() * np.arange(len(line))) + self.sum_x_offset.get()
            self.ax_image, = self.im_ax.plot(xdata, line, '-')
            self.im_ax.axis('auto')
            self.im_ax.set_xlabel(self.sum_x_label.get() or self.plot_option.get())
            self.im_fig.tight_layout()
            self.plot_config_rois()

        self.toolbar.update()
        self.im_fig.canvas.draw()
        # Load axis mode
        self.update_value(value)
        # Run additional callbacks
        for function in self.extra_plot_callbacks:
            function()

    def update_image(self, event=None):
        """replace array in plot (e.g. on changing slider)"""
        self._clear_image_error()
        if self.filename is None:
            return
        image, value = self._get_image()

        self.update_value(value)
        option = self.PLOT_OPTIONS.index(self.plot_option.get())
        if option == 0:  # Image
            self.ax_image.set_array(image)
            self.update_colormap_details()
        elif 1 <= option <= 2:  # sum axis 0/1
            line = image.sum(axis=option-1)
            xdata = np.arange(len(line))
            self.ax_image.set_data(xdata, line)
            self.toolbar.update()
            self.im_fig.canvas.draw()
        # Update ROIs
        self.plot_config_rois()
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
        option = self.PLOT_OPTIONS.index(self.plot_option.get())
        shape = self.map.get_image_shape()
        ymin, ymax = self.im_ax.get_ylim()
        if rois:
            try:
                with hdfmap.load_hdf(self.filename) as hdf:
                    for n, (name, cen_i, cen_j, wid_i, wid_j, det_name) in enumerate(rois):
                        if det_name == detector:
                            cen_i, cen_j, wid_i, wid_j = self.map.eval(hdf, f"{cen_i},{cen_j},{wid_i},{wid_j}")
                            if self.flip_x.get():
                                cen_j = shape[1] - cen_j
                            if self.flip_y.get():
                                # print(name, 'flip y:', shape, cen_i, shape[0] - cen_i)
                                cen_i = shape[0] - cen_i
                            if option == 1: # sum axis 0
                                cen_i = (ymax + ymin) / 2
                                wid_i = (ymax - ymin)
                            elif option == 2:  # sum axis 1
                                cen_j = (ymax + ymin) / 2
                                wid_j = (ymax - ymin)
                            roi_square = np.array([
                                # x, y
                                [cen_i - wid_i // 2, cen_j - wid_j // 2],
                                [cen_i - wid_i // 2, cen_j + wid_j // 2],
                                [cen_i + wid_i // 2, cen_j + wid_j // 2],
                                [cen_i + wid_i // 2, cen_j - wid_j // 2],
                                [cen_i - wid_i // 2, cen_j - wid_j // 2],
                            ])
                            self.im_line(roi_square[:, 1], roi_square[:, 0], 'k-', lw=2, scaley=False, scalex=False)
                            text_pos = roi_square.max(axis=0)
                            self.text(text_pos[1] + wid_j * 0.05, text_pos[0] + wid_i * 0.1, str(n), va='top')
            except Exception as e:
                self._show_image_error(f'Error plotting ROIs: {e}')
        self.im_fig.canvas.draw()

    def mouse_select_roi(self):
        """Select a roi with the mouse"""
        if self.PLOT_OPTIONS.index(self.plot_option.get()) > 0:
            return self.mouse_select_roi_1d()

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
            det_shape = self.map.get_image_shape()
            name = f"{detector}_roi"
            roi_count = 1
            roi_names = [roi[0] for roi in self.config.get(C.roi)]
            while f"{name}{roi_count}" in roi_names:
                roi_count += 1
            self.add_roi(
                name=f"{name}{roi_count}",
                cen_i=det_shape[0] - int(y_cen) if self.flip_y.get() else int(y_cen),
                cen_j=det_shape[1] - int(x_cen) if self.flip_x.get() else int(x_cen),
                wid_i=int(abs(y_wid)),
                wid_j=int(abs(x_wid)),
                image_name=detector
            )
            self.rectangle.set_bounds(0, 0, 0, 0)
            self.im_fig.canvas.draw()
            disconnect()

        press = self.im_fig.canvas.mpl_connect('button_press_event', mouse_press)
        move = self.im_fig.canvas.mpl_connect('motion_notify_event', mouse_move)
        release = self.im_fig.canvas.mpl_connect('button_release_event', mouse_release)
        self.im_fig.canvas._tkcanvas.master.config(cursor="crosshair")

    def mouse_select_roi_1d(self):
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
                y_min, y_max = self.im_ax.get_ylim()
                x_end = event.xdata
                # y_end = event.ydata
                self.rectangle.set_bounds(x_start[0], y_min, x_end - x_start[0], y_max - y_min)
                self.im_fig.canvas.draw()

        def mouse_release(event):
            x_end = event.xdata
            y_end = event.ydata
            x_wid = x_end - x_start[0]
            y_wid = y_end - y_start[0]
            x_cen = x_start[0] + x_wid/2
            y_cen = y_start[0] + y_wid/2
            detector = self.detector_name.get()
            det_shape = self.map.get_image_shape()
            sum_axis_n = self.PLOT_OPTIONS.index(self.plot_option.get()) - 1
            sum_axis_len = det_shape[sum_axis_n]
            name = f"{detector}_roi"
            roi_count = 1
            roi_names = [roi[0] for roi in self.config.get(C.roi)]
            while f"{name}{roi_count}" in roi_names:
                roi_count += 1
            self.add_roi(
                name=f"{name}{roi_count}",
                cen_i=int(sum_axis_len // 2) if sum_axis_n == 0 else int(x_cen),
                cen_j=int(sum_axis_len // 2) if sum_axis_n == 1 else int(x_cen),
                wid_i=int(sum_axis_len) if sum_axis_n == 0 else int(x_wid),
                wid_j=int(sum_axis_len) if sum_axis_n == 1 else int(x_wid),
                image_name=detector
            )
            self.rectangle.set_bounds(0, 0, 0, 0)
            self.im_fig.canvas.draw()
            disconnect()

        press = self.im_fig.canvas.mpl_connect('button_press_event', mouse_press)
        move = self.im_fig.canvas.mpl_connect('motion_notify_event', mouse_move)
        release = self.im_fig.canvas.mpl_connect('button_release_event', mouse_release)
        self.im_fig.canvas._tkcanvas.master.config(cursor="crosshair")