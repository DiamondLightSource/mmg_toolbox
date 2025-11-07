"""
widget for selecting scan numbers and s
"""

import tkinter as tk
from tkinter import ttk
import asteval

from mmg_toolbox.utils.env_functions import (get_scan_numbers, scan_number_mapping)
from mmg_toolbox.utils.file_functions import get_scan_number
from ..misc.logging import create_logger
from ..misc.config import get_config

logger = create_logger(__file__)


class ScanRangeSelector:
    """Frame with """

    def __init__(self, root: tk.Misc, initial_directory: str | None = None, config: dict | None = None):
        logger.info('Creating ScanRangeSelector')
        self.root = root
        self.config = config or get_config()

        # variables
        self.exp_folder = tk.StringVar(self.root, initial_directory)
        self.number_start = tk.StringVar(self.root, '-10')
        self.number_end = tk.StringVar(self.root, '-1')
        self.number_step = tk.IntVar(self.root, 1)
        self.file_list = []

        # Range selection
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

        ttk.Label(frm, text='First:').pack(side=tk.LEFT, padx=2)
        var = ttk.Entry(frm, textvariable=self.number_start, width=8)
        var.pack(side=tk.LEFT, padx=2)
        var.bind("<Return>", self.update_numbers)
        ttk.Label(frm, text='Last:').pack(side=tk.LEFT, padx=2)
        var = ttk.Entry(frm, textvariable=self.number_end, width=8)
        var.pack(side=tk.LEFT, padx=2)
        var.bind("<Return>", self.update_numbers)
        ttk.Label(frm, text='Step:').pack(side=tk.LEFT, padx=2)
        var = ttk.Entry(frm, textvariable=self.number_step, width=4)
        var.pack(side=tk.LEFT, padx=2)
        var.bind("<Return>", self.update_numbers)
        ttk.Button(frm, text='Get numbers', command=self.numbers_from_exp).pack(side=tk.LEFT)
        ttk.Button(frm, text='Generate', command=self.update_numbers).pack(side=tk.LEFT, padx=4)
        ttk.Button(frm, text='Select Files', command=self.select_files).pack(side=tk.LEFT, padx=4)

        # Text box
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        ttk.Label(frm, text='Scans = ').pack(side=tk.LEFT, padx=2)
        self.text = tk.Text(frm, wrap=tk.WORD, width=65, height=5)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        var = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        self.text.configure(yscrollcommand=var.set)
        ttk.Button(frm, text='Check', command=self.show_metadata).pack(side=tk.LEFT, fill=tk.Y)

    def numbers_from_exp(self):
        exp_folder = self.exp_folder.get()
        if exp_folder:
            numbers = get_scan_numbers(exp_folder)
            self.number_start.set(str(numbers[0]))
            self.number_end.set(str(numbers[-1]))

    def update_numbers(self, event=None):
        first = eval(self.number_start.get())
        last = eval(self.number_end.get())
        step = self.number_step.get()

        if (last - first) / step > 1000:
            raise IOError('Range is too large')

        exp_folder = self.exp_folder.get()
        if not exp_folder:
            return
        scan_numbers = get_scan_numbers(exp_folder)
        if first < 1 or last < 1:
            last_scan = scan_numbers[-1]
            if first < 1:
                first = last_scan + first
            if last < 1:
                last = last_scan + last

        scan_range = [n for n in range(first, last+1, step) if n in scan_numbers]
        self.text.replace("1.0", tk.END, str(scan_range))

    def generate_scan_numbers(self) -> list[int]:
        scan_text = self.text.get("1.0", tk.END)
        if not scan_text.strip():
            return []
        safe_eval = asteval.Interpreter(use_numpy=True)
        scan_numbers = safe_eval(scan_text)
        return scan_numbers

    def generate_scan_files(self) -> dict[int, str]:
        scan_numbers = self.generate_scan_numbers()
        scan_files = scan_number_mapping(self.exp_folder.get())
        return {number: scan_files[number] for number in scan_numbers if number in scan_files}

    def select_files(self):
        from ..apps.scans import list_scans
        file_list = list_scans(self.exp_folder.get())
        files = list_scans(*file_list, parent=self.root, config=self.config, button_name='Select')
        if files:
            numbers = [get_scan_number(file) for file in files]
            self.text.replace("1.0", tk.END, str(numbers))

    def show_metadata(self):
        from ..apps.scans import list_scans
        file_list = self.generate_scan_files().values()
        if len(file_list) == 0:
            return
        list_scans(*file_list, parent=self.root, config=self.config)
