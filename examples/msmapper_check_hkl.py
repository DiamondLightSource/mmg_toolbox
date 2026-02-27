"""
Check hkl and orientation matrix of msmapper result


"""

import numpy as np

from mmg_toolbox import data_file_reader
from mmg_toolbox.diffraction.lattice import bmatrix

np.set_printoptions(precision=3, suppress=True)


f = '/dls/i16/data/2025/mm41580-1/1114494.nxs'
f = '/scratch/grp66007/data/IrTe2 Data and HKL scan/1043567.nxs'

scan = data_file_reader(f)

# Load ub matrix from file - 3 options
# sample/ub_matrix and ubMeta should be transformed into the DLS lab frame
# xtlinfo should be directly from diffcalc
ub_matrix = scan('sample_ub_matrix').squeeze()
print('sample ub_matrix -> this is in NXsample and should be in the lab frame')
print(ub_matrix)
ub_matrix_ubmeta = scan('ubMeta_ub_matrix').squeeze()
print('ubMeta ub_matrix -> should be the same as sample ub_matrix')
print(ub_matrix_ubmeta)
ub_matrix_xtlinfo = scan('array([[UB11, UB12, UB13], [UB21, UB22, UB23], [UB31, UB32, UB33]]) / (2 * pi)')
print('xtlinfo ub_matrix / 2pi -> this is directly from DiffCalc in the Diffractometer frame')
print(ub_matrix_xtlinfo)

# Check sample and ubMeta
try:
    assert np.sum(np.abs(ub_matrix - ub_matrix_ubmeta)) < 1e-6
except AssertionError:
    print('\n***WARNING: ubMatrix does not match ubMatrix UB***\n\n')

# Determine transformation

orientation_matrix = scan('orientation_matrix').squeeze()
print('orientation_matrix -> this is in NXsample and should be in the lab frame')
print(orientation_matrix)

b_matrix = np.dot(ub_matrix,  np.linalg.inv(orientation_matrix))
print('b_matrix from ub_matrix')
print(b_matrix)
a, b, c, alpha, beta, gamma = scan('sample_unit_cell')
print('b_matrix from lattice parameters')
print(bmatrix(a, b, c, alpha, beta, gamma))

# test transformation
# see https://gerrit.diamond.ac.uk/c/gda/gda-diamond/+/44467/4/configurations/i16-config/scripts/localStationScripts/UBCalcMetadata.py#52
# Diffcalc -> y along beam, x vertical, z horizontal
# Diffcalc-DLS = y_diffcalc -> z_dls, x_diffcalc -> y_dls, z_diffcalc -> x_dls
# transform by [[0, 1, 0], [0, 0, 1], [1, 0, 0]].T
check_ub = np.dot(np.array(ub_matrix_xtlinfo), np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]]))
# check_ub = np.dot(ub_matrix_xtlinfo, np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]]))
print('\n\nsample_ub')
print(ub_matrix)
print('diffcalc_ub')
print(ub_matrix_xtlinfo)
print('check_ub')
print(check_ub)
assert np.sum(np.abs(check_ub - ub_matrix)) < 1e-6

# diffcalc = json.loads(scan('diffcalc_data'))
# print(json.dumps(diffcalc, indent=4))
# diffcalc_ub = np.array(diffcalc['ub_matrix']).squeeze()


