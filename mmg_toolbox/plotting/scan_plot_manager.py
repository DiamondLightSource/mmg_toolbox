"""
Plot Manager for the Scan object
"""

import numpy as np
import matplotlib.pyplot as plt
from ..nexus.nexus_scan import NexusScan
from .matplotlib import (
    set_plot_defaults, plot_line, plot_image,
    FIG_SIZE, FIG_DPI, DEFAULT_CMAP
)

"----------------------------------------------------------------------------------------------------------------------"
"----------------------------------------------- ScanPlotManager ------------------------------------------------------"
"----------------------------------------------------------------------------------------------------------------------"


class ScanPlotManager:
    """
    ScanPlotManager
        scan.plot = ScanPlotManager(scan)
        scan.plot() # plot default axes
        scan.plot.plot(xaxis, yaxis)  # creates figure
        scan.plot.plotline(xaxis, yaxis)  # plots line on current figure
        scan.plot.image()  # create figure and display detector image

    :param scan: NexusScan object
    """
    set_plot_defaults = set_plot_defaults
    show = plt.show

    def __init__(self, scan: NexusScan):
        self.scan = scan

    def __call__(self, *args, **kwargs):
        return self.plot(*args, **kwargs)

    def plotline(self, xaxis: str = 'axes', yaxis: str = 'signal', *args, **kwargs):
        """
        Plot scanned datasets on matplotlib axes subplot
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param args: given directly to plt.plot(..., *args, **kwars)
        :param axes: matplotlib.axes subplot, or None to use plt.gca()
        :param kwargs: given directly to plt.plot(..., *args, **kwars)
        :return: list lines object, output of plot
        """
        data = self.scan.get_plot_data(xaxis, yaxis)

        if 'label' not in kwargs:
            kwargs['label'] = self.scan.label()
        axes = kwargs.pop('axes') if 'axes' in kwargs else plt.subplot()
        lines = plot_line(axes, data['x'], data['y'], None, *args, **kwargs)
        return lines

    def plot(self, xaxis: str = 'axes', yaxis: str | list[str] = 'signal', *args,
             axes: plt.Axes | None = None, **kwargs) -> plt.Axes:
        """
        Create matplotlib figure with plot of the scan
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis, also accepts list of names for multiple lines
        :param args: given directly to plt.plot(..., *args, **kwars)
        :param axes: matplotlib.axes subplot, or None to create a figure
        :param kwargs: given directly to plt.plot(..., *args, **kwars)
        :return: axes object
        """
        axes = plt.subplot() if axes is None else axes

        if isinstance(yaxis, str):
            yaxis = [yaxis]

        for _yaxis in yaxis:
            data = self.scan.get_plot_data(xaxis, _yaxis)
            plot_line(axes, data['x'], data['y'], None, *args, label=_yaxis, **kwargs)

        # Add labels
        xlab, ylab = self.scan.map.generate_ids(xaxis, yaxis[0], modify_missing=False)
        axes.set_xlabel(xlab)
        axes.set_title(self.scan.title())
        if len(yaxis) == 1:
            axes.set_ylabel(ylab)
        else:
            axes.legend()
        return axes

    def image(self, index: int | tuple | slice | None = None, xaxis: str = 'axes',
              axes: plt.Axes | None = None, clim: tuple[float, float] | None = None,
              cmap: str = DEFAULT_CMAP, colorbar: bool = False, **kwargs) -> plt.Axes:
        """
        Plot image in matplotlib figure (if available)
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param xaxis: name or address of xaxis dataset
        :param axes: matplotlib axes to plot on (None to create figure)
        :param clim: [min, max] colormap cut-offs (None for auto)
        :param cmap: str colormap name (None for auto)
        :param colorbar: False/ True add colorbar to plot
        :param kwargs: additional arguments for plot_detector_image
        :return: axes object
        """
        # x axis data
        xdata = self.scan.eval(xaxis)
        xname, = self.scan.map.generate_ids(xaxis, modify_missing=False)
        xdata = np.reshape(xdata, -1)  # handle multi-dimension data

        # image data
        im = self.scan.image(index)
        if im is None:
            im = np.zeros((101, 101))
        if index is None or index == 'sum':
            xvalue = xdata[np.size(xdata) // 2]
        else:
            xvalue = xdata[index]

        # plot
        axes = plt.subplot() if axes is None else axes
        plot_image(axes, im, clim=clim, cmap=cmap, **kwargs)
        if not self.scan.map.image_data:
            axes.text(0.5, 0.5, 'No Detector Image', c='w',
                      horizontalalignment='center',
                      verticalalignment='center',
                      transform=axes.transAxes)
        if colorbar:
            plt.colorbar(ax=axes)
        ttl = '%s\n%s [%s] = %s' % (self.scan.title(), xname, index, xvalue)
        axes.set_title(ttl)
        return axes

    def detail(self, xaxis: str = 'axes', yaxis: str | list[str] = 'signal',
               index: int | tuple | slice | None = None, clim: tuple[float, float] | None = None,
               cmap: str = DEFAULT_CMAP, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure with plot of the scan and detector image
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis, also accepts list of names for multiple plots
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param clim: [min, max] colormap cut-offs (None for auto)
        :param cmap: str colormap name (None for auto)
        :param kwargs: given directly to plt.plot(..., *args, **kwars)
        :return: figure object
        """

        # Create figure
        fig, ((lt, rt), (lb, rb)) = plt.subplots(2, 2, figsize=[FIG_SIZE[0] * 1.2, FIG_SIZE[1] * 1.2], dpi=FIG_DPI)
        fig.subplots_adjust(hspace=0.35, left=0.1, right=0.95)

        # Top left - line plot
        self.plot(xaxis, yaxis, axes=lt, **kwargs)

        # Top right - image plot
        try:
            self.image(index, xaxis, cmap=cmap, clim=clim, axes=rt)
        except (FileNotFoundError, KeyError, TypeError):
            rt.text(0.5, 0.5, 'No Image')
            rt.set_axis_off()

        # Bottom-Left - details
        details = str(self.scan)
        lb.text(-0.2, 1, details, ha='left', va='top', multialignment="left", fontsize=12, wrap=True)
        lb.set_axis_off()

        # Bottom-Right - fit results
        rb.set_axis_off()
        if 'fit' in yaxis:
            fit_report = str(self.scan.fit)
            rb.text(-0.2, 1, fit_report, ha='left', va='top',  multialignment="left", fontsize=12, wrap=True)
        return fig

    def scananddetector(self, xaxis: str = 'axes', yaxis: str | list[str] = 'signal',
                        index: int | tuple | slice | None = None, clim: tuple[float, float] | None = None,
                        cmap: str = DEFAULT_CMAP, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure with plot of the scan and detector image
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis, also accepts list of names for multiple plots
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param clim: [min, max] colormap cut-offs (None for auto)
        :param cmap: str colormap name (None for auto)
        :param kwargs: given directly to plt.plot(..., *args, **kwars)
        :return: Figure object
        """

        # Create figure
        fig, (lt, rt) = plt.subplots(1, 2, figsize=[FIG_SIZE[0] * 1.5, FIG_SIZE[1]], dpi=FIG_DPI)
        fig.subplots_adjust(hspace=0.35, left=0.1, right=0.95)

        # left - line plot
        self.plot(xaxis, yaxis, axes=lt, **kwargs)

        # right - image plot
        self.image(index, xaxis, cmap=cmap, clim=clim, axes=rt)
        return fig

    def image_histogram(self, index: int | tuple | slice | None = None,
                        axes: plt.Axes | None = None, **kwargs) -> plt.Axes:
        """
        Plot image in matplotlib figure (if available)
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param axes: matplotlib axes to plot on (None to create figure)
        :param kwargs: additional arguments for plot_detector_image
        :param cut_ratios: list of cut-ratios, each cut has a different colour and given as ratio of max intensity
        :return: axes object
        """
        if index is None:
            index = ()
        vol = self.scan.get_image(index=index)

        axes.hist(np.log10(vol[vol > 0].flatten()), 100)

        axes.set_xlabel('Log$_{10}$ Pixel Intensity')
        axes.set_ylabel('N')
        axes.set_title(self.scan.title())
        return axes


