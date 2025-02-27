"""
test user interface
"""

from mmg_toolbox.tkguis.styles import create_root
from mmg_toolbox.tkguis.widgets.python_editor import PythonEditor
from mmg_toolbox.tkguis.widgets.folder_treeview import NexusFolderTreeViewFrame
from mmg_toolbox.tkguis.widgets.nexus_treeview import HDFViewer
from mmg_toolbox.tkguis.widgets.simple_plot import NexusDefaultPlot

if __name__ == '__main__':
    # root = create_root('Test')
    # NexusFolderTreeViewFrame(root)
    # root.mainloop()

    f = "/scratch/grp66007/data/i16/das_example_data/1041304.nxs"
    # HDFViewer(f)
    obj = NexusDefaultPlot(f)
    obj.root.mainloop()

