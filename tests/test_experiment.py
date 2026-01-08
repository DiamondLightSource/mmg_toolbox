"""
mmg_toolbox tests
Test experiment folder functions
"""


from mmg_toolbox.utils.experiment import Experiment
from mmg_toolbox.nexus.nexus_scan import NexusScan, NexusDataHolder
from . import only_dls_file_system
from .example_files import DIR

@only_dls_file_system
def test_file_loader():
    exp = Experiment(DIR + '/i16', DIR + '/i16/cm37262-1')
    scan = exp.scan(1109527)
    assert isinstance(scan, NexusDataHolder)
    scan_range = range(1032120, 1032130)
    scans = exp.scans(*scan_range)
    assert len([scn for scn in scans if isinstance(scn, NexusScan)]) == len(scans)


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




