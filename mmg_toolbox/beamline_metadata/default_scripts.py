"""
Default Scripts and Notebooks for beamlines

see mmg_toolbox.scripts.scripts.py
"""

import os
from mmg_toolbox.scripts.scripts import create_script, create_notebook, R

# names from mmg_toolbox.scripts.scripts.SCRIPTS
DEFAULT_SCRIPTS = ['example']
# names from mmg_toolbox.scripts.scripts.NOTEBOOKS
DEFAULT_NOTEBOOKS = ['example']

BEAMLINE_SCRIPTS = {
    'default': {
        'scripts': DEFAULT_SCRIPTS,
        'notebooks': DEFAULT_NOTEBOOKS
    },
    'i06': {
        'scripts': [],
        'notebooks': []
    },
    'i06-1': {
        'scripts': ['spectra'],
        'notebooks': []
    },
    'i10': {
        'scripts': ['peak fitting', 'plot multi-line'],
        'notebooks': []
    },
    'i10-1': {
        'scripts': ['spectra'],
        'notebooks': []
    },
    'i16': {
        'scripts': ['peak fitting', 'plot multi-line'],
        'notebooks': []
    },
    'i21': {
        'scripts': [],
        'notebooks': []
    },
}


def create_beamline_scripts(beamline: str, directory: str, **replacements):
    """Create default python and jupyter scripts in directory"""
    default_scripts = BEAMLINE_SCRIPTS['default']
    if beamline in BEAMLINE_SCRIPTS:
        beamline_scripts = BEAMLINE_SCRIPTS[beamline]
        for key in default_scripts:
            default_scripts[key].extend(beamline_scripts[key])
    template = {
        R.beamline: beamline,
        R.exp: directory,
        R.description: "An example script using mmg_toolbox",
        R.title: 'mmg_toolbox Example Script',
    }
    template.update(replacements)
    # Create script files
    for script_name in default_scripts['scripts']:
        filename = os.path.join(directory, script_name + '.py')
        if not os.path.isfile(filename):
            create_script(filename, script_name, **template)
        else:
            print(f'Script {filename} already exists')
    for notebook_name in default_scripts['notebooks']:
        filename = os.path.join(directory, notebook_name + '.ipynb')
        if not os.path.isfile(filename):
            create_notebook(filename, notebook_name, **template)
        else:
            print(f'Notebook {filename} already exists')

