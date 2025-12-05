"""
Automatic data file reader
"""

from datetime import datetime
from collections import defaultdict

from mmg_toolbox.utils.misc_functions import DataHolder
from mmg_toolbox.utils.dat_file_reader import read_dat_file
from mmg_toolbox.utils.env_functions import get_beamline
from mmg_toolbox.nexus.nexus_reader import read_nexus_file, NexusDataHolder


def data_file_reader(filename: str, beamline: str | None = None) -> NexusDataHolder | DataHolder:
    """
    Read Nexus or dat file as DataHolder
    """
    beamline = beamline or get_beamline(None, filename=filename)
    if filename.endswith('.dat'):
        return read_dat_file(filename)
    return read_nexus_file(filename, beamline=beamline)


def read_gda_terminal_log(filename: str) -> dict[str, list[str]]:
    """Read GDA terminal log using specific time stamp regex"""
    dt_format = '%Y-%m-%d %H:%M:%S,%f'
    line2dt = lambda ln: datetime.strptime(ln.split('|')[0].strip(), dt_format)
    tab_title = '%a %d%b'

    tabs = defaultdict(list)
    with open(filename) as file:
        for line in file:
            try:
                time = line2dt(line)
                title = time.strftime(tab_title)
                tabs[title] += [line.strip()]
            except ValueError as e:
                pass
    return tabs
