"""
mmg_toolbox example
Example script using the Experiment class to get files from data folders
"""

import numpy as np
from mmg_toolbox import data_file_reader
from diffraction.lattice import bmatrix

np.set_printoptions(precision=3, suppress=True)

scan = data_file_reader('/dls/science/groups/das/ExampleData/i16/azimuths/1108746.nxs')

a, b, c, alpha, beta, gamma = scan('NXsample_unit_cell')
orientation_matrix = scan('NXsample_orientation_matrix')
ub_matrix = scan('NXsample_ub_matrix')

print(a, b, c, alpha, beta, gamma)
print('orientation_matrix')
print(orientation_matrix)
print('ub_matrix')
print(ub_matrix)
print('b_matrix')
print(np.dot(ub_matrix,  np.linalg.inv(orientation_matrix)))

print('\nCalcualted b matrix')
print(bmatrix(a, b, c, alpha, beta, gamma))