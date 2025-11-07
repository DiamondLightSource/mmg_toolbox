"""
Matplotlib plotting functions

e.g.
>> set_plot_defaults()
>> axs = create_multiplot(2, 2, title='New figure')
>> plot_line(axs[0], x, y)
>> plot_line(axs[1], x2, y2, label='data 2')
>> plot_lines(ax[2], x, [y, y2])
>> plot_detector_image(ax[3], image)
>> labels('title', 'x', 'y', legend=True, axes=axs[0])
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import Axes, Line2D
from matplotlib.collections import QuadMesh
from matplotlib.patches import Polygon, Rectangle
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

DEFAULT_FONTSIZE = 14
FIG_SIZE = [12, 8]
FIG_DPI = 80
DEFAULT_CMAP = 'viridis'


'----------------------------Plot manipulation--------------------------'


def set_plot_defaults(rcdefaults=False):
    """
    Set custom matplotlib rcparams, or revert to matplotlib defaults
    These handle the default look of matplotlib plots
    See: https://matplotlib.org/stable/tutorials/introductory/customizing.html#the-default-matplotlibrc-file
    :param rcdefaults: False*/ True, if True, revert to matplotlib defaults
    :return: None
    """
    if rcdefaults:
        print('Return matplotlib rcparams to default settings.')
        plt.rcdefaults()
        return

    plt.rc('figure', figsize=FIG_SIZE, dpi=FIG_DPI, autolayout=False)
    plt.rc('lines', marker='o', color='r', linewidth=2, markersize=6)
    plt.rc('errorbar', capsize=2)
    plt.rc('legend', loc='best', frameon=False, fontsize=DEFAULT_FONTSIZE)
    plt.rc('axes', linewidth=2, titleweight='bold', labelsize='large')
    plt.rc('xtick', labelsize='large')
    plt.rc('ytick', labelsize='large')
    plt.rc('axes.formatter', limits=(-3, 3), offset_threshold=6)
    plt.rc('image', cmap=DEFAULT_CMAP)  # default colourmap, see https://matplotlib.org/stable/gallery/color/colormap_reference.html
    # Note font values appear to only be set when plt.show is called
    plt.rc(
        'font',
        family='serif',
        style='normal',
        weight='bold',
        size=DEFAULT_FONTSIZE,
        serif=['Times New Roman', 'Times', 'DejaVu Serif']
    )
    # plt.rcParams["savefig.directory"] = os.path.dirname(__file__) # Default save directory for figures


def generate_subplots(n_plots: int, subplots: tuple[int, int] = (4, 4), ax_size: tuple[float, float] = (5, 3),
                      suptitle: str | None = None) -> list[tuple[plt.Figure, Axes]]:
    """
    Generate a grid of n_plots.
    If n_plots is larger than the number of subplots on a figure, multiple figures will be generated.

        fig_ax = generate_subplots(25, subplots=(4, 4), suptitle='plots')
        for fig, ax in fig_ax:
            ax.plot(x, y)

    :param n_plots: number of subplots to generate
    :param subplots: [nrows, ncols] number of subplots to generate per figure [vertical, horizontal]
    :param ax_size: [horiz, vert] size of each axis in inches (scaled by dpi)
    :param suptitle: title of each figure (the figure number will be appended)
    :return: list of (fig, axes), length n_plots
    """
    nrows, ncols = subplots
    n_figures = int(np.ceil(n_plots / float(nrows * ncols)))
    hsize, vsize = ax_size

    fig_ax = []
    for n in range(n_figures):
        fig, axs = plt.subplots(nrows, ncols, figsize=[hsize * ncols, vsize * nrows], dpi=FIG_DPI)
        fig.subplots_adjust(hspace=0.35, wspace=0.32, left=0.07, right=0.97)
        if suptitle is not None:
            fig.suptitle(suptitle + f" {n+1}/{n_figures}" if n_figures > 1 else "")
        ax_list = [(fig, ax) for ax in axs.flatten()]
        for fig, ax in ax_list[n_plots:]:
            ax.set_axis_off()
        fig_ax.extend(ax_list[:n_plots])
        n_plots -= len(ax_list)
    return fig_ax


def plot_line(axes: Axes, xdata: np.ndarray, ydata: np.ndarray, yerrors: np.ndarray | None = None,
              line_spec: str = '-o', *args, **kwargs) -> list[Line2D]:
    """
    Plot line on given matplotlib axes subplot
    Uses matplotlib.plot or matplotlib.errorbar if yerrors is not None
    :param axes: matplotlib figure or subplot axes, None uses current axes
    :param xdata: array data on x axis
    :param ydata: array data on y axis
    :param yerrors: array errors on y axis (or None)
    :param line_spec: str matplotlib.plot line_spec
    :param args: additional arguments
    :param kwargs: additional arguments
    :return: output of plt.plot [line], or plt.errorbar [line, xerrors, yerrors]
    """
    if yerrors is None:
        lines = axes.plot(xdata, ydata, line_spec, *args, **kwargs)
    else:
        lines = axes.errorbar(xdata, ydata, yerrors, *args, fmt=line_spec, **kwargs)
    return lines


PlotData = tuple[float | None, np.ndarray, np.ndarray, np.ndarray] | tuple[float | None, np.ndarray, np.ndarray]

def plot_lines(axes: Axes, *plot_data: PlotData,
               cmap: str = DEFAULT_CMAP, line_spec: str = '-o', **kwargs) -> tuple[list[Line2D], plt.cm.ScalarMappable]:
    """
    Plot lines on given matplotlib axes subplot
    Uses matplotlib.plot or matplotlib.errorbar if yerrors is not None
    :param axes: matplotlib figure or subplot axes, None uses current axes
    :param plot_data: [value, xdata, ydata, yerrors] or [value, xdata, ydata]
    :param cmap: name of colormap to generate colour variation in lines
    :param line_spec: str or list[m] of str matplotlib.plot line_spec
    :param kwargs: additional arguments
    :return: output of plt.plot [line], or plt.errorbar [line, xerrors, yerrors]
    :return: ScalarMappable for use in colorbar
    """

    cdata = np.array([data[0] for data in plot_data])
    if None in cdata:
        cdata = np.arange(len(plot_data))
    norm = plt.Normalize()
    cnorm = norm(cdata)
    # cnorm = cdata - (cdata.min() - max(0.05 * ))
    # cnorm = cnorm / cnorm.max()
    cols = plt.get_cmap(cmap)(cnorm)

    # Create ScalarMappable for colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap)
    sm.set_array(cdata)

    lines = []
    for data, col in zip(plot_data, cols):
        value, x, y, err = (data + (None, ) * 3)[:4]
        if y is None:
            y = x
            x = np.arange(y)
        lines.extend(plot_line(axes, x, y, err, line_spec, c=col, **kwargs))
    return lines, sm


def plot_image(axes: Axes, image: np.ndarray, clim: tuple[float, float] = None,
               *args, **kwargs) -> Axes:
    """
    Plot 2D image
    :param axes: matplotlib figure or subplot axes, None uses current axe
    :param image: 2d array image data
    :param clim: None or [min, max] values for color cutoff
    :param args: additional arguments for plt.pcolormesh
    :param kwargs: additional arguments for plt.pcolormesh
    :return: axes object
    """

    if 'shading' not in kwargs.keys():
        kwargs['shading'] = 'gouraud'
    if clim:
        kwargs['vmin'] = clim[0]
        kwargs['vmax'] = clim[1]

    axes.pcolormesh(image, *args, **kwargs)
    axes.invert_yaxis()
    axes.axis('image')
    return axes


def plot_2d_surface(axes: Axes, image: np.ndarray,
                    xdata: np.ndarray | None = None, ydata: np.ndarray = None,
                    clim: tuple[float, float] = None, axlim: str = 'image', **kwargs) -> QuadMesh:
    """
    Plot 2D data as colourmap surface
    :param axes: matplotlib figure or subplot axes, None uses current axe
    :param image: 2d array image data
    :param xdata: array data, 2d or 1d
    :param ydata: array data 2d or 1d
    :param clim: None or [min, max] values for color cutoff from plt.clim
    :param axlim: axis limits from plt.axis
    :param kwargs: additional arguments for plt.pcolormesh
    :return: output of plt.pcolormesh
    """

    if 'shading' not in kwargs:
        kwargs['shading'] = 'gouraud'
    if clim:
        kwargs['vmin'] = clim[0]
        kwargs['vmax'] = clim[1]

    if xdata is None or ydata is None:
        surface = axes.pcolormesh(image, **kwargs)
    else:
        if np.ndim(xdata) == 1 and np.ndim(ydata) == 1:
            ydata, xdata = np.meshgrid(ydata, xdata)
        surface = axes.pcolormesh(xdata, ydata, image, **kwargs)
    axes.axis(axlim)
    return surface


def plot_3d_lines(axes: Axes3D, zdata: list[np.ndarray],
                  xdata: list[np.ndarray] | None = None, ydata: list[np.ndarray] | None = None,
                  labels: list[str] | None = None, **kwargs) -> list[Line2D]:
    """
    Plot 2D image data as 3d surface
    :param axes: matplotlib figure or subplot axes, None uses current axe
    :param zdata: 2d array [n, m]
    :param xdata: array data, 2d or 1d
    :param ydata: array data 2d or 1d
    :param labels: list of labels for each line, or None
    :param kwargs: additional arguments for plt.plot
    :return: output of plt.plot
    """
    lines = []
    for n, z in enumerate(zdata):
        x = np.arange(z.shape[0]) if xdata is None else xdata[n]
        y = n * np.ones(z.shape[0]) if ydata is None else ydata[n]
        if y.size == 1:
            y = y * np.ones(z.shape[0])
        if labels is not None:
            kwargs['label'] = labels[n]
        lines.extend(axes.plot(x, y, z, **kwargs))
    return lines


def plot_3d_surface(axes: Axes3D, image: np.ndarray,
                    xdata: np.ndarray | None = None, ydata: np.ndarray | None = None,
                    samples: int | None = None, clim: tuple[int, int] | None = None,
                    axlim: str = 'auto', **kwargs) -> Poly3DCollection:
    """
    Plot 2D image data as 3d surface
    :param axes: matplotlib figure or subplot axes, None uses current axe
    :param image: 2d array image data
    :param xdata: array data, 2d or 1d
    :param ydata: array data 2d or 1d
    :param samples: max number of points to take in each direction, by default does not downsample
    :param clim: None or [min, max] values for color cutoff from plt.clim
    :param axlim: axis limits from plt.axis
    :param kwargs: additional arguments for plt.plot_surface
    :return: output of plt.plot_surface
    """
    if samples:
        kwargs['rcount'] = samples
        kwargs['ccount'] = samples
    else:
        # default in plot_surface is 50
        kwargs['rcount'],  kwargs['ccount'] = np.shape(image)
    if clim:
        kwargs['vmin'] = clim[0]
        kwargs['vmax'] = clim[1]

    if xdata is None or ydata is None:
        surface = axes.plot_surface(image, **kwargs)
    else:
        if np.ndim(xdata) == 1 and np.ndim(ydata) == 1:
            ydata, xdata = np.meshgrid(ydata, xdata)
        surface = axes.plot_surface(xdata, ydata, image, **kwargs)
    axes.axis(axlim)
    return surface



def set_span_bounds(span: Rectangle | Polygon, xmin: float, xmax: float, ymin: float, ymax: float):
    """Set bounds for span=ax.axvspan, working for old matplotlib versions"""
    if hasattr(span, "set_bounds"):
        # Rectangle patch
        width = xmax - xmin
        height = ymax - ymin
        span.set_bounds(xmin, ymin, width, height)
    else:
        # Polygon patch: update vertices
        new_verts = [
            (xmin, ymin),
            (xmin, ymax),
            (xmax, ymax),
            (xmax, ymin),
            (xmin, ymin),
        ]
        span.set_xy(new_verts)
