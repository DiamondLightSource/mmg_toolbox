"""
Configuration Options
"""
from __future__ import annotations

import os
import json

from mmg_toolbox.utils.env_functions import TMPDIR, get_beamline, get_user, check_file_access
import mmg_toolbox.beamline_metadata.config as config
from .matplotlib import FIGURE_SIZE, FIGURE_DPI, IMAGE_SIZE, DEFAULT_COLORMAP


class C(config.C):
    """Names used in config object"""
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
    default_colormap = 'default_colormap'
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
BEAMLINE_CONFIG = config.BEAMLINE_CONFIG


CONFIG = {
    **config.CONFIG,
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
    C.default_colormap: DEFAULT_COLORMAP,
}

def check_config_filename(config_filename: str | None) -> str:
    """Check config filename is writable, raise OSError if not"""
    if config_filename is None:
        config_filename = CONFIG_FILE
    return check_file_access(config_filename)


def load_config(config_filename: str = CONFIG_FILE) -> dict:
    """Loads a config dict from file, by default from the default location"""
    if os.path.isfile(config_filename):
        with open(config_filename, 'r') as f:
            return json.load(f)
    return {}


def default_config(beamline: str | None = None) -> dict:
    """Returns the default beamline config dict"""
    cfg = CONFIG.copy()
    if beamline is None:
        beamline = get_beamline()
    if beamline in config.BEAMLINE_CONFIG:
        cfg.update(config.BEAMLINE_CONFIG[beamline])
    return cfg


def get_config(config_filename: str | None = None, beamline: str | None = None) -> dict:
    """merge loaded config into default beamline config and return the config dict"""
    config_filename = check_config_filename(config_filename)
    user_config = load_config(config_filename)
    cfg = default_config(beamline)
    if beamline and user_config.get(C.beamline) and beamline != user_config.get(C.beamline):
        # default config overrides user config when changing beamline
        user_config.update(cfg)
        return user_config
    cfg.update(user_config)
    return cfg


def reset_config(cfg: dict) -> None:
    """Reset config dict in place with default values of beamline"""
    beamline = cfg.get(C.beamline, None)
    cfg.clear()
    cfg.update(default_config(beamline))


def save_config(cfg: dict):
    """Save the config dict into the file location referenced in config['config_file']"""
    config_filename = cfg.get(C.conf_file, CONFIG_FILE)
    with open(config_filename, 'w') as f:
        json.dump(cfg, f)
    print('Saved config to {}'.format(config_filename))


def save_config_as(config_filename: str | None = None, **kwargs):
    """Save the config dict into a new file location"""
    cfg = get_config(config_filename)
    cfg.update(kwargs)
    cfg[C.conf_file] = config_filename
    save_config(cfg)

