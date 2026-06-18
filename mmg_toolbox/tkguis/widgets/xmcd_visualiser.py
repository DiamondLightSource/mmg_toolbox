"""
a tkinter frame with 3 sections:
    1. scan choice, scan pairs + options
    2. Grid of pair-subtraction-plots with checkboxes
    3. average of selected pairs
"""
import os
from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from mmg_toolbox.utils.misc_functions import string2numbers
from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.utils.env_functions import get_processing_directory
from mmg_toolbox.xas import SpectraContainer, SpectraContainerSubtraction, average_scans, polarised_pairs
from mmg_toolbox.xas.spectra import BACKGROUND_FUNCTIONS

from ..misc.functions import create_scrollable_window
from ..misc.logging import create_logger
from ..misc.config import get_config, C
from .simple_plot import SimplePlot

logger = create_logger(__file__)
BACKGROUNDS = ['None'] + list(BACKGROUND_FUNCTIONS)
GRID_COLUMNS = 2
GRID_FIG_SIZE = (4, 2)
GRID_FIG_DPI = 70

# TODO: refactor folders to make tkgui/xmcd_visualiser folder
# TODO: add tabs
# TODO: add tab for sum rule analysis
# TODO: add tab for plotting multiple processed files
# TODO: add all-xas plots

class XMCDVisualiser:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, data_directory: str | None = None,
                 proc_directory: str | None = None,
                 scan_range_str: str = None, pairs: list[tuple[int, int]] = None,
                 config: dict | None = None):
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


class PairSelector:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser, scan_range_str: str = '12345-12355'):
        self._base = base
        self.root = root

        # variables
        modes = ['TEY', 'TFY']
        backgrounds = BACKGROUNDS
        self.scan_range = tk.StringVar(self.root, '')
        self.dls_loader = tk.BooleanVar(self.root, False)
        self.mode_option = tk.StringVar(self.root, modes[0])
        self.bkg_option = tk.StringVar(self.root, backgrounds[0])
        self.pair_numbers: list[tuple[tk.IntVar, tk.IntVar, Callable]] = []

        grid_options = dict(padx=5, pady=5, sticky='nsew')
        # window = ttk.Frame(self.root)
        # window.pack(side='top', fill='x')
        self.root.rowconfigure(0, weight=0)  # scan numbers
        self.root.rowconfigure(1, weight=1)  # pairs
        self.root.rowconfigure(2, weight=0)  # options

        # Files
        frm = ttk.LabelFrame(self.root, text='Scan Numbers')
        # frm.pack(side='top', fill='x')
        frm.grid(row=0, column=0, **grid_options)
        var = entry_with_placeholder(frm, self.scan_range, scan_range_str)
        var.pack(side='left')
        ttk.Checkbutton(frm, text='DLS Loader', variable=self.dls_loader).pack(side='left')
        ttk.Button(frm, text='List', command=self.btn_list_scans).pack(side='left')
        ttk.Button(frm, text='Find Pairs', command=self.btn_find_pairs).pack(side='left')

        # Pairs
        frm = ttk.LabelFrame(self.root, text='Pairs', relief='groove')
        # frm.pack(side='top', fill='x')
        frm.grid(row=1, column=0, **grid_options)
        self.pair_frm = create_scrollable_window(frm, height=100, width=100)
        # self.pair_frm.pack(side='top', fill='x')
        ttk.Button(frm, text='+', command=self.add_pair).pack(side='top', fill='x')
        self.add_pair()

        # Options
        frm = ttk.LabelFrame(self.root, text='Options')
        # frm.pack(side='top', fill='x')
        frm.grid(row=2, column=0, **grid_options)
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

        def update_label(event=None):
            n1, n2 = var1.get(), var2.get()
            if n1 and n2:
                s1, s2 = self._base.load_pair(n1, n2)
                subtract = s1 - s2
                label.set(subtract.label())

        def remove():
            self.pair_numbers.remove((var1, var2, update_label))
            frm.destroy()

        en = ttk.Entry(frm, textvariable=var1, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        en = ttk.Entry(frm, textvariable=var2, width=10)
        en.pack(side='left')
        en.bind('<Return>', update_label)
        ttk.Button(frm, text='X', command=remove, width=1).pack(side='left', padx=1)
        ttk.Label(frm, textvariable=label).pack(side='left')
        self.pair_numbers.append((var1, var2, update_label))
        update_label()

    def get_pair_numbers(self) -> list[tuple[int, int]]:
        return [
            vals for v1, v2, update in self.pair_numbers
            if all(vals := (v1.get(), v2.get()))
        ]

    def set_pair_numbers(self, pair_numbers: list[tuple[int, int]]) -> None:
        for n, (scan_no1, scan_no2) in enumerate(pair_numbers):
            if n < len(self.pair_numbers):
                v1, v2, update = self.pair_numbers[n]
                v1.set(scan_no1)
                v2.set(scan_no1)
                update()
            else:
                self.add_pair(scan_no1, scan_no2)
            if n == 0:
                scan, = self._base.load_scans(scan_no1)
                self.update_modes(scan)

    def update_modes(self, scan: SpectraContainer):
        modes = list(scan.spectra)
        self.ch_modes.set_menu(modes[0], *modes)

    def btn_list_scans(self):
        from ..apps.edit_text import EditText
        scan_numbers = string2numbers(self.scan_range.get())
        scans = self._base.load_scans(*scan_numbers, dls_loader=self.dls_loader.get())
        out = '\n'.join(s.label() for s in scans)
        EditText(
            expression=out,
            parent=self.root,
            textwidth=50,
            title=f'Spectra Scans in range: {scan_numbers}',
        )

    def btn_find_pairs(self):
        scan_numbers = string2numbers(self.scan_range.get())
        scans = self._base.load_scans(*scan_numbers, dls_loader=self.dls_loader.get())
        if scans:
            self.update_modes(scans[0])
            pol_pairs = polarised_pairs(*scans)
            for n, (s1, s2) in enumerate(pol_pairs):
                if n < len(self.pair_numbers):
                    v1, v2, update = self.pair_numbers[n]
                    v1.set(s1.metadata.scan_no)
                    v2.set(s2.metadata.scan_no)
                    update()
                else:
                    self.add_pair(s1.metadata.scan_no, s2.metadata.scan_no)


class GridPlot:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        self._base = base
        self.root = root
        self.figure_frames: list[ttk.Frame] = []
        self.figures: list[SimplePlot] = []
        self.n_columns = GRID_COLUMNS
        self.grid_fig_size = GRID_FIG_SIZE
        self.grid_fig_dpi = GRID_FIG_DPI

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.grid_options = dict(padx=5, pady=5, sticky='nsew')

        tk_scaling = root.tk.call('tk', 'scaling')
        print(f"tk scaling: {tk_scaling}")
        grid_width = tk_scaling * self.n_columns * self.grid_fig_size[0] * self.grid_fig_dpi + 10
        grid_height = tk_scaling * 2 * self.grid_fig_size[1] * self.grid_fig_dpi + 10
        self.window = create_scrollable_window(self.root, width=grid_width, height=grid_height)


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
            fig_size=self.grid_fig_size,
            fig_dpi=self.grid_fig_dpi,
        )
        figure.toolbar.destroy()  # remove toolbar for small figures
        spectra.create_combined_axes(mode, figure.ax1)
        figure.ax1.legend([spectra.spectra1.name, spectra.spectra2.name, spectra.name], frameon=False)
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
            fig.ax1.legend([s.spectra1.name, s.spectra2.name, s.name], frameon=False)
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
            config=self._base.config
        )

        # Buttons
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
        ttk.Button(frm, text='Add Spectra to List', command=self.btn_add_spectra).pack(side='top', fill='x')
        line = ttk.Frame(frm)
        line.pack(side='top', fill='x')
        ttk.Label(line, text='Filename').pack(side='left')
        ttk.Entry(line, textvariable=self.output_name).pack(side='left')
        ttk.Button(frm, text='Save NeXus', command=self.btn_nexus).pack(side='top', fill='x')
        ttk.Button(frm, text='Save CSV', command=self.btn_csv).pack(side='top', fill='x')

    def update_plot(self, spectra: SpectraContainerSubtraction, mode: str = 'tey'):
        self.figure.ax1.clear()
        self.spectra = spectra
        self.mode = mode
        spectra.create_combined_axes(mode, self.figure.ax1)
        self.figure.ax1.legend([spectra.spectra1.name, spectra.spectra2.name, spectra.name], frameon=False)
        self.figure.update_axes()

    def btn_add_spectra(self):
        """Add spectra to different panel"""
        pass

    def btn_nexus(self):
        output_name = self.output_name.get()
        filename = self._base.generate_output_filename(output_name, '.nxs')
        if self.spectra and output_name:
            self.spectra.write_nexus(filename)

    def btn_csv(self):
        output_name = self.output_name.get()
        filename = self._base.generate_output_filename(output_name, '.csv')
        if self.spectra and output_name and self.mode:
            self.spectra.write_csv(filename, self.mode)


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

