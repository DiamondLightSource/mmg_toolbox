"""
mmg_toolbox tests
Test top-level imports
"""

def test_standard_imports():
    errors = None
    try:
        import mmg_toolbox
        from mmg_toolbox import data_file_reader, Experiment, version_info, module_info
    except ImportError as e:
        errors = e
    assert errors is None


def test_xas_imports():
    errors = None
    try:
        from mmg_toolbox import xas
        from mmg_toolbox.utils.file_functions import replace_scan_number
        from mmg_toolbox.xas.nxxas_loader import is_nxxas
        from mmg_toolbox.xas.spectra_container import average_polarised_scans
        from mmg_toolbox.utils.gda_functions import gda_datavis_file_message
    except ImportError as e:
        errors = e
    assert errors is None


def test_fitting_imports():
    errors = None
    try:
        from mmg_toolbox import fitting
        from mmg_toolbox.fitting import multipeakfit, peakfit
        # from mmg_toolbox.utils import fitting
    except ImportError as e:
        errors = e
    assert errors is None


def test_plotting_imports():
    errors = None
    try:
        from mmg_toolbox import plotting
        from mmg_toolbox.plotting.matplotlib import set_plot_defaults
    except ImportError as e:
        errors = e
    assert errors is None


def test_other_imports():
    errors = None
    try:
        from mmg_toolbox.diffraction.lattice import bmatrix, cal2theta
        from mmg_toolbox.diffraction.msmapper import update_msmapper_nexus
    except ImportError as e:
        errors = e
    assert errors is None

