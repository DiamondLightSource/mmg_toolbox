"""
a tkinter frame with a single plot
"""
import tkinter as tk
from tkinter import ttk

import hdfmap
from hdfmap import create_nexus_map

from ..misc.logging import create_logger
from ..misc.config import get_config
from .simple_plot import SimplePlot

logger = create_logger(__file__)


class NexusDefaultPlot:
    def __init__(self, root: tk.Misc, hdf_filename: str,
                 nexus_map: hdfmap.NexusMap | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = hdf_filename
        self.map = create_nexus_map(hdf_filename) if nexus_map is None else nexus_map
        self.config = get_config() if config is None else config

        with hdfmap.load_hdf(hdf_filename) as hdf:
            self.data = self.map.get_plot_data(hdf)

        # 'xlabel': str label of first axes
        # 'ylabel': str label of first signal
        # 'xdata': flattened array of first axes
        # 'ydata': flattend array of first signal
        # 'axes_names': list of axes names,
        # 'signal_names': list of signal + auxilliary signal names,
        # 'axes_data': list of ND arrays of data for axes,
        # 'signal_data': list of ND array of data for signal + auxilliary signals,
        # 'axes_labels': list of axes labels as 'name [units]',
        # 'signal_labels': list of signal labels,
        # 'data': dict of all scannables axes,
        # 'title': str title as 'filename\nNXtitle'

        self.axes_x = tk.StringVar(self.root, self.data['xlabel'])
        self.axes_y = tk.StringVar(self.root, self.data['ylabel'])
        self.normalise = tk.BooleanVar(self.root, False)
        selection_x = tk.StringVar(self.root, self.data['xlabel'])
        selection_y = tk.StringVar(self.root, self.data['ylabel'])
        axes_options = list(self.data['data'].keys())
        signal_options = axes_options[::-1]

        def select_x(event):
            self.axes_x.set(selection_x.get())
            self.update_axes()

        def select_y(event):
            self.axes_y.set(selection_y.get())
            self.update_axes()

        section = ttk.Frame(self.root)
        section.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        var = ttk.Label(frm, text='X Axes:', width=20)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.axes_x, width=30)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axes)
        var.bind('<KP_Enter>', self.update_axes)
        self.combo_x = ttk.Combobox(frm, values=axes_options,
                                    textvariable=selection_x)
        self.combo_x.pack(side=tk.LEFT, expand=tk.YES)
        self.combo_x.bind('<<ComboboxSelected>>', select_x)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
        var = ttk.Label(frm, text='Y Axes:', width=20)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.axes_y, width=30)
        var.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axes)
        var.bind('<KP_Enter>', self.update_axes)
        self.combo_y = ttk.Combobox(frm, values=signal_options,
                                    textvariable=selection_y)
        self.combo_y.pack(side=tk.LEFT, expand=tk.YES)
        self.combo_y.bind('<<ComboboxSelected>>', select_y)
        var = ttk.Checkbutton(frm, text='Normalise', variable=self.normalise, command=self.normalise_signal)
        var.pack(side=tk.LEFT)

        self.plot_widget = SimplePlot(
            root=root,
            xdata=self.data['xdata'],
            ydata=self.data['ydata'],
            xlabel=self.data['xlabel'],
            ylabel=self.data['ylabel'],
            title=self.data['title']
        )
        self.line = self.plot_widget.plot_list[0]

    def update_data(self):
        with hdfmap.load_hdf(self.filename) as hdf:
            self.data = self.map.get_plot_data(hdf)
        self.update_axes()

    def normalise_signal(self, event=None):
        signal = self.axes_y.get()
        norm_by = self.config.get('normalise_factor', '')
        if signal.endswith(norm_by):
            signal = signal.replace(norm_by, '')
        if self.normalise.get():
            self.axes_y.set(signal + norm_by)
        else:
            self.axes_y.set(signal)
        self.update_axes()

    def update_axes(self, event=None):
        xaxis = self.axes_x.get()
        yaxis = self.axes_y.get()
        if xaxis in self.data['data'] and yaxis in self.data['data']:
            self.line.set_data(
                self.data['data'][xaxis],
                self.data['data'][yaxis]
            )
        else:
            with hdfmap.load_hdf(self.filename) as hdf:
                xdata = self.map.eval(hdf, xaxis)
                ydata = self.map.eval(hdf, yaxis)
            self.line.set_data(xdata, ydata)
        self.plot_widget.ax1.set_xlabel(xaxis)
        self.plot_widget.ax1.set_ylabel(yaxis)
        self.plot_widget.update_axes()
