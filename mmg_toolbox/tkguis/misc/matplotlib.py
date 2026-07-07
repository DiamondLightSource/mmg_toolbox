"""
Useful tkinter functions that use matplotlib
"""
import matplotlib.pyplot as plt
import numpy as np
import pickle
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.colorbar import Colorbar
from matplotlib.collections import QuadMesh
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from .styles import create_root, get_style_background
from .config import C, FIGURE_SIZE, IMAGE_SIZE, FIGURE_DPI, DEFAULT_COLORMAP
from .screen_size import get_figure_size


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
        fig: Figure = pickle.loads(pickle.dumps(self.canvas.figure))
        root = create_root('Figure', parent=self.master)
        TkFigure(root, None, fig, FIGURE_SIZE, FIGURE_DPI)

    def __init__(self, canvas_, parent_):
        # Add additional functions
        self.toolitems += (
            # (name, description, image, function)
            (None, None, None, None),  # seperator
            # ('copy', 'Copy Figure', 'filesave', 'copy_button'),
            ('popout', 'Popout Figure', 'qt4_editor_options', 'popout_figure'),
        )

        NavigationToolbar2Tk.__init__(self, canvas_, parent_)
        bg = get_style_background(parent_)
        self.config(background=bg)


class TkFigure:
    """
    Create a tkinter frame with a single figure
    """
    def __init__(self, root: tk.Misc, config: dict | None = None, fig: plt.Figure | None = None,
                 fig_size: tuple[int, int] | None = None, fig_dpi: int = None):
        self.root = root
        self.config = config or {}
        self.fig = fig or plt.Figure()
        # Set fig size
        fig_size = fig_size or get_figure_size(root, self.config, C.plot_size)
        fig_dpi = fig_dpi or self.config.get(C.plot_dpi, FIGURE_DPI)
        self.fig.set_dpi(fig_dpi)
        self.fig.set_size_inches(fig_size[0], fig_size[1])

        # get the current background
        bg = get_style_background(root)

        try:
            self.fig.patch.set_facecolor(bg)
        except ValueError:
            print(f"Cannot set background color of {bg}")
            bg = '#dcdad5'

        frm = ttk.Frame(root)
        frm.pack(side='left', expand=True, fill='both', pady=2, padx=5)
        self.canvas = FigureCanvasTkAgg(self.fig, frm)
        self.canvas.get_tk_widget().configure(bg='black')
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True, padx=5, pady=2)

        # Toolbar
        frm2 = ttk.Frame(frm)
        frm2.pack(side='top', expand=True, fill='both', padx=5, pady=2)
        # toolbar = NavigationToolbar2Tk(canvas, frm)
        self.toolbar = CustomToolbar(self.canvas, frm2)
        self.toolbar.config(background=bg)
        self.toolbar.update()
        self.toolbar.pack(fill='x')  # , expand=tk.YES)

    def _update(self):
        self.fig.canvas.draw()
        if self.toolbar.winfo_exists():
            self.toolbar.update()

    def duplicate(self, root: tk.Misc, fig_size: tuple[int, int] | None = None, fig_dpi: int = None) -> 'TkFigure':
        fig: Figure = pickle.loads(pickle.dumps(self.fig))
        return TkFigure(root, self.config, fig, fig_size, fig_dpi)

# TODO: replace ini_image with TkFigure type thing
def ini_image(frame: tk.Misc, figure_size: tuple[int, int] | None = None,
              figure_dpi: int | None = None) -> tuple[Figure, Axes, list[Line2D], QuadMesh, Colorbar, CustomToolbar]:
    """
    Create an empty image plot on a tk canvas with toolbar

        fig, ax, plot_list, image, cbar, toolbar = ini_image(frame, figure_size, figure_dpi)
        image.remove()
        image = ax.pcolormesh(image_array, shading='auto')
        colorbar.update_normal(image)
        toolbar.update()
        fig.canvas.draw()

    :param frame: parent frame within which the figure will be placed.
    :param figure_size: size of the figure in inches [horiz, vert], passed to matplotlib.Figure()
    :param figure_dpi: figure DPI, passed to matplotlib.Figure()
    :returns: tuple[Figure, Axes, list[Line2D], Toolbar]
    """
    if figure_size is None:
        figure_size = IMAGE_SIZE
    if figure_dpi is None:
        figure_dpi = FIGURE_DPI

    # get the current background
    bg = get_style_background(frame)

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

    # Colorbar
    # add_colorbar_clim(canvas, fig, ax1_image, cb1, frame)

    # Toolbar
    frm2 = ttk.Frame(frm)
    frm2.pack(side=tk.TOP, expand=tk.NO, fill=tk.X, padx=5, pady=2)
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


def add_colorbar_clim(canvas, fig, im, cbar, root, entry_height=25, pad=5):
    """
    Attach Tkinter Entry boxes for vmin/vmax above and below a Matplotlib colorbar.

    Parameters
    ----------
    canvas : FigureCanvasTkAgg
    fig : matplotlib.figure.Figure
    im : AxesImage (from imshow)
    cbar : matplotlib.colorbar.Colorbar
    root : tk.Tk or tk.Frame (parent widget)
    entry_height : int (pixel height of entry boxes)
    pad : int (padding in pixels)
    """

    canvas_widget = canvas.get_tk_widget()

    # Create Entry widgets
    entry_vmin = tk.Entry(root, width=20, justify="center")
    entry_vmax = tk.Entry(root, width=20, justify="center")

    # Initialize values
    vmin, vmax = im.get_clim()
    entry_vmin.insert(0, f"{vmin:.3g}")
    entry_vmax.insert(0, f"{vmax:.3g}")

    def update_clim(event=None):
        try:
            vmin = float(entry_vmin.get())
            vmax = float(entry_vmax.get())
            if vmin < vmax:
                im.set_clim(vmin, vmax)
                canvas.draw_idle()
        except ValueError:
            pass

    entry_vmin.bind("<Return>", update_clim)
    entry_vmax.bind("<Return>", update_clim)

    def reposition(event=None):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        bbox = cbar.ax.get_window_extent(renderer=renderer)

        x0, y0 = bbox.x0, bbox.y0
        x1, y1 = bbox.x1, bbox.y1

        width = x1 - x0
        height = y1 - y0

        # --- Expand width slightly (colorbar axes are often too tight)
        width *= 10
        x0 -= (width - (x1 - x0)) / 2

        entry_vmax.place(x=x0, y=y0 - entry_height - pad,
                         width=width, height=entry_height)

        entry_vmin.place(x=x0, y=y1 + pad,
                         width=width, height=entry_height)

    # Initial placement
    root.update()
    reposition()

    # Reposition on resize
    canvas_widget.bind("<Configure>", reposition)

    return entry_vmin, entry_vmax


