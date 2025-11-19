"""
tkinter widget to find scans
"""

import tkinter as tk
from tkinter import ttk
import hdfmap

from mmg_toolbox.utils.experiment import Experiment
from ..misc.config import C
from ..misc.logging import create_logger
from ..apps.namespace_select import create_metadata_selector

logger = create_logger(__file__)


class FindScans:
    """
    tkinter frame to find scans
    """
    def __init__(self, root: tk.Misc, exp_folder: str, config: dict, scan_file: str | None = None,
                 metadata_list: list[str] | None = None, close_fun=None):
        self.root = root
        self.close_fun = root.destroy if close_fun is None else close_fun
        self.exp = Experiment(exp_folder, instrument=config.get(C.beamline, None))
        self.scan_file = scan_file or self.exp.get_scan_filename(-1)
        self.hdf_map = hdfmap.create_nexus_map(self.scan_file)
        self.scan_numbers = []
        self.vars: list[tuple[tk.StringVar, tk.StringVar, tk.StringVar, tk.StringVar]] = []
        self.return_on_first = False
        metadata_list = metadata_list or []

        window = tk.Frame(self.root)
        window.pack(fill=tk.BOTH, expand=tk.YES, padx=2, pady=2)

        ttk.Label(window, text='Find Scans', style='subtitle.TLabel').pack(side=tk.TOP, pady=5)
        self.var_sec = ttk.Frame(window, relief=tk.RIDGE, borderwidth=2)
        self.var_sec.pack(side=tk.TOP, fill=tk.BOTH, padx=2, pady=2)

        line = ttk.Frame(self.var_sec)
        line.pack(side=tk.TOP, fill=tk.X, padx=2, pady=3)
        ttk.Label(line, text='Name / expression', width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(line, text='Value', width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(line, text='Tolerance', width=10).pack(side=tk.LEFT, padx=2)

        self.add_vars(*metadata_list)

        sec = ttk.Frame(self.var_sec)
        sec.pack(side=tk.BOTTOM, fill=tk.X, padx=2, pady=5)
        ttk.Button(sec, text='Add', command=self.add_vars).pack()

        sec = ttk.Frame(window)
        sec.pack(side=tk.BOTTOM, fill=tk.X, padx=2, pady=5)
        ttk.Button(sec, text='Find Scans', command=self.find_scans).pack(side=tk.LEFT, padx=3)
        ttk.Button(sec, text='Close', command=self.close_fun).pack(side=tk.LEFT, padx=3)

    def add_vars(self, *metadata_names: str):
        metadata_names = metadata_names + ('', )
        for name in metadata_names:
            var_name = tk.StringVar(self.root, name)
            var_lab = tk.StringVar(self.root, '')
            var_val = tk.StringVar(self.root, '')
            var_tol = tk.StringVar(self.root, '')
            self.vars.append((var_name, var_lab, var_val, var_tol))
            self.add_var_line(var_name, var_lab, var_val, var_tol)

    def add_var_line(self, var_name: tk.StringVar, var_lab: tk.StringVar,
                     var_val: tk.StringVar, var_tol: tk.StringVar):
        def update_val(_event=None):
            if var_name.get():
                val = self.hdf_map.eval(self.hdf_map.load_hdf(), var_name.get())
                var_val.set(val)
                if isinstance(val, str):
                    var_lab.set('contains')
                    var_tol.set('--')
                else:
                    var_lab.set('~=')
                    var_tol.set('1.0')

        def select():
            metadata = create_metadata_selector(self.hdf_map, self.root)
            if metadata:
                var_name.set(metadata[0])
                update_val()

        def remove():
            var_name.set('')
            var_val.set('')
            var_tol.set('')

        line = ttk.Frame(self.var_sec)
        line.pack(side=tk.TOP, fill=tk.X, padx=2, pady=3)
        ttk.Button(line, text=':', width=1, command=select).pack(side=tk.LEFT)
        var = ttk.Entry(line, textvariable=var_name, width=20)
        var.pack(side=tk.LEFT, padx=5)
        var.bind('<Return>', update_val)
        ttk.Label(line, textvariable=var_lab, width=10, anchor=tk.E).pack(side=tk.LEFT, padx=2)
        ttk.Entry(line, textvariable=var_val, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(line, text='+/-').pack(side=tk.LEFT)
        ttk.Entry(line, textvariable=var_tol, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(line, text='X', command=remove, width=1).pack(side=tk.LEFT, padx=5)
        update_val()

    def get_parameters(self) -> dict[str, str | float | tuple[float, float]]:
        pars = {}
        for var_name, var_lab, var_val, var_tol in self.vars:
            name = var_name.get()
            if name:
                value = var_val.get()
                tol = var_tol.get()
                try:
                    value = float(value)
                except ValueError:
                    pass
                try:
                    tol = float(tol)
                except ValueError:
                    tol = None
                if tol:
                    pars[name] = (value, tol)
                else:
                    pars[name] = value
        logger.debug(f"FindScans parameters: {pars}")
        return pars

    def find_scans(self):
        pars = self.get_parameters()
        scans = self.exp.find_scans(hdf_map=self.hdf_map, first_only=self.return_on_first, **pars)
        self.scan_numbers = [scan.scan_number() for scan in scans]
        logger.debug(f"found scan numbers: {self.scan_numbers}")
        self.close_fun()

    def wait_for_numbers(self) -> list[int]:
        self.root.wait_window()
        logger.debug('Returning scan numbers')
        return self.scan_numbers

    def wait_for_number(self) -> list[int]:
        self.return_on_first = True
        self.root.wait_window()
        logger.debug('Returning first scan number')
        return self.scan_numbers

    def wait_for_files(self) -> dict[int, str]:
        self.root.wait_window()
        logger.debug('Returning scan files')
        return {n: self.exp.scan_list[n] for n in self.scan_numbers}
