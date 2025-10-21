"""
widget for running scripts
"""

import os
import tkinter as tk
from tkinter import ttk

from ...scripts import scripts
from mmg_toolbox.utils.env_functions import (get_scan_numbers, get_last_scan_number, get_first_file)
from mmg_toolbox.utils.file_functions import get_scan_number, replace_scan_number
from ..misc.logging import create_logger
from ..misc.config import get_config
from ..misc.functions import select_folder

logger = create_logger(__file__)


class ScriptRunner:
    """Frame with """

    def __init__(self, root: tk.Misc, config: dict | None = None):
        logger.info('Creating ScriptRunner')
        self.root = root
        self.config = get_config() if config is None else config

        exp_directory = self.config.get('default_directory')
        proc_directory = self.config.get('processing_directory')

        self.exp_folder = tk.StringVar(root, exp_directory)
        self.proc_folder = tk.StringVar(root, proc_directory)
        self.script_name = tk.StringVar(root, 'example')
        self.notebook_name = tk.StringVar(root, 'example')
        self.script_desc = tk.StringVar(root, 'blah')
        self.notebook_desc = tk.StringVar(root, 'basd')
        self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.number_start = tk.StringVar(self.root, '-10')
        self.number_end = tk.StringVar(self.root, '-1')
        self.number_step = tk.IntVar(self.root, 1)
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

        # Metadata selection
        sec = ttk.LabelFrame(self.root, text='Metadata')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(sec)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Metadata:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.metadata_name, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Choose', command=self.browse_metadata).pack(side=tk.LEFT)

        # Range selection
        sec = ttk.LabelFrame(self.root, text='Scan Numbers')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        frm = ttk.Frame(sec)
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
        frm = ttk.Frame(sec)
        frm.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

        ttk.Label(frm, text='Scans = ').pack(side=tk.LEFT, padx=2)
        self.text = tk.Text(frm, wrap=tk.WORD, width=65, height=5)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        var = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.text.yview)
        var.pack(side=tk.LEFT, fill=tk.Y)
        self.text.configure(yscrollcommand=var.set)
        ttk.Button(frm, text='Check', command=self.show_metadata).pack(side=tk.LEFT, fill=tk.Y)

        # Script Selection
        sec = ttk.LabelFrame(self.root, text='Script')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)

        line = ttk.Frame(sec)
        line.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        var = ttk.OptionMenu(line, self.script_name, *scripts.SCRIPTS.keys(),
                             command=self.script_select)
        var.pack(side=tk.LEFT, padx=4)
        ttk.Label(line, textvariable=self.script_desc).pack(side=tk.LEFT)

        sec = ttk.LabelFrame(self.root, text='Notebook')
        sec.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=4, pady=4)
        line = ttk.Frame(sec)
        line.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        var = ttk.OptionMenu(line, self.notebook_name, *scripts.NOTEBOOKS.keys(),
                             command=self.notebook_select)
        var.pack(side=tk.LEFT, padx=4)
        ttk.Label(line, textvariable=self.notebook_desc).pack(side=tk.LEFT)

        line = ttk.Frame(self.root)
        line.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        ttk.Label(line, text='file', width=10).pack(side=tk.LEFT, padx=2)
        ttk.Entry(line, textvariable=self.output_file, width=60).pack(side=tk.LEFT, padx=2)
        ttk.Button(line, text='RUN', command=self.run_template).pack(side=tk.LEFT)

    def browse_metadata(self):
        pass

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

    def script_select(self, event=None):
        filename, desc = scripts.SCRIPTS[self.script_name.get()]
        self.script_desc.set(desc)
        proc = self.proc_folder.get()
        self.output_file.set(os.path.join(proc, filename))

    def notebook_select(self, event=None):
        filename, desc = scripts.NOTEBOOKS[self.notebook_name.get()]
        self.notebook_desc.set(desc)
        proc = self.proc_folder.get()
        self.output_file.set(os.path.join(proc, filename))

    def run_template(self, event=None):
        output_file = self.output_file.get()
        if output_file.endswith('.ipynb'):
            print(f"Creating notebook file: {output_file}")
            notebook_template = self.notebook_name.get()
            scripts.create_notebook(output_file, notebook_template, **self.options)
            print("Running notebook...")
        elif output_file.endswith('.py'):
            print(f"Creating script file: {output_file}")
            script_template = self.script_name.get()
            scripts.create_script(output_file, script_template, **self.options)
            print(f"Running script...")
        else:
            raise Exception('File is not script or notebook')

    def run_script(self, script_file: str, *scan_files: str, **options):
        pass

    def run_notebook(self, notebook_file: str, *scan_files: str, **options):
        pass

    def browse_datadir(self):
        folder = select_folder(self.root)
        if folder:
            self.exp_folder.set(folder)

    def browse_analysis(self):
        folder = select_folder(self.root)
        if folder:
            self.proc_folder.set(folder)
