"""
test user interface
"""

# # from mmg_toolbox.tkguis.styles import create_root
# from mmg_toolbox.tkguis.widgets.python_editor import PythonEditor
# # from mmg_toolbox.tkguis.widgets.folder_treeview import NexusFolderTreeViewFrame
# from mmg_toolbox.tkguis.widgets.nexus_treeview import HDFViewer
# from mmg_toolbox.tkguis.widgets.simple_plot import NexusDefaultPlot
from mmg_toolbox.tkguis import create_file_browser
from mmg_toolbox.tkguis.misc.logging import set_all_logging_level

if __name__ == '__main__':
    set_all_logging_level('debug')
    window = create_file_browser()

    # f = "/scratch/grp66007/data/i16/das_example_data/1041304.nxs"
    # # HDFViewer(f)
    # obj = NexusDefaultPlot(f)
    # obj.root.mainloop()

