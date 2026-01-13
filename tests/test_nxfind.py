"""
Test nx_find
"""

import h5py

from . import only_dls_file_system
from .example_files import DIR
from mmg_toolbox.nexus.nexus_functions import nx_find, nx_find_all


@only_dls_file_system
def test_nx_find():
    f = DIR + 'i06/i06-1-372210.nxs'

    with h5py.File(f) as hdf:

        dataset = nx_find(hdf, 'NXdata', 'signal')
        assert isinstance(dataset, h5py.Dataset)
        assert dataset.shape == (500, )

        dataset = nx_find(hdf, 'axes')
        assert isinstance(dataset, h5py.Dataset)
        assert dataset.shape == (500, )
        assert dataset.name == '/entry/fesData/fastEnergy'

        datasets = nx_find_all(hdf, 'axes')
        assert isinstance(datasets, list)
        assert len(datasets) == 6

        dataset = nx_find(hdf, 'NXentry', 'instrument/s1/x_gap')
        assert isinstance(dataset, h5py.Dataset)
        assert dataset.name == '/entry/instrument/s1/x_gap'
