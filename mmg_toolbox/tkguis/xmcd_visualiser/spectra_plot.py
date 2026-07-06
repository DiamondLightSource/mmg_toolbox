"""
Plot Spectra data
"""

import tkinter as tk

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

    def _update_plot(self):
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
        mcd.plot_sum_rules_ratio(ax=self.ax_bottom, split_energy=None)
        # signal_ratio = self.spectra.calculate_signal_ratio()
        idx = abs(mcd.signal).argmax()
        x, y = mcd.energy[idx], mcd.signal[idx]
        # self.ax_bottom.text(x, y, f"max signal = {signal_ratio[self.mode]:.2%}")
        self.ax_bottom.set_xlabel('E [eV]')
        self.ax_bottom.legend(frameon=False, loc='upper right')

        # self.ax1.legend([self.spectra.spectra1.name, self.spectra.spectra2.name, self.spectra.name], frameon=False)
        # self.fig.tight_layout()
        self._update()

    def update_spectra(self, spectra: SpectraContainerSubtraction, mode: str | None = None):
        if mode:
            self.mode = mode
        self.spectra = spectra
        self._update_plot()

    def update_mode(self, mode: str):
        self.mode = mode
        self._update_plot()
