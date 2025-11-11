"""

"""

import tkinter as tk

from mmg_toolbox.tkguis.misc.functions import topmenu, select_hdf_file
from mmg_toolbox.tkguis.misc.styles import RootWithStyle, create_root


def create_nexus_viewer(filename: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    File Viewer of the NeXus structure
    """
    from mmg_toolbox.tkguis.widgets.hdf_viewer import HDFViewer

    root = create_root(parent=parent, window_title='NeXus File Viewer')

    widget = HDFViewer(root, filename, config)

    menu = {
        'File': {
            'Open': widget.select_file
        },
    }
    topmenu(root, menu, add_themes=False, add_about=True)

    if parent is None:
        root.mainloop()
    return root


def create_nexus_plotter(*filenames: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 1D line data from a NeXus file
    """
    from ..widgets.nexus_plot import NexusDefaultPlot
    from mmg_toolbox.tkguis.apps.config_editor import ConfigEditor

    root = create_root('NeXus File Default Plot', parent=parent)
    widget = NexusDefaultPlot(root, *filenames, config=config)

    def load_file():
        new_filename = select_hdf_file(root)
        if new_filename:
            widget.update_data_from_files(new_filename)

    menu = {
        'File': {
            'Open': load_file,
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }

    topmenu(root, menu, add_themes=False, add_about=True)
    if parent is None:
        root.mainloop()
    return root


def create_nexus_image_plotter(filename: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 2D images from detectors in a NeXus file, including a slider
    """
    from ..widgets.nexus_image import NexusDetectorImage

    root = create_root(parent=parent, window_title='NeXus File Image Plot')

    widget = NexusDetectorImage(root, filename, config)

    def load_file():
        new_filename = select_hdf_file(root)
        if new_filename:
            widget.update_image_data_from_file(new_filename)

    menu = {
        'File': {
            'Open': load_file,
        },
    }
    topmenu(root, menu, add_themes=False, add_about=True)

    if parent is None:
        root.mainloop()
    return root


def create_nexus_plot_and_image(*filenames: str, parent: tk.Misc | None = None, config: dict | None = None) -> RootWithStyle:
    """
    Plot 1D line and image data from a NeXus file
    """
    from ..widgets.nexus_plot_and_image import NexusPlotAndImage
    from mmg_toolbox.tkguis.apps.config_editor import ConfigEditor

    root = create_root('NeXus File Default Plot', parent=parent)
    widget = NexusPlotAndImage(root, *filenames, config=config, horizontal_alignment=True)

    def load_file():
        new_filename = select_hdf_file(root)
        if new_filename:
            widget.update_data_from_files(new_filename)

    menu = {
        'File': {
            'Open': load_file,
        },
        'Config.': {
            'Edit Config.': lambda: ConfigEditor(root, config),
        }
    }

    topmenu(root, menu, add_themes=False, add_about=True)
    if parent is None:
        root.mainloop()
    return root


