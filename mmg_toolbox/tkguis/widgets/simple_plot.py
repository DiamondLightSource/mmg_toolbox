"""
a tkinter frame with a single plot
"""
import tkinter as tk

from ..misc.config import C
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
            figure_size=self.config.get(C.plot_size, None),
            figure_dpi=self.config.get(C.plot_dpi, None),
        )
        self.ax1.set_xlabel(xlabel)
        self.ax1.set_ylabel(ylabel)
        self.ax1.set_title(title)
        self.plot(xdata, ydata)
        self._y_axis_expansion_factor = 0.1

    def plot(self, *args, **kwargs):
        lines = self.ax1.plot(*args, **kwargs)
        self.plot_list.extend(lines)
        self.update_axes()

    def remove_lines(self):
        for obj in self.plot_list:
            obj.remove()
        self.plot_list.clear()

    def reset_plot(self):
        # self.ax1.set_xlabel(self.xaxis.get())
        # self.ax1.set_ylabel(self.yaxis.get())
        self.ax1.set_title('')
        self.ax1.set_prop_cycle(None)  # reset colours
        self.ax1.legend([]).set_visible(False)
        self.remove_lines()

    def _relim(self):
        if not any(len(line.get_xdata()) for line in self.plot_list):
            return
        max_x_val = max(max(line.get_xdata()) for line in self.plot_list)
        min_x_val = min(min(line.get_xdata()) for line in self.plot_list)
        max_y_val = max(max(line.get_ydata()) for line in self.plot_list)
        min_y_val = min(min(line.get_ydata()) for line in self.plot_list)
        # expand y-axis slightly beyond data
        y_diff = max_y_val - min_y_val
        if y_diff == 0:
            y_diff = max_y_val
        y_axis_max = max_y_val + self._y_axis_expansion_factor * y_diff
        y_axis_min = min_y_val - self._y_axis_expansion_factor * y_diff
        # max_y_val = 1.05 * max_y_val if max_y_val > 0 else max_y_val * 0.98
        # min_y_val = 0.95 * min_y_val if min_y_val > 0 else min_y_val * 1.02
        self.ax1.axis((min_x_val, max_x_val, y_axis_min, y_axis_max))
        self.ax1.autoscale_view()

    def update_axes(self):
        # self.ax1.relim()
        # self.ax1.autoscale(True)
        # self.ax1.autoscale_view()
        self._relim()
        self.fig.canvas.draw()
        self.toolbar.update()


class MultiAxisPlot(SimplePlot):
    def __init__(self, root: tk.Misc, xdata: list[float], ydata: dict[str, float],
                 xlabel: str = '', ylabel: str = '', title: str = '', config: dict | None = None):
        #TODO: Complete multi-axis plot, use ideas from nexus_plot.py
        super().__init__(root, xdata, ydata, xlabel, ylabel, title, config)
