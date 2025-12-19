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
def test_autoprocess_xmcd_processor():
    print("No example xmcd_processor file, skipping...")
    assert os.path.isfile(NB_PATHS['xmcd_processor.ipynb'])
    # import papermill as pm
    # pm.execute_notebook(
    #     NB_PATHS['xmcd_processor.ipynb'],
    #     'output.ipynb',
    #     parameters={
    #         'inpath': FILES_DICT[''],  # need example with scan x -10 -1 1 xmcd_processor
    #         'outpath': 'output.nxs',
    #     }
    # )
    # assert os.path.isfile('output.ipynb')
    # assert os.path.isfile('1234-1235_xmcd.nxs')
    #
    # with h5py.File('output.nxs', 'r') as hdf:
    #     assert isinstance(hdf['/processed/xmcd/tey'], h5py.Dataset)
    #
    # os.remove('output.ipynb')
    # os.remove('output.nxs')


@only_dls_file_system
def test_msmapper_processor():
    import papermill as pm
    import nbformat

    # Remove analysis group from output if it exists
    with h5py.File(FILES_DICT['msmapper volume 527'], 'a') as hdf:
        if 'analysis' in hdf:
            del hdf['analysis']

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

    with h5py.File(FILES_DICT['msmapper volume 527']) as hdf:
        assert isinstance(hdf['/analysis/h_axis/fit'], h5py.Dataset)

    os.remove('output.ipynb')
