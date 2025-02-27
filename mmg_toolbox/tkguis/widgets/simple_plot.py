"""
a tkinter frame with a single plot
"""

from hdfmap import create_nexus_map

from ..styles import create_root
from ..matplotlib import ini_plot


class SimplePlot:
    """
    Simple plot
    """

    def __init__(self, xdata, ydata, xlabel='', ylabel='', title='', parent=None):
        self.root = create_root('Simple Plot', parent)

        self.fig, self.ax1, self.plot_list, self.toolbar = ini_plot(self.root)
        self.ax1.set_xlabel(xlabel)
        self.ax1.set_ylabel(ylabel)
        self.ax1.set_title(title)
        self.plot(xdata, ydata)


    def plot(self, *args, **kwargs):
        lines = self.ax1.plot(*args, **kwargs)
        self.plot_list.extend(lines)
        self.update_plot()

    def reset_plot(self):
        # self.ax1.set_xlabel(self.xaxis.get())
        # self.ax1.set_ylabel(self.yaxis.get())
        self.ax1.set_title('')
        self.ax1.set_prop_cycle(None)  # reset colours
        self.ax1.legend([]).set_visible(False)
        for obj in self.ax1.lines:
            obj.remove()

    def update_plot(self):
        self.ax1.relim()
        self.ax1.autoscale(True)
        self.ax1.autoscale_view()
        self.fig.canvas.draw()
        self.toolbar.update()


class NexusDefaultPlot(SimplePlot):
    def __init__(self, hdf_filename):
        self.map = create_nexus_map(hdf_filename)
        with self.map.load_hdf() as hdf:
            self.data = self.map.get_plot_data(hdf)
        super().__init__(
            xdata=self.data['xdata'],
            ydata=self.data['ydata'],
            xlabel=self.data['xlabel'],
            ylabel=self.data['ylabel'],
            title=self.data['title']
        )

