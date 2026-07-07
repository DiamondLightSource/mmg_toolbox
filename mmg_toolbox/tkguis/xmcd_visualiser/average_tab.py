"""
a tkinter frame with 3 sections:
    1. scan choice, scan pairs + options
    2. Grid of pair-subtraction-plots with checkboxes
    3. average of selected pairs
"""
import os
import tkinter as tk
from tkinter import ttk

from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.xas import SpectraContainerSubtraction, SpectraContainer, average_scans

from ..misc.logging import create_logger
from ..misc.config import C
from .widget import XMCDVisualiser

logger = create_logger(__file__)

class Average:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        from .average_plot import AveragePlot
        from .grid_plot import GridPlot
        from .pair_selector import PairSelector
        self._base = base
        self.root = root
        self.use_dls_loader = False
        instrument = self._base.config.get(C.beamline, None)
        data_directory = self._base.config.get(C.current_dir, '')
        self.exp = Experiment(data_directory, instrument=instrument)
        self.pair_numbers: list[tuple[int, int]] = []
        self.pairs: list[tuple[SpectraContainer, SpectraContainer]] = []
        self.selection: list[tk.BooleanVar] = []

        # Average Tab
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')
        
        tab = ttk.Frame(self.root)
        tab.grid(column=0, row=0, **grid_options)
        tab.columnconfigure(0, weight=0)  # set window resize properties
        tab.columnconfigure(1, weight=1)  # only resize middle panel
        tab.columnconfigure(2, weight=0)
        tab.rowconfigure(0, weight=1)

        # LEFT
        frm = ttk.LabelFrame(tab, text='Files')
        frm.grid(column=0, row=0, **grid_options)
        self.pair_selector = PairSelector(frm, self)

        # MIDDLE
        frm = ttk.LabelFrame(tab, text='Select Plots')
        frm.grid(column=1, row=0, **grid_options)
        self.grid_plots = GridPlot(frm, self._base.config)

        # RIGHT
        frm = ttk.LabelFrame(tab, text='Average Data')
        frm.grid(column=2, row=0, **grid_options)
        self.average_plot = AveragePlot(frm, self, self._base.config)

    def add_exp_path(self, filename: str):
        if os.path.isfile(filename):
            filename = os.path.dirname(filename)
        self.exp.add_data_paths(filename)

    def load_scans(self, *scan_number: int, dls_loader: bool | None = None) -> list[SpectraContainer]:
        return self.exp.load_xas(*scan_number, dls_loader=self.use_dls_loader if dls_loader is None else dls_loader)

    def load_pair(self, scan_number1: int, scan_number2: int, dls_loader: bool | None = None) -> tuple[SpectraContainer, SpectraContainer]:
        dls_loader = self.use_dls_loader if dls_loader is None else dls_loader
        s1, s2 = self.exp.load_xas(scan_number1, scan_number2, dls_loader=dls_loader)
        return s1, s2

    def process_pair(self, scan_number1: int, scan_number2: int,
                     background: str) -> tuple[SpectraContainer, SpectraContainer]:
        scan1, scan2 = self.load_pair(scan_number1, scan_number2)
        scan1_proc = scan1.divide_by_preedge()
        scan2_proc = scan2.divide_by_preedge()
        if background != 'None':
            scan1_proc = scan1_proc.remove_background(background)
            scan2_proc = scan2_proc.remove_background(background)
        return scan1_proc, scan2_proc

    def _update_pair_numbers(self):
        self.pair_numbers = self.pair_selector.get_pair_numbers()
        self.selection = [tk.BooleanVar(self.root, True) for _ in self.pair_numbers]

    def _update_pairs(self):
        background = self.pair_selector.bkg_option.get()
        self.pairs = [self.process_pair(s1, s2, background) for s1, s2 in self.pair_numbers]

    def plot_pairs(self, event=None):
        self._update_pair_numbers()
        self._update_pairs()
        mode = self.pair_selector.mode_option.get()
        if self.pairs:
            self.grid_plots.clear_plots()
            spectra_check = [(s1 - s2, check) for (s1, s2), check in zip(self.pairs, self.selection)]
            self.grid_plots.create_grid(*spectra_check, mode=mode, command=self.plot_average)
            self.plot_average()

    def plot_average(self, event=None):
        mode = self.pair_selector.mode_option.get()
        if self.pairs:
            s1 = average_scans(*[s1 for (s1, s2), check in zip(self.pairs, self.selection) if check.get()])
            s2 = average_scans(*[s2 for (s1, s2), check in zip(self.pairs, self.selection) if check.get()])
            spectra = s1 - s2
            self.average_plot.update_plot(spectra, mode=mode)
            self._base.sum_rules.update_plot(spectra, mode=mode)

    def update_plots(self, event=None):
        self._update_pairs()
        mode = self.pair_selector.mode_option.get()
        if self.pairs:
            spectra = [s1 - s2 for (s1, s2), check in zip(self.pairs, self.selection)]
            self.grid_plots.update_plots(*spectra, mode=mode)
            self.plot_average()

    def add_comparison_spectra(self, spectra: SpectraContainerSubtraction):
        self._base.comparison.treeview.add_scan(spectra)

