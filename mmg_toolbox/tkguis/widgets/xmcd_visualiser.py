"""
a tkinter frame with 3 sections:
    1. scan choice, scan pairs + options
    2. Grid of pair-subtraction-plots with checkboxes
    3. average of selected pairs
"""
import tkinter as tk
from tkinter import ttk

import numpy as np

from ..misc.logging import create_logger
from ..misc.config import get_config, C
from .simple_plot import SimplePlot
from mmg_toolbox.utils.misc_functions import string2numbers
from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.xas import SpectraContainer, SpectraContainerSubtraction, average_scans, polarised_pairs
from mmg_toolbox.xas.spectra import BACKGROUND_FUNCTIONS

logger = create_logger(__file__)
BACKGROUNDS = ['None'] + list(BACKGROUND_FUNCTIONS)


class XMCDVisualiser:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, data_directory: str | None = None,
                 config: dict | None = None):
        self.root = root
        self.config = config or get_config()
        self.use_dls_loader = False
        self.exp = Experiment(data_directory, instrument=self.config.get(C.beamline, None))
        self.pair_numbers: list[tuple[int, int]] = []
        self.pairs: list[tuple[SpectraContainer, SpectraContainer]] = []
        self.selection: list[tk.BooleanVar] = []

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        window = ttk.Frame(self.root)
        window.grid(column=0, row=0, **grid_options)
        window.columnconfigure(0, weight=0)
        window.columnconfigure(1, weight=1)
        window.columnconfigure(2, weight=0)

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

    def load_scans(self, *scan_number: int) -> list[SpectraContainer]:
        return self.exp.load_xas(*scan_number, dls_loader=self.use_dls_loader)

    def load_pair(self, scan_number1: int, scan_number2: int) -> tuple[SpectraContainer, SpectraContainer]:
        s1, s2 = self.exp.load_xas(scan_number1, scan_number2, dls_loader=self.use_dls_loader)
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


class PairSelector:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        self._base = base
        self.root = root

        # variables
        modes = ['TEY', 'TFY']
        backgrounds = BACKGROUNDS
        self.scan_range = tk.StringVar(self.root, '')
        self.mode_option = tk.StringVar(self.root, modes[0])
        self.bkg_option = tk.StringVar(self.root, backgrounds[0])
        self.pair_numbers: list[tuple[tk.IntVar, tk.IntVar]] = []

        # Files
        frm = ttk.LabelFrame(self.root, text='Files')
        frm.pack(side='top', fill='x')
        var = entry_with_placeholder(frm, self.scan_range, '12345-12360')
        var.pack(side='left')
        var = ttk.Button(frm, text='List', command=self.btn_list_scans)
        var.pack(side='left')
        var = ttk.Button(frm, text='Find Pairs', command=self.btn_find_pairs)
        var.pack(side='left')

        # Pairs
        frm = ttk.LabelFrame(self.root, text='Pairs', relief='groove', height=30)
        frm.pack(side='top', fill='x')
        self.pair_frm = ttk.Frame(frm)
        self.pair_frm.pack(side='top', fill='x')
        ttk.Button(frm, text='+', command=self.add_pair).pack(side='top', fill='x')
        var = ttk.Scrollbar(frm, orient='vertical')
        var.pack(side='right', fill='y')
        self.add_pair()

        # Options
        frm = ttk.LabelFrame(self.root, text='Options')
        frm.pack(side='top', fill='x')
        self.ch_modes = ttk.OptionMenu(frm, self.mode_option, modes[0], *modes,
                                       command=self._base.update_plots)
        self.ch_modes.pack(side='top', fill='x', padx=4)
        ttk.OptionMenu(frm, self.bkg_option, backgrounds[0], *backgrounds,
                       command=self._base.update_plots).pack(side='top', fill='x', padx=4)
        ttk.Button(frm, text='Plot', command=self._base.plot_pairs).pack(side='top', fill='x', padx=10, pady=3)

    def add_pair(self, number1: int | None = None, number2: int | None = None):
        var1 = tk.IntVar(self.root, number1)
        var2 = tk.IntVar(self.root, number2)
        label = tk.StringVar(self.root, '')

        frm = ttk.Frame(self.pair_frm)
        frm.pack(side='top', fill='x')

        def remove():
            self.pair_numbers.remove((var1, var2))
            frm.destroy()

        def update_label(event=None):
            n1, n2 = var1.get(), var2.get()
            if n1 and n2:
                s1, s2 = self._base.load_pair(n1, n2)
                subtract = s1 - s2
                label.set(subtract.label())

        en = ttk.Entry(frm, textvariable=var1, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        en = ttk.Entry(frm, textvariable=var2, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        ttk.Button(frm, text='X', command=remove, width=1).pack(side='left', padx=1)
        ttk.Label(frm, textvariable=label).pack(side='left')
        self.pair_numbers.append((var1, var2))
        update_label()

    def get_pair_numbers(self) -> list[tuple[int, int]]:
        return [
            vals for v1, v2 in self.pair_numbers
            if all(vals := (v1.get(), v2.get()))
        ]

    def update_modes(self, scan: SpectraContainer):
        modes = list(scan.spectra)
        self.ch_modes.set_menu(modes[0], *modes)

    def btn_list_scans(self):
        pass

    def btn_find_pairs(self):
        scan_numbers = string2numbers(self.scan_range.get())
        scans = self._base.load_scans(*scan_numbers)
        if scans:
            self.update_modes(scans[0])
            pol_pairs = polarised_pairs(*scans)
            for n, (s1, s2) in enumerate(pol_pairs):
                if n < len(self.pair_numbers):
                    v1, v2 = self.pair_numbers[n]
                    v1.set(s1.metadata.scan_no)
                    v2.set(s2.metadata.scan_no)
                else:
                    self.add_pair(s1.metadata.scan_no, s2.metadata.scan_no)


class GridPlot:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        self._base = base
        self.root = root
        self.figure_frames: list[ttk.Frame] = []
        self.figures: list[SimplePlot] = []
        self.n_columns = 2

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.grid_options = dict(padx=5, pady=5, sticky='nsew')

        self.window = tk.Canvas(self.root)
        # self.window.grid(column=0, row=0, **self.grid_options)
        self.window.pack(side='left', fill='both', expand=True)
        y_scroll = ttk.Scrollbar(self.root, orient='vertical', command=self.window.yview)
        x_scroll = ttk.Scrollbar(self.root, orient='horizontal', command=self.window.xview)
        self.window.configure(yscrollcommand=y_scroll.set)
        self.window.configure(xscrollcommand=x_scroll.set)
        y_scroll.pack(side='right', fill='y')
        x_scroll.pack(side='bottom', fill='x')


    def create_plot(self, column: int, row: int,
                    spectra: SpectraContainerSubtraction, mode: str,
                    title: str, check_var: tk.BooleanVar) -> tuple[ttk.Frame, SimplePlot]:
        frm = ttk.Frame(self.window, relief='ridge')
        frm.grid(column=column, row=row, **self.grid_options)

        header = ttk.Frame(frm)
        header.pack(side='top', fill='x', padx=3, pady=2)
        ttk.Label(header, text=title).pack(side='left')
        ttk.Checkbutton(header, variable=check_var, command=self._base.plot_average).pack(side='left')

        figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title=title,
            config=self._base.config,
        )
        spectra.create_combined_axes(mode, figure.ax1)
        figure.update_axes()

        self.figure_frames.append(frm)
        self.figures.append(figure)
        return frm, figure

    def create_grid(self, *spectra_check: tuple[SpectraContainerSubtraction, tk.BooleanVar], mode: str):
        # n_rows = len(spectra_check) // self.n_columns
        for n, (spec, check) in enumerate(spectra_check):
            print(f"Grid pos: column: {n % self.n_columns}, row: {n // self.n_columns}, {spec.label()}")
            self.create_plot(n % self.n_columns, n // self.n_columns, spec, mode, spec.label(), check)

    def clear_plots(self):
        for frm in self.figure_frames:
            frm.destroy()

    def update_plots(self, *spectra: SpectraContainerSubtraction, mode: str):
        if len(spectra) != len(self.figures):
            raise Exception(f"Number of figures({len(self.figures)}) does not match spectra({len(spectra)}).")
        for fig, s in zip(self.figures, spectra):
            fig.ax1.clear()
            s.create_combined_axes(mode, fig.ax1)
            fig.update_axes()


class AveragePlot:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        self._base = base
        self.root = root
        self.spectra: SpectraContainerSubtraction | None = None
        self.mode: str = ''
        self.output_name = tk.StringVar(self.root, '')

        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
        self.figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title='Average',
            config=self._base.config,
        )

        # Buttons
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
        ttk.Button(frm, text='Save NeXus', command=self.btn_nexus).pack(side='top', fill='x')
        ttk.Button(frm, text='Save CSV', command=self.btn_csv).pack(side='top', fill='x')

    def update_plot(self, spectra: SpectraContainerSubtraction, mode: str = 'tey'):
        self.figure.ax1.clear()
        self.spectra = spectra
        self.mode = mode
        spectra.create_combined_axes(mode, self.figure.ax1)
        self.figure.update_axes()

    def btn_nexus(self):
        output_name = self.output_name.get()
        if self.spectra and output_name:
            self.spectra.write_nexus(output_name + '.nxs')

    def btn_csv(self):
        output_name = self.output_name.get()
        if self.spectra and output_name and self.mode:
            self.spectra.write_csv(output_name + '.csv', self.mode)


def entry_with_placeholder(root: tk.Misc, text: tk.Variable, placeholder_text: str, **kwargs) -> ttk.Entry:
    """Create an entry widget with placeholder text"""

    def on_focus_in(event):
        if entry.get() == placeholder_text:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_focus_out(event):
        if entry.get() == "":
            entry.insert(0, placeholder_text)
            entry.config(fg="grey")

    entry = tk.Entry(root, textvariable=text, fg="grey", **kwargs)
    entry.insert(0, placeholder_text)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    return entry

