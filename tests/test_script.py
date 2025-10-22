"""
test user interface
"""

import numpy as np
from mmg_toolbox.tkguis.misc.styles import create_root
# from mmg_toolbox.tkguis.widgets.python_editor import PythonEditor
# # from mmg_toolbox.tkguis.widgets.folder_treeview import NexusFolderTreeViewFrame
# from mmg_toolbox.tkguis.widgets.nexus_treeview import HDFViewer
# from mmg_toolbox.tkguis.widgets.simple_plot import NexusDefaultPlot
from mmg_toolbox.tkguis import create_nexus_file_browser, create_data_viewer, create_title_window
from mmg_toolbox.tkguis.widgets.scan_selector import FolderScanSelector
# from mmg_toolbox.tkguis.widgets.nexus_details import NexusDetails
from mmg_toolbox.tkguis.widgets.nexus_image import NexusDetectorImage
from mmg_toolbox.tkguis.misc.logging import set_all_logging_level
from mmg_toolbox.tkguis.misc.matplotlib import ini_image

if __name__ == '__main__':
    pass
    # set_all_logging_level('debug')
    # window = create_file_browser()

    # f = "/scratch/grp66007/data/i16/das_example_data/1041304.nxs"
    # f = r"C:\Users\grp66007\OneDrive - Diamond Light Source Ltd\I16\Nexus_Format\example_nexus\1041304.nxs"
    # root = create_root('details')
    # NexusDetails(root, hdf_filename=f)
    # root.mainloop()

    # # HDFViewer(f)
    # obj = NexusDefaultPlot(f)
    # obj.root.mainloop()

    # root = create_root('folder')
    # root.geometry('200x300')
    # FolderScanSelector(root)
    # root.mainloop()

    # create_data_viewer(r"C:\Users\grp66007\OneDrive - Diamond Light Source Ltd\I16\Nexus_Format\example_nexus")
    # create_title_window()

    # root = create_root('image')
    # NexusDetectorImage(root, hdf_filename=r"C:\Users\grp66007\OneDrive - Diamond Light Source Ltd\I16\Nexus_Format\example_nexus\1041304.nxs")
    # root.mainloop()

    # root = create_root('Image')
    # fig, ax, ax_image, colorbar, toolbar = ini_image(root)
    # ax_image.remove()
    # ax_image = ax.pcolormesh(10 * np.random.rand(200, 50), shading='auto')
    # ax.set_xlim([0, 50])
    # ax.set_ylim([0, 200])
    # fig.canvas.draw()
    # root.mainloop()




