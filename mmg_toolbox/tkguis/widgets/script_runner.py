"""
widget for running scripts
"""

import os
import tkinter as tk
from tkinter import ttk

import hdfmap

from mmg_toolbox.scripts import scripts
from mmg_toolbox.utils.env_functions import get_first_file, run_python_script
from ..misc.logging import create_logger
from ..misc.config import get_config
from ..misc.functions import select_folder
from ..widgets.scan_range_selector import ScanRangeSelector

logger = create_logger(__file__)


class ScriptRunner:
    """Frame with """

    def __init__(self, root: tk.Misc, config: dict | None = None):
        logger.info('Creating ScriptRunner')
        self.root = root
        self.config = config or get_config()

        exp_directory = self.config.get('default_directory')
        proc_directory = self.config.get('processing_directory')

        self.exp_folder = tk.StringVar(root, exp_directory)
        self.proc_folder = tk.StringVar(root, proc_directory)
        self.script_name = tk.StringVar(root, 'example')
        self.notebook_name = tk.StringVar(root, 'example')
        self.script_desc = tk.StringVar(root, 'blah')
        self.notebook_desc = tk.StringVar(root, 'basd')
        self.output_file = tk.StringVar(root, proc_directory + '/file.py')
        self.metadata_name = tk.StringVar(self.root, '')
        self.options = {}
        self.file_list = []

        sec = ttk.LabelFrame(self.root, text='Folders')
        sec.pack(side='top', fill='both', expand=True, padx=4, pady=4)

        frm = ttk.Frame(sec)
        frm.pack(side='top', fill='x', expand=True, padx=4)
        ttk.Label(frm, text='Data Dir:', width=15).pack(side='left', padx=4)
        ttk.Entry(frm, textvariable=self.exp_folder, width=60).pack(side='left')
        ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side='left')

        frm = ttk.Frame(sec)
        frm.pack(side='top', fill='x', expand=True, padx=4)
        ttk.Label(frm, text='Analysis Dir:', width=15).pack(side='left', padx=4)
        ttk.Entry(frm, textvariable=self.proc_folder, width=60).pack(side='left')
        ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side='left')

        # Metadata selection
        sec = ttk.LabelFrame(self.root, text='Metadata')
        sec.pack(side='top', fill='both', expand=True, padx=4, pady=4)

        frm = ttk.Frame(sec)
        frm.pack(side='top', fill='x', expand=True, padx=4)
        ttk.Label(frm, text='Metadata:', width=15).pack(side='left', padx=4)
        ttk.Entry(frm, textvariable=self.metadata_name, width=60).pack(side='left')
        ttk.Button(frm, text='Choose', command=self.browse_metadata).pack(side='left')

        # Range selection
        sec = ttk.LabelFrame(self.root, text='Scan Numbers')
        sec.pack(side='top', fill='both', expand=True, padx=4, pady=4)

        self.range = ScanRangeSelector(sec, exp_directory, self.config)
        self.range.exp_folder.set(exp_directory)

        # Script Selection
        sec = ttk.LabelFrame(self.root, text='Script')
        sec.pack(side='top', fill='both', expand=True, padx=4, pady=4)

        line = ttk.Frame(sec)
        line.pack(side='top', fill='x', expand=True)
        var = ttk.OptionMenu(line, self.script_name, self.script_name.get(), *scripts.SCRIPTS.keys(),
                             command=self.script_select)
        var.pack(side='left', padx=4)
        ttk.Label(line, textvariable=self.script_desc).pack(side='left')

        sec = ttk.LabelFrame(self.root, text='Notebook')
        sec.pack(side='top', fill='both', expand=True, padx=4, pady=4)
        line = ttk.Frame(sec)
        line.pack(side='top', fill='x', expand=True)
        var = ttk.OptionMenu(line, self.notebook_name, self.notebook_name.get(), *scripts.NOTEBOOKS.keys(),
                             command=self.notebook_select)
        var.pack(side='left', padx=4)
        ttk.Label(line, textvariable=self.notebook_desc).pack(side='left')

        line = ttk.Frame(self.root)
        line.pack(side='top', fill='x', expand=True)
        ttk.Label(line, text='file', width=6).pack(side='left', padx=2)
        ttk.Entry(line, textvariable=self.output_file, width=60).pack(side='left', padx=2)
        ttk.Button(line, text='RUN', command=self.run_template).pack(side='left')
        ttk.Button(line, text='View', command=self.view_script).pack(side='left')

    def browse_metadata(self):
        from ..apps.namespace_select import create_metadata_selector
        scan_file = next(iter(self.range.generate_scan_files().values()), get_first_file(self.exp_folder.get()))
        hdf_map = hdfmap.create_nexus_map(scan_file)
        paths = create_metadata_selector(hdf_map)
        if paths:
            self.metadata_name.set(', '.join(path for path in paths))

    def update_options(self):
        exp_folder = self.exp_folder.get()
        self.range.exp_folder.set(exp_folder)
        scans = self.range.generate_scan_files()
        scan_numbers = list(scans)
        scan_files = scans.values()
        new = {
            # {{template}}: replacement
            'beamline': self.config.get('beamline', ''),
            # 'description': '',
            'filepaths': '\n    '.join(scan_files),
            'experiment_dir': exp_folder,
            'scan_numbers': str(scan_numbers),
            # 'title': 'a nice plot',
            'x-axis': 'axes',
            'y-axis': 'signal',
            'value': self.metadata_name.get()
        }
        self.options.clear()
        self.options.update(new)

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
        if self.range.text.get("1.0", tk.END).strip() == '':
            return
        self.update_options()
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
            run_python_script(output_file)
        else:
            raise Exception('File is not script or notebook')

    def run_script(self, script_file: str):
        pass

    def run_notebook(self, notebook_file: str, *scan_files: str, **options):
        pass

    def view_script(self):
        from ..apps.python_editor import create_python_editor
        create_python_editor(open(self.output_file.get()).read(), parent=self.root, config=self.config)

    def browse_datadir(self):
        folder = select_folder(self.root)
        if folder:
            self.exp_folder.set(folder)

    def browse_analysis(self):
        folder = select_folder(self.root)
        if folder:
            self.proc_folder.set(folder)

