"""
Start tkgui
"""

from mmg_toolbox import start_gui

# start_gui('/dls/science/groups/das/ExampleData/i16/azimuths/1108750.nxs')
# start_gui('/dls/science/groups/das/ExampleData/i16/azimuths')
# start_gui()

from mmg_toolbox.tkguis.apps.nexus import create_nexus_plot_and_image

# create_nexus_plot_and_image('/dls/science/groups/das/ExampleData/i16/azimuths/1108750.nxs')
create_nexus_plot_and_image('/dls/i16/data/2025/nt43883-1/1113041.nxs')
