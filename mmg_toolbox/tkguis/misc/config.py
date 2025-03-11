"""
Configuration Options
"""

import os
import tempfile
import json

from ...env_functions import get_beamline

# config name (saved in TMPDIR)
TMPFILE = 'mmg_config.json'

# Find writable directory
TMPDIR = tempfile.gettempdir()
if not os.access(TMPDIR, os.W_OK):
    TMPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if not os.access(TMPDIR, os.W_OK):
        TMPDIR = os.path.expanduser('~')
CONFIG_FILE = os.path.join(TMPDIR, TMPFILE)

META_STRING = """
{filename}
{filepath}
{start_time}
cmd = {scan_command}
axes = {_axes}
signal = {_signal}
shape = {axes.shape}
"""

REPLACE_NAMES = {
    # NEW_NAME: EXPRESSION
    '_t': '(count_time|counttime|t?(1.0))',
}

CONFIG = {
    'config_file': CONFIG_FILE,
    'default_beamline': None,
    'normalise_factor': '/Transmission/count_time/(rc/300.)',
    'replace_names': {},
    'metadata_string': META_STRING
}

BEAMLINE_CONFIG = {
    'i06': {
        'default_beamline': 'i06',
    },
    'i06-1': {
        'default_beamline': 'i06-1',
    },
    'i06-2': {
        'default_beamline': 'i06-2',
    },
    'i10': {
        'default_beamline': 'i10',
    },
    'i10-1': {
        'default_beamline': 'i10-1',
    },
    'i16': {
        'default_beamline': 'i16',
    },
    'i21': {
        'default_beamline': 'i21',
    },
}


def load_config(config_filename: str = CONFIG_FILE) -> dict:
    if os.path.isfile(config_filename):
        with open(config_filename, 'r') as f:
            return json.load(f)
    return {}


def get_config(config_filename: str = CONFIG_FILE) -> dict:
    config = CONFIG.copy()
    beamline = get_beamline()
    if beamline in BEAMLINE_CONFIG:
        config.update(BEAMLINE_CONFIG[beamline])
    user_config = load_config(config_filename)
    config.update(user_config)
    return config


def save_config(config_filename: str = CONFIG_FILE, **kwargs):
    config = get_config(config_filename)
    config.update(kwargs)
    config['config_file'] = config_filename
    with open(config_filename, 'w') as f:
        json.dump(config, f)

