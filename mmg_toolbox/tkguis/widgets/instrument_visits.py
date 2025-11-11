"""
tk widgets shows recent vists for beamlines
"""

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone
from threading import Thread


from mmg_toolbox.utils.env_functions import get_notebook_directory, get_dls_visits, scan_number_mapping
from ..apps.data_viewer import create_data_viewer
from ..misc.logging import create_logger
from ..misc.config import get_config

logger = create_logger(__file__)


def visit_frame(parent: tk.Misc, visit: str, scans: dict[int, str], notebooks: dict[int, str], command: () = None):

    ttk.Button(parent, text=visit, width=12, command=command).pack(side="left", padx=5)

    frm = ttk.Frame(parent)
    frm.pack(side="left", fill="y", expand=True)

    if len(scans) > 0:
        last_scan_number = list(scans)[-1]
        last_scan_path = list(scans.values())[-1]
        last_scan_time = datetime.fromtimestamp(os.path.getmtime(last_scan_path), tz=timezone.utc)
        last_scan = f", #{last_scan_number:<8} ({last_scan_time:%Y-%m-%d %H:%M})"
    else:
        last_scan = ""
    scan_str = f"Scans: {len(scans):4}{last_scan}"
    ttk.Label(frm, text=scan_str).pack(side="top", fill="x", padx=5)

    if len(notebooks) > 0:
        last_notebook_number = list(notebooks)[-1]
        last_notebook_path = list(notebooks.values())[-1]
        last_notebook_time = datetime.fromtimestamp(os.path.getmtime(last_notebook_path), tz=timezone.utc)
        last_notebook = f", #{last_notebook_number:<8} ({last_notebook_time:%Y-%m-%d %H:%M})"
    else:
        last_notebook = ""
    nb_str = f"Notebooks: {len(notebooks):4}{last_notebook}"
    ttk.Label(frm, text=nb_str).pack(side="top", fill="x", padx=5)


class InstrumentVisits:
    def __init__(self, parent: tk.Misc, instrument: str, config: dict | None = None):
        self.root = parent
        self.config = config or get_config()
        self.instrument = instrument
        self.visits = get_dls_visits(instrument)
        self.last_visits = list(self.visits)[:3]

        self.frame = ttk.Frame(parent, relief="raised", borderwidth=2)
        self.frame.pack(side="top", fill="both", expand=True)
        ttk.Label(self.frame, text=instrument, style="title.TLabel").grid(row=0, column=0, columnspan=3, padx=5, pady=20, sticky="w")

        th = Thread(target=self.populate_visits)
        th.start()

    def populate_visits(self):
        r, c = 0, 0
        for visit, path in self.visits.items():
            cmd = lambda p=path: create_data_viewer(path, self.root, self.config)

            if r < 3:
                scans = scan_number_mapping(path)
                if len(scans) > 0:
                    notebooks = scan_number_mapping(get_notebook_directory(path), extension='.ipynb')
                    line = ttk.Frame(self.frame)
                    line.grid(row=r+1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
                    visit_frame(line, visit, scans, notebooks, cmd)
                    r += 1
            elif r < 5:
                ttk.Button(self.frame, text=visit, width=12, command=cmd).grid(row=r+1, column=c, padx=5, pady=5)
                r += 1 if c == 2 else 0
                c = c + 1 if c < 2 else 0

