"""
Deploy .ipynb notebooks for the gda-zocalo-connector

05/12/2025
"""
from shutil import copy2

from tests.test_notebooks import test_autoprocess_xas_notebook, test_msmapper_processor

GDA_ZOCALO_PROCESSORS_DIR = '/dls_sw/i06/scripts/gda-zocalo/notebooks/'
I16_PROCESSOR_DIR = '/dls_sw/i16/scripts/AutoProc'

def copy_notebook(nb_name):
    copy2(nb_name, GDA_ZOCALO_PROCESSORS_DIR + nb_name)
    print('Copied ' + nb_name)

if __name__ == "__main__":
    test_autoprocess_xas_notebook()
    # if this completes, copy the files across
    copy_notebook('xas_notebook.ipynb')

    # xmcd_processor - no tests as don't have example data
    copy_notebook('xmcd_processor.ipynb')

    test_msmapper_processor()
    copy_notebook('msmapper_processor.ipynb')
