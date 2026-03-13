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
def test_nexus_processor():
    import papermill as pm
    import nbformat

    dat_file = '/dls/science/groups/das/ExampleData/hdfmap_tests/i10/spool/i10-618365.dat'
    if os.path.isfile(dat_file):
        os.remove(dat_file)

    pm.execute_notebook(
        NB_PATHS['nexus_processor.ipynb'],
        'output.ipynb',
        parameters={
            'inpath': FILES_DICT['i10 scan'],
            'outpath': 'output.nxs',
            'nxs2dat': True,
        }
    )

    nb = nbformat.read('output.ipynb', as_version=4)
    assert nb.metadata.papermill.exception is None
    assert os.path.isfile(dat_file)

    os.remove('output.ipynb')
    os.remove(dat_file)


@only_dls_file_system
def test_nexus2srs_processor():
    import papermill as pm
    import nbformat

    dat_file = '/dls/science/groups/das/ExampleData/hdfmap_tests/i10/spool/i10-921636.dat'
    if os.path.isfile(dat_file):
        os.remove(dat_file)

    pm.execute_notebook(
        NB_PATHS['nexus2srs_processor.ipynb'],
        'output.ipynb',
        parameters={
            'inpath': FILES_DICT['i10 pimte new scan'],
            'outpath': 'output.nxs',
        }
    )

    nb = nbformat.read('output.ipynb', as_version=4)
    assert nb.metadata.papermill.exception is None
    assert os.path.isfile(dat_file)

    os.remove('output.ipynb')
    os.remove(dat_file)


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

    # os.remove('output.ipynb')
    os.remove('output.nxs')


@only_dls_file_system
def test_autoprocess_xmcd_processor():
    assert os.path.isfile(NB_PATHS['xmcd_processor.ipynb'])
    import papermill as pm
    import json

    # inject working files into notebook
    # Construct the new notebook cell
    new_code = (
        "scan_files = ['/dls/science/groups/das/ExampleData/hdfmap_tests/i10/i10-1-37436.nxs',\n"
        " '/dls/science/groups/das/ExampleData/hdfmap_tests/i10/i10-1-37437.nxs',\n"
        " '/dls/science/groups/das/ExampleData/hdfmap_tests/i10/i10-1-37438.nxs',\n"
        " '/dls/science/groups/das/ExampleData/hdfmap_tests/i10/i10-1-37439.nxs']"
    )
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": new_code.splitlines(keepends=True)
    }

    # Load notebook JSON
    with open(NB_PATHS['xmcd_processor.ipynb'], "r", encoding="utf-8") as f:
        nb = json.load(f)
    # Insert after the 4th cell (index 3)
    nb["cells"].insert(4, new_cell)

    # Save modified notebook
    # temp_path = NB_PATHS['xmcd_processor.ipynb'].replace(".ipynb", "_temp.ipynb")
    with open('output.ipynb', "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

    pm.execute_notebook(
        'output.ipynb',
        'output.ipynb',
        parameters={
            'inpath': FILES_DICT['i06-1 xmcd_processor dummy'],  # need example with scan x -10 -1 1 xmcd_processor
            'outpath': 'output.nxs',
        }
    )
    assert os.path.isfile('37436-37439_xmcd.nxs')

    with h5py.File('37436-37439_xmcd.nxs', 'r') as hdf:
        assert isinstance(hdf['/processed/xmcd/tey'], h5py.Dataset)

    os.remove('output.ipynb')
    os.remove('37436-37439_xmcd.nxs')


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
