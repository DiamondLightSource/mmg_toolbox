import tkinter as tk
from tkinter import ttk

from mmg_toolbox.xas import SpectraContainerSubtraction
from ..misc.functions import create_scrollable_window
from ..widgets.simple_plot import SimplePlot


GRID_COLUMNS = 2
GRID_FIG_SIZE = (4, 3)
GRID_FIG_DPI = 40


class GridPlot:
    def __init__(self, root: tk.Misc, config: dict | None = None):
        self.config = config
        self.root = root
        self.figure_frames: list[ttk.Frame] = []
        self.figures: list[SimplePlot] = []
        self.n_columns = GRID_COLUMNS
        self.grid_fig_size = GRID_FIG_SIZE
        self.grid_fig_dpi = GRID_FIG_DPI

        self.root.rowconfigure(0, weight=1)
        for n in range(self.n_columns):
            self.root.columnconfigure(n, weight=1)
        self.grid_options = dict(padx=5, pady=5, sticky='nsew')

        tk_scaling = root.tk.call('tk', 'scaling')
        grid_width = tk_scaling * self.n_columns * self.grid_fig_size[0] * self.grid_fig_dpi
        grid_height = tk_scaling * 2 * self.grid_fig_size[1] * self.grid_fig_dpi
        self.window = create_scrollable_window(self.root, width=grid_width, height=grid_height)


    def create_plot(self, column: int, row: int,
                    spectra: SpectraContainerSubtraction, mode: str | None,
                    title: str, check_var: tk.BooleanVar, command) -> tuple[ttk.Frame, SimplePlot]:
        frm = ttk.Frame(self.window, relief='ridge')
        frm.grid(column=column, row=row, **self.grid_options)

        header = ttk.Frame(frm)
        header.pack(side='top', fill='x', padx=3, pady=2)
        ttk.Label(header, text=title).pack(side='left')
        ttk.Checkbutton(header, variable=check_var, command=command).pack(side='left')

        figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title=title,
            config=self.config,
            fig_size=self.grid_fig_size,
            fig_dpi=self.grid_fig_dpi,
        )
        figure.toolbar.destroy()  # remove toolbar for small figures
        spectra.create_combined_axes(mode, figure.ax1)
        figure.ax1.set_title('')
        figure.ax1.legend([spectra.spectra1.name, spectra.spectra2.name, spectra.name], frameon=False)
        figure.fig.tight_layout()
        figure.update_axes()

        self.figure_frames.append(frm)
        self.figures.append(figure)
        return frm, figure

    def create_grid(self, *spectra_check: tuple[SpectraContainerSubtraction, tk.BooleanVar],
                    mode: str | None = None, command=None):
        for n, (spec, check) in enumerate(spectra_check):
            self.create_plot(
                column=n % self.n_columns,
                row=n // self.n_columns,
                spectra=spec,
                mode=mode,
                title=spec.label(),
                check_var=check,
                command=command
            )

    def add_next_plot(self, spectra_check: tuple[SpectraContainerSubtraction, tk.BooleanVar],
                      mode: str | None = None, command=None):
        n = len(self.figures)
        spec, check = spectra_check
        self.create_plot(
            column=n % self.n_columns,
            row=n // self.n_columns,
            spectra=spec,
            mode=mode,
            title=spec.label(),
            check_var=check,
            command=command
        )

    def clear_plots(self):
        for frm in self.figure_frames:
            frm.destroy()

    def update_plots(self, *spectra: SpectraContainerSubtraction, mode: str | None = None):
        if len(spectra) != len(self.figures):
            raise Exception(f"Number of figures({len(self.figures)}) does not match spectra({len(spectra)}).")
        for fig, s in zip(self.figures, spectra):
            fig.ax1.clear()
            s.create_combined_axes(mode, fig.ax1)
            fig.ax1.legend([s.spectra1.name, s.spectra2.name, s.name], frameon=False)
            fig.update_axes()
