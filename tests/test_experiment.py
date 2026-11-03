"""
mmg_toolbox tests
Test experiment folder functions
"""

import os
import numpy as np
import h5py
from pytest import approx
from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.nexus.nexus_scan import NexusScan, NexusDataHolder
from . import only_dls_file_system
from .example_files import DIR

@only_dls_file_system
def test_file_loader():
    exp = Experiment(DIR + '/i16', DIR + '/i16/cm37262-1')
    scan = exp.scan(1109527)
    assert isinstance(scan, NexusDataHolder)
    assert scan.beamline == 'i16'
    # Check local data injection
    assert scan('beamline, scan_number, filename, cmd') == ('i16', 1109527, '1109527.nxs', 'flyscancn eta_fly 0.005 61 pil3_100k 0.1 0.5 roi1 roi2')
    # Check config roi
    assert scan('pilroi1_total').shape == (61, )
    scan_range = range(1032120, 1032130)
    scans = exp.scans(*scan_range)
    assert len([scn for scn in scans if isinstance(scn, NexusScan)]) == len(scans)


@only_dls_file_system
def test_find_scans():
    exp = Experiment(DIR + '/i16/cm37262-1')
    scan_nos = exp.get_nearby_scan_numbers(1032337)
    assert len(scan_nos) == 20
    assert scan_nos[-1] - scan_nos[0] == 42
    scans = exp.find_scans(*scan_nos, **{'cmd': 'scan stokes_fly'})
    assert len(scans) == 4


@only_dls_file_system
def test_get_value_changes():
    exp = Experiment(DIR + '/i16/cm37262-1')
    scans = exp.scans(*range(1033447, 1033453))
    data = exp.get_value_changes(*scans)
    print('\n'.join(f"{name} : {np.std(array):.2f}" for name, array in data.items()))
    assert len(data) == 10
    assert next(iter(data)).endswith('stokes')
    assert np.std(data['stokes']) == approx(94.55868, abs=0.0001)


@only_dls_file_system
def test_experiment_getitem():
    exp = Experiment(DIR + '/i16')
    all_scan_numbers = exp.all_scan_numbers()
    all_scans = [s for s in exp]
    assert len(all_scans) == len(exp) == len(all_scan_numbers)
    last_scans = exp[-5:]
    assert len(last_scans) == 5
    assert isinstance(last_scans[0], NexusScan)


@only_dls_file_system
def test_check_scan():
    exp = Experiment(DIR + '/i16/cm37262-1', instrument='i16')
    out = exp.scan_str(0)
    print(out)
    assert 'Atten = 80' in out
    scan_range = range(1032120, 1032130)
    strings = exp.scans_str(*scan_range)
    print('\n'.join(strings))
    assert len(strings) == len(scan_range)


@only_dls_file_system
def test_plots():
    exp = Experiment(DIR + '/i16/cm37262-1', instrument='i16')
    exp.plot(1032120)
    # exp.plot_scans()


@only_dls_file_system
def test_2d_mesh():
    exp = Experiment('/dls/science/groups/das/ExampleData/i16/2dscans_2026/', instrument='i16')
    pass


@only_dls_file_system
def test_i16_vortex_multiplot():
    #exp = Experiment('/dls/i16/data/2026/mm43750-1', instrument='i16')
    exp = Experiment('/dls/science/groups/das/ExampleData/i16/vortex_2026', instrument='i16')
    exp.add_roi('xsp3_roi1', '1', '915', 2, 126, 'xsp3')
    exp.add_roi('xsp3_roi2', '1', '755', 2, 116, 'xsp3')
    exp.add_roi('xsp3_roi3', '1', '1104', 2, 135, 'xsp3')

    ax = exp.plot.multi_lines(1146572, 1146573, xaxis='axes', yaxis='signal')
    assert ax
    ax = exp.plot.multi_lines(1146572, 1146573, xaxis='axes', yaxis='(xsp3_roi3_total - min(xsp3_roi3_total)) / ic1monitor')
    assert ax

    scan1, scan2 = exp.scans(1146572, 1146573)

    x, x_label = scan1.get_plot_axis('axes')
    assert x_label == 'energy2'
    assert x.shape == (121, )

    data = scan1.get_plot_data('axes', 'xsp3_roi3_total')
    assert data['x'].shape == (121, )


@only_dls_file_system
def test_experiment_file():
    exp = Experiment(DIR + '/i16/cm37262-1')
    filename = DIR + '/i16/cm37262-1/cm37262-1.h5'

    if os.path.isfile(filename):
        os.remove(filename)
    exp.create_experiment_file(filename)

    with h5py.File(filename) as hdf:
        assert len(hdf) == 1332
        assert isinstance(hdf['/1032123/measurement/ic1monitor'], h5py.Dataset)
