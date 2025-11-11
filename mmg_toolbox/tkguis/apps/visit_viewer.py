
from tkinter import ttk

from mmg_toolbox.utils.env_functions import MMG_BEAMLINES
from ..misc.config import get_config
from ..misc.styles import create_root


def create_visit_viewer(config: dict | None = None):
    """Visit Viewer"""
    from ..widgets.instrument_visits import InstrumentVisits

    root = create_root(window_title='DLS Visits')
    config = config or get_config()

    visit_widgets = []
    for row in range(2):
        for col in range(4):
            index = (row * 4) + col
            if index >= len(MMG_BEAMLINES):
                break
            beamline = MMG_BEAMLINES[index]
            frame = ttk.Frame(root)
            frame.grid(row=row, column=col, padx=5, pady=5)
            visit_widgets.append(InstrumentVisits(frame, beamline, config))

    root.mainloop()
    return root
