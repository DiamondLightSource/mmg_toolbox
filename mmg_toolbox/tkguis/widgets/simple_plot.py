"""
a tkinter frame with a single plot
"""
import tkinter as tk

from ..misc.matplotlib import ini_plot
from ..misc.logging import create_logger

logger = create_logger(__file__)


class SimplePlot:
    """
    Simple plot - single plot in frame with axes
    """

    def __init__(self, root: tk.Misc, xdata: list[float], ydata: list[float],
                 xlabel: str = '', ylabel: str = '', title: str = '', config: dict | None = None):
        self.root = root
        self.config = config or {}

        self.fig, self.ax1, self.plot_list, self.toolbar = ini_plot(
            frame=self.root,
            figure_size=self.config.get('figure_size'),
            figure_dpi=self.config.get('figure_dpi'),
        )
        self.ax1.set_xlabel(xlabel)
        self.ax1.set_ylabel(ylabel)
        self.ax1.set_title(title)
        self.plot(xdata, ydata)

    def plot(self, *args, **kwargs):
        lines = self.ax1.plot(*args, **kwargs)
        self.plot_list.extend(lines)
        self.update_axes()

    def reset_plot(self):
        # self.ax1.set_xlabel(self.xaxis.get())
        # self.ax1.set_ylabel(self.yaxis.get())
        self.ax1.set_title('')
        self.ax1.set_prop_cycle(None)  # reset colours
        self.ax1.legend([]).set_visible(False)
        for obj in self.ax1.lines:
            obj.remove()

    def update_axes(self):
        self.ax1.relim()
        self.ax1.autoscale(True)
        self.ax1.autoscale_view()
        self.fig.canvas.draw()
        self.toolbar.update()
