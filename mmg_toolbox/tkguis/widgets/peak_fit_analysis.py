"""
widget for performing peak fitting on a list of scans
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt

import hdfmap
import numpy as np

from mmg_toolbox import Experiment
from mmg_toolbox.utils.env_functions import get_processing_directory
from mmg_toolbox.utils.fitting import multipeakfit, FitResults, PEAK_MODELS, BACKGROUND_MODELS, Model
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from ..misc.functions import select_folder, show_error
from ..widgets.nexus_treeview import _Treeview
from ..widgets.simple_plot import SimplePlot

logger = create_logger(__file__)


class ScanPeakTreeview(_Treeview):
    """Treeview object for peak details of scans"""
    def __init__(self, root: tk.Misc):
        super().__init__(root, 'n_peaks', 'model', 'background', 'pars', 'filepath')
        # Populate tree
        self.tree.heading("#0", text="Scan number")
        self.tree.column("#0", minwidth=100, width=10)
        self.tree.column("n_peaks", width=10, anchor='c')
        self.tree.column("model", width=200, anchor='c')
        self.tree.column("background", width=200, anchor='c')
        self.tree.column("filepath", width=0)
        self.tree.column("pars", width=400, anchor='c')
        self.tree.heading("n_peaks", text="N Peaks")
        self.tree.heading("model", text="Model")
        self.tree.heading("background", text="Background")
        self.tree.heading("pars", text="Parameters")

    columns = [
        # (name, text, width, reverse, sort_col)
        ("#0", 'Scan number', 100, False, None),
        ("n_peaks", 'N Peaks', 50, True, None),
        ("power", 'Peak Power', 50, True, None),
        ("distance", 'Distance', 50, True, None),
        ("model", 'Model', 200, False, None),
        ("filepath", 'File Path', 0, False, None),
    ]

    def populate(self, *scan_details: tuple[int, int, str, str, list, str]):
        """Load HDF file, populate ttk.treeview object"""
        for scan_no, n_peaks, model, background, pars, filepath in scan_details:
            values = str(n_peaks), model, background, pars, filepath
            self.tree.insert("", tk.END, text=str(scan_no), values=values)

    def get_selection(self) -> list[tuple[int, int, str, str, list, str]]:
        return [[int(self.tree.item(iid)['text'])] + self.tree.item(iid)['values'] for iid in self.tree.selection()]

    def get_current_filepath(self):
        iid = next(iter(self.tree.selection()))
        return self.tree.set(iid, 'filepath')

    def first_scan_number(self) -> int:
        iid = next(iter(self.tree.get_children()))
        return int(self.tree.item(iid, 'text'))

    def first_filepath(self):
        iid = next(iter(self.tree.get_children()))
        return self.tree.set(iid, 'filepath')


class PeakFitAnalysis:
    """Frame to perform peak fitting on a set of scans"""

    def __init__(self, root: tk.Misc, config: dict | None = None, exp_directory: str | None = None,
                 proc_directory: str | None = None, scan_numbers: list[int] | None = None,
                 metadata: str | None = None, x_axis: str | None = None, y_axis: str | None = None):
        logger.info('Creating PeakFitAnalysis')
        self.root = root
        self.config = config or get_config()
        exp_directory = exp_directory or self.config.get(C.current_dir, '')
        proc_directory = proc_directory or self.config.get(C.current_proc, get_processing_directory(exp_directory))

        self.exp_folder = tk.StringVar(root, exp_directory)
        self.proc_folder = tk.StringVar(root, proc_directory)
        self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.x_axis = tk.StringVar(self.root, 'axes' if x_axis is None else x_axis)
        self.y_axis = tk.StringVar(self.root, 'signal' if y_axis is None else y_axis)
        self.metadata_name = tk.StringVar(self.root, '' if metadata is None else metadata)
        self.all_n_peaks = tk.IntVar(self.root, 1)
        self.all_peak_power = tk.DoubleVar(self.root, 1)
        self.all_peak_distance = tk.IntVar(self.root, 10)
        self.all_model = tk.StringVar(self.root, 'Gaussian')
        self.all_background = tk.StringVar(self.root, 'Slope')
        self.scan_n_peaks = tk.IntVar(self.root, 1)
        self.scan_peak_power = tk.DoubleVar(self.root, 1)
        self.scan_peak_distance = tk.IntVar(self.root, 10)
        self.scan_model = tk.StringVar(self.root, 'Gaussian')
        self.scan_background = tk.StringVar(self.root, 'Slope')
        self.scan_title = tk.StringVar(self.root, '')
        self.scan_label = tk.StringVar(self.root, '')
        self.options = {}
        self.file_list = []
        self.map: hdfmap.NexusMap | None = None
        self.fit: FitResults | None = None
        self.mask = np.array([])

        # ---Top section---
        top = ttk.LabelFrame(self.root, text='Folders')
        top.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(top)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Data Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.exp_folder, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side=tk.LEFT)

        frm = ttk.Frame(top)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Analysis Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.proc_folder, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side=tk.LEFT)

        # Axis + Metadata selection
        top = ttk.LabelFrame(self.root, text='Axes')
        top.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(top)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='X:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.x_axis, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_x_axis, width=1, padding=0).pack(side=tk.LEFT)

        ttk.Label(frm, text='Y:', width=2).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.y_axis, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_y_axis, width=1, padding=0).pack(side=tk.LEFT)

        ttk.Label(frm, text='Metadata:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.metadata_name, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_metadata, width=1, padding=0).pack(side=tk.LEFT)

        # Model selection
        frm = ttk.Frame(top)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='N Peaks:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.all_n_peaks, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Power:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='?', command=self.help_power, width=2, padding=0).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=self.all_peak_power, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Distance:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Button(frm, text='?', command=self.help_peak_distance, width=2, padding=0).pack(side=tk.LEFT)
        ttk.Entry(frm, textvariable=self.all_peak_distance, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Model:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.all_model, values=list(PEAK_MODELS)).pack(side=tk.LEFT, padx=2)

        ttk.Label(frm, text='Background:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.all_background, values=list(BACKGROUND_MODELS)).pack(side=tk.LEFT, padx=2)

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

        # Fit parameters
        frm = ttk.Frame(right)
        frm.pack(side=tk.TOP, fill=tk.BOTH, padx=2, pady=2)

        self.ini_parameters(frm)

        # ---Bottom---
        bottom = ttk.Frame(self.root)
        bottom.pack(side=tk.TOP, expand=tk.YES, pady=8, padx=4)
        ttk.Button(bottom, text='Fig', command=self.perform_fit, width=10).pack(side=tk.LEFT)

        # ---Start---
        self.add_scans(*scan_numbers)

    def ini_parameters(self, root: tk.Misc):
        ttk.Label(root, text='Scan:', textvariable=self.scan_title).pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(root, textvariable=self.scan_label).pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='N Peaks:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.scan_n_peaks, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Power:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.scan_peak_power, width=3).pack(side=tk.LEFT)

        ttk.Label(frm, text='Distance:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.scan_peak_distance, width=3).pack(side=tk.LEFT)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Model:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.scan_model, values=list(PEAK_MODELS)).pack(side=tk.LEFT, padx=2)

        ttk.Label(frm, text='Background:', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Combobox(frm, textvariable=self.scan_background, values=list(BACKGROUND_MODELS)).pack(side=tk.LEFT, padx=2)

        frm = ttk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # parameters
        # TODO: add parameters

    def add_scans(self, *scan_numbers: int):
        scan_files = self.get_scan_files(*scan_numbers)

        n_peaks = self.all_n_peaks.get()
        model = self.all_model.get()
        background = self.all_background.get()
        params = []
        scan_details = [
            (n, n_peaks, model, background, params, f)
            for n, f in zip(scan_numbers, scan_files)
        ]
        self.scans.populate(*scan_details)

    def browse_datadir(self):
        folder = select_folder(self.root)
        if folder:
            self.exp_folder.set(folder)

    def browse_analysis(self):
        folder = select_folder(self.root)
        if folder:
            self.proc_folder.set(folder)

    def browse_x_axis(self):
        from ..apps.namespace_select import create_scannable_selector
        scan_file = self.scans.first_filepath()
        hdf_map = hdfmap.create_nexus_map(scan_file)
        names = create_scannable_selector(hdf_map)
        if names:
            self.x_axis.set(', '.join(name for name in names))

    def browse_y_axis(self):
        from ..apps.namespace_select import create_scannable_selector
        scan_file = self.scans.first_filepath()
        hdf_map = hdfmap.create_nexus_map(scan_file)
        names = create_scannable_selector(hdf_map)
        if names:
            self.y_axis.set(', '.join(name for name in names))

    def browse_metadata(self):
        from ..apps.namespace_select import create_metadata_selector
        scan_file = self.scans.first_filepath()
        hdf_map = hdfmap.create_nexus_map(scan_file)
        paths = create_metadata_selector(hdf_map)
        if paths:
            self.metadata_name.set(', '.join(path for path in paths))

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

    def get_experiment(self):
        return Experiment(self.exp_folder.get(), instrument=self.config.get('beamline', None))

    def get_scan_files(self, *scan_numbers: int) -> list[str]:
        try:
            exp = self.get_experiment()
            scan_files = [exp.get_scan_filename(n) for n in scan_numbers]
            self.map = hdfmap.create_nexus_map(scan_files[0])
        except Exception as e:
            show_error(e, self.root, raise_exception=False)
            raise e
        return scan_files

    def get_scan_xy_data(self, filename: str) -> tuple[np.ndarray, np.ndarray]:
        x_axis = self.x_axis.get()
        y_axis = self.y_axis.get()
        with self.map.load_hdf(filename) as hdf:
            x_data = self.map.eval(hdf, x_axis)
            y_data = self.map.eval(hdf, y_axis)
        return x_data, y_data

    def get_fit_xy_data(self) -> tuple[np.ndarray, np.ndarray]:
        if self.fit is None:
            return np.array([]), np.array([])
        return self.fit.fit()

    def select_scan(self, event=None):
        select = self.scans.get_selection()
        if not select:
            return
        scan_no, n_peaks, model, background, params, filepath = select[0]
        self.scan_n_peaks.set(n_peaks)
        self.scan_model.set(model)
        self.scan_background.set(background)
        self.scan_title.set(filepath)
        self.scan_label.set(str(scan_no))
        self.perform_fit()
        self.plot_scan()

    def plot_scan(self):
        filepath = self.scans.get_current_filepath()
        x_data, y_data = self.get_scan_xy_data(filepath)
        x_fit, y_fit = self.get_fit_xy_data()
        x_label, y_label = self.map.generate_ids(self.x_axis.get(), self.y_axis.get())

        self.data_line.set_xdata(x_data)
        self.data_line.set_ydata(y_data)
        self.fit_line.set_xdata(x_fit)
        self.fit_line.set_ydata(y_fit)
        self.plot.ax1.set_xlabel(x_label)
        self.plot.ax1.set_ylabel(y_label)
        self.plot.update_axes()

    def perform_fit(self):
        filepath = self.scans.get_current_filepath()
        x_data, y_data = self.get_scan_xy_data(filepath)

        results = multipeakfit(
            xvals=x_data,
            yvals=y_data,
            yerrors=None,
            npeaks=self.scan_n_peaks.get(),
            min_peak_power=None,
            peak_distance_idx=10,
            model=self.scan_model.get(),
            background=self.scan_background.get(),
            initial_parameters=None,
            fix_parameters=None,
            method='leastsq',
        )
        self.fit = results



