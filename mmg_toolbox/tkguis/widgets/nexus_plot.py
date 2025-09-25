"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
import numpy as np
import h5py

import hdfmap
from hdfmap import create_nexus_map
from hdfmap.eval_functions import generate_identifier

from ..misc.logging import create_logger
from ..misc.config import get_config, C
from .simple_plot import SimplePlot

logger = create_logger(__file__)


class NexusDefaultPlot(SimplePlot):
    """
    Tkinter widget for Nexus plot
    Widget contains 2D plot with single choice of x and y axes.

      widget  = NexusDefaultPlot(root, 'file.nxs', config)

    Axes can be chosen from a dropdown menu of the default scannables,
    or an entry box will be evaluated, allowing expressions.
    """
    def __init__(self, root: tk.Misc, *hdf_filenames: str, config: dict | None = None):
        self.root = root
        self.filenames = hdf_filenames
        self.map: hdfmap.NexusMap | None = None
        self.config = get_config() if config is None else config
        self._plot_data: list[dict] = []
        self._scannable_data: list[dict[str, np.ndarray]] = []

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
        if hdf_filenames:
            self.update_data_from_files(*hdf_filenames)

    def _clear_error(self):
        self.error_message.set('')

    def _set_error(self, msg: str):
        self.error_message.set(msg)

    def plot(self, *args, **kwargs):
        lines = self.ax1.plot(*args, **kwargs)
        self.plot_list.extend(lines)

    def remove_lines(self):
        for obj in self.plot_list:
            obj.remove()
        self.plot_list.clear()

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

    def update_data_from_files(self, *filenames: str, hdf_map: hdfmap.NexusMap | None = None):
        if not filenames:
            return
        self._clear_error()
        self.filenames = filenames
        self.map = create_nexus_map(filenames[0]) if hdf_map is None else hdf_map
        self._load_data()
        if not self._scannable_data:
            self._set_error("No data loaded")
            return
        first_dataset = self._scannable_data[0]
        self.combo_x['values'] = list(first_dataset.keys())
        self.combo_y['values'] = list(reversed(first_dataset.keys()))
        # Default axes choice
        axes, signals = self.map.nexus_default_names()
        if not self.fix_x.get():
            self.axes_x.set(next(iter(axes), f'arange({self.map.scannables_length()})'))
        if not self.fix_y.get():
            self.axes_y.set(next(iter(signals), f'zeros({self.map.scannables_length()})'))
        self.update_axis_choice()

    def _label(self, name: str) -> str:
        path = self.map.combined.get(name, '')
        if not path:
            return name
        units = self.map.get_attr(path, 'units', '')
        unit_str = f" [{units}]" if units else ''
        return generate_identifier(path) + unit_str

    def _load_data(self):
        self._plot_data = []
        self._scannable_data = []
        errors = []
        for filename in self.filenames:
            try:
                with hdfmap.load_hdf(filename) as hdf:
                    plot_data = self.map.get_plot_data(hdf)
            except Exception as e:
                errors.append(f"Error loading data in file {os.path.basename(filename)}: {e}")
            self._plot_data.append(plot_data)
            self._scannable_data.append(plot_data.get('data', {}))
        if errors:
            self._set_error('\n'.join(errors))

    def get_xy_data(self, x_label: str, *y_labels: str) -> tuple[list[np.ndarray], list[np.ndarray]]:
        x_data: list[np.ndarray] = []
        y_data: list[np.ndarray] = []
        errors = []
        for filename, scannables in zip(self.filenames, self._scannable_data):
            this_x_data = scannables.get(x_label, None)
            this_y_data = [scannables.get(label, None) for label in y_labels]

            if this_x_data is None or any(data is None for data in this_y_data):
                # Load additional data
                with hdfmap.load_hdf(filename) as hdf:
                    if this_x_data is None:
                        try:
                            this_x_data = self.map.eval(hdf, x_label, np.arange(self.map.scannables_length()))
                        except Exception as e:
                            errors.append(f"Error loading x-axis in file {os.path.basename(filename)}: {e}")
                            this_x_data = np.arange(self.map.scannables_length())
                    for n, label in enumerate(y_labels):
                        if this_y_data[n] is None:
                            try:
                                this_y_data[n] = self.map.eval(hdf, label, np.arange(self.map.scannables_length()))
                            except Exception as e:
                                errors.append(f"Error loading y-axis in file {os.path.basename(filename)}: {e}")
                                this_y_data[n] = np.arange(len(this_x_data))
            x_data.extend([this_x_data] * len(this_y_data))
            y_data.extend(this_y_data)

        if errors:
            self._set_error('\n'.join(errors))

        return x_data, y_data

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
        x_label = self.axes_x.get()
        y_label = self.axes_y.get()
        xdata, ydata = self.get_xy_data(x_label, y_label)
        self.update_from_data(
            x_data=xdata,
            y_data=ydata,
            x_label=self._label(x_label),
            y_label=self._label(y_label),
            title=os.path.basename(self.filenames[0]),
            legend=[os.path.basename(filename) for filename in self.filenames],
        )
        self.line = self.plot_list[0]


class NexusMultiAxisPlot(NexusDefaultPlot):
    """
    1D line plot widget with selection box for selecting multiple axes.
    """
    def __init__(self, root: tk.Misc, *hdf_filenames: str,
                 config: dict | None = None):
        super().__init__(root, *hdf_filenames, config=config)
        self.listbox = self._axis_listbox()

    def _axis_listbox(self):
        frame = ttk.Frame(self.root)
        frame.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar = ttk.Scrollbar(frame)
        listbox = ttk.Treeview(frame, yscrollcommand=scrollbar.set, show="tree")
        listbox.column("#0", width=100, stretch=tk.YES)
        listbox.bind("<<TreeviewSelect>>", self.select_listbox_items)
        scrollbar.configure(command=listbox.yview)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        return listbox

    def update_data_from_files(self, *filenames: str, hdf_map: hdfmap.NexusMap | None = None):
        super().update_data_from_files(*filenames, hdf_map=hdf_map)
        auto_signal = self.axes_y.get()

        # populate listbox
        self.listbox.delete(*self.listbox.get_children())
        first_dataset = self._scannable_data[0]
        for item in first_dataset:
            self.listbox.insert("", tk.END, text=item)
            if item == auto_signal:
                self.listbox.focus()


    def select_listbox_items(self, event=None):
        if len(self.listbox.selection()) == 0:
            return
        self.remove_lines()
        x_label = self.axes_x.get()
        labels = [self.listbox.item(item)['text'] for item in self.listbox.selection()]
        xdata, ydata = self.get_xy_data(x_label, *labels)
        self.update_from_data(
            x_data=xdata,
            y_data=ydata,
            x_label=self._label(x_label),
            y_label=self._label(labels[0]),
            title=os.path.basename(self.filenames[0]),
            legend=labels,
        )
        self.line = self.plot_list[0]

    def update_axis_choice(self, event=None):
        # select item in list if it matches
        yaxis = self.axes_y.get()
        self.listbox.selection_set([
            item for item in self.listbox.get_children()
            if yaxis == self.listbox.item(item)['text']
        ])
        self.listbox.see(next(iter(self.listbox.selection()), ''))
        super().update_axis_choice(event)
