"""
Script & Notebook templates
"""

import os
import re
import datetime

re_replacement = re.compile(r"{{(.+?)}}")


class R:
    """Names used in replacements"""
    date = 'date'  # note that this one is generated in generate_script
    beamline = 'beamline'
    description = 'description'
    filepaths = 'filepaths'
    exp = 'experiment_dir'
    proc = 'processing_dir'
    scanno = 'scan_number'
    scannos = 'scan_numbers'
    title = 'title'
    xaxis = 'x-axis'
    yaxis = 'y-axis'
    value = 'value'

SCRIPTS = {
    # name: (filename, description)
    'example': ('example_script.py', 'a simple example script'),
    'plot multi-line': ('experiment_multiline.py', 'create a multi-line plot'),
    'peak fitting': ('experiment_fitting.py', 'fit peaks and plot the results'),
    'spectra': ('spectra_script.py', 'normalise spectra and subtract polarisations')
}

NOTEBOOKS = {
    # name: (filename, description)
    'example': ('example_notebook.ipynb', 'An example notebook describing mmg_toolbox'),
    'xmcd': ('xmcd_notebook.ipynb', 'An example notebook describing XAS analysis'),
    'msmapper': ('msmapper_notebook.ipynb', 'An example notebook describing MSMapper analysis'),
}

TEMPLATE = {
    # {{template}}: replacement
    R.beamline: '',
    R.description: 'a short description',
    R.filepaths: "'file1.nxs', 'file2.nxs', 'file3.nxs'",
    R.exp: 'path/to/dir',
    R.scanno: '-1',
    R.scannos: 'range(-10, 0)',
    R.title: 'a nice plot',
    R.xaxis: 'axes',
    R.yaxis: 'signal',
    R.value: 'sample_temperature?(300)'
}


def find_replacements(string: str) -> list[str]:
    """find all replacements in string"""
    return re_replacement.findall(string)


def generate_script(template_name: str, **replacements) -> str:
    """generate script str from template"""
    template_file, description = SCRIPTS[template_name]
    template_file = os.path.join(os.path.dirname(__file__), template_file)
    template_changes = TEMPLATE.copy()
    template_changes[R.date] = str(datetime.date.today())
    template_changes.update(replacements)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        param = "{{" + name + "}}"
        # print(f"Replacing {template_string.count(param)} instances of {param}")
        template_string = template_string.replace(param, value)
    return template_string


def create_script(new_script_path: str, template_name: str, **replacements):
    """create script from template"""
    script = generate_script(template_name, **replacements)

    with open(new_script_path, 'w') as new:
        new.write(script)
    print(f"Created {new_script_path}")


def create_notebook(new_notebook_path: str, template_name: str, **replacements):
    """create script from template"""
    template_file, description = NOTEBOOKS[template_name]
    template_file = os.path.join(os.path.dirname(__file__), template_file)
    template_changes = TEMPLATE.copy()
    template_changes[R.date] = str(datetime.date.today())
    template_changes.update(replacements)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        param = "{{" + name + "}}"
        # print(f"Replacing {template_string.count(param)} instances of {param}")
        template_string = template_string.replace(param, value)

    with open(new_notebook_path, 'w') as new:
        new.write(template_string)
    print(f"Created {new_notebook_path}")

