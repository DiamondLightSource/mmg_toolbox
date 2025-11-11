"""
a tkinter frame with a single plot
"""
import tkinter as tk

import matplotlib.pyplot as plt
from numpy import ndarray

from ..misc.config import C
from ..misc.screen_size import get_figure_size, get_screen_size_inches
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
        self._y_axis_expansion_factor = 0.1

        fig_size = get_figure_size(root, self.config, C.plot_size)
        self.fig, self.ax1, self.plot_list, self.toolbar = ini_plot(
            frame=self.root,
            figure_size=fig_size,
            figure_dpi=self.config.get(C.plot_dpi, None),
        )
        self.ax1.set_xlabel(xlabel)
        self.ax1.set_ylabel(ylabel)
        self.ax1.set_title(title)
        self.plot(xdata, ydata)

    def plot(self, *args, **kwargs) -> list[plt.Line2D]:
        lines = self.ax1.plot(*args, **kwargs)
        self.plot_list.extend(lines)
        self.update_axes()
        return lines

    def update_labels(self, x_label: str | None = None, y_label: str | None = None,
                      title: str | None = None, legend: bool = False):
        if x_label:
            self.ax1.set_xlabel(x_label)
        if y_label:
            self.ax1.set_ylabel(y_label)
        if title:
            self.ax1.set_title(title)
        if legend:
            self.ax1.legend()
        else:
            self.ax1.legend([]).set_visible(False)

    def plot_from_data(self, x_data: list[ndarray], y_data: list[ndarray], x_label: str = '', y_label: str = '',
                       title: str = '', labels: list[str] | None = None):
        labels = [f"data #{n + 1}" for n in range(len(x_data))] if labels is None else labels
        self.reset_plot()
        for xdata, ydata, label in zip(x_data, y_data, labels):
            lines = self.ax1.plot(xdata, ydata, label=label)
            self.plot_list.extend(lines)
        self.update_labels(x_label=x_label, y_label=y_label, title=title, legend=True if len(labels) > 1 else False)
        self.update_axes()

    def update_from_data(self, x_data: list[ndarray], y_data: list[ndarray], x_label: str | None = None,
                         y_label: str | None = None, title: str | None = None, legend: list[str] | None = None):
        if len(x_data) == len(self.plot_list):
            # replace lines
            legend = [None for _n in range(len(x_data))] if legend is None else legend
            for xdata, ydata, label, line in zip(x_data, y_data, legend, self.plot_list):
                line.set_data(xdata, ydata)
                if label:
                    line.set_label(label)
            self.update_labels(x_label=x_label, y_label=y_label, title=title, legend=True if len(legend) > 1 else False)
            self.update_axes()
        else:
            self.plot_from_data(x_data, y_data, x_label, y_label, title, legend)

    def remove_lines(self):
        for obj in self.plot_list:
            obj.remove()
        self.plot_list.clear()

    def reset_plot(self):
        # self.ax1.set_xlabel(self.xaxis.get())
        # self.ax1.set_ylabel(self.yaxis.get())
        # self.ax1.set_title('')
        self.ax1.set_prop_cycle(None)  # reset colours
        self.ax1.legend([]).set_visible(False)
        self.remove_lines()

    def _relim(self):
        if not any(len(line.get_xdata()) for line in self.plot_list):
            return
        max_x_val = max(max(x) for line in self.plot_list if len(x := line.get_xdata()) > 0)
        min_x_val = min(min(x) for line in self.plot_list if len(x := line.get_xdata()) > 0)
        max_y_val = max(max(y) for line in self.plot_list if len(y := line.get_ydata()) > 0)
        min_y_val = min(min(y) for line in self.plot_list if len(y := line.get_ydata()) > 0)
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
