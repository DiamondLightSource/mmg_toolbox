"""
a tkinter frame with a single plot
"""
import os
import tkinter as tk
from tkinter import ttk
import numpy as np

import hdfmap
from hdfmap import create_nexus_map
from hdfmap.eval_functions import generate_identifier

from mmg_toolbox.utils.env_functions import get_scan_number
from mmg_toolbox.utils.fitting import multipeakfit, FitResults, find_peaks_str
from ..misc.logging import create_logger
from ..misc.config import get_config
from .simple_plot import SimplePlot
from .treeview import CanvasTreeview


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
        self.config = config or get_config()
        self._plot_data: list[dict] = []
        self._scannable_data: list[dict[str, np.ndarray]] = []  # plot data: list of dicts of arrays
        self._fit_result: FitResults | None = None

        self.axes_x = tk.StringVar(self.root, 'axes')
        self.axes_y = tk.StringVar(self.root, 'signal')
        self.normalise = tk.BooleanVar(self.root, False)
        self.fix_x = tk.BooleanVar(self.root, False)
        self.fix_y = tk.BooleanVar(self.root, False)
        self.fit_model = tk.StringVar(self.root, 'Gaussian')
        self.max_peaks = tk.IntVar(self.root, 1)
        self.do_fit = tk.BooleanVar(self.root, False)
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
        section.pack(side=tk.TOP, expand=tk.NO, fill=tk.BOTH)

        frm = ttk.Frame(section)
        frm.pack(side=tk.LEFT)
        line = ttk.Frame(frm)
        line.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        var = ttk.Label(line, text='X Axes:', width=10)
        var.pack(side=tk.LEFT)
        combo_x = ttk.Combobox(line, values=axes_options,
                               textvariable=selection_x, width=20)
        # combo_x.pack(side=tk.LEFT, padx=5)
        # combo_x.bind('<<ComboboxSelected>>', select_x)
        var = ttk.Entry(line, textvariable=self.axes_x, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        var = ttk.Checkbutton(line, text='Fix', variable=self.fix_x)
        var.pack(side=tk.LEFT)

        line = ttk.Frame(frm)
        line.pack(side=tk.TOP, expand=tk.NO, fill=tk.X)
        var = ttk.Label(line, text='Y Axes:', width=10)
        var.pack(side=tk.LEFT)
        combo_y = ttk.Combobox(line, values=signal_options,
                               textvariable=selection_y, width=20)
        # combo_y.pack(side=tk.LEFT, padx=5)
        # combo_y.bind('<<ComboboxSelected>>', select_y)
        var = ttk.Entry(line, textvariable=self.axes_y, width=30)
        var.pack(side=tk.LEFT)
        # var.bind('<KeyRelease>', self.fun_expression_reset)
        var.bind('<Return>', self.update_axis_choice)
        var.bind('<KP_Enter>', self.update_axis_choice)
        var = ttk.Checkbutton(line, text='Fix', variable=self.fix_y)
        var.pack(side=tk.LEFT)
        var = ttk.Checkbutton(line, text='Normalise', variable=self.normalise, command=self.normalise_signal)
        var.pack(side=tk.LEFT)

        # Fitting
        frm = ttk.Frame(section, relief=tk.RIDGE, borderwidth=2)
        frm.pack(side=tk.LEFT, padx=4)
        line = ttk.Frame(frm)
        line.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(line, text='Max peaks:').pack(side=tk.LEFT)
        var = ttk.Entry(line, textvariable=self.max_peaks, width=2)
        var.pack(side=tk.LEFT)
        var.bind('<Return>', self.perform_fit)
        var.bind('<KP_Enter>', self.perform_fit)
        ttk.Checkbutton(line, variable=self.do_fit).pack(side=tk.LEFT)

        line = ttk.Frame(frm)
        line.pack(side=tk.TOP, fill=tk.X)
        fit_options = ['Line', 'Gaussian', 'Lorentzian', 'pVoight']  # TODO: get this from somewhere else
        var = ttk.Combobox(line, values=fit_options,
                           textvariable=self.fit_model, width=12)
        var.pack(side=tk.LEFT)
        var.bind('<<ComboboxSelected>>', self.perform_fit)
        ttk.Button(line, text=':', command=self.fit_results, width=1, padding=0).pack(side=tk.LEFT, padx=1)

        # Fitting
        frm = ttk.Frame(section)
        frm.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(frm, text='Processing', command=self.multiplots).pack(side=tk.TOP, fill=tk.X)
        ttk.Button(frm, text='Fitting', command=self.peakfiting).pack(side=tk.TOP, fill=tk.X)

        # Error line
        frm = ttk.Frame(self.root)
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
        if not x_label or not y_label:
            return
        xdata, ydata = self.get_xy_data(x_label, *y_label.split(','))
        self.update_from_data(
            x_data=xdata,
            y_data=ydata,
            x_label=self._label(x_label),
            y_label=self._label(y_label),
            title=os.path.basename(self.filenames[0]),
            legend=[os.path.basename(filename) for filename in self.filenames],
        )
        self.line = self.plot_list[0]

    def _perform_fit(self) -> tuple[FitResults | None, str]:
        """Returns (FitResults, label)"""
        x_label = self.axes_x.get()
        y_label = self.axes_y.get()
        model = self.fit_model.get()
        peaks = self.max_peaks.get()
        if not x_label or not y_label:
            return None, ''
        xdata, ydata = self.get_xy_data(x_label, y_label)
        result = multipeakfit(
            xvals=xdata[0],
            yvals=ydata[0],
            npeaks=peaks,
            model=model,
        )
        x_fit, y_fit = result.fit_data(ntimes=1)  # don't interpolate as x will be the wrong
        label = f"fit_{y_label}_{peaks}{model}"
        self._scannable_data[0][label] = y_fit
        self._fit_result = result
        return result, label

    def perform_fit(self, event=None):
        result, label = self._perform_fit()
        if result is None:
            return
        x, y = result.fit_data()
        lines = self.ax1.plot(x, y, label=label)
        self.plot_list.extend(lines)
        self.update_labels(legend=True)
        self.update_axes()

    def fit_options(self):
        pass

    def fit_results(self):
        from ..apps.edit_text import EditText

        x_axis = self.axes_x.get()
        y_axis = self.axes_y.get()
        if not x_axis or not y_axis:
            return
        xdata, ydata = self.get_xy_data(x_axis, y_axis)
        peak_str = find_peaks_str(xdata[0], ydata[0])

        title = os.path.basename(self.filenames[0])
        x_label, y_label = self.map.generate_ids(x_axis, y_axis)
        label = f"{x_label} vs {y_label}"
        out = f"{title}\n{label}\n\n"
        out += peak_str + '\n\n'
        if self._fit_result is not None:
            out += str(self._fit_result)
        EditText(out, parent=self.root, title=title)

    def multiplots(self):
        from ..apps.multi_scan_analysis import create_multi_scan_analysis
        # Note that exp directory and proc directory are in config
        create_multi_scan_analysis(
            parent=self.root,
            config=self.config,
            scan_numbers=[get_scan_number(f) for f in self.filenames],
            x_axis=self.axes_x.get(),
            y_axis=self.axes_y.get(),
        )

    def peakfiting(self):
        from ..apps.peak_fit_analysis import create_peak_fit
        # Note that exp directory and proc directory are in config
        create_peak_fit(
            parent=self.root,
            config=self.config,
            scan_numbers=[get_scan_number(f) for f in self.filenames],
            x_axis=self.axes_x.get(),
            y_axis=self.axes_y.get(),
        )


class NexusMultiAxisPlot(NexusDefaultPlot):
    """
    1D line plot widget with selection box for selecting multiple axes.
    """
    def __init__(self, root: tk.Misc, *hdf_filenames: str,
                 config: dict | None = None):
        super().__init__(root, *hdf_filenames, config=config)
        self.fig.subplots_adjust(right=0.97)
        self.listbox = self._axis_listbox()

    def _axis_listbox(self) -> ttk.Treeview:
        frame = ttk.Frame(self.root, width=150)
        frame.pack(side=tk.RIGHT, fill=tk.Y)
        frame.pack_propagate(False)

        y_scrollbar = ttk.Scrollbar(frame)
        x_scrollbar = ttk.Scrollbar(frame, orient="horizontal")
        listbox = ttk.Treeview(frame, yscrollcommand=y_scrollbar.set,
                               xscrollcommand=x_scrollbar.set, show="tree")
        listbox.column("#0", width=200, stretch=tk.YES)
        listbox.bind("<<TreeviewSelect>>", self.select_listbox_items)
        y_scrollbar.configure(command=listbox.yview)
        x_scrollbar.configure(command=listbox.xview)

        y_scrollbar.pack(side="right", fill="y")
        x_scrollbar.pack(side="bottom", fill="x")
        listbox.pack(side="left", fill="both", expand=True)
        return listbox

    def update_data_from_files(self, *filenames: str, hdf_map: hdfmap.NexusMap | None = None):
        super().update_data_from_files(*filenames, hdf_map=hdf_map)
        auto_signal = self.axes_y.get()

        # populate listbox
        self.listbox.delete(*self.listbox.get_children())
        first_dataset = self._scannable_data[0]
        for item in first_dataset:
            iid = self.listbox.insert("", tk.END, text=item)
            if item == auto_signal:
                self.listbox.selection_add(iid)
                self.listbox.focus(iid)

    def select_listbox_items(self, event=None):
        if len(self.listbox.selection()) == 0:
            return
        self.remove_lines()
        x_label = self.axes_x.get()
        labels = [self.listbox.item(item)['text'] for item in self.listbox.selection()]
        self.axes_y.set(labels[0])
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
        if self.do_fit.get():
            self.perform_fit()

    def update_axis_choice(self, event=None):
        # select item in list if it matches
        yaxis = self.axes_y.get()
        iid = next((
            item for item in self.listbox.get_children()
            if yaxis == self.listbox.item(item)['text']
        ), None)
        if not iid:
            iid = self.listbox.insert("", tk.END, text=yaxis)
        self.listbox.selection_set(iid)
        self.listbox.see(iid)
        super().update_axis_choice(event)

    def perform_fit(self, event=None):
        result, label = self._perform_fit()
        if result is None:
            return
        if label not in (self.listbox.item(iid, 'text') for iid in self.listbox.get_children()):
            iid = self.listbox.insert("", tk.END, text=label)
        else:
            iid = next(iid for iid in self.listbox.get_children() if self.listbox.item(iid, 'text') == label)
        self.listbox.selection_add(iid)
