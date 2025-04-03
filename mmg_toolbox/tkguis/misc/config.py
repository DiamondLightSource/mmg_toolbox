"""
Configuration Options
"""

import os
import json

from ...env_functions import TMPDIR, YEAR, get_beamline

# config name (saved in TMPDIR)
TMPFILE = 'mmg_config.json'
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

META_LIST = {
    # scan number and start_time included by default
    # name: format
    'cmd': '{scan_command}'
}

REPLACE_NAMES = {
    # NEW_NAME: EXPRESSION
    '_t': '(count_time|counttime|t?(1.0))',
}

CONFIG = {
    'config_file': CONFIG_FILE,
    'default_directory': os.path.expanduser('~'),
    'processing_directory': os.path.expanduser('~'),
    'notebook_directory': os.path.expanduser('~'),
    'normalise_factor': '',
    'replace_names': {},
    'metadata_string': META_STRING,
    'metadata_list': META_LIST,
    'default_colormap': 'twilight',
}

BEAMLINE_CONFIG = {
    'i06': {
        'beamline': 'i06',
        'default_directory': f"/dls/i06/data/{YEAR}/",
    },
    'i06-1': {
        'beamline': 'i06-1',
        'default_directory': f"/dls/i06-1/data/{YEAR}/",
    },
    'i06-2': {
        'beamline': 'i06-2',
        'default_directory': f"/dls/i06-2/data/{YEAR}/",
    },
    'i10': {
        'beamline': 'i10',
        'default_directory': f"/dls/i10/data/{YEAR}/",
    },
    'i10-1': {
        'beamline': 'i10-1',
        'default_directory': f"/dls/i10-1/data/{YEAR}/",
    },
    'i16': {
        'beamline': 'i16',
        'default_directory': f"/dls/i16/data/{YEAR}/",
        'normalise_factor': '/Transmission/count_time/(rc/300.)',
    },
    'i21': {
        'beamline': 'i21',
        'default_directory': f"/dls/i21/data/{YEAR}/",
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

