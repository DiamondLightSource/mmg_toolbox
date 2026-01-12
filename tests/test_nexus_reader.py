"""
mmg_toolbox tests
Test nexus reader
"""
import numpy as np

from mmg_toolbox.nexus.nexus_scan import NexusScan, NexusDataHolder
from mmg_toolbox.nexus.nexus_reader import (read_nexus_file, read_nexus_files, find_scans,
                                            find_similar_scans, find_matching_scans)
from . import only_dls_file_system
from .example_files import DIR

@only_dls_file_system
def test_read_nexus_file():
    f = DIR + '/i16/1109527.nxs'
    scan = read_nexus_file(f)
    assert isinstance(scan, NexusDataHolder)
    assert len(scan.eta_fly) == 61
    assert scan.roi2_sum.max() == 692919
    assert abs(scan.metadata.Tsample-300) < 0.1
    assert scan.scan_number() == 1109527
    assert scan.title() == '#1109527'


@only_dls_file_system
def test_read_nexus_files():
    files = [DIR + f'/i16/cm37262-1/{n}.nxs' for n in range(1032120, 1032130)]
    scans = read_nexus_files(*files)
    assert isinstance(scans[0], NexusScan)


@only_dls_file_system
def test_read_nexus_tiff_files():
    file = DIR + f'/i16/777777.nxs'
    scan, = read_nexus_files(file)
    assert isinstance(scan, NexusScan)
    image = scan.image()
    assert type(image) is np.ndarray
    assert image.shape == (195, 487)


@only_dls_file_system
def test_read_old_nexus_file():
    file = DIR + f'/i16/777777.nxs'
    scan, = read_nexus_files(file)
    data = scan.get_plot_data()
    assert 'x' in data and 'y' in data
    assert data['xlabel'] == 'TimeFromEpoch'
    assert data['ylabel'] == 'sum'
    assert data['x'].size == data['y'].size == 81
    assert len(data['data'].keys()) == 19


@only_dls_file_system
def test_find_scans():
    files = [DIR + f'/i16/cm37262-1/{n}.nxs' for n in range(1032115, 1032135)]
    found_files = find_scans(*files, scan_command='pil3_100k')
    assert len(found_files) == 7
    found_files = find_scans(*files, scan_command='merlin', Ta=(300,0.2))
    assert len(found_files) == 2
    match  = {'start_time.timestamp()': (1705399908, 5)}
    found_files = find_scans(*files, **match)
    assert len(found_files) == 2

