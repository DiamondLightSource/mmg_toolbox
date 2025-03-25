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
from .simple_plot import SimplePlot

logger = create_logger(__file__)


"""
'xlabel': str label of first axes
'ylabel': str label of first signal
'xdata': flattened array of first axes
'ydata': flattend array of first signal
'axes_names': list of axes names,
'signal_names': list of signal + auxilliary signal names,
'axes_data': list of ND arrays of data for axes,
'signal_data': list of ND array of data for signal + auxilliary signals,
'axes_labels': list of axes labels as 'name [units]',
'signal_labels': list of signal labels,
'data': dict of all scannables axes,
'title': str title as 'filename\nNXtitle'
"""


class NexusDefaultPlot(SimplePlot):
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.filename = hdf_filename
        self.map: hdfmap.NexusMap | None = None
        self.config = get_config() if config is None else config
        self.data = {}

        self.axes_x = tk.StringVar(self.root, 'axes')
        self.axes_y = tk.StringVar(self.root, 'signal')
        self.normalise = tk.BooleanVar(self.root, False)

        self.combo_x, self.combo_y = self.ini_axes_select()

        super().__init__(
            root=root,
            xdata=[],
            ydata=[],
            xlabel=self.axes_x.get(),
            ylabel=self.axes_y.get(),
            title=''
        )
        self.line = self.plot_list[0]
        if hdf_filename:
            self.update_data_from_file(hdf_filename)

    def ini_axes_select(self):
        selection_x = tk.StringVar(self.root, 'axes')
        selection_y = tk.StringVar(self.root, 'signal')
        axes_options = ['axes', 'signal']
        signal_options = axes_options[::-1]

        def select_x(event):
            self.axes_x.set(selection_x.get())
            self.update_axis_choice()

        def select_y(event):
            self.axes_y.set(selection_y.get())
            self.update_axis_choice()

        section = ttk.Frame(self.root)
        section.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        var = ttk.Label(frm, text='X Axes:', width=10)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.axes_x, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        combo_x = ttk.Combobox(frm, values=axes_options,
                               textvariable=selection_x, width=20)
        combo_x.pack(side=tk.LEFT)
        combo_x.bind('<<ComboboxSelected>>', select_x)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        var = ttk.Label(frm, text='Y Axes:', width=10)
        var.pack(side=tk.LEFT)
        var = ttk.Entry(frm, textvariable=self.axes_y, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        combo_y = ttk.Combobox(frm, values=signal_options,
                                    textvariable=selection_y, width=20)
        combo_y.pack(side=tk.LEFT)
        combo_y.bind('<<ComboboxSelected>>', select_y)
        var = ttk.Checkbutton(frm, text='Normalise', variable=self.normalise, command=self.normalise_signal)
        var.pack(side=tk.LEFT)
        return combo_x, combo_y

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self.filename = filename
        self.map = create_nexus_map(self.filename) if hdf_map is None else hdf_map
        with hdfmap.load_hdf(self.filename) as hdf:
            self.update_data(hdf)
        self.combo_x['values'] = list(self.data['data'].keys())
        self.combo_y['values'] = list(reversed(self.data['data'].keys()))
        if self.axes_x.get() not in self.combo_x['values']:
            self.axes_x.set(self.data['xlabel'])
        if self.axes_y.get() not in self.combo_y['values']:
            self.axes_y.set(self.data['ylabel'])
        self.update_axis_choice()

    def update_data(self, hdf: h5py.File):
        self.data = self.map.get_plot_data(hdf)

    def normalise_signal(self, event=None):
        signal = self.axes_y.get()
        norm_by = self.config.get('normalise_factor', '')
        if signal.endswith(norm_by):
            signal = signal.replace(norm_by, '')
        if self.normalise.get():
            self.axes_y.set(signal + norm_by)
        else:
            self.axes_y.set(signal)
        self.update_axis_choice()

    def update_axis_choice(self, event=None):
        xaxis = self.axes_x.get()
        yaxis = self.axes_y.get()
        if 'data' in self.data and xaxis in self.data['data'] and yaxis in self.data['data']:
            self.line.set_data(
                self.data['data'][xaxis],
                self.data['data'][yaxis]
            )
        else:
            with hdfmap.load_hdf(self.filename) as hdf:
                xdata = self.map.eval(hdf, xaxis, default=np.arange(self.map.scannables_length()))
                ydata = self.map.eval(hdf, yaxis)

            if ydata.shape != xdata.shape:
                ydata = np.ones_like(xdata)

            self.line.set_data(xdata, ydata)
        self.ax1.set_xlabel(xaxis)
        self.ax1.set_ylabel(yaxis)
        self.ax1.set_title(self.data['title'])
        self.update_axes()

