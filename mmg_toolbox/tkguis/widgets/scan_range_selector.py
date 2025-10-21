"""
widget for selecting scan numbers and s
"""

import os
import tkinter as tk
from tkinter import ttk

from mmg_toolbox.utils.env_functions import (get_scan_numbers, get_last_scan_number, get_first_file)
from mmg_toolbox.utils.file_functions import get_scan_number, replace_scan_number
from ..misc.logging import create_logger
from ..misc.config import get_config

logger = create_logger(__file__)


class ScanRangeSelector:
    """Frame with """

    def __init__(self, root: tk.Misc, initial_directory: str | None = None, config: dict | None = None):
        logger.info('Creating ScanRangeSelector')
        self.root = root
        self.config = get_config() if config is None else config

        # variables
        self.exp_folder = tk.StringVar(self.root, initial_directory)
        self.save_folder = tk.StringVar(self.root, '')
        self.number_start = tk.StringVar(self.root, '-10')
        self.number_end = tk.StringVar(self.root, '-1')
        self.number_step = tk.IntVar(self.root, 1)
        self.metadata_name = tk.StringVar(self.root, '')
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
        ttk.Button(frm, text='Select Files', command=self.select_files).pack(side=tk.RIGHT, padx=4)

        # Text box
        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        ttk.Label(frm, text='Scans = ').pack(side=tk.LEFT, padx=2)
        self.text = tk.Text(frm, wrap=tk.WORD, width=65, height=5)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        var = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        self.text.configure(yscrollcommand=var.set)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
        ttk.Button(frm, text='Check', command=self.show_metadata).pack()

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
        if exp_folder and (first < 1 or last < 1):
            last_scan = get_last_scan_number(exp_folder)
            if first < 1:
                first = last_scan + first
            if last < 1:
                last = last_scan + last
            # numbers = get_scan_numbers(exp_folder)
            # if first < numbers[0] and last < numbers[0]:
            #     scan_range = [numbers[idx] for idx in range(first, last+1, step)]

        scan_range = list(range(first, last+1, step))
        self.text.replace("1.0", tk.END, str(scan_range))

    def generate_scan_numbers(self) -> list[int]:
        scan_text = self.text.get("1.0", tk.END)
        scan_numbers = eval(scan_text)
        return scan_numbers

    def numbers2files(self, scan_numbers: list[int]) -> list[str]:
        exp_folder = self.exp_folder.get()
        scan_file_template = get_first_file(exp_folder)
        scan_files = (replace_scan_number(scan_file_template, number) for number in scan_numbers)
        return [file for file in scan_files if os.path.isfile(file)]

    def generate_scan_files(self) -> list[str]:
        scan_numbers = self.generate_scan_numbers()
        return self.numbers2files(scan_numbers)

    def select_files(self):
        from ..apps.scans import select_scans
        files = select_scans(self.exp_folder.get(), self.root, self.config)
        if files:
            numbers = [get_scan_number(file) for file in files]
            self.text.replace("1.0", tk.END, str(numbers))

    def show_metadata(self):
        from ..apps.scans import list_scans
        metadata_list = self.metadata_name.get().split(',')
        file_list = self.generate_scan_files()
        list_scans(*file_list, parent=self.root, config=self.config, metadata_list=metadata_list)
