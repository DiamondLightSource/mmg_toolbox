"""
mmg_toolbox tests
Test nexus reader
"""
import os

import h5py
import numpy as np
from pytest import approx

from mmg_toolbox.nexus.nexus_scan import NexusScan, load_nexus_scan
from . import only_dls_file_system
from .example_files import DIR


@only_dls_file_system
def test_nexus_scan():
    f = DIR + '/i16/1109527.nxs'
    scan = NexusScan(f)

    assert str(scan) == '\n1109527.nxs\n/dls/science/groups/das/ExampleData/hdfmap_tests//i16/1109527.nxs\n2025-09-22 11:32:29.381000\ncmd = flyscancn eta_fly 0.005 61 pil3_100k 0.1 0.5 roi1 roi2\naxes = /entry/measurement/eta_fly_fly\nsignal = /entry/measurement/roi2_sum\ndetector = pil3_100k\nshape = (61,)\n'
    assert scan('cmd') == 'flyscancn eta_fly 0.005 61 pil3_100k 0.1 0.5 roi1 roi2'
    assert scan('max(signal / Transmission / (rc/300.) / _t)') == approx(1215483134.5953412)
    assert scan.scan_number() == 1109527
    start, stop, duration = scan.start_end_duration()
    assert duration.total_seconds() == approx(41.514)

    values, name = scan.get_plot_axis('signal0 / signal1 / gains_atten_Transmission')
    assert name == 'roi2_sum / count_time / Transmission'
    assert values.shape == (61, )
    values, name = scan.get_plot_axis('IMAGE / Transmission')
    assert name == 'pil3_100k / Transmission'
    assert values.shape == (61, )

    scannables = scan.get_scannables()
    assert len(scannables) == 23
    assert 'ic1monitor' in scannables

    metadata = scan.get_metadata()
    assert len(metadata) == 202
    assert 'Tsample' in metadata

    image = scan.image()
    assert image.shape == (195, 487)
    assert image.max() == 58849

    volume = scan.volume()
    assert volume.shape == (61, 195, 487)
    assert scan.get_max_index() == (approx(63957), (33, 103, 238))
    assert scan.image_background() == approx(1.0)

    times = scan.get_scan_time()
    assert times.shape == (61, )
    assert (times[-1] - times[0]).total_seconds() == approx(6.0)


@only_dls_file_system
def test_i06_data():
    f = DIR + '/i06/i06-384074.nxs'
    scan = NexusScan(f)

    image = scan.image()
    assert image.shape == (512, 512)

    plot = scan.get_plot_data()
    assert plot['axes_names'] == ['pol', 'ds']
    assert plot['signal_names'] == ['YDriver1_meanvalue']
    assert plot['xlabel'] == 'pol'
    assert plot['ylabel'] == 'medipix'
    assert plot['xdata'].shape == (40,)
    assert plot['ydata'].shape == (40, 1)


@only_dls_file_system
def test_save_load_nexus_scan():
    f = DIR + '/i16/1109527.nxs'
    scan = NexusScan(f)

    some_data = np.arange(100).reshape((10, 10))
    scan.add_local(some_data=some_data)
    eval_data = scan('max(signal / Transmission / (rc/300.) / _t)')  # added to local
    signal_data = scan('signal')  # added to local

    # write nexus
    scan.save('test_nexus_scan.nxs')

    # load nexus
    check_scan = load_nexus_scan('test_nexus_scan.nxs')
    assert check_scan.filename == f
    assert check_scan.map.filename == f
    assert check_scan._local_data['signal'] == approx(signal_data)
    assert check_scan('max(signal / Transmission / (rc/300.) / _t)') == approx(eval_data)
    assert check_scan('axes').shape == (61, )

    check_scan = NexusScan('test_nexus_scan.nxs')
    check_scan.load_local_data()
    assert check_scan.filename == f
    assert check_scan.map.filename == f
    assert check_scan._local_data['signal'] == approx(signal_data)
    assert check_scan('max(signal / Transmission / (rc/300.) / _t)') == approx(eval_data)
    assert check_scan('axes').shape == (61,)

    os.remove('test_nexus_scan.nxs')


@only_dls_file_system
def test_save_load_csv():
    f = DIR + '/i16/1109527.nxs'
    scan = NexusScan(f)
    scan.save_csv('test_nexus_scan.csv', 'axes', 'signal', 'sqrt(signal)')

    data = np.loadtxt('test_nexus_scan.csv', delimiter=',')
    assert data.shape == (61, 3)


@only_dls_file_system
def test_save_load_nxdata():
    f = DIR + '/i16/1144224.nxs'  # 2D scan
    scan = NexusScan(f)

    # write nexus
    scan.save('test_nexus_scan.nxs')
    with h5py.File('test_nexus_scan.nxs', 'a') as hdf:
        scan.save_nxdata(hdf['NexusScan'], 'data', 'axes', 'signal', 'sqrt(signal)', default=True)

    with h5py.File('test_nexus_scan.nxs', 'r') as h:
        assert isinstance(h['NexusScan/data/sx'], h5py.Dataset)
        assert isinstance(h['NexusScan/data/sy'], h5py.Dataset)
        assert isinstance(h['NexusScan/data/roi2_sum'], h5py.Dataset)
        assert len(h['NexusScan/data']) == 5

    os.remove('test_nexus_scan.nxs')


@only_dls_file_system
def test_copy_file():
    f = DIR + '/i16/1109527.nxs'
    scan = NexusScan(f)

    if os.path.isfile('test_copy_1109527.nxs'):
        print("test_copy_1109527.nxs exists - removing")
        os.remove('test_copy_1109527.nxs')
    if os.path.isfile('1109527-pilatus3_100k.hdf'):
        print("1109527-pilatus3_100k.hdf exists - removing")
        os.remove('1109527-pilatus3_100k.hdf')

    original_file_size = os.path.getsize(f)
    links = scan.map.find_links()
    original_additional_size = sum([os.path.getsize(DIR + '/i16/' + ff) for ff in links.values()])
    print(f"Original file is {original_file_size*1e-6:.2f} MB, +  {original_additional_size*1e-6:.2f} MB in {len(links)} linked files.")

    # copy linked files
    scan.copy_file('test_copy_1109527.nxs', copy_linked_files=True)
    new_file_size = os.path.getsize('test_copy_1109527.nxs')
    print(f"New file (copy links) is {new_file_size*1e-6:.2f} MB")

    with h5py.File('test_copy_1109527.nxs', 'r') as h:
        assert '/entry/instrument/pil3_100k/data' in h
        assert isinstance(h['/entry/instrument/pil3_100k/data'], h5py.Dataset)

    # Merge & compress linked files
    if os.path.isfile('test_copy_1109527_merge.nxs'):
        print("test_copy_1109527_merge.nxs exists - removing")
        os.remove('test_copy_1109527_merge.nxs')
    scan.copy_file('test_copy_1109527_merge.nxs', merge_links=True)
    new_file_size = os.path.getsize('test_copy_1109527_merge.nxs')
    print(f"New file (with merge) is {new_file_size * 1e-6:.2f} MB")

    with h5py.File('test_copy_1109527_merge.nxs', 'r') as h:
        dataset = h['/entry/instrument/pil3_100k/data']
        assert isinstance(dataset, h5py.Dataset)
        assert dataset[-1].shape == (195, 487)
        assert dataset.attrs['signal'] == 1
        assert new_file_size < 0.2 * (original_file_size + original_additional_size)  # compression makes this much smaller
        assert scan.image(0) == approx(dataset[0])  # lossless compression

    os.remove('test_copy_1109527_merge.nxs')
    os.remove('1109527-pilatus3_100k.hdf')
    os.remove('test_copy_1109527.nxs')