"""
Configuration Options
"""

import os
import json

from ...env_functions import TMPDIR, YEAR, get_beamline


class C:
    """Names used in config object"""
    conf_file = 'config_file'
    default_directory = 'default_directory'
    processing_directory = 'processing_directory'
    notebook_directory = 'notebook_directory'
    recent_data_directories = 'recent_data_directories'
    normalise_factor = 'normalise_factor'
    replace_names = 'replace_names'
    metadata_string = 'metadata_string'
    metadata_list = 'metadata_list'
    default_colormap = 'default_colormap'
    beamline = 'beamline'


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
    C.conf_file: CONFIG_FILE,
    C.default_directory: os.path.expanduser('~'),
    C.processing_directory: os.path.expanduser('~'),
    C.notebook_directory: os.path.expanduser('~'),
    C.recent_data_directories: [os.path.expanduser('~')],
    C.normalise_factor: '',
    C.replace_names: {},
    C.metadata_string: META_STRING,
    C.metadata_list: META_LIST,
    C.default_colormap: 'twilight',
}

BEAMLINE_CONFIG = {
    'i06': {
        C.beamline: 'i06',
        C.default_directory: f"/dls/i06/data/{YEAR}/",
    },
    'i06-1': {
        C.beamline: 'i06-1',
        C.default_directory: f"/dls/i06-1/data/{YEAR}/",
    },
    'i06-2': {
        C.beamline: 'i06-2',
        C.default_directory: f"/dls/i06-2/data/{YEAR}/",
    },
    'i10': {
        C.beamline: 'i10',
        C.default_directory: f"/dls/i10/data/{YEAR}/",
    },
    'i10-1': {
        C.beamline: 'i10-1',
        C.default_directory: f"/dls/i10-1/data/{YEAR}/",
    },
    'i16': {
        C.beamline: 'i16',
        C.default_directory: f"/dls/i16/data/{YEAR}/",
        C.normalise_factor: '/Transmission/count_time/(rc/300.)',
    },
    'i21': {
        C.beamline: 'i21',
        C.default_directory: f"/dls/i21/data/{YEAR}/",
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
    config[C.conf_file] = config_filename
    with open(config_filename, 'w') as f:
        json.dump(config, f)

