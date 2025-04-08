"""
a tkinter frame
"""
import os
import tkinter as tk
from tkinter import ttk

from ...env_functions import get_dls_visits
from ..misc.logging import create_logger
from ..misc.config import get_config
from ..misc.functions import select_folder

logger = create_logger(__file__)


class TitleWindow:
    def __init__(self, root: tk.Misc, config: dict | None = None):
        self.root = root
        self.config = get_config() if config is None else config

        self.beamline = self.config.get('beamline', 'i16')
        self.visits = get_dls_visits(self.beamline)
        self.visits.update({'default': self.config.get('default_directory', '.')})
        current_visit = next(iter(self.visits))
        self.visit = tk.StringVar(self.root, current_visit)
        self.data_dir = tk.StringVar(self.root, self.visits[current_visit])
        self.proc_dir = tk.StringVar(self.root, self.visits[current_visit])
        self.notebook_dir = tk.StringVar(self.root, self.visits[current_visit])
        self.dls_directories(self.visits[current_visit])

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        ttk.Label(frm, text=self.beamline, style="Red.TLabel").pack()

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES)
        ttk.Label(frm, text='Visit:').pack(side=tk.LEFT, padx=4)
        ttk.OptionMenu(frm, self.visit, *list(self.visits.keys()),
                       command=self.choose_visit).pack(side=tk.LEFT, padx=4)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Data Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.data_dir, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_datadir).pack(side=tk.LEFT)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Analysis Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.proc_dir, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_analysis).pack(side=tk.LEFT)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, padx=4)
        ttk.Label(frm, text='Notebook Dir:', width=15).pack(side=tk.LEFT, padx=4)
        ttk.Entry(frm, textvariable=self.notebook_dir, width=60).pack(side=tk.LEFT)
        ttk.Button(frm, text='Browse', command=self.browse_notebook).pack(side=tk.LEFT)

        frm = ttk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, pady=6)
        ttk.Button(frm, text='Data Viewer', command=self.open_data_viewer, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text='NeXus Browser', command=self.open_file_browser, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text='Notebook Browser', command=self.open_notebook_browser, width=20).pack(side=tk.LEFT)
        ttk.Button(frm, text='Script Runner', command=self.open_script_runner, width=20).pack(side=tk.LEFT)

    def dls_directories(self, data_dir: str):
        proc_dir = os.path.join(data_dir, 'processing')
        notebook_dir = os.path.join(data_dir, 'processed', 'notebooks')
        if os.path.isdir(proc_dir):
            self.proc_dir.set(proc_dir)
        if os.path.isdir(notebook_dir):
            self.notebook_dir.set(notebook_dir)

    def choose_visit(self, event=None):
        visit_folder = self.visits[self.visit.get()]
        self.data_dir.set(visit_folder)
        self.dls_directories(visit_folder)

    def browse_datadir(self):
        folder = select_folder(self.root)
        if folder:
            self.data_dir.set(folder)
            self.dls_directories(folder)

    def browse_analysis(self):
        folder = select_folder(self.root)
        if folder:
            self.proc_dir.set(folder)

    def browse_notebook(self):
        folder = select_folder(self.root)
        if folder:
            self.notebook_dir.set(folder)

    def open_data_viewer(self):
        from ..main import create_data_viewer
        create_data_viewer(self.data_dir.get(), self.root, self.config)

    def open_file_browser(self):
        from ..main import create_file_browser
        create_file_browser(self.root, self.data_dir.get())

    def open_notebook_browser(self):
        from ..main import create_jupyter_browser
        create_jupyter_browser(self.root, self.notebook_dir.get())

    def open_script_runner(self):
        from ..main import create_script_runner
        folders = {
            'default_directory': self.data_dir.get(),
            'processing_directory': self.proc_dir.get(),
            'notebook_directory': self.notebook_dir.get(),
        }
        self.config.update(folders)
        create_script_runner(self.root, self.config)




