"""
Script & Notebook templates
"""

import os
import datetime


SCRIPTS = {
    # name: (filename, description)
    'example': ('example_script.py', 'a simple example'),
    'plot multi-line': ('experiment_multiline.py', 'create a multi-line plot'),
    'peak fitting': ('experiment_fitting.py', 'fit peaks and plot the results'),
    'spectra': ('spectra_script.py', 'normalise spectra and subtract polarisations')
}

NOTEBOOKS = {
    # name: (filename, description)
    'example': ('example_notebook.ipynb', 'a basic example'),
}

TEMPLATE = {
    # {{template}}: replacement
    'description': 'a short description',
    'filepaths': "'file1.nxs', 'file2.nxs', 'file3.nxs'",
    'experiment_dir': 'path/to/dir',
    'scan_numbers': 'range(-10, 0)',
    'title': 'a nice plot',
    'x-axis': 'axes',
    'y-axis': 'signal',
    'value': 'Ta'
}


def generate_script(template_name: str, **replacements) -> str:
    """generate script str from template"""
    template_file, description = SCRIPTS[template_name]
    template_file = os.path.join(os.path.dirname(__file__), template_file)
    template_changes = TEMPLATE.copy()
    template_changes.update(replacements)
    template_changes['date'] = str(datetime.date.today())
    print(template_file)
    print(template_changes)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        param = "{{" + name + "}}"
        print(f"Replacing {template_string.count(param)} instances of {param}")
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
    template_changes.update(replacements)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        param = "{{" + name + "}}"
        print(f"Replacing {template_string.count(param)} instances of {param}")
        template_string = template_string.replace(param, value)

    with open(new_notebook_path, 'w') as new:
        new.write(template_string)
    print(f"Created {new_notebook_path}")

