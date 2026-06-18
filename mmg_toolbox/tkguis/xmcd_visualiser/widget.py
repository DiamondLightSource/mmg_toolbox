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
from mmg_toolbox.utils.env_functions import get_processing_directory
from mmg_toolbox.xas import SpectraContainer, average_scans

from ..misc.logging import create_logger
from ..misc.config import get_config, C

logger = create_logger(__file__)

# TODO: add tabs
# TODO: add tab for sum rule analysis
# TODO: add tab for plotting multiple processed files

class XMCDVisualiser:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, data_directory: str | None = None,
                 proc_directory: str | None = None,
                 scan_range_str: str = None, pairs: list[tuple[int, int]] = None,
                 config: dict | None = None):
        from .average_plot import AveragePlot
        from .grid_plot import GridPlot
        from .pair_selector import PairSelector
        self.root = root
        self.config = config or get_config()
        self.use_dls_loader = False

        if data_directory is None:
            data_directory = self.config.get(C.current_dir, '')
        if proc_directory is None:
            proc_directory = self.config.get(C.current_proc, get_processing_directory(data_directory))
        logger.info(f"data_directory: {data_directory}\nproc_directory: {proc_directory}")
        self.processing_directory = proc_directory
        self.exp = Experiment(data_directory, instrument=self.config.get(C.beamline, None))
        self.pair_numbers: list[tuple[int, int]] = []
        self.pairs: list[tuple[SpectraContainer, SpectraContainer]] = []
        self.selection: list[tk.BooleanVar] = []

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        window = ttk.Frame(self.root)
        window.grid(column=0, row=0, **grid_options)
        window.columnconfigure(0, weight=0)  # set window resize properties
        window.columnconfigure(1, weight=1)  # only resize middle panel
        window.columnconfigure(2, weight=0)
        window.rowconfigure(0, weight=1)

        # LEFT
        frm = ttk.LabelFrame(window, text='Files')
        frm.grid(column=0, row=0, **grid_options)
        self.pair_selector = PairSelector(frm, self)

        # MIDDLE
        frm = ttk.LabelFrame(window, text='Select Plots')
        frm.grid(column=1, row=0, **grid_options)
        self.grid_plots = GridPlot(frm, self)

        # RIGHT
        frm = ttk.LabelFrame(window, text='Average Data')
        frm.grid(column=2, row=0, **grid_options)
        self.average_plot = AveragePlot(frm, self)

        if scan_range_str:
            self.pair_selector.scan_range.set(scan_range_str)
        if pairs:
            self.pair_selector.set_pair_numbers(pairs)

    def generate_output_filename(self, name: str, extension: str = '.nxs'):
        path, name = os.path.split(name)
        name, ext = os.path.splitext(name)
        path = path or self.processing_directory
        return os.path.join(path, name + extension)

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
            self.grid_plots.create_grid(*spectra_check, mode=mode)
            self.plot_average()

    def plot_average(self, event=None):
        mode = self.pair_selector.mode_option.get()
        if self.pairs:
            s1 = average_scans(*[s1 for (s1, s2), check in zip(self.pairs, self.selection) if check.get()])
            s2 = average_scans(*[s2 for (s1, s2), check in zip(self.pairs, self.selection) if check.get()])
            spectra = s1 - s2
            self.average_plot.update_plot(spectra, mode=mode)

    def update_plots(self, event=None):
        self._update_pairs()
        mode = self.pair_selector.mode_option.get()
        if self.pairs:
            spectra = [s1 - s2 for (s1, s2), check in zip(self.pairs, self.selection)]
            self.grid_plots.update_plots(*spectra, mode=mode)
            self.plot_average()


