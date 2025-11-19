"""
widget for running scripts
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt

import hdfmap

from mmg_toolbox import Experiment
from mmg_toolbox.scripts import NOTEBOOKS, SCRIPTS, R
from mmg_toolbox.utils.env_functions import get_first_file, get_processing_directory
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from ..misc.functions import select_folder
from ..misc.processing_options import create_script_from_template, create_notebook_from_template
from ..widgets.scan_range_selector import ScanRangeSelector

logger = create_logger(__file__)


class MultiScanAnalysis:
    """Frame with scan number generation and buttons for plotting and processing options"""

    def __init__(self, root: tk.Misc, config: dict | None = None, exp_directory: str | None = None,
                 proc_directory: str | None = None, scan_numbers: list[int] | None = None,
                 metadata: str | None = None, x_axis: str | None = None, y_axis: str | None = None):
        logger.info('Creating ScriptRunner')
        self.root = root
        self.config = config or get_config()

        if exp_directory is None:
            exp_directory = self.config.get(C.current_dir, '')
        if proc_directory is None:
            proc_directory = self.config.get(C.current_proc, get_processing_directory(exp_directory))

        self.exp_folder = tk.StringVar(root, exp_directory)
        self.proc_folder = tk.StringVar(root, proc_directory)
        self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.x_axis = tk.StringVar(self.root, 'axes' if x_axis is None else x_axis)
        self.y_axis = tk.StringVar(self.root, 'signal' if y_axis is None else y_axis)
        self.metadata_name = tk.StringVar(self.root, metadata or config.get(C.default_metadata, ''))
        self.script_name = tk.StringVar(root, 'example')
        self.script_desc = tk.StringVar(root, '')
        self.options = {}
        self.file_list = []

        # sec = ttk.LabelFrame(self.root, text='Folders')
        # sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)
        #
        # frm = ttk.Frame(sec)
        # frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # ttk.Label(frm, text='Data Dir:', width=15).pack(side=tk.LEFT, padx=4)
        # ttk.Entry(frm, textvariable=self.exp_folder, width=60).pack(side=tk.LEFT)
        # ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side=tk.LEFT)
        #
        # frm = ttk.Frame(sec)
        # frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        # ttk.Label(frm, text='Analysis Dir:', width=15).pack(side=tk.LEFT, padx=4)
        # ttk.Entry(frm, textvariable=self.proc_folder, width=60).pack(side=tk.LEFT)
        # ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side=tk.LEFT)

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

        self.range = ScanRangeSelector(sec, exp_directory, self.config, metadata_getter=self.metadata_name)
        self.range.exp_folder.set(exp_directory)
        if scan_numbers is not None:
            self.range.text.insert("1.0", str(scan_numbers))

        line = ttk.Frame(self.root)
        line.pack(side=tk.TOP, expand=tk.YES, pady=8, padx=4)
        ttk.Button(line, text='Plot', command=self.plot_legend, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot lines', command=self.plot_lines, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot Meta', command=self.plot_metadata, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Multi-Plot', command=self.multiplot, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot 2D', command=self.plot2d, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot 3D', command=self.plot3d, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Plot Surf', command=self.plot3d, width=10).pack(side=tk.LEFT)

        line = ttk.Frame(self.root)
        line.pack(side=tk.TOP, expand=tk.YES, pady=8, padx=4)
        ttk.Button(line, text='Fits', command=self.fitting, width=10).pack(side=tk.LEFT)
        ttk.Button(line, text='Convert to dat', command=self.convert2dat).pack(side=tk.LEFT)

        # Scripts
        script_names = ('Scripts:',) + tuple(SCRIPTS) + ('Notebooks:',) + tuple(NOTEBOOKS)
        self.scripts = {f"{n:2} {name}": name for n, name in enumerate(script_names)}
        ttk.Button(line, text='Create', command=self.script_create).pack(side=tk.LEFT, padx=(20, 0))
        var = ttk.OptionMenu(line, self.script_name, 'Script', *self.scripts,
                             command=self.script_select)
        var.pack(side=tk.LEFT, padx=4)
        ttk.Label(line, textvariable=self.script_desc).pack(side=tk.LEFT)

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

    def fitting(self):
        from ..apps.peak_fit_analysis import create_peak_fit
        scan_numbers = self.range.generate_scan_numbers()
        create_peak_fit(
            parent=self.root,
            config=self.config,
            exp_directory=self.exp_folder.get(),
            proc_directory=self.proc_folder.get(),
            scan_numbers=scan_numbers,
            metadata=self.metadata_name.get(),
            x_axis=self.x_axis.get(),
            y_axis=self.y_axis.get()
        )

    def convert2dat(self):
        from nexus2srs import run_nexus2srs
        scan_files = self.range.generate_scan_files()
        answer = messagebox.askokcancel(
            title='Nexus2SRS',
            message=f'Convert {len(scan_files)} NeXus files to .dat format?',
            icon='warning',
            parent=self.root
        )
        if answer:
            run_nexus2srs('-tiff', *scan_files.values())
            messagebox.showinfo(
                title='Nexus2SRS',
                message='Conversion complete!',
                parent=self.root
            )

    def plot_legend(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        exp.plot.plot(*scan_numbers, xaxis=xaxis, yaxis=yaxis)
        plt.show()

    def plot_lines(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        exp.plot.multi_lines(*scan_numbers, xaxis=xaxis, yaxis=yaxis, value=values)
        plt.show()

    def plot2d(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        values = values if values else None
        exp.plot.surface_2d(*scan_numbers, xaxis=xaxis, signal=yaxis, values=values)
        plt.show()

    def plot3d(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        values = values if values else None
        exp.plot.lines_3d(*scan_numbers, xaxis=xaxis, signal=yaxis, values=values)
        plt.show()

    def plot_surf(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        values = values if values else None
        exp.plot.surface_3d(*scan_numbers, xaxis=xaxis, signal=yaxis, values=values)
        plt.show()

    def multiplot(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        xaxis = self.x_axis.get()
        yaxis = self.y_axis.get()
        values = self.metadata_name.get()
        values = values if values else None
        exp.plot.multi_plot(*scan_numbers, xaxis=xaxis, yaxis=yaxis, value=values)
        plt.show()

    def plot_metadata(self):
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        values = self.metadata_name.get().split(',')
        exp.plot.metadata(*scan_numbers, values=values)
        plt.show()

    def script_select(self, _event=None):
        script_label = self.script_name.get()
        script_index = int(script_label.split()[0])
        notebook_index = next(n for n, lab in enumerate(self.scripts.values()) if 'Notebooks:' in lab)
        script = self.scripts[script_label]
        if script_index < notebook_index and script in SCRIPTS:
            _, desc = SCRIPTS[script]
            desc = 'Script: ' + desc
            self.script_desc.set(desc)
        elif script in NOTEBOOKS:
            _, desc = NOTEBOOKS[script]
            desc = 'Notebook: ' + desc
            self.script_desc.set(desc)
        else:
            self.script_desc.set('')

    def script_create(self, _event=None):
        proc = self.proc_folder.get()
        script_name = self.script_name.get()
        if script_name not in self.scripts:
            return
        script = self.scripts[self.script_name.get()]
        exp = self.get_experiment()
        scan_numbers = self.range.generate_scan_numbers()
        if not scan_numbers:
            return
        scan_files = self.range.generate_scan_files()
        values = self.metadata_name.get().split(',')
        value = values[0] if values else None
        first_scan, = exp.scans(scan_numbers[0])

        replacements = {
            R.exp: self.exp_folder.get(),
            R.filepaths: '\n'.join(f"    '{f}'," for f in scan_files.values()),
            R.beamline: self.config.get(C.beamline, ''),
            R.scannos: str(scan_numbers),
            R.title: exp.generate_scans_title(*scan_numbers, metadata_str=value, hdf_map=first_scan.map),
            R.description: 'Created by  MultiScanAnalysis',
            R.xaxis: self.x_axis.get(),
            R.yaxis: self.y_axis.get(),
            R.value: self.metadata_name.get(),
        }

        if script in SCRIPTS:
            create_script_from_template(self.root, script, proc, self.config, **replacements)
        elif script in NOTEBOOKS:
            create_notebook_from_template(self.root, script, proc, self.config, **replacements)

