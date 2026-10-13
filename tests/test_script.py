"""
test user interface
"""

import os
from mmg_toolbox.scripts.scripts import (list_templates, generate_script,
                                         R, Rxas,
                                         create_script, create_notebook)

def test_list_templates(capsys):
    out = list_templates()
    warnings = capsys.readouterr()

    print('\n', out)
    assert 'Warning' not in warnings.out, "Warnings listed in list_templates()"
    assert len(out) > 300


def test_example_script():
    scan_files = ['12345.nxs', '12346.nxs']
    replacements = {
        R.filepaths: '\n    '.join(f"'{f}'," for f in scan_files),
        R.beamline: 'i16',
        R.scannos: '[12345, 12346]',
        R.title: 'Test Title',
        R.description: 'Created by test_script.py',
    }
    script = generate_script('example', **replacements)
    print(script)
    assert len(script) > 400
    assert "filenames = [\n    '12345.nxs',\n    '12346.nxs',\n]" in script, 'formatting wrong'
    assert "data = scan.get_plot_data('axes', 'signal')" in script, 'default axes incorrect'

    create_script('test_script.py', 'example', **replacements)
    assert os.path.isfile('test_script.py')
    os.remove('test_script.py')


def test_example_notebook():
    replacements = {
        R.exp: '/dls/i16/data/2026/cm12345-1',
        R.beamline: 'i16',
        R.scannos: '[12345, 12346]',
        R.title: 'Test Title',
        R.description: 'Created by test_script.py',
        R.scanno: '9999',
        R.value: 'Ta',
        R.xaxis: 'axes',
        R.yaxis: 'signal / Transmission',
    }
    create_notebook('test_notebook.ipynb', 'example', **replacements)

    assert os.path.isfile('test_notebook.ipynb')
    nb = open('test_notebook.ipynb', 'r').read()
    assert "exp = Experiment('/dls/i16/data/2026/cm12345-1', instrument='i16')" in nb
    assert "exp.plot.multi_lines(*[12345, 12346], xaxis='axes', yaxis='signal / Transmission')" in nb

    os.remove('test_notebook.ipynb')


def test_xmcd_script():
    files1 = ['12345.nxs', '12346.nxs']
    files2 = ['12347.nxs', '12348.nxs']
    opt = {
        Rxas.files1: '\n    '.join(f"'{f}'," for f in files1),
        Rxas.files2: '\n    '.join(f"'{f}'," for f in files2),
        Rxas.mode: 'TEY',
        Rxas.proc: '.',
        Rxas.description: 'test - description',
        Rxas.title: 'xmcd test',
        Rxas.background: 'linear'
    }
    script = generate_script('xmcd', **opt)
    print(script)
    assert len(script) > 1000
    assert "files_pol1 = [\n    '12345.nxs',\n    '12346.nxs',\n]" in script
    assert "background = 'linear'" in script


