"""
Plot Spectra data
"""

import tkinter as tk
from tkinter import ttk

from mmg_toolbox.xas import SpectraContainerSubtraction
from ..misc.matplotlib import TkFigure


class SpectraPlot(TkFigure):
    def __init__(self, root: tk.Misc, spectra: SpectraContainerSubtraction | None = None, mode: str | None = None,
                 config: dict | None = None, fig_size: tuple[int, int] | None = None, fig_dpi: int = None):
        super().__init__(
            root=root,
            config=config,
            fig_size=fig_size,
            fig_dpi=fig_dpi,
        )
        self.grid_spec = self.fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0)
        self.ax_top = self.fig.add_subplot(self.grid_spec[0])
        self.ax_bottom = self.fig.add_subplot(self.grid_spec[1])
        self.fig.tight_layout()
        self.spectra = spectra
        self.mode = mode or (spectra.metadata.default_mode if spectra else None)
        if spectra:
            self._update_plot()

    def _update_plot(self, split_energy: float | None = None):
        self.ax_top.clear()
        self.ax_bottom.clear()

        for edge_label, energy in self.spectra.get_edges().items():
            self.ax_top.axvline(energy, color='k', alpha=0.3)
            self.ax_bottom.axvline(energy, color='k', alpha=0.3)
            self.ax_top.text(energy, 0.9, edge_label, color='k', alpha=0.3,
                             ha='right', va='top', transform=self.ax_top.get_xaxis_transform())

        for parent in self.spectra.parents:
            spectrum = parent.spectra[self.mode]
            spectrum.plot(ax=self.ax_top, label=parent.name)
        self.ax_top.set_ylabel(self.mode)
        self.ax_top.legend(frameon=False, loc='upper right')

        mcd = self.spectra.spectra[self.mode]
        mcd.plot_sum_rules_ratio(ax=self.ax_bottom, split_energy=split_energy)
        # signal_ratio = self.spectra.calculate_signal_ratio()
        idx = abs(mcd.signal).argmax()
        x, y = mcd.energy[idx], mcd.signal[idx]
        # self.ax_bottom.text(x, y, f"max signal = {signal_ratio[self.mode]:.2%}")
        self.ax_bottom.set_xlabel('E [eV]')
        self.ax_bottom.legend(frameon=False, loc='upper right')
        self._update()

    def update_spectra(self, spectra: SpectraContainerSubtraction, mode: str | None = None):
        if mode:
            self.mode = mode
        self.spectra = spectra
        self._update_plot()

    def update_mode(self, mode: str):
        self.mode = mode
        self._update_plot()


class SpectraPlotSlider(SpectraPlot):
    """SpectraPlot with slider for energy split and sum rules"""
    def __init__(self, root: tk.Misc, spectra: SpectraContainerSubtraction | None = None, mode: str | None = None,
                 config: dict | None = None, fig_size: tuple[int, int] | None = None, fig_dpi: int = None):
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=0)
        root.grid_rowconfigure(2, weight=0)

        frame = ttk.Frame(root)
        frame.grid(row=0, column=0, sticky='nsew')
        super().__init__(frame, spectra, mode, config, fig_size, fig_dpi)
        self.slider_value = tk.DoubleVar(root, 0)
        self.report = tk.StringVar(root, '')

        frame = ttk.Frame(root)
        frame.grid(row=1, column=0, sticky='nsew')
        # Add Slider
        self.slider = self.ini_slider(frame)
        # Add Report
        frm = ttk.LabelFrame(root, text='Sum Rules', relief='ridge')
        frm.grid(row=2, column=0, sticky='nsew')
        ttk.Label(frm, textvariable=self.report).pack(side='left', fill='both')

    def ini_slider(self, root: tk.Misc):
        if self.spectra:
            spectrum = next(iter(self.spectra.spectra.values()))
            en_min, en_max = min(spectrum.energy), max(spectrum.energy)
            edges = self.spectra.get_edges()
            default_split = spectrum.get_split_energy(edges)
            self.slider_value.set(default_split)
        else:
            en_min, en_max = 0, 100
            self.slider_value.set(50)

        frm = ttk.Frame(root)
        frm.pack(side='top', fill='x', expand=True, pady=2, padx=5)

        slider = ttk.Scale(frm, from_=en_min, to=en_max, variable=self.slider_value, orient='horizontal',
                            command=self.update_slider)
        slider.pack(side='left', expand=True)
        ttk.Label(frm, textvariable=self.slider_value, width=12).pack(side='left')
        return slider

    def update_spectra(self, spectra: SpectraContainerSubtraction, mode: str | None = None):
        super().update_spectra(spectra, mode)

        spectrum = next(iter(self.spectra.spectra.values()))
        en_min, en_max = min(spectrum.energy), max(spectrum.energy)
        self.slider.config(from_=en_min, to=en_max)
        edges = self.spectra.get_edges()
        default_split = spectrum.get_split_energy(edges)
        self.slider_value.set(default_split)
        self.update_slider()

    def update_slider(self, event=None):
        split = self.slider_value.get()
        self._update_plot(split_energy=split)
        report = self.spectra.sum_rules_report(split_energy=split)
        self.report.set(report)
