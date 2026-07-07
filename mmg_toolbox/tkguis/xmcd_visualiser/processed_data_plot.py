"""

"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from h5py import is_hdf5

from mmg_toolbox.xas import SpectraContainerSubtraction
from mmg_toolbox.xas.nxxas_loader import load_xas_scans, is_subtraction
from mmg_toolbox.plotting.matplotlib import plot_lines, plot_3d_lines

from ..misc.logging import create_logger
from ..misc.functions import show_error, select_hdf_file
from ..widgets.treeview import CanvasTreeview
from ..widgets.simple_plot import SimplePlot
from .widget import XMCDVisualiser

logger = create_logger(__file__)
METADATA_OPTIONS = {
    # OptionMenu: XasMetadata
    'Temperature': 'temp',
    'Field': 'mag_field',
    'Pitch': 'pitch'
}


def load_subtraction_file(root: tk.Misc, initial_directory: str | None = None) -> str | None:
    filename = select_hdf_file(root, initial_directory)
    if filename and not is_subtraction(filename):
        messagebox.showwarning(
            title='File must be a processed XMCD file',
            message=f"File: \n{filename}\n is not an XAS Subtraction file.",
            parent=root
        )
        filename = None
    return filename


class ProcessedTreeView(CanvasTreeview):
    """Treeview object for peak details of scans"""
    def __init__(self, root: tk.Misc, width: int | None = None, height: int | None = None):
        self._spectra_check: list[tuple[SpectraContainerSubtraction, tk.BooleanVar]] = []
        self._current_id: int = 0
        columns = [
            # name, title, width, reverse, sort_col
            ('#0', "Name", 400, False, None),
            ('scan', "Scan", 100, False, None),
            ('filename', "Filename", 0, False, None),
            ('index', "index", 0, False, None),
        ]
        super().__init__(root, *columns, width=width, height=height)

    def populate(self, *scans: SpectraContainerSubtraction):
        self.delete()
        for scan in scans:
            self.add_scan(scan)

    def add_scan(self, scan: SpectraContainerSubtraction):
        if not isinstance(scan, SpectraContainerSubtraction):
            show_error(
                message=f"Object {repr(scan)} is not SpectraContainerSubtraction",
                parent=self.root,
                raise_exception=True
            )
        if scan.metadata.filename:
            name = os.path.basename(scan.metadata.filename).rstrip('.nxs')
        else:
            name = scan.label()
        scan_no = scan.get_raw_metadata('scan_no')
        filename = scan.metadata.filename
        selected = tk.BooleanVar(self.root, True)
        values = (str(scan_no), filename, str(self._current_id))
        self.tree.insert("", tk.END, text=name, values=values)
        self._spectra_check.append((scan, selected))
        self._current_id += 1

    def get_selected_objects(self) -> list[tuple[SpectraContainerSubtraction, tk.BooleanVar]]:
        return [
            self._spectra_check[int(self.tree.set(iid, 'index'))]
            for iid in self.tree.selection()
        ]


class Comparison:
    """
    tkinter widget containing scan pair selector, grid plot and average plot

    widget = XMCD_Visualiser(root, 'initial/folder', config)
    """

    def __init__(self, root: tk.Misc, base: XMCDVisualiser):
        from .grid_plot import GridPlot
        self._base = base
        self.root = root
        self.output_name = tk.StringVar(self.root, '')
        self.selection: list[tk.BooleanVar] = []
        self.metadata_option = tk.StringVar(self.root, 'Temperature')

        # Comparison Tab
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        grid_options = dict(padx=5, pady=5, sticky='nsew')

        tab = ttk.Frame(self.root)
        tab.grid(column=0, row=0, **grid_options)
        tab.columnconfigure(0, weight=0)  # set window resize properties
        tab.columnconfigure(1, weight=1)  # only resize middle panel
        tab.columnconfigure(2, weight=0)
        tab.rowconfigure(0, weight=1)

        # LEFT
        frm = ttk.LabelFrame(tab, text='Files')
        frm.grid(column=0, row=0, **grid_options)
        self.treeview = self._data_selection(frm)

        # MIDDLE
        frm = ttk.LabelFrame(tab, text='Select Plots')
        frm.grid(column=1, row=0, **grid_options)
        self.grid_plots = GridPlot(frm, self._base.config)

        # RIGHT
        frm = ttk.LabelFrame(tab, text='Combined Data')
        frm.grid(column=2, row=0, **grid_options)
        self.multiplot = self._comparison_plot(frm)

    def _data_selection(self, frame: tk.Misc) -> ProcessedTreeView:
        ttk.Button(frame, text='Browse Data', command=self.browse_data).pack(side='top', fill='x')

        frm = ttk.Frame(frame)
        frm.pack(side='top', fill='both')
        treeview = ProcessedTreeView(frm)
        treeview.bind_select(self.select)
        return treeview

    def _comparison_plot(self, frame: tk.Misc) -> SimplePlot:
        frm = ttk.Frame(frame)
        frm.pack(side='top', fill='x')
        metadata_options = list(METADATA_OPTIONS)
        ttk.OptionMenu(frm, self.metadata_option, metadata_options[0], *metadata_options,
                       command=self.update_plot).pack(side='top', fill='x', padx=4)

        frm = ttk.Frame(frame)
        frm.pack(side='top', fill='x')
        figure = SimplePlot(
            root=frm,
            xdata=[],
            ydata=[],
            xlabel='Energy [eV]',
            ylabel='',
            title='XMCD Spectra',
            config=self._base.config
        )

        # Buttons
        frm = ttk.Frame(frame)
        frm.pack(side='top', fill='x')
        line = ttk.Frame(frm)
        line.pack(side='top', fill='x')
        ttk.Label(line, text='Filename').pack(side='left')
        ttk.Entry(line, textvariable=self.output_name).pack(side='left')
        # ttk.Button(frm, text='Save NeXus', command=self.btn_nexus).pack(side='top', fill='x')
        # ttk.Button(frm, text='Save CSV', command=self.btn_csv).pack(side='top', fill='x')
        ttk.Button(frm, text='Plot 3D', command=self.btn_plot3).pack(side='top', fill='x')
        return figure

    def select(self, event=None):
        spectra_check = self.treeview.get_selected_objects()
        self.grid_plots.create_grid(*spectra_check, command=self.update_plot)
        self.update_plot()

    def get_selected_scans(self) -> list[SpectraContainerSubtraction]:
        spectra_check = self.treeview.get_selected_objects()
        return [spectra for spectra, check in spectra_check if check.get()]

    def add_processed_file(self, filename: str):
        scan, = load_xas_scans(filename)
        self.treeview.add_scan(scan)

    def browse_data(self):
        # TODO: replace with load_subtraciton_file
        filenames = filedialog.askopenfilenames(
            title='Select file to open',
            filetypes=[('NXS file', '.nxs'),
                       ('HDF file', '.h5'), ('HDF file', '.hdf'), ('HDF file', '.hdf5'),
                       ('All files', '.*')],
            parent=self.root,
        )
        for filename in filenames:
            if is_hdf5(filename) and is_subtraction(filename):
                self.add_processed_file(filename)
            else:
                messagebox.showwarning(
                    title='Incorrect File Type',
                    message=f"File: \n{filename}\n is not a valid processed file",
                    parent=self.root
                )

    def update_plot(self, event=None):
        scans = self.get_selected_scans()
        meta_option = METADATA_OPTIONS[self.metadata_option.get()]
        plot_data = [
            (
                getattr(scan.metadata, meta_option),
                scan.spectra[scan.metadata.default_mode].energy,
                scan.spectra[scan.metadata.default_mode].signal
            )
            for scan in scans
        ]
        self.multiplot.ax1.clear()
        plot_lines(self.multiplot.ax1, *plot_data, line_spec='-')
        self.multiplot.update_axes()

    def btn_plot3(self):
        import matplotlib.pyplot as plt
        plt.ion()
        scans = self.get_selected_scans()
        meta_option = METADATA_OPTIONS[self.metadata_option.get()]
        x_data = [
            getattr(scan.metadata, meta_option) +
            0 * scan.spectra[scan.metadata.default_mode].energy
            for scan in scans
        ]
        y_data = [scan.spectra[scan.metadata.default_mode].energy for scan in scans]
        z_data = [scan.spectra[scan.metadata.default_mode].signal for scan in scans]
        fig, ax = plt.subplots(1, 1, projection='3d')
        plot_3d_lines(ax, z_data, x_data, y_data)
