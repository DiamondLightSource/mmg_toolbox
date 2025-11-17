"""
tkinter widget to find scans
"""

import tkinter as tk
from tkinter import ttk
import hdfmap

from mmg_toolbox.utils.experiment import Experiment
from ..misc.config import C


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
        self.hdf_map = hdfmap.create_nexus_map(scan_file)
        self.scan_numbers = []
        self.vars = []
        metadata_list = metadata_list or []
        self.add_vars(*metadata_list)

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

        if self.vars:
            for var_name, var_val, var_tol in self.vars:
                self.add_var_line(var_name, var_val, var_tol)
        else:
            self.new_var()

        sec = ttk.Frame(self.var_sec)
        sec.pack(side=tk.BOTTOM, fill=tk.X, padx=2, pady=5)
        ttk.Button(sec, text='Add', command=self.new_var).pack()

        sec = ttk.Frame(window)
        sec.pack(side=tk.BOTTOM, fill=tk.X, padx=2, pady=5)
        ttk.Button(sec, text='Find Scans', command=self.find_scans).pack(side=tk.LEFT, padx=3)
        ttk.Button(sec, text='Close', command=self.close_fun).pack(side=tk.LEFT, padx=3)

    def add_vars(self, *metadata_names: str):
        with hdfmap.load_hdf(self.scan_file) as hdf:
            self.vars += [
                # field_name/expression, match, tolerance
                (
                    tk.StringVar(self.root, name),
                    tk.StringVar(self.root, self.hdf_map.eval(hdf, name) if name else ''),
                    tk.StringVar(self.root, '')
                ) for name in metadata_names
            ]

    def add_var_line(self, var_name: tk.StringVar, var_val: tk.StringVar, var_tol: tk.StringVar):
        def update_val(_event=None):
            if var_name.get():
                var_val.set(self.hdf_map.eval(self.hdf_map.load_hdf(), var_name.get()))

        def remove():
            var_name.set('')
            var_val.set('')
            var_tol.set('')

        line = ttk.Frame(self.var_sec)
        line.pack(side=tk.TOP, fill=tk.X, padx=2, pady=3)
        var = ttk.Entry(line, textvariable=var_name, width=20)
        var.pack(side=tk.LEFT, padx=5)
        var.bind('<Return>', update_val)
        ttk.Entry(line, textvariable=var_val, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Entry(line, textvariable=var_tol, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(line, text='X', command=remove, width=1).pack(side=tk.LEFT, padx=5)

    def new_var(self):
        self.add_vars('')
        var_name, var_val, var_tol = self.vars[-1]
        self.add_var_line(var_name, var_val, var_tol)

    def get_parameters(self) -> dict[str, str | float | tuple[float, float]]:
        pars = {}
        for var_name, var_val, var_tol in self.vars:
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
        return pars

    def find_scans(self):
        pars = self.get_parameters()
        print('find parameters:', pars)
        scans = self.exp.find_scans(hdf_map=self.hdf_map, **pars)
        self.scan_numbers = [scan.scan_number for scan in scans]
        print('found scans numbers', self.scan_numbers)
        self.close_fun()

    def show(self):
        self.root.wait_window()
        return self.scan_numbers
