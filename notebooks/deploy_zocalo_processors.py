"""
Deploy .ipynb notebooks for the gda-zocalo-connector

05/12/2025
"""

import nbformat

from tests.test_notebooks import (test_autoprocess_xas_notebook, test_autoprocess_xmcd_processor,
                                  test_msmapper_processor)

GDA_ZOCALO_PROCESSORS_DIR = '/dls_sw/i06/scripts/gda-zocalo/notebooks/'
I16_PROCESSOR_DIR = '/dls_sw/i16/scripts/AutoProc'

def clean_notebook(nb_name):
    nb = nbformat.read(nb_name, as_version=nbformat.NO_CONVERT)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell['outputs'] = []
        if 'parameters' in cell.metadata.get('tags', []):
            # replace path names in parameter cell
            source = cell.source.splitlines()
            for i, line in enumerate(source):
                if 'inpath = ' in line or 'outpath = ' in line:
                    line = ''
                source[i] = line
            source = source + ['inpath = ""', 'outpath = ""']
            cell['source'] = '\n'.join(line for line in source if line.strip())
    nbformat.write(nb, GDA_ZOCALO_PROCESSORS_DIR + nb_name)
    print(f"Notebook cleaned and moved: {nb_name}")


if __name__ == "__main__":
    print('Testing xas_notebook.ipynb')
    test_autoprocess_xas_notebook()
    clean_notebook('xas_notebook.ipynb')

    print('Testing xmcd_processor.ipynb (not testing as no test data)')
    test_autoprocess_xmcd_processor()
    clean_notebook('xmcd_processor.ipynb')

    print('Testing msmapper_processor.ipynb')
    test_msmapper_processor()
    clean_notebook('msmapper_processor.ipynb')