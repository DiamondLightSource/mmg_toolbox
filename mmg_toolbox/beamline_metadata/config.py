"""
Beamline or User Configuration Options
"""

from mmg_toolbox.utils.env_functions import YEAR
from .hdfmap_generic import HdfMapMMGMetadata as Md
from .metadata_strings import BEAMLINE_META, META_STRING, META_LABEL


class C:
    """Names used in config object"""
    conf_file = 'config_file'
    default_directory = 'default_directory'
    normalise_factor = 'normalise_factor'
    replace_names = 'replace_names'
    metadata_string = 'metadata_string'
    metadata_list = 'metadata_list'
    metadata_label = 'metadata_label'
    default_metadata = 'default_metadata'
    beamline = 'beamline'
    scan_description = 'scan_description'
    scan_title = 'scan_title'
    roi = 'roi'

DEFAULT_SCAN_DESCRIPTION = '{(cmd|user_input_command|user_command|scan_command)}'
DEFAULT_SCAN_TITLE = "{entry_identifier?(filename)}: " + DEFAULT_SCAN_DESCRIPTION

META_LIST = {
    # scan number and start_time included by default
    # name: format
    'cmd': DEFAULT_SCAN_DESCRIPTION
}

REPLACE_NAMES = {
    # NEW_NAME: EXPRESSION
    '_t': '(count_time|counttime|t?(1.0))',
    '_cmd': DEFAULT_SCAN_DESCRIPTION.strip('{}'),
}

ROIs: list[tuple[str, str | int, str | int, int, int, str]] = [
    # (name, cen_i, cen_j, wid_i, wid_j, det_name)
]

CONFIG = {
    C.conf_file: '',
    C.normalise_factor: '',
    C.replace_names: REPLACE_NAMES,
    C.roi: ROIs,
    C.metadata_string: META_STRING,
    C.metadata_list: META_LIST,
    C.metadata_label: META_LABEL,
    C.default_metadata: Md.temp,
    C.scan_description: DEFAULT_SCAN_DESCRIPTION,
    C.scan_title: DEFAULT_SCAN_TITLE,
}

BEAMLINE_CONFIG = {
    'i06': {
        C.beamline: 'i06',
        C.default_directory: f"/dls/i06/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06'],
        C.normalise_factor: '',
        # C.default_metadata: '',
    },
    'i06-1': {
        C.beamline: 'i06-1',
        C.default_directory: f"/dls/i06-1/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06-1'],
        C.normalise_factor: '',
        # C.default_metadata: '',
    },
    'i06-2': {
        C.beamline: 'i06-2',
        C.default_directory: f"/dls/i06-2/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i06-2'],
        C.normalise_factor: '',
        # C.default_metadata: '',
    },
    'i10': {
        C.beamline: 'i10',
        C.default_directory: f"/dls/i10/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i10'],
        C.normalise_factor: '',
        # C.default_metadata: '',
    },
    'i10-1': {
        C.beamline: 'i10-1',
        C.default_directory: f"/dls/i10-1/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i10-1'],
        C.normalise_factor: '/(mcs16|macr16|mcse16|macj316|mcsh16|macj216)',
        # C.default_metadata: '',
    },
    'i16': {
        C.beamline: 'i16',
        C.default_directory: f"/dls/i16/data/{YEAR}/",
        C.normalise_factor: '/Transmission/count_time/(rc/300.)',
        C.metadata_string: BEAMLINE_META['i16'],
        C.roi: [
            ('pilroi1', 'pil3_centre_j', 'pil3_centre_i', 30, 30, 'pil3_100k'),
        ],
        C.default_metadata: 'Tsample',
    },
    'i21': {
        C.beamline: 'i21',
        C.default_directory: f"/dls/i21/data/{YEAR}/",
        C.metadata_string: BEAMLINE_META['i21'],
        C.normalise_factor: '',
        # C.default_metadata: '',
    },
}


def beamline_config(beamline: str | None = None) -> dict:
    """Returns the default beamline config dict"""
    config = CONFIG.copy()
    if beamline and beamline in BEAMLINE_CONFIG:
        config.update(BEAMLINE_CONFIG[beamline])
    elif beamline:
        config[C.beamline] = beamline
    return config


def add_roi(config: dict, name: str, cen_i: int | str, cen_j: int | str,
            wid_i: int = 30, wid_j: int = 30, image_name: str = 'IMAGE'):
    """
    Create an image ROI (region of interest) and update the config

    :param config: dict of config values
    :param name: string name of the ROI
    :param cen_i: central pixel index along first dimension, can be callable string
    :param cen_j: central pixel index along second dimension, can be callable string
    :param wid_i: full width along first dimension, in pixels
    :param wid_j: full width along second dimension, in pixels
    :param image_name: string name of the image
    """
    roi = (name, cen_i, cen_j, wid_i, wid_j, image_name)
    current_roi_list = config.get(C.roi, [])
    names = [c_roi[0] for c_roi in current_roi_list]
    if name in names:
        # overwrite
        current_roi_list[names.index(name)] = roi
    else:
        current_roi_list.append(roi)
    config[C.roi] = current_roi_list