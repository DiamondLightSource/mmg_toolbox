"""
Plot Manager for the Experiment object
"""

import numpy as np
import matplotlib.pyplot as plt
import hdfmap
from ..utils.experiment import Experiment
from .matplotlib import (
    set_plot_defaults, generate_subplots, plot_lines, plot_2d_surface, plot_3d_surface, plot_3d_lines,
    FIG_SIZE, FIG_DPI, DEFAULT_CMAP, Axes3D
)


class ExperimentPlotManager:
    """
    ExperimentPlotManager
        scan.plot = ScanPlotManager(scan)
        scan.plot() # plot default axes
        scan.plot.plot(xaxis, yaxis)  # creates figure
        scan.plot.plotline(xaxis, yaxis)  # plots line on current figure
        scan.plot.image()  # create figure and display detector image

    :param experiment: Experiment object
    """
    set_plot_defaults = set_plot_defaults
    show = plt.show

    def __init__(self, experiment: Experiment):
        self.exp = experiment

    def __call__(self, *args, **kwargs):
        return self.plot(*args, **kwargs)

    def plot(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
             xaxis: str = 'axes', yaxis: str | list[str] = 'signal', axes: plt.Axes | None = None, **kwargs) -> plt.Axes:
        """
        Create matplotlib figure with a line plot from a or several scans

            axes = exp.plot.plot(file1, file2, xaxis='eta', yaxis='roi2_sum')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis, also accepts list of names for multiple lines
        :param axes: matplotlib.axes subplot, or None to create a figure
        :param kwargs: given directly to plt.plot(..., **kwars)
        :return: axes object
        """
        scans = self.exp.scans(*scan_files, hdf_map=hdf_map)
        if axes is None:
            fig, axes = plt.subplots()
        for scan in scans:
            scan.plot.plot(xaxis, yaxis, axes=axes, **kwargs)
        if len(scan_files) > 1:
            axes.legend(scan_files)
        axes.set_title(self.exp.generate_scans_title(*scan_files))
        return axes

    def image(self,  scan_file: int | str = -1, hdf_map: hdfmap.NexusMap | None = None,
              index: int | tuple | slice | None = None, xaxis: str = 'axes',
              axes: plt.Axes | None = None, clim: tuple[float, float] | None = None,
              cmap: str = DEFAULT_CMAP, colorbar: bool = False, **kwargs) -> plt.Axes | None:
        """
        Plot image in matplotlib figure (if available)
        :param scan_file: scan number or filename
        :param hdf_map: hdfmap object or None
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param xaxis: name or address of xaxis dataset
        :param axes: matplotlib axes to plot on (None to create figure)
        :param clim: [min, max] colormap cut-offs (None for auto)
        :param cmap: str colormap name (None for auto)
        :param colorbar: False/ True add colorbar to plot
        :param kwargs: additional arguments for plot_detector_image
        :return: axes object or None if no image
        """
        scan = self.exp.scans(scan_file, hdf_map=hdf_map)[0]
        if scan.map.image_data:
            return scan.plot.image(index, xaxis, axes, clim, cmap, colorbar, **kwargs)
        return None

    def detail(self, scan_file: int | str = -1, hdf_map: hdfmap.NexusMap | None = None,
               xaxis: str = 'axes', yaxis: str | list[str] = 'signal',
               index: int | tuple | slice | None = None, clim: tuple[float, float] | None = None,
               cmap: str = DEFAULT_CMAP, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure with plot of the scan and detector image
        :param scan_file: scan number or filename
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis, also accepts list of names for multiple plots
        :param index: int, detector image index, 0-length of scan, if None, use centre index
        :param clim: [min, max] colormap cut-offs (None for auto)
        :param cmap: str colormap name (None for auto)
        :param kwargs: given directly to plt.plot(..., *args, **kwars)
        :return: figure object
        """
        scan = self.exp.scans(scan_file, hdf_map=hdf_map)[0]

        # Create figure
        fig, ((lt, rt), (lb, rb)) = plt.subplots(2, 2, figsize=[FIG_SIZE[0] * 1.2, FIG_SIZE[1] * 1.2], dpi=FIG_DPI)
        fig.subplots_adjust(hspace=0.35, left=0.1, right=0.95)
        fig.suptitle(scan.title())

        # Top left - line plot
        scan.plot(xaxis, yaxis, axes=lt, **kwargs)
        lt.set_title(None)

        # Top right - image plot
        scan.plot.image(index, xaxis, cmap=cmap, clim=clim, axes=rt)
        rt.set_title(None)

        # Bottom-Left - details
        details = self.exp.scan_str(scan_file, hdf_map=hdf_map)
        lb.text(-0.2, 1, details, ha='left', va='top', multialignment="left", fontsize=12, wrap=True)
        lb.set_axis_off()

        # Bottom-Right - fit results
        rb.set_axis_off()
        if 'fit' in yaxis:
            fit_report = str(scan.fit)
            rb.text(-0.2, 1, fit_report, ha='left', va='top', multialignment="left", fontsize=12, wrap=True)
        return fig

    def multi_lines(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                    xaxis: str = 'axes', yaxis: str = 'signal', value: str | None = None,
                    axes: plt.Axes | None = None, **kwargs) -> plt.Axes:
        """
        Create matplotlib figure with a line plot from a or several scans

            axes = exp.plot.multi_lines(*range(-10, 0), xaxis='eta', yaxis='roi2_sum', value='Tsample')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or path of array to plot on x axis
        :param yaxis: str name or path of array to plot on y axis
        :param value: str name or path of float value to distinguish lines
        :param axes: matplotlib.axes subplot, or None to create a figure
        :param kwargs: given directly to plt.plot(..., **kwars)
        :return: axes object
        """
        scans = self.exp.scans(*scan_files, hdf_map=hdf_map)
        hdf_map = scans[0].map

        plot_data = []
        for scan in scans:
            with hdfmap.load_hdf(scan.filename) as hdf:
                xdata = hdf_map.eval(hdf, xaxis)
                ydata = hdf_map.eval(hdf, yaxis)
                value_data = np.mean(hdf_map.eval(hdf, value)) if value else None
                plot_data.append((value_data, xdata, ydata))

        if axes is None:
            fig, axes = plt.subplots()
        lines, sm = plot_lines(axes, *plot_data, **kwargs)

        x_lab, y_lab, value_label = hdf_map.generate_ids(xaxis, yaxis, value, modify_missing=False)
        axes.set_xlabel(x_lab)
        axes.set_ylabel(y_lab)
        axes.set_title(self.exp.generate_scans_title(*scan_files, hdf_map=hdf_map))

        plt.colorbar(sm, ax=axes, label=value_label)
        return axes

    def multi_plot(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                   xaxis: str = 'axes', yaxis: str | list[str] = 'signal', value: str | None = None,
                   subplots: tuple[int, int] = (4, 4), **kwargs) ->  list[tuple[plt.Figure, plt.Axes]]:
        """
        Create matplotlib figure with a line plot from a or several scans

            axes = exp.plot.multi_plot(*range(-10, 0), xaxis='eta', yaxis='roi2_sum', value='Tsample')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or path of array to plot on x axis
        :param yaxis: str name or path of array to plot on y axis, or a list of names for multiple plots per axis
        :param value: str name or path of float value to distinguish lines
        :param subplots: [int, int] number of subplots per figure [vertical, horizontal]
        :param kwargs: given directly to plt.plot(..., **kwars)
        :return: list of figures
        """
        scans = self.exp.scans(*scan_files, hdf_map=hdf_map)
        ttl = self.exp.generate_scans_title(*scan_files)
        fig_ax = generate_subplots(len(scan_files), subplots=subplots, suptitle=ttl)

        for scan, (fig, ax) in zip(scans, fig_ax):
            scan.plot.plot(xaxis=xaxis, yaxis=yaxis, axes=ax, **kwargs)
            val = scan.format("\n%s = {%s}" % (value, value)) if value is not None else ""
            ttl_exp = scan.title() + val
            ax.set_title(ttl_exp)
        return fig_ax

    def surface_2d(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                   xaxis: str = 'axes', signal: str = 'signal', values: str | None = None,
                   axes: plt.Axes | None = None, clim: tuple[float, float] | None = None,
                   axlim: str = 'image', **kwargs) -> plt.Axes:
        """
        Create matplotlib figure with a 2D image

            axes = exp.plot.surface_2d(*range(-10, 0), xaxis='eta', signal='roi2_sum', values='Tsample')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or path of array to plot on x axis
        :param signal: str name or path of array to plot on z axis
        :param values: str name or path of float value to distinguish different scans
        :param axes: matplotlib.axes subplot, or None to create a figure
        :param clim: None or [min, max] values for color cutoff from plt.clim
        :param axlim: axis limits from plt.axis
        :param kwargs: given directly to plt.pcolormesh(..., **kwargs)
        :return: axes object
        """
        first_file = self.exp.get_scan_filename(scan_files[0])
        hdf_map = hdfmap.create_nexus_map(first_file) if hdf_map is None else hdf_map
        x, y, z = self.exp.generate_mesh(*scan_files, hdf_map=hdf_map,
                                         axes=xaxis, signal=signal, values=values)

        if axes is None:
            fig, axes = plt.subplots()
        surf = plot_2d_surface(axes=axes, image=z, xdata=x, ydata=y, clim=clim, axlim=axlim, **kwargs)
        axes.set_title(self.exp.generate_scans_title(*scan_files))

        x_lab, y_lab, value_label = hdf_map.generate_ids(xaxis, signal, values, modify_missing=False)
        axes.set_xlabel(x_lab)
        axes.set_ylabel(value_label)
        axes.figure.colorbar(surf, ax=axes, label=signal)
        return axes

    def lines_3d(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                 xaxis: str = 'axes', signal: str = 'signal', values: str | None = None,
                 axes: Axes3D | None = None, legend: bool = False, **kwargs) -> Axes3D:
        """
        Create matplotlib figure with a 2D image

            axes = exp.plot.surface_2d(*range(-10, 0), xaxis='eta', yaxis='roi2_sum', value='Tsample')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or path of array to plot on x axis
        :param signal: str name or path of array to plot on z axis
        :param values: str name or path of float value to distinguish different scans
        :param axes: matplotlib.axes subplot, or None to create a figure
        :param legend: if True, adds a legend
        :param kwargs: given directly to plt.plot(..., **kwargs)
        :return: axes object
        """
        first_file = self.exp.get_scan_filename(scan_files[0])
        hdf_map = hdfmap.create_nexus_map(first_file) if hdf_map is None else hdf_map
        scans = self.exp.scans(*scan_files, hdf_map=hdf_map)
        data_fields = [signal, xaxis] + ([values] if values is not None else [])
        data = self.exp.join_scan_data(*scan_files, hdf_map=hdf_map, data_fields=data_fields)
        labels = [scan.label() for scan in scans]

        if axes is None:
            fig = plt.figure()
            axes = fig.add_subplot(111, projection='3d')
        plot_3d_lines(axes, data[signal], data[xaxis], data.get(values, None), labels=labels, **kwargs)
        axes.set_title(self.exp.generate_scans_title(*scan_files))

        x_lab, signal_label, value_label = hdf_map.generate_ids(xaxis, signal, values, modify_missing=False)
        axes.set_xlabel(x_lab)
        axes.set_ylabel(value_label)
        axes.set_zlabel(signal_label)
        if legend:
            axes.legend()
        return axes

    def surface_3d(self, *scan_files: int | str, hdf_map: hdfmap.NexusMap | None = None,
                   xaxis: str = 'axes', signal: str = 'signal', values: str | None = None,
                   axes: Axes3D | None = None, clim: tuple[float, float] | None = None,
                   axlim: str = 'image', **kwargs) -> Axes3D:
        """
        Create matplotlib figure with a 3D image

            axes = exp.plot.surface_3d(*range(-10, 0), xaxis='eta', yaxis='roi2_sum', value='Tsample')

        :param scan_files: scan number or filename (multiple allowed)
        :param hdf_map: hdfmap object or None
        :param xaxis: str name or path of array to plot on x axis
        :param signal: str name or path of array to plot on z axis
        :param values: str name or path of float value to distinguish different scans
        :param axes: matplotlib.axes3D subplot, or None to create a figure
        :param clim: None or [min, max] values for color cutoff from plt.clim
        :param axlim: axis limits from plt.axis
        :param kwargs: given directly to plt.pcolormesh(..., **kwargs)
        :return: axes object
        """
        first_file = self.exp.get_scan_filename(scan_files[0])
        hdf_map = hdfmap.create_nexus_map(first_file) if hdf_map is None else hdf_map
        x, y, z = self.exp.generate_mesh(*scan_files, hdf_map=hdf_map,
                                         axes=xaxis, signal=signal, values=values)

        if axes is None:
            fig = plt.figure()
            axes = fig.add_subplot(111, projection='3d')
        plot_3d_surface(axes=axes, image=z, xdata=x, ydata=y, clim=clim, axlim=axlim, **kwargs)
        axes.set_title(self.exp.generate_scans_title(*scan_files))

        x_lab, signal_label, value_label = hdf_map.generate_ids(xaxis, signal, values, modify_missing=False)
        axes.set_xlabel(x_lab)
        axes.set_ylabel(value_label)
        axes.set_zlabel(signal_label)
        return axes

    def metadata(self, *scan_files: int | str, values: str | list[str], hdf_map: hdfmap.NexusMap | None = None,
                 axes: plt.Axes | None = None) -> plt.Axes:
        """
        Create matplotlib figure with plot of metadata vs scan number

        :param scan_files: scan number or filename (multiple allowed)
        :param values: field name or path of float value to distinguish different scans
        :param hdf_map: hdfmap object or None
        :param axes: matplotlib.axes subplot, or None to create a figure
        :return: axes object
        """
        scans = self.exp.scans(*scan_files, hdf_map=hdf_map)
        ttl = self.exp.generate_scans_title(*scan_files)

        values = [values] if isinstance(values, str) else values
        data = {
            name: np.array([scan.values(name) for scan in scans])
            for name in values
        }

        x_data = [scan.scan_number() for scan in scans]
        if axes is None:
            fig, axes = plt.subplots()
        for name in data:
            axes.plot(x_data, data[name], '-o', label=name)
        axes.set_xlabel('Scan number')
        axes.legend()
        axes.set_title(ttl)
        return axes
