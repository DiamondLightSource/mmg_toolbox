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
        self.ax1 = self.fig.add_subplot(1, 1, 1)
        self.spectra = spectra
        self.mode = mode or (spectra.metadata.default_mode if spectra else None)
        if spectra:
            self.update_mode(mode)

    def _update_plot(self):
        self.ax1.clear()
        self.spectra.create_combined_axes(self.mode, self.ax1)
        self.ax1.set_title('')
        self.ax1.legend([self.spectra.spectra1.name, self.spectra.spectra2.name, self.spectra.name], frameon=False)
        self.fig.tight_layout()
        self._update()

    def update_spectra(self, spectra: SpectraContainerSubtraction, mode: str | None = None):
        if mode:
            self.mode = mode
        self.spectra = spectra
        self._update_plot()

    def update_mode(self, mode: str):
        self.mode = mode
        self._update_plot()
