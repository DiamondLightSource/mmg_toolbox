"""
Script & Notebook templates
"""

import os


SCRIPTS = {
    # name: (filename, description)
    'example': ('example_script.py', 'a simple example'),
}

NOTEBOOKS = {
    # name: (filename, description)
    'example': ('example_notebook.ipynb', 'a basic example'),
}

TEMPLATE = {
    # {{template}}: replacement
    'description': 'a short description',
    'filepaths': 'file1.nxs, file2.nxs, file3.nxs',
    'title': 'a nice plot'
}


def create_script(new_script_path: str, template_name: str, **replacements):
    """create script from template"""
    template_file, description = SCRIPTS[template_name]
    template_changes = TEMPLATE.copy()
    template_changes.update(replacements)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        param = "{{" + name + "}}"
        template_string.replace(param, value)

    with open(new_script_path, 'w') as new:
        new.write(template_string)


def create_notebook(new_notebook_path: str, template_name: str, **replacements):
    """create script from template"""
    template_file, description = NOTEBOOKS[template_name]
    template_changes = TEMPLATE.copy()
    template_changes.update(replacements)

    template_string = open(template_file, 'r').read()
    for name, value in template_changes.items():
        template_string.replace(name, value)

    with open(new_notebook_path, 'w') as new:
        new.write(template_string)

