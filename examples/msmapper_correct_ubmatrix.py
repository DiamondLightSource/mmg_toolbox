"""

"""

import numpy as np
import h5py
import hdfmap
from mmg_toolbox.diffraction.lattice import bmatrix

old_file = '/scratch/grp66007/data/IrTe2 Data and HKL scan/1043567.nxs'
old_file = '/scratch/grp66007/data/IrTe2 Data and HKL scan/1069511.nxs'
new_file = old_file.replace('.nxs', '_corrected.nxs')

diffcalc2nex = [[1, 0 ,0], [0, 0, -1], [0, 1, 0]]
diffcalc2lab = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
nex2lab = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]

m = hdfmap.create_nexus_map(old_file)

vector_paths = [
    '/instrument/transformations/delta',
    '/instrument/transformations/gamma',
    '/instrument/transformations/offsetdelta',
    '/sample/transformations/kappa',
    '/sample/transformations/mu',
    '/sample/transformations/phi',
    '/sample/transformations/theta',
    '/instrument/pil3_100k/module/fast_pixel_direction',
    '/instrument/pil3_100k/module/module_offset',
    '/instrument/pil3_100k/module/slow_pixel_direction',
    '/instrument/pil3_100k/transformations/origin_offset',
]

print(new_file)
with h5py.File(old_file, 'r') as orig, h5py.File(new_file, 'w') as new:
    entry = '/entry' if 'entry' in orig['/'] else '/entry1'
    orig.copy(entry, new['/'], entry)

    diffcalc_ub = m.eval(orig, 'array([[UB11, UB12, UB13], [UB21, UB22, UB23], [UB31, UB32, UB33]]) / (2 * pi)')
    unit_cell = m.get_data(orig, 'unit_cell')
    orientation_matrix = m.get_data(orig, 'orientation_matrix', default=np.eye(3))
    old_ub = m.get_data(orig, 'ub_matrix')
    b = bmatrix(*unit_cell)
    ub = orientation_matrix @ b

    dls_ub = diffcalc2lab @ diffcalc_ub
    chk_ub = nex2lab @ old_ub
    dls_or = nex2lab @ orientation_matrix

    print(f"Old ub:\n{old_ub}\nCheck U.B:\n{ub}\nDLS ub:\n{dls_ub}\nCheck DLS ub:\n{chk_ub}")

    print('\nChange ub_matrix and orientation matrix')
    new[entry + '/sample/ub_matrix'][0] = dls_ub
    if entry + '/sample/orientation_matrix' in new:
        new[entry + '/sample/orientation_matrix'][0] = dls_or

    print('\nChange vectors')
    for path in vector_paths:
        old_vector = new[entry + path].attrs['vector']
        new_vector = nex2lab @ old_vector
        new[entry + path].attrs['vector'] = new_vector
        print(f"{entry + path}: {old_vector} -> {new_vector}")

    # add units to delta_offset
    new[entry + '/instrument/transformations/offsetdelta'].attrs['units'] = b'deg'

print(f"Created updated file: {new_file}")