import os
import tkinter as tk
from tkinter import ttk

from mmg_toolbox.xas import SpectraContainerSubtraction
from ..misc.config import C
from ..misc.matplotlib import TkFigure
from ..widgets.simple_plot import SimplePlot
from .spectra_plot import SpectraPlot
from .average_tab import Average


class AveragePlot:
    def __init__(self, root: tk.Misc, base: Average, config: dict | None = None):
        self._base = base
        self.config = config
        self.root = root
        self.spectra: SpectraContainerSubtraction | None = None
        self.mode: str = ''
        self.output_name = tk.StringVar(self.root, '')

        # Pol 1
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
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
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
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

        # Average
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
        self.figure = SpectraPlot(frm, config=self.config)

        # Buttons
        frm = ttk.Frame(self.root)
        frm.pack(side='top', fill='x')
        ttk.Button(frm, text='Add Spectra to List', command=self.btn_add_spectra).pack(side='top', fill='x')
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
        for spec in spectra.spectra1.parents:
            spectrum = spec.spectra[self.mode]
            self.pol1_figure.plot(spectrum.energy, spectrum.signal, label=spec.name)
        self.pol1_figure.ax1.legend(frameon=False)
        self.pol1_figure.ax1.set_title(spectra.spectra1.name)
        self.pol1_figure.update_axes()

        self.pol2_figure.remove_lines()
        self.pol2_figure.reset_plot()
        for spec in spectra.spectra2.parents:
            spectrum = spec.spectra[self.mode]
            self.pol2_figure.plot(spectrum.energy, spectrum.signal, label=spec.name)
        self.pol2_figure.ax1.legend(frameon=False)
        self.pol2_figure.ax1.set_title(spectra.spectra2.name)
        self.pol2_figure.update_axes()

        self.figure.update_spectra(spectra, self.mode)
        self.output_name.set(spectra.label())

    def generate_output_filename(self, name: str, extension: str = '.nxs'):
        path, name = os.path.split(name)
        name, ext = os.path.splitext(name)
        path = path or self.config.get(C.current_proc, '')
        return os.path.join(path, name + extension)

    def btn_add_spectra(self):
        """Add spectra to different panel"""
        if self.spectra:
            self._base.add_comparison_spectra(self.spectra)

    def btn_nexus(self):
        output_name = self.output_name.get()
        filename = self.generate_output_filename(output_name, '.nxs')
        if self.spectra and output_name:
            self.spectra.write_nexus(filename)

    def btn_csv(self):
        output_name = self.output_name.get()
        filename = self.generate_output_filename(output_name, '.csv')
        if self.spectra and output_name and self.mode:
            self.spectra.write_csv(filename, self.mode)
