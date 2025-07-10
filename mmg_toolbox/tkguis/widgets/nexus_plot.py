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
'xlabel': str mode of first axes
'ylabel': str mode of first signal
'xdata': flattened array of first axes
'ydata': flattend array of first signal
'axes_names': list of axes names,
'signal_names': list of signal + auxilliary signal names,
'axes_data': list of ND arrays of data for axes,
'signal_data': list of ND array of data for signal + auxilliary raw_signals,
'axes_labels': list of axes labels as 'name [units]',
'signal_labels': list of signal labels,
'data': dict of all scannables axes,
'title': str title as 'filename\nNXtitle'
"""


class NexusDefaultPlot(SimplePlot):
    """
    Tkinter widget for Nexus plot
    Widget contains 2D plot with single choice of x and y axes.

      widget  = NexusDefaultPlot(root, 'file.nxs', config)

    Axes can be chosen from a dropdown menu of the default scannables,
    or an entry box will be evaluated, allowing expressions.
    """
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
        self.fix_x = tk.BooleanVar(self.root, False)
        self.fix_y = tk.BooleanVar(self.root, False)
        self.error_message = tk.StringVar(self.root, '')

        self.combo_x, self.combo_y = self.ini_axes_select()

        super().__init__(
            root=root,
            xdata=[],
            ydata=[],
            xlabel=self.axes_x.get(),
            ylabel=self.axes_y.get(),
            title='',
            config=config
        )
        self.line = self.plot_list[0]
        if hdf_filename:
            self.update_data_from_file(hdf_filename)

    def _clear_error(self):
        self.error_message.set('')

    def _set_error(self, msg: str):
        self.error_message.set(msg)

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
        combo_x = ttk.Combobox(frm, values=axes_options,
                               textvariable=selection_x, width=20)
        combo_x.pack(side=tk.LEFT, padx=5)
        combo_x.bind('<<ComboboxSelected>>', select_x)
        var = ttk.Entry(frm, textvariable=self.axes_x, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        var = ttk.Checkbutton(frm, text='Fix', variable=self.fix_x)
        var.pack(side=tk.LEFT)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        var = ttk.Label(frm, text='Y Axes:', width=10)
        var.pack(side=tk.LEFT)
        combo_y = ttk.Combobox(frm, values=signal_options,
                               textvariable=selection_y, width=20)
        combo_y.pack(side=tk.LEFT, padx=5)
        combo_y.bind('<<ComboboxSelected>>', select_y)
        var = ttk.Entry(frm, textvariable=self.axes_y, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        var = ttk.Checkbutton(frm, text='Fix', variable=self.fix_y)
        var.pack(side=tk.LEFT)
        var = ttk.Checkbutton(frm, text='Normalise', variable=self.normalise, command=self.normalise_signal)
        var.pack(side=tk.LEFT)

        frm = ttk.Frame(section)
        frm.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        ttk.Label(frm, textvariable=self.error_message, style='error.TLabel').pack()
        return combo_x, combo_y

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        self._clear_error()
        self.filename = filename
        self.map = create_nexus_map(filename) if hdf_map is None else hdf_map
        with hdfmap.load_hdf(filename) as hdf:
            self.update_data(hdf)
        if 'data' not in self.data:
            self._set_error('error loading plot data')
            return
        self.combo_x['values'] = list(self.data['data'].keys())
        self.combo_y['values'] = list(reversed(self.data['data'].keys()))
        if not self.fix_x.get():
            self.axes_x.set(self.data['xlabel'])
        if not self.fix_y.get():
            self.axes_y.set(self.data['ylabel'])
        self.update_axis_choice()

    def update_data(self, hdf: h5py.File):
        try:
            self.data = self.map.get_plot_data(hdf)
            self.ax1.set_title(self.data['title'])
        except Exception as exc:
            self._set_error(f"Error loading plot data: {exc}")
            raise exc

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

    def get_xy_data(self, xaxis: str, *yaxes: str) -> tuple[np.ndarray, list[np.ndarray]]:

        xdata = []
        ydata = []
        if 'data' in self.data and xaxis in self.data['data']:
            xdata = self.data['data'][xaxis]
            ydata = [ self.data['data'][yaxis] for yaxis in yaxes if yaxis in self.data['data'] ]
        if len(xdata) == 0 or len(ydata) == 0:
            with hdfmap.load_hdf(self.filename) as hdf:
                if len(xdata) == 0:
                    xdata = self.map.eval(hdf, xaxis, default=np.arange(self.map.scannables_length()))
                if len(ydata) == 0:
                    ydata = [self.map.eval(hdf, yaxis) for yaxis in yaxes]

        for n, yarray in enumerate(ydata):
            if yarray.shape != xdata.shape:
                ydata[n] = np.ones(xdata.size)
            else:
                ydata[n] = yarray.flatten()
        xdata = xdata.flatten()
        if len(ydata) == 0:
            ydata = [np.ones_like(xdata)]
        return xdata, ydata

    def update_axis_choice(self, event=None):
        xaxis = self.axes_x.get()
        yaxis = self.axes_y.get()
        xdata, ydata = self.get_xy_data(xaxis, yaxis)
        self.line.set_data(xdata, ydata[0])
        self.ax1.set_xlabel(self.axes_x.get())
        self.ax1.set_ylabel(self.axes_y.get())
        self.update_axes()


class NexusMultiAxisPlot(NexusDefaultPlot):
    """
    1D line plot widget with selection box for selecting multiple axes.
    """
    def __init__(self, root: tk.Misc, hdf_filename: str | None = None,
                 config: dict | None = None):
        super().__init__(root, hdf_filename, config)
        self.listbox = self._axis_listbox()

    def _axis_listbox(self):
        frame = ttk.Frame(self.root)
        frame.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar = ttk.Scrollbar(frame)
        listbox = ttk.Treeview(frame, yscrollcommand=scrollbar.set, show="tree")
        listbox.bind("<<TreeviewSelect>>", self.select_listbox_items)
        scrollbar.configure(command=listbox.yview)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        return listbox

    def update_data_from_file(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        super().update_data_from_file(filename, hdf_map)

        # populate listbox
        self.listbox.delete(*self.listbox.get_children())
        for item in self.data['data']:
            self.listbox.insert("", tk.END, text=item)

    def select_listbox_items(self, event=None):
        if len(self.listbox.selection()) == 0:
            return
        self.remove_lines()
        labels = [self.listbox.item(item)['text'] for item in self.listbox.selection()]
        xdata, ydata = self.get_xy_data(self.axes_x.get(), *labels)
        for label, yarray in zip(labels, ydata):
            self.plot(xdata, yarray, label=label)
        label = 'various' if len(labels) > 2 else ', '.join(labels)
        self.ax1.set_xlabel(self.axes_x.get())
        self.ax1.set_ylabel(label)
        self.line = self.plot_list[0]
        self.update_axes()

    def update_axis_choice(self, event=None):
        yaxis = self.axes_y.get()
        self.listbox.selection_set([
            item for item in self.listbox.get_children()
            if yaxis == self.listbox.item(item)['text']
        ])
        self.listbox.see(next(iter(self.listbox.selection()), ''))
        super().update_axis_choice(event)
