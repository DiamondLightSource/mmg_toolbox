"""
mmg_toolbox tests
Test tkinter dataviewer
"""

from mmg_toolbox.tkguis import create_title_window, create_data_viewer, create_nexus_viewer, create_nexus_file_browser
from . import only_dls_file_system


def test_file_loader():
    # currently don't have a good way of doing this
    # root.mainloop() calls freeze the test
    assert True

