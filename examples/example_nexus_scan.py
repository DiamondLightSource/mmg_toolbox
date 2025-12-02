"""
mmg_toolbox example
Example script using the Experiment class to get files from data folders
"""

from mmg_toolbox import data_file_reader

scan = data_file_reader('/dls/science/groups/das/ExampleData/i16/azimuths/1108746.nxs', beamline='i16')

print(scan)

scan.plot.plot()
scan.plot.show()

