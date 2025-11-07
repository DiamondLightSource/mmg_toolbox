"""
widget for performing peak fitting on a list of scans
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt

import hdfmap
import numpy as np

from mmg_toolbox import Experiment
from mmg_toolbox.plotting.matplotlib import generate_subplots, set_span_bounds
from mmg_toolbox.utils.env_functions import get_processing_directory
from mmg_toolbox.utils.fitting import (multipeakfit, FitResults, PEAK_MODELS, BACKGROUND_MODELS,
                                       Model, find_peaks, find_peaks_str)
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from ..misc.functions import show_error
from .treeview import CanvasTreeview
from ..widgets.simple_plot import SimplePlot

logger = create_logger(__file__)

FIT_PARAMETERS = ['amplitude', 'center', 'fwhm', 'background']


class ScanFitModel:
    def __init__(self, scan_no: int, filepath: str, metadata: float, title: str, label: str):
        self.scan_no = scan_no
        self.filepath = filepath
        self.metadata = metadata
        self.x_data = np.array([])
        self.y_data = np.array([])
        self.use_dataset = True
        self.n_peaks: int | None = None
        self.peak_model = 'Gaussian'
        self.background_model = 'Slope'
        self.power: float | None = None
        self.distance = 10
        self.mask: np.ndarray | None = None
        self.title = title
        self.label = label
        self.model: Model | None = None
        self.result: FitResults | None = None

    def fit(self) -> FitResults:
        self.result = multipeakfit(
            xvals=self.x_data,
            yvals=self.y_data,
            yerrors=None,
            npeaks=self.n_peaks,
            min_peak_power=self.power,
            peak_distance_idx=self.distance,
            model=self.peak_model,
            background=self.background_model,
            initial_parameters=None,
            fix_parameters=None,
            method='leastsq',
        )
        return self.result


class ScanPeakTreeview(CanvasTreeview):
    """Treeview object for peak details of scans"""
    def __init__(self, root: tk.Misc, width: int | None = None, height: int | None = None):
        columns = [
            ('#0', 'Scan number', 100, False, None),
            ('metadata', 'Metadata', 100, False, None),
            ('model', 'Model', 200, False, None),
            ('filepath', 'Filepath', 0, False, None),
        ]
        super().__init__(root, *columns, width=width, height=height)

    def populate(self, *scan_details: ScanFitModel):
        self.delete()
        for model in scan_details:
            metadata_str = f"{model.metadata:.5}"
            models = f"{model.n_peaks} {model.peak_model} + {model.background_model}"
            values = (metadata_str, models, model.filepath)
            self.tree.insert("", tk.END, text=str(model.scan_no), values=values)

    def get_current_filepath(self):
        iid = next(iter(self.tree.selection()))
        return self.tree.set(iid, 'filepath')

    def first_scan_number(self) -> int:
        iid = self.first_item()
        return int(self.tree.item(iid, 'text'))

    def first_filepath(self):
        iid = self.first_item()
        return self.tree.set(iid, 'filepath')


class PeakFitAnalysis:
    """Frame to perform peak fitting on a set of scans"""

    def __init__(self, root: tk.Misc, config: dict | None = None, exp_directory: str | None = None,
                 proc_directory: str | None = None, scan_numbers: list[int] | None = None,
                 metadata: str | None = None, x_axis: str | None = None, y_axis: str | None = None):
        logger.info('Creating PeakFitAnalysis')
        self.root = root
        self.config = config or get_config()
        self.exp_directory = exp_directory or self.config.get(C.current_dir, '')
        self.proc_directory = proc_directory or self.config.get(C.current_proc, get_processing_directory(self.exp_directory))

        # self.exp_folder = tk.StringVar(root, exp_directory)
        # self.proc_folder = tk.StringVar(root, proc_directory)
        # self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.x_axis = tk.StringVar(self.root, 'axes' if x_axis is None else x_axis)
        self.y_axis = tk.StringVar(self.root, 'signal' if y_axis is None else y_axis)
        self.metadata_name = tk.StringVar(self.root, '' if metadata is None else metadata)
        self.all_n_peaks = tk.IntVar(self.root, 1)
        self.all_peak_power = tk.DoubleVar(self.root, 1)
        self.all_peak_distance = tk.IntVar(self.root, 10)
        self.all_model = tk.StringVar(self.root, 'Gaussian')
        self.all_background = tk.StringVar(self.root, 'Slope')
        self.scan_use_scan = tk.BooleanVar(self.root, True)
        self.scan_n_peaks = tk.IntVar(self.root, 1)
        self.scan_peak_power = tk.DoubleVar(self.root, 1)
        self.scan_use_peaks = tk.BooleanVar(self.root, True)
        self.scan_use_power = tk.BooleanVar(self.root, True)
        self.scan_peak_distance = tk.IntVar(self.root, 10)
        self.scan_model = tk.StringVar(self.root, 'Gaussian')
        self.scan_background = tk.StringVar(self.root, 'Slope')
        self.scan_title = tk.StringVar(self.root, '')
        self.scan_label = tk.StringVar(self.root, '')
        self.plot_option = tk.StringVar(self.root, FIT_PARAMETERS[0])
        self.map: hdfmap.NexusMap | None = None
        self.fit_models: list[ScanFitModel] = []

        # ---Top section---
        self.ini_top_section(self.root)

        # ---Middle section---
        middle = ttk.Frame(self.root)
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        # Left side - scan selection
        left = ttk.LabelFrame(middle, text='Scan Numbers')
        left.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)

        self.scans = ScanPeakTreeview(left)
        self.scans.bind_select(self.select_scan)

        # Right side
        right = ttk.Frame(middle)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)

        # Plot
        frm = ttk.Frame(right)
        frm.pack(side=tk.TOP, fill=tk.BOTH, padx=2, pady=2)

        self.plot = SimplePlot(frm, [], [], x_axis, y_axis, config=self.config)
        self.data_line, = self.plot.plot([], [], 'bo-', label='Data')
        self.mask_line, = self.plot.plot([], [], '.', label='mask')
        self.fit_line, = self.plot.plot([], [], 'r-', label='Fit')
        self.pl_span = self.plot.ax1.axvspan(0, 0, alpha=0.2)

        # Fit parameters
        frm = ttk.Frame(right)
        frm.pack(side=tk.TOP, fill=tk.BOTH, padx=2, pady=2)

        self.ini_parameters(frm)

        # ---Bottom---
        bottom = ttk.Frame(self.root)
        bottom.pack(side=tk.TOP, expand=tk.YES, pady=8, padx=4)
        ttk.Button(bottom, text='Plot All', command=self.fit_plots).pack(side=tk.LEFT)
        ttk.Button(bottom, text='Plot Fit results', command=self.fit_all).pack(side=tk.LEFT)
        options = ['All'] + FIT_PARAMETERS
        ttk.Combobox(bottom, textvariable=self.plot_option, values=options).pack(side=tk.LEFT, padx=2)

        # ---Start---
        self.add_scans(*scan_numbers)
        self.scans.tree.selection_set(self.scans.first_item())

    def ini_top_section(self, root: tk.Misc):
        # top = ttk.LabelFrame(root, text='Folders')
        # top.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)
        #
        # frm = ttk.Frame(top)
        # frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # ttk.Label(frm, text='Data Dir:', width=15).pack(side=tk.LEFT, padx=4)
        # ttk.Entry(frm, textvariable=self.exp_folder, width=60).pack(side=tk.LEFT)
        # ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side=tk.LEFT)
        #
        # frm = ttk.Frame(top)
        # frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # ttk.Label(frm, text='Analysis Dir:', width=15).pack(side=tk.LEFT, padx=4)
        # ttk.Entry(frm, textvariable=self.proc_folder, width=60).pack(side=tk.LEFT)
        # ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side=tk.LEFT)

        # Axis + Metadata selection
        top = ttk.LabelFrame(root, text='Axes')
        top.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(top)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='X:', width=2).pack(side=tk.LEFT, padx=2)
        var = ttk.Entry(frm, textvariable=self.x_axis, width=20)
        var.pack(side=tk.LEFT)
        var.bind("<Return>", self.plot_scan)
        var.bind("<KP_Enter>", self.plot_scan)
        ttk.Button(frm, text=':', command=self.browse_x_axis, width=1, padding=0).pack(side=tk.LEFT)

        ttk.Label(frm, text='Y:', width=2).pack(side=tk.LEFT, padx=4)
        var = ttk.Entry(frm, textvariable=self.y_axis, width=20)
        var.pack(side=tk.LEFT)
        var.bind("<Return>", self.plot_scan)
        var.bind("<KP_Enter>", self.plot_scan)
        ttk.Button(frm, text=':', command=self.browse_y_axis, width=1, padding=0).pack(side=tk.LEFT)

        ttk.Label(frm, text='Metadata:', width=15).pack(side=tk.LEFT, padx=4)
        var = ttk.Entry(frm, textvariable=self.metadata_name, width=20)
        var.pack(side=tk.LEFT)
        var.bind("<Return>", self.update_scans)
        var.bind("<KP_Enter>", self.update_scans)
        ttk.Button(frm, text=':', command=self.browse_metadata, width=1, padding=0).pack(side=tk.LEFT)
        ttk.Button(frm, text='Update', command=self.update_scans, padding=1).pack(side=tk.RIGHT, padx=5)

        # Model selection
        frm = ttk.LabelFrame(root, text='Fit Options')
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        ttk.Label(frm, text='N Peaks:', width=8).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.all_n_peaks, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Power:', width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='?', command=self.help_power, width=2, padding=0).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=self.all_peak_power, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Distance:', width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='?', command=self.help_peak_distance, width=2, padding=0).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=self.all_peak_distance, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Model:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.all_model, values=list(PEAK_MODELS)).pack(side=tk.LEFT, padx=2)

        ttk.Label(frm, text='Background:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.all_background, values=list(BACKGROUND_MODELS)).pack(side=tk.LEFT, padx=2)

    def ini_parameters(self, root: tk.Misc):
        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4, pady=2)
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT)
        line = ttk.Frame(left)
        line.pack(side=tk.TOP)
        ttk.Checkbutton(line, variable=self.scan_use_scan, command=self.update_model).pack(side=tk.LEFT)
        ttk.Label(line, textvariable=self.scan_title).pack(side=tk.LEFT, fill=tk.X, padx=5, pady=2)
        ttk.Label(left, textvariable=self.scan_label, width=20).pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        right = ttk.Frame(frm)
        right.pack(side=tk.LEFT)
        ttk.Button(right, text='Fit', command=self.perform_fit).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(right, text='Results', command=self.display_results).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4, pady=2)
        opt = ttk.Frame(frm, relief=tk.GROOVE)
        opt.pack(side=tk.LEFT, padx=5, pady=4)
        ttk.Label(opt, text='N Peaks:', width=10).pack(side=tk.LEFT, padx=2)
        ttk.Entry(opt, textvariable=self.scan_n_peaks, width=3).pack(side=tk.LEFT)
        ttk.Checkbutton(opt, variable=self.scan_use_peaks, command=self.update_model, padding=0).pack(side=tk.LEFT, padx=2)

        opt = ttk.Frame(frm, relief=tk.GROOVE)
        opt.pack(side=tk.LEFT, padx=5, pady=4)
        ttk.Label(opt, text='Power:', width=10).pack(side=tk.LEFT, padx=2)
        ttk.Entry(opt, textvariable=self.scan_peak_power, width=3).pack(side=tk.LEFT)
        ttk.Checkbutton(opt, variable=self.scan_use_power, command=self.update_model, padding=0).pack(side=tk.LEFT, padx=2)

        opt = ttk.Frame(frm, relief=tk.GROOVE)
        opt.pack(side=tk.LEFT, padx=5, pady=4)
        ttk.Label(opt, text='Distance:', width=10).pack(side=tk.LEFT, padx=2)
        ttk.Entry(opt, textvariable=self.scan_peak_distance, width=3).pack(side=tk.LEFT)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4, pady=2)
        ttk.Label(frm, text='Model:').pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.scan_model, values=list(PEAK_MODELS), width=10).pack(side=tk.LEFT, padx=2)

        ttk.Label(frm, text='Background:').pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.scan_background, values=list(BACKGROUND_MODELS),
                     width=10).pack(side=tk.LEFT, padx=2)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, padx=4, pady=2)
        ttk.Button(frm, text='Select Region', command=self.select_region).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='Mask Region', command=self.select_mask).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='Reset', command=self.reset_mask).pack(side=tk.LEFT, padx=2)

        # frm = ttk.Frame(root)
        # frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # parameters
        # TODO: add parameters

    def browse_x_axis(self):
        from ..apps.namespace_select import create_scannable_selector
        names = create_scannable_selector(self.map)
        if names:
            self.x_axis.set(', '.join(name for name in names))
            self.plot_scan()

    def browse_y_axis(self):
        from ..apps.namespace_select import create_scannable_selector
        names = create_scannable_selector(self.map)
        if names:
            self.y_axis.set(', '.join(name for name in names))
            self.plot_scan()

    def browse_metadata(self):
        from ..apps.namespace_select import create_metadata_selector
        paths = create_metadata_selector(self.map)
        if paths:
            self.metadata_name.set(', '.join(path for path in paths))
            self.update_scans()

    def help_power(self):
        messagebox.showinfo(
            title='Peak Power',
            message=(
                'A peak must achieve this ratio of signal / background to count as a peak.\n' +
                'Put 0 to allow all peaks.'
            ),
            parent=self.root,
        )

    def help_peak_distance(self):
        messagebox.showinfo(
            title='Peak Distance',
            message='Multiple peaks must be separated by this distance, in units of x-elements',
            parent=self.root,
        )

    #######################################################
    ################## methods ############################
    #######################################################

    def get_experiment(self):
        return Experiment(self.exp_directory, instrument=self.config.get('beamline', None))

    def get_scan_files(self, *scan_numbers: int) -> list[str]:
        try:
            exp = self.get_experiment()
            scan_files = [exp.get_scan_filename(n) for n in scan_numbers]
            self.map = hdfmap.create_nexus_map(scan_files[0])
        except Exception as e:
            show_error(e, self.root, raise_exception=False)
            raise e
        return scan_files

    def get_metadata(self, *scan_files: str) -> np.ndarray:
        name = self.metadata_name.get().split(',')[0]
        metadata = np.zeros(len(scan_files))
        if not name:
            return metadata
        for n, filename in enumerate(scan_files):
            with hdfmap.load_hdf(filename) as hdf:
                metadata[n] = self.map.eval(hdf, name)
        return metadata

    def add_scans(self, *scan_numbers: int):
        scan_files = self.get_scan_files(*scan_numbers)
        self.fit_models = [
            ScanFitModel(
                scan_no=n,
                filepath=f,
                metadata=0,
                title=str(n),
                label=f
            ) for n, f in zip(scan_numbers, scan_files)
        ]
        self.update_scans()

    def update_scans(self, event=None):
        metadata = self.get_metadata(*(model.filepath for model in self.fit_models))
        for n, model in enumerate(self.fit_models):
            model.metadata = metadata[n]
            model.peak_model = self.all_model.get()
            model.background_model = self.all_background.get()
            model.n_peaks = self.all_n_peaks.get()
            model.power = self.all_peak_power.get()
            model.distance = self.all_peak_distance.get()
        self.scans.populate(*self.fit_models)

    def get_scan_xy_data(self, filename: str | None = None) -> tuple[np.ndarray, np.ndarray]:
        if filename is None:
            filename = self.scans.get_current_filepath()
        x_axis = self.x_axis.get()
        y_axis = self.y_axis.get()
        with self.map.load_hdf(filename) as hdf:
            x_data = self.map.eval(hdf, x_axis, np.arange(self.map.scannables_length()))
            y_data = self.map.eval(hdf, y_axis, np.ones_like(x_data))
        return x_data, y_data

    def select_scan(self, event=None):
        index = self.scans.get_index()
        model = self.fit_models[index]
        self.scan_use_scan.set(model.use_dataset)
        self.scan_n_peaks.set(0 if model.n_peaks is None else model.n_peaks)
        self.scan_use_peaks.set(False if model.n_peaks is None else True)
        self.scan_model.set(model.peak_model)
        self.scan_background.set(model.background_model)
        self.scan_peak_power.set(0 if model.power is None else model.power)
        self.scan_use_power.set(False if model.power is None else True)
        self.scan_peak_distance.set(model.distance)
        self.scan_title.set(model.title)
        self.scan_label.set(model.label)
        self.perform_fit()

    def update_model(self, index: int | None = None) -> ScanFitModel:
        if index is None:
            index = self.scans.get_index()
        model = self.fit_models[index]
        x_data, y_data = self.get_scan_xy_data(model.filepath)
        mask = self.fit_models[self.scans.get_index()].mask
        if mask is not None:
            x_data = x_data[mask]
            y_data = y_data[mask]
        model.x_data = x_data
        model.y_data = y_data
        model.use_dataset = self.scan_use_scan.get()
        model.n_peaks = self.scan_n_peaks.get() if self.scan_use_peaks.get() else None
        model.peak_model = self.scan_model.get()
        model.background_model = self.scan_background.get()
        model.power = self.scan_peak_power.get() if self.scan_use_power.get() else None
        model.distance = self.scan_peak_distance.get()
        return model

    def plot_scan(self, event=None):
        model = self.fit_models[self.scans.get_index()]
        x_data, y_data = self.get_scan_xy_data(model.filepath)
        if model.mask is not None:
            x_mask = x_data[model.mask]
            y_mask = y_data[model.mask]
            x_data = x_data[~model.mask]
            y_data = y_data[~model.mask]
        else:
            x_mask, y_mask = [], []

        if model.result is not None:
            x_fit, y_fit = model.result.fit_data(x_data)
        else:
            x_fit, y_fit = [], []

        x_label, y_label = self.map.generate_ids(self.x_axis.get(), self.y_axis.get())

        self.data_line.set_xdata(x_data)
        self.data_line.set_ydata(y_data)
        self.mask_line.set_xdata(x_mask)
        self.mask_line.set_ydata(y_mask)
        self.fit_line.set_xdata(x_fit)
        self.fit_line.set_ydata(y_fit)
        self.plot.ax1.set_xlabel(x_label)
        self.plot.ax1.set_ylabel(y_label)
        set_span_bounds(self.pl_span, x_data[0], x_data[0], y_data[0], y_data[0])
        # self.pl_span.set_bounds(x_data[0], y_data[0], 0, 0)
        self.plot.update_axes()

    def perform_fit(self):
        model = self.update_model()
        model.fit()
        self.plot_scan()

    def display_results(self):
        from ..apps.edit_text import EditText
        model = self.update_model()
        if model.result is None:
            return
        peak_str = find_peaks_str(model.x_data, model.y_data,
                                  min_peak_power=model.power, peak_distance_idx=model.distance)

        meta_str = f"{self.metadata_name.get()} = {model.metadata:.5g}"
        out = f"{model.title}\n{model.label}\n{meta_str}\n\n"
        # out += f"Power = {peak_ratio(model.y_data)}\n\n"
        out += peak_str + '\n\n'
        out += str(model.result)
        EditText(out, parent=self.root, title=model.label)

    def scans_title(self):
        scan_numbers = [model.scan_no for model in self.fit_models]
        exp = self.get_experiment()
        return exp.generate_scans_title(*scan_numbers, hdf_map=self.map)

    def fit_all(self):
        option = self.plot_option.get()
        if option == 'All':
            self._plot_all_results()
            return

        metadata, value, error = [], [], []
        for n in range(len(self.fit_models)):
            model = self.update_model(n)
            if model.use_dataset:
                result = model.fit()
                metadata.append(model.metadata)
                val, err = result.get_value(option)
                value.append(val)
                error.append(err)

        x_label = self.metadata_name.get()
        y_label = option.capitalize()

        fig, ax = plt.subplots()
        ax.errorbar(metadata, value, error, fmt='-o')
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(self.scans_title())
        plt.show()

    def _plot_all_results(self):
        dpi = self.config.get(C.plot_dpi)
        fig, axes = plt.subplots(2, 2, figsize=[12, 12], dpi=dpi)
        fig.suptitle(self.scans_title())
        axes = axes.flatten()
        x_label = self.metadata_name.get()
        metadata = [model.metadata for model in self.fit_models]
        results = [model.fit() for model in self.fit_models]
        for ax, option in zip(axes, FIT_PARAMETERS):
            values, errors = zip(*[result.get_value(option) for result in results])
            ax.errorbar(metadata, values, errors, fmt='-o', label=option)
            ax.set_xlabel(x_label)
            ax.set_ylabel(option.capitalize())
        plt.show()

    def fit_plots(self):
        x_label, y_label, name = self.map.generate_ids(self.x_axis.get(), self.y_axis.get(), self.metadata_name.get())

        fig_axes = generate_subplots(len(self.fit_models))
        for n, (fig, axes) in enumerate(fig_axes):
            model = self.update_model(n)
            x_data, y_data = self.get_scan_xy_data(model.filepath)
            if model.mask is not None:
                x_mask = x_data[model.mask]
                y_mask = y_data[model.mask]
                x_data = x_data[~model.mask]
                y_data = y_data[~model.mask]
            else:
                x_mask, y_mask = [], []

            if model.use_dataset:
                result = model.fit()
                x_fit, y_fit = result.fit_data(x_data)
            else:
                x_fit, y_fit = [], []

            title = f"{model.title}\n{name} = {model.metadata:.5g}"

            axes.plot(x_mask, y_mask, 'b.', label=None)
            axes.plot(x_data, y_data, 'b-o', label='Data')
            axes.plot(x_fit, y_fit, 'r-', label='Fit')
            axes.set_xlabel(x_label)
            axes.set_ylabel(y_label)
            axes.legend()
            axes.set_title(title)
        plt.show()

    "------------------------------------------------------------------------"
    "---------------------------Button Functions-----------------------------"
    "------------------------------------------------------------------------"

    def chk_y(self):
        """Apply functions to y-axis"""
        # old_log, old_smooth, old_diff = self.ydata_checkboxes
        # log = self.ylog.get()
        # smooth = self.ysmooth.get()
        # diff = self.ydiff.get()
        # # update original data
        # if sum(self.ydata_checkboxes) == 0:
        #     xdata, ydata, yerror = self.gen_data()
        #     self.ydata_original = ydata
        # data = 1.0 * self.ydata_original
        # if log:
        #     data = np.log10(data)
        # if diff:
        #     data = np.gradient(data)
        # if smooth:
        #     data = i16_peakfit.functions.conv_gauss(data, len(data) // 4, 0.1)
        # self.ydata_checkboxes = [log, smooth, diff]
        # self.txt_y.delete("1.0", tk.END)
        # self.txt_y.insert("1.0", str(list(data)))
        # self.plot_data()

    def but_find_peaks(self):
        """Button Find Peaks"""
        x_data, y_data = self.get_scan_xy_data()
        mask = self.fit_models[self.scans.get_index()].mask
        if mask is not None:
            x_data = x_data[mask]
            y_data = y_data[mask]
        model = self.update_model()

        # Run find peaks, create message
        idx, pwr = find_peaks(y_data, None, min_peak_power=model.power, peak_distance_idx=model.distance)
        s = "Found %d peaks\n" % len(idx)
        s += "  Index | Position | Power\n"
        for _idx, _pwr in zip(idx, pwr):
            s += f"  {_idx:5} | {x_data[_idx]:8.4g} | {_pwr:5.2f}\n"
        # self.message.set('Found %d peaks' % len(idx))
        # self.txt_res.delete('1.0', tk.END)
        # self.txt_res.insert('1.0', s)
        print(s) #TODO: Do something with this

    def select_peaks(self):
        """Button Select Peaks"""

        def get_mouseposition(event):
            print(event.x, event.y, event.xdata, event.ydata, event.inaxes)
            self.plot.fig.canvas.mpl_disconnect(press)
            # self.root.unbind("<Button-1>")
            self.plot.root.config(cursor="arrow")

            if event.inaxes:
                print(f"Position selected: ({event.xdata:.4}, {event.ydata:.4})")
                # self.message.set('Position selected: (%.4g, %.4g)' % (event.xdata, event.ydata))
                # Add peak
                # self.add_peak('Gaussian', event.xdata, event.ydata)

            else:
                # self.message.set('No position selected')
                print('No position selected')

        # self.message.set('Click on Figure to add a peak')
        press = self.plot.fig.canvas.mpl_connect('button_press_event', get_mouseposition)
        # self.root.bind("<Button-1>", get_mouseposition)
        self.plot.root.config(cursor="crosshair")

    def select_region(self):
        """Button click to select"""

        x_data, ydata = self.get_scan_xy_data()
        model = self.fit_models[self.scans.get_index()]
        mask = model.mask
        if mask is None or len(ydata) != len(mask):
            mask = np.ones(x_data.shape, dtype=bool)

        xval = [np.min(x_data)]
        ipress = [False]

        def disconnect():
            self.plot_scan()
            self.plot.fig.canvas.mpl_disconnect(press)
            self.plot.fig.canvas.mpl_disconnect(move)
            self.plot.fig.canvas.mpl_disconnect(release)
            self.plot.root.config(cursor="arrow")

        def mouse_press(event):
            if event.inaxes:
                xval[0] = event.xdata
                ipress[0] = True
            else:
                disconnect()

        def mouse_move(event):
            if event.inaxes and ipress[0]:
                x_max = event.xdata
                ax_ymin, ax_ymax = self.plot.ax1.get_ylim()
                # span = [[xval[0], ax_ymin], [xval[0], ax_ymax], [x_max, ax_ymax], [x_max, ax_ymin], [xval[0], ax_ymin]]
                # self.pl_span.set_xy(span)
                set_span_bounds(self.pl_span, xval[0], x_max, ax_ymin, ax_ymax)
                # self.pl_span.set_bounds(xval[0], ax_ymin, x_max - xval[0], ax_ymax - ax_ymin)
                self.plot.update_axes()

        def mouse_release(event):
            x_min = min(xval[0], event.xdata)
            x_max = max(xval[0], event.xdata)
            new_selection = (x_data > x_min) * (x_data < x_max)
            if np.any(mask[new_selection]):
                mask[new_selection] = False
            else:
                mask[~new_selection] = True
            model.mask = mask
            disconnect()

        self.plot_scan()
        # self.message.set('Click & Drag region to select')
        press = self.plot.fig.canvas.mpl_connect('button_press_event', mouse_press)
        move = self.plot.fig.canvas.mpl_connect('motion_notify_event', mouse_move)
        release = self.plot.fig.canvas.mpl_connect('button_release_event', mouse_release)
        # self.root.bind("<Button-1>", get_mouseposition)
        self.plot.root.config(cursor="crosshair")

    def select_mask(self):
        """Button click to mask"""

        xdata, ydata = self.get_scan_xy_data()
        mask = self.fit_models[self.scans.get_index()].mask
        if mask is None or len(ydata) != len(mask):
            mask = np.zeros(xdata.shape, dtype=bool)

        xval = [np.min(xdata)]
        ipress = [False]

        def disconnect():
            self.plot_scan()
            self.plot.fig.canvas.mpl_disconnect(press)
            self.plot.fig.canvas.mpl_disconnect(move)
            self.plot.fig.canvas.mpl_disconnect(release)
            self.plot.root.config(cursor="arrow")

        def mouse_press(event):
            if event.inaxes:
                xval[0] = event.xdata
                ipress[0] = True
            else:
                disconnect()

        def mouse_move(event):
            if event.inaxes and ipress[0]:
                x_max = event.xdata
                ax_ymin, ax_ymax = self.plot.ax1.get_ylim()
                # span = [[xval[0], ax_ymin], [xval[0], ax_ymax], [x_max, ax_ymax], [x_max, ax_ymin], [xval[0], ax_ymin]]
                # self.pl_span.set_xy(span)
                set_span_bounds(self.pl_span, xval[0], x_max, ax_ymin, ax_ymax)
                # self.pl_span.set_bounds(xval[0], ax_ymin, x_max - xval[0], ax_ymax - ax_ymin)
                self.plot.update_axes()

        def mouse_release(event):
            x_min = min(xval[0], event.xdata)
            x_max = max(xval[0], event.xdata)
            new_selection = (xdata > x_min) * (xdata < x_max)
            mask[new_selection] = True
            disconnect()

        self.plot_scan()
        # self.message.set('Click & Drag region to select')
        press = self.plot.fig.canvas.mpl_connect('button_press_event', mouse_press)
        move = self.plot.fig.canvas.mpl_connect('motion_notify_event', mouse_move)
        release = self.plot.fig.canvas.mpl_connect('button_release_event', mouse_release)
        # self.root.bind("<Button-1>", get_mouseposition)
        self.plot.root.config(cursor="crosshair")

    def reset_mask(self):
        xdata, ydata = self.get_scan_xy_data()
        self.fit_models[self.scans.get_index()].mask = np.zeros(xdata.shape, dtype=bool)
        self.plot_scan()
