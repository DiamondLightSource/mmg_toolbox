"""
Configuration Options
"""
from __future__ import annotations

import os
import json

from mmg_toolbox.utils.env_functions import TMPDIR, YEAR, get_beamline, get_user, check_file_access
from .beamline_metadata import BEAMLINE_META, META_STRING, META_LABEL
from .matplotlib import FIGURE_SIZE, FIGURE_DPI, IMAGE_SIZE, DEFAULT_COLORMAP


class C:
    """Names used in config object"""
    conf_file = 'config_file'
    default_directory = 'default_directory'
    processing_directory = 'processing_directory'
    notebook_directory = 'notebook_directory'
    recent_data_directories = 'recent_data_directories'
    small_screen_height = 'small_screen_height'
    text_size = 'text_size'
    text_size_small = 'text_size_small'
    plot_size = 'plot_size'
    image_size = 'image_size'
    plot_max_percent = 'plot_max_percent'
    plot_dpi = 'plot_dpi'
    plot_title = 'plot_title'
    normalise_factor = 'normalise_factor'
    replace_names = 'replace_names'
    metadata_string = 'metadata_string'
    metadata_list = 'metadata_list'
    metadata_label = 'metadata_label'
    default_colormap = 'default_colormap'
    beamline = 'beamline'
    roi = 'roi'
    current_dir = 'current_dir'
    current_proc = 'current_proc'
    current_nb = 'current_nb'


# config name (saved in TMPDIR)
USER = get_user()
TMPFILE = f'mmg_config_{USER}.json'
CONFIG_FILE = os.path.join(TMPDIR, TMPFILE)
SMALL_SCREEN_HEIGHT = 800  # pixels, reduce size if screen smaller than this
TEXT_WIDTH = 50  # Determines the width of text areas in DataViewer in characters
TEXT_HEIGHT = 25  # Determines height of text area in Dataviewer in lines
TEXT_HEIGHT_SMALL = 10  # TEXT_HEIGHT when screen is small
MAX_PLOT_SCREEN_PERCENTAGE = (75, 25)  # (wid, height) max plot size as % of screen


META_LIST = {
    # scan number and start_time included by default
    # name: format
    'cmd': '{(cmd|scan_command)}'
}

REPLACE_NAMES = {
    # NEW_NAME: EXPRESSION
    '_t': '(count_time|counttime|t?(1.0))',
}

ROIs: list[tuple[str, str | int, str | int, int, int, str]] = [
    # (name, cen_i, cen_j, wid_i, wid_j, det_name)
]

CONFIG = {
    C.conf_file: CONFIG_FILE,
    C.default_directory: os.path.expanduser('~'),
    C.processing_directory: os.path.expanduser('~'),
    C.notebook_directory: os.path.expanduser('~'),
    C.recent_data_directories: [os.path.expanduser('~')],
    C.small_screen_height: SMALL_SCREEN_HEIGHT,
    C.text_size: (TEXT_WIDTH, TEXT_HEIGHT),
    C.text_size_small: (TEXT_WIDTH, TEXT_HEIGHT_SMALL),
    C.plot_size: FIGURE_SIZE,
    C.image_size: IMAGE_SIZE,
    C.plot_max_percent: MAX_PLOT_SCREEN_PERCENTAGE,
    C.plot_dpi: FIGURE_DPI,
    C.plot_title: '{filename}\n{(cmd|scan_command)}',
    C.normalise_factor: '',
    C.replace_names: REPLACE_NAMES,
    C.roi: ROIs,
    C.metadata_string: META_STRING,
    C.metadata_list: META_LIST,
    C.metadata_label: META_LABEL,
    C.default_colormap: DEFAULT_COLORMAP,
}

BEAMLINE_CONFIG = {
    'i06': {
        C.beamline: 'i06',
        C.default_directory: f"/dls/i06/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06'],
        C.normalise_factor: '',
    },
    'i06-1': {
        C.beamline: 'i06-1',
        C.default_directory: f"/dls/i06-1/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06-1'],
        C.normalise_factor: '',
    },
    'i06-2': {
        C.beamline: 'i06-2',
        C.default_directory: f"/dls/i06-2/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06-2'],
        C.normalise_factor: '',
    },
    'i10': {
        C.beamline: 'i10',
        C.default_directory: f"/dls/i10/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i10'],
        C.normalise_factor: '',
    },
    'i10-1': {
        C.beamline: 'i10-1',
        C.default_directory: f"/dls/i10-1/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i10-1'],
        C.normalise_factor: '/(mcs16|macr16|mcse16|macj316|mcsh16|macj216)',
    },
    'i16': {
        C.beamline: 'i16',
        C.default_directory: f"/dls/i16/data/{YEAR}/",
        C.normalise_factor: '/Transmission/count_time/(rc/300.)',
        C.metadata_string: BEAMLINE_META['i16'],
        C.roi: [
            ('pilroi1', 'pil3_centre_j', 'pil3_centre_i', 30, 30, 'pil3_100k'),
        ]
    },
    'i21': {
        C.beamline: 'i21',
        C.default_directory: f"/dls/i21/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i21'],
        C.normalise_factor: '',
    },
}


def check_config_filename(config_filename: str | None) -> str:
    """Check config filename is writable, raise OSError if not"""
    if config_filename is None:
        config_filename = CONFIG_FILE
    return check_file_access(config_filename)


def load_config(config_filename: str = CONFIG_FILE) -> dict:
    if os.path.isfile(config_filename):
        with open(config_filename, 'r') as f:
            return json.load(f)
    return {}


def default_config(beamline: str | None = None) -> dict:
    config = CONFIG.copy()
    if beamline is None:
        beamline = get_beamline()
    if beamline in BEAMLINE_CONFIG:
        config.update(BEAMLINE_CONFIG[beamline])
    return config


def get_config(config_filename: str | None = None, beamline: str | None = None) -> dict:
    config_filename = check_config_filename(config_filename)
    user_config = load_config(config_filename)
    config = default_config(beamline)
    config.update(user_config)
    return config


def reset_config(config: dict) -> None:
    """Reset config dict in place with default values of beamline"""
    beamline = config.get(C.beamline, None)
    config.clear()
    config.update(default_config(beamline))


def save_config(config: dict):
    config_filename = config.get(C.conf_file, CONFIG_FILE)
    with open(config_filename, 'w') as f:
        json.dump(config, f)
    print('Saved config to {}'.format(config_filename))


def save_config_as(config_filename: str | None = None, **kwargs):
    config = get_config(config_filename)
    config.update(kwargs)
    config[C.conf_file] = config_filename
    save_config(config)

