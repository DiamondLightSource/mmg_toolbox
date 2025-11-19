"""
mmg_toolbox tests
Test tkinter dataviewer
"""

import tkinter as tk

from mmg_toolbox.tkguis.misc.styles import create_root
from mmg_toolbox.tkguis.misc.config import default_config, C
from mmg_toolbox.tkguis.widgets.nexus_data_viewer import NexusDataViewer
from . import only_dls_file_system


def test_config():
    config = default_config(beamline='')
    assert C.conf_file in config
    assert C.metadata_string in config
    assert C.default_metadata in config

    config = default_config(beamline='i10-1')
    assert config.get(C.beamline) == 'i10-1'


@only_dls_file_system
def test_widgets():
    config = default_config()

    from mmg_toolbox.tkguis.widgets.title_window import TitleWindow
    root = create_root('test')
    widget = TitleWindow(root, config)
    assert widget
    root.destroy()

    from mmg_toolbox.tkguis.widgets.multi_scan_analysis import MultiScanAnalysis
    root = create_root('test')
    widget = MultiScanAnalysis(root, config)
    assert widget
    root.destroy()

    from mmg_toolbox.tkguis.widgets.peak_fit_analysis import PeakFitAnalysis
    root = create_root('test')
    widget = PeakFitAnalysis(root, config)
    assert widget
    root.destroy()


@only_dls_file_system
def test_data_viewer():
    f = '/dls/science/groups/das/ExampleData/i16/azimuths'

    root = create_root('test')
    config = default_config(beamline='i16')
    widget = NexusDataViewer(root, f, config)
    assert widget
    # Check initial line plotted
    widget.selector_widget.add_folder(f)
    widget.select_first_file()
    widget.on_file_select()
    assert len(widget.plot_widget.plot_list) == 1
    assert len(widget.plot_widget.listbox.get_children()) == 21
    s = "cmd = flyscancn eta_fly 0.002 101 merlin 0.5 0.25 mroi2"
    assert s in widget.detail_widget.textbox.get(1.0, tk.END)

    # Check multi-plot
    folder_iid = next(iter(widget.selector_widget.tree.get_children()))
    scan_items = widget.selector_widget.tree.get_children(folder_iid)
    assert len(scan_items) > 100
    widget.selector_widget.tree.selection_set(*scan_items[:5])
    widget.on_file_select()  # <<TreeviewSelect>>
    assert len(widget.plot_widget.plot_list) == 5

    # Check multi-y-axis
    y_axis_items = widget.plot_widget.listbox.get_children()
    assert len(y_axis_items) == 21
    widget.plot_widget.listbox.selection_set(y_axis_items[:2])
    widget.plot_widget.select_listbox_items()  # <<TreeviewSelect>>
    assert len(widget.plot_widget.plot_list) == 10

    # Check fitting
    widget.selector_widget.tree.selection_set(scan_items[0])
    widget.on_file_select()  # <<TreeviewSelect>>
    assert len(widget.plot_widget.plot_list) == 1
    # perform fit
    widget.plot_widget.perform_fit()
    assert widget.plot_widget._fit_result.amplitude > 1
    assert len(widget.plot_widget.listbox.get_children()) == len(y_axis_items) + 1
    # plot fit
    widget.plot_widget.select_listbox_items()
    assert len(widget.plot_widget.plot_list) == 2


@only_dls_file_system
def test_nexus_viewer_rois():
    f = '/dls/science/groups/das/ExampleData/i16'
    root = create_root('test')
    config = default_config()
    widget = NexusDataViewer(root, f, config)
    assert widget
    # Check initial line plotted
    widget.selector_widget.add_folder(f)
    widget.select_first_file()

    # Select scan
    widget.selector_widget.select_box.set('1041304')
    widget.selector_widget.select_from_box()
    widget.on_file_select()  # <<TreeviewSelect>>
    assert abs(widget.plot_widget.index_line.get_xdata()[0] - 72.69) < 0.01

    # Check detector image
    widget.plot_widget.view_index.set(56)
    widget.plot_widget.update_image()
    image = widget.plot_widget.ax_image.get_array()
    assert image.max() > 100000

    # Add new ROI
    widget.plot_widget.add_roi('test_roi', 152, 208, 63, 54, 'pil3_100k')
    y_axis_items = widget.plot_widget.listbox.get_children()
    y_axis_item = next(iid for iid in y_axis_items if 'test_roi_total' in widget.plot_widget.listbox.item(iid, 'text'))
    widget.plot_widget.listbox.selection_set(y_axis_item)
    widget.plot_widget.select_listbox_items()  # <<TreeviewSelect>>
    assert widget.plot_widget.line.get_ydata().max() > 3e8




