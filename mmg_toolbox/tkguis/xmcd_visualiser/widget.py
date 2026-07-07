"""
a tkinter frame with 3 sections:
    1. scan choice, scan pairs + options
    2. Grid of pair-subtraction-plots with checkboxes
    3. average of selected pairs
"""
import tkinter as tk
from tkinter import ttk


from ..misc.logging import create_logger
from ..misc.config import get_config

logger = create_logger(__file__)

# TODO: add tab for sum rule analysis

class XMCDVisualiser:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, scan_range_str: str = None,
                 pairs: list[tuple[int, int]] = None, config: dict | None = None):
        from .average_tab import Average
        from .processed_data_plot import Comparison
        self.root = root
        self.config = config or get_config()

        # Window
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Tabs
        self.view_tabs = ttk.Notebook(self.root)
        tab1 = ttk.Frame(self.view_tabs)
        tab2 = ttk.Frame(self.view_tabs)
        # self.view_tabs.bind('<<NotebookTabChanged>>', self.tab_change)

        self.view_tabs.add(tab1, text='Average Data')
        self.view_tabs.add(tab2, text='Compare Data')

        # Average Tab
        self.average = Average(tab1, self)

        # Comparison Tab
        self.comparison = Comparison(tab2, self)
        self.view_tabs.grid(column=0, row=0, sticky='nsew')

        if scan_range_str:
            self.average.pair_selector.scan_range.set(scan_range_str)
        if pairs:
            self.average.pair_selector.set_pair_numbers(pairs)
            self.average.plot_pairs()
