"""
widget for running scripts
"""

import tkinter as tk
from tkinter import ttk

import hdfmap

from mmg_toolbox import Experiment
from mmg_toolbox.utils.env_functions import get_first_file, get_processing_directory
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from ..misc.functions import select_folder
from ..widgets.scan_range_selector import ScanRangeSelector

logger = create_logger(__file__)


class MultiScanAnalysis:
    """Frame with """

    def __init__(self, root: tk.Misc, config: dict | None = None, exp_directory: str | None = None,
                 proc_directory: str | None = None, scan_numbers: list[int] | None = None):
        logger.info('Creating ScriptRunner')
        self.root = root
        self.config = get_config() if config is None else config

        if exp_directory is None:
            exp_directory = self.config.get(C.current_dir, '')
        if proc_directory is None:
            proc_directory = self.config.get(C.current_proc, get_processing_directory(exp_directory))

        self.exp_folder = tk.StringVar(root, exp_directory)
        self.proc_folder = tk.StringVar(root, proc_directory)
        self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.x_axis = tk.StringVar(self.root, 'axes')
        self.y_axis = tk.StringVar(self.root, 'signal')
        self.metadata_name = tk.StringVar(self.root, '')
        self.options = {}
        self.file_list = []

        sec = ttk.LabelFrame(self.root, text='Folders')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(sec)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Data Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.exp_folder, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side=tk.LEFT)

        frm = ttk.Frame(sec)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Analysis Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.proc_folder, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side=tk.LEFT)

        # Axis + Metadata selection
        sec = ttk.LabelFrame(self.root, text='Axes')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(sec)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='X:', width=2).pack(side=tk.LEFT, padx=2)
        ttk.Entry(frm, textvariable=self.x_axis, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_x_axis, width=1).pack(side=tk.LEFT)

        ttk.Label(frm, text='Y:', width=2).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.y_axis, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_y_axis, width=1).pack(side=tk.LEFT)

        ttk.Label(frm, text='Metadata:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.metadata_name, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text=':', command=self.browse_metadata, width=1).pack(side=tk.LEFT)

        # Range selection
        sec = ttk.LabelFrame(self.root, text='Scan Numbers')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        self.range = ScanRangeSelector(sec, exp_directory, self.config)
        self.range.exp_folder.set(exp_directory)
        if scan_numbers is not None:
            self.range.text.insert("1.0", str(scan_numbers))

        line = ttk.Frame(self.root)
        line.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, pady=8, padx=4)
        ttk.Button(line, text='Plot', command=self.plot, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot 2D', command=self.plot2d, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot 3D', command=self.plot3d, width=10).pack(side=tk.LEFT)

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
        scan_file = next(iter(self.range.generate_scan_files().values()), get_first_file(self.exp_folder.get()))
        hdf_map = hdfmap.create_nexus_map(scan_file)
        names = create_scannable_selector(hdf_map)
        if names:
            self.x_axis.set(', '.join(name for name in names))

    def browse_y_axis(self):
        from ..apps.namespace_select import create_scannable_selector
        scan_file = next(iter(self.range.generate_scan_files().values()), get_first_file(self.exp_folder.get()))
        hdf_map = hdfmap.create_nexus_map(scan_file)
        names = create_scannable_selector(hdf_map)
        if names:
            self.y_axis.set(', '.join(name for name in names))

    def browse_metadata(self):
        from ..apps.namespace_select import create_metadata_selector
        scan_file = next(iter(self.range.generate_scan_files().values()), get_first_file(self.exp_folder.get()))
        hdf_map = hdfmap.create_nexus_map(scan_file)
        paths = create_metadata_selector(hdf_map)
        if paths:
            self.metadata_name.set(', '.join(path for path in paths))

    def get_experiment(self):
        return Experiment(self.exp_folder.get(), instrument=self.config.get('beamline', None))

    def plot(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        exp.plot.multi_lines(*scan_numbers, xaxis=xaxis, yaxis=yaxis, values=values)

    def plot2d(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        exp.plot.surface_2d(*scan_numbers, xaxis=xaxis, yaxis=yaxis, values=values)

    def plot3d(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        exp.plot.lines_3d(*scan_numbers, xaxis=xaxis, yaxis=yaxis, values=values)



