"""
Test autoprocessing notebooks using papermill
"""

import os
import h5py
from . import only_dls_file_system
from .example_files import FILES_DICT

NOTEBOOKS = os.path.join(os.path.dirname(__file__), '..', 'notebooks')
NB_PATHS = {
    name: os.path.join(NOTEBOOKS, name)
    for name in os.listdir(NOTEBOOKS) if name.endswith('.ipynb')
}


@only_dls_file_system
def test_autoprocess_xas_notebook():
    import papermill as pm
    pm.execute_notebook(
        NB_PATHS['xas_notebook.ipynb'],
        'output.ipynb',
        parameters={
            'inpath': FILES_DICT['i06-1 zacscan'],
            'outpath': 'output.nxs',
        }
    )
    assert os.path.isfile('output.ipynb')
    assert os.path.isfile('output.nxs')

    with h5py.File('output.nxs', 'r') as hdf:
        assert isinstance(hdf['/entry/divide_by_preedge/tey'], h5py.Dataset)

    os.remove('output.ipynb')
    os.remove('output.nxs')


@only_dls_file_system
def test_msmapper_processor():
    import papermill as pm
    import nbformat
    pm.execute_notebook(
        NB_PATHS['msmapper_processor.ipynb'],
        'output.ipynb',
        parameters={
            'inpath': FILES_DICT['i16 pilatus eta scan, new nexus format'],
            'outpath': 'output.nxs',
        }
    )

    nb = nbformat.read('output.ipynb', as_version=4)
    assert nb.metadata.papermill.exception is None

    os.remove('output.ipynb')
