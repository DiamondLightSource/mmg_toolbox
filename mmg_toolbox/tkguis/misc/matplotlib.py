"""
Useful tkinter functions that use matplotlib
"""
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from .styles import create_root

# parameters
FIGURE_SIZE = (8, 3)
IMAGE_SIZE = (8, 3)
FIGURE_DPI = 60
SMALL_FIGURE_DPI = 40
COLORMAPS = ['viridis', 'Spectral', 'plasma', 'inferno', 'Greys', 'Blues', 'winter', 'autumn',
             'hot', 'hot_r', 'hsv', 'rainbow', 'jet', 'twilight', 'hsv']
DEFAULT_COLORMAP = 'twilight'


class CustomToolbar(NavigationToolbar2Tk):
    """Customised version of matplotlib toolbar with added popout and copy functions"""

    def copy_button(self):
        """Copy figure to clipboard - doesn't currently work"""
        import io
        from PIL import Image
        # print(self.canvas.figure.canvas.tostring_rgb())
        image_buffer, (width, height) = self.canvas.figure.canvas.print_to_buffer()
        img = Image.frombytes("RGBA", (width, height), image_buffer)
        io_buffer = io.BytesIO()
        img.save(io_buffer, format='PNG')
        io_buffer.seek(0)
        self.master.clipboard_clear()
        self.master.clipboard_append(io_buffer.getvalue(), format="image/png")  # adds byte array to buffer but isn't interpreted

    def popout_figure(self):
        """Create a new tk window and display figure"""
        root = create_root('Figure', parent=self.master)
        fig, ax1, plot_list, toolbar = ini_plot(root, FIGURE_SIZE, FIGURE_DPI)

        for old_ax in self.canvas.figure.get_axes():
            ax1.set_title(old_ax.title.get_text())
            ax1.set_xlabel(old_ax.get_xlabel())
            ax1.set_ylabel(old_ax.get_ylabel())
            for line in old_ax.lines:
                ax1.plot(line.get_xdata(), line.get_ydata())

    def __init__(self, canvas_, parent_):
        # Add additional functions
        self.toolitems += (
            # (name, description, image, function)
            (None, None, None, None),  # seperator
            # ('copy', 'Copy Figure', 'filesave', 'copy_button'),
            ('popout', 'Popout Figure', 'qt4_editor_options', 'popout_figure'),
        )
        NavigationToolbar2Tk.__init__(self, canvas_, parent_)


def ini_plot(frame: tk.Misc, figure_size: tuple[int, int] | None = None,
             figure_dpi: int | None = None) -> tuple[Figure, Axes, list[Line2D], NavigationToolbar2Tk]:
    """Create a lineplot on a tk canvas with toolbar"""
    if figure_size is None:
        figure_size = FIGURE_SIZE
    if figure_dpi is None:
        figure_dpi = FIGURE_DPI

    # get the current background
    style = ttk.Style()
    bg = style.lookup('.', 'background')

    fig = Figure(figsize=figure_size, dpi=figure_dpi)
    try:
        fig.patch.set_facecolor(bg)
    except ValueError:
        print(f"Cannot set background color of {bg}")
        bg = '#dcdad5'
    # fig.subplots_adjust(left=0.2, bottom=0.2)
    # Amplitude
    ax1 = fig.add_subplot(111)
    ax1.set_autoscaley_on(True)
    ax1.set_autoscalex_on(True)
    ax1.set_xlabel(u'Axis 0')
    ax1.set_ylabel(u'Axis 1')
    ax1.set_title('filename')
    plot_list: list[plt.Line2D] = []

    frm = ttk.Frame(frame)
    # TODO: provide pack options input to control packing options
    frm.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH, pady=2, padx=5)
    canvas = FigureCanvasTkAgg(fig, frm)
    canvas.get_tk_widget().configure(bg='black')
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=5, pady=2)

    # Toolbar
    frm2 = ttk.Frame(frm)
    frm2.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=5, pady=2)
    # toolbar = NavigationToolbar2Tk(canvas, frm)
    toolbar = CustomToolbar(canvas, frm2)
    toolbar.config(background=bg)
    toolbar.update()
    toolbar.pack(fill=tk.X)#, expand=tk.YES)
    return fig, ax1, plot_list, toolbar


def ini_image(frame: tk.Misc, figure_size: tuple[int, int] | None = None, figure_dpi: int | None = None):
    """Create an image plot on a tk canvas with toolbar"""
    if figure_size is None:
        figure_size = IMAGE_SIZE
    if figure_dpi is None:
        figure_dpi = FIGURE_DPI

    # get the current background
    style = ttk.Style()
    bg = style.lookup('.', 'background')

    fig = Figure(figsize=figure_size, dpi=figure_dpi)
    try:
        fig.patch.set_facecolor(bg)
    except ValueError:
        print(f"Cannot set background color of {bg}")
        bg = '#dcdad5'

    ax1 = fig.add_subplot(111)
    # zeros = np.array([[0 for n in range(10)] for m in range(10)])
    xvals = np.arange(100)
    yvals = np.arange(100)
    default = np.random.rand(100, 100)
    ax1_image = ax1.pcolormesh(xvals, yvals, default, shading='auto', cmap=DEFAULT_COLORMAP)
    ax1.set_xlabel(u'Axis 0')
    ax1.set_ylabel(u'Axis 1')
    ax1.set_xlim([0, 100])
    ax1.set_ylim([0, 100])
    cb1 = fig.colorbar(ax1_image, ax=ax1)
    ax1.axis('image')
    plot_list: list[plt.Line2D] = []

    frm = ttk.Frame(frame)
    frm.pack(expand=tk.YES, fill=tk.BOTH, pady=2, padx=5)
    # frm.configure(bg=bg)
    canvas = FigureCanvasTkAgg(fig, frm)
    # canvas.get_tk_widget().configure(bg=bg)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES, padx=5, pady=2)

    # Toolbar
    frm2 = ttk.Frame(frm)
    frm2.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH, padx=5, pady=2)
    # toolbar = NavigationToolbar2Tk(canvas, frm)
    toolbar = CustomToolbar(canvas, frm2)
    toolbar.config(background=bg)
    toolbar.update()
    toolbar.pack(fill=tk.X, expand=tk.YES)
    return fig, ax1, plot_list, ax1_image, cb1, toolbar


def add_rectangle(ax: Axes, left: float, bottom: float, width: float, height: float) -> Rectangle:
    """Add rectangle to axes"""
    rect = Rectangle((left, bottom), width, height, fill=False, edgecolor='black', facecolor='white', zorder=2)
    ax.add_patch(rect)
    return rect