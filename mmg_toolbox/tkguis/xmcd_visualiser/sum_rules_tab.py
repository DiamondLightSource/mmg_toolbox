
import tkinter as tk
from tkinter import ttk

from mmg_toolbox.xas import SpectraContainerSubtraction
from ..misc.config import generate_output_filename
from ..widgets.simple_plot import SimplePlot
from .spectra_plot import SpectraPlotSlider
from .widget import XMCDVisualiser


class SumRules:
    def __init__(self, root: tk.Misc, base: XMCDVisualiser, config: dict | None = None):
        self._base = base
        self.config = config
        self.root = root
        self.spectra: SpectraContainerSubtraction | None = None
        self.mode: str = ''
        self.output_name = tk.StringVar(self.root, '')

        # Average Tab
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=0)
        self.root.rowconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        # Column 1 - XAS plots
        col = ttk.Frame(self.root)
        col.grid(column=0, row=0, **grid_options)

        # Pol 1
        frm = ttk.Frame(col)
        frm.grid(column=0, row=0, **grid_options)
        self.pol1_figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title='Pol 1',
            config=self.config
        )
        self.pol1_figure.ax1.set_xlabel('Energy [eV]')
        self.pol1_figure.fig.tight_layout()

        # Pol 2
        frm = ttk.Frame(col)
        frm.grid(column=0, row=1, **grid_options)
        self.pol2_figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title='Pol 2',
            config=self.config
        )
        self.pol2_figure.ax1.set_xlabel('Energy [eV]')
        self.pol2_figure.fig.tight_layout()

        # Column 2 - Average
        frm = ttk.Frame(self.root)
        frm.grid(column=1, row=0, **grid_options)
        self.figure = SpectraPlotSlider(frm, config=self.config)

        # Column 3 - Buttons
        frm = ttk.Frame(self.root)
        frm.grid(column=2, row=0, **grid_options)
        ttk.Button(frm, text='Add Spectra to Comparison', command=self.btn_add_spectra).pack(side='top', fill='x')
        line = ttk.Frame(frm)
        line.pack(side='top', fill='x')
        ttk.Label(line, text='Filename:').pack(side='left', padx=5)
        ttk.Entry(line, textvariable=self.output_name).pack(side='left', fill='x', expand=True)
        ttk.Button(frm, text='Save NeXus', command=self.btn_nexus).pack(side='top', fill='x')
        ttk.Button(frm, text='Save CSV', command=self.btn_csv).pack(side='top', fill='x')

    def update_plot(self, spectra: SpectraContainerSubtraction, mode: str = 'tey'):
        self.spectra = spectra
        self.mode = mode

        self.pol1_figure.remove_lines()
        self.pol1_figure.reset_plot()
        spectra.add_edge_lines(self.pol1_figure.ax1)
        self.pol2_figure.remove_lines()
        for spec in spectra.spectra1.parents:
            spectrum = spec.spectra[self.mode]
            self.pol1_figure.plot(spectrum.energy, spectrum.signal, label=spec.name)
        self.pol1_figure.ax1.legend(frameon=False)
        self.pol1_figure.ax1.set_title(spectra.spectra1.name)
        self.pol1_figure.update_axes()

        self.pol2_figure.remove_lines()
        self.pol2_figure.reset_plot()
        spectra.add_edge_lines(self.pol2_figure.ax1)
        for spec in spectra.spectra2.parents:
            spectrum = spec.spectra[self.mode]
            self.pol2_figure.plot(spectrum.energy, spectrum.signal, label=spec.name)
        self.pol2_figure.ax1.legend(frameon=False)
        self.pol2_figure.ax1.set_title(spectra.spectra2.name)
        self.pol2_figure.update_axes()

        self.figure.update_spectra(spectra, self.mode)
        self.output_name.set(spectra.label())

    def btn_add_spectra(self):
        """Add spectra to different panel"""
        if self.spectra:
            self._base.comparison.treeview.add_spectra(self.spectra)

    def btn_nexus(self):
        output_name = self.output_name.get()
        filename = generate_output_filename(output_name, '.nxs', self.config)
        if self.spectra and output_name:
            self.spectra.write_nexus(filename)

    def btn_csv(self):
        output_name = self.output_name.get()
        filename = generate_output_filename(output_name, '.csv', self.config)
        if self.spectra and output_name and self.mode:
            self.spectra.write_csv(filename, self.mode)