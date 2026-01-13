"""
mmg_toolbox tests
Test metadata from beamlines
"""

import pytest

from . import only_dls_file_system
from .example_files import DIR

def test_metadata_import():
    errors = None
    try:
        from mmg_toolbox import metadata, xas_metadata, nexus_metadata
    except ImportError as e:
        errors = e
    assert errors is None


@only_dls_file_system
def test_scan_string():
    from mmg_toolbox import Experiment, metadata

    exp = Experiment(DIR + '/i16', instrument='i16')

    # print all scans in folder
    m = f"{metadata.scanno}, {metadata.start}, {metadata.cmd}, {metadata.energy}, {metadata.temp}"
    for scan in exp[:10]:
        scn, start, cmd, energy, temp = scan(m)
        assert scn > 100
        assert len(cmd) > 10

    scan = exp.scan(1109527)
    s = str(scan)
    assert s.count('\n') > 10
    assert 'energy = 7 keV' in s

    energy_str = scan.format('Energy = {incident_energy:.2f} {incident_energy@units?("keV")}')
    assert energy_str == 'Energy = 7.11 keV'
    assert scan.metadata.sy == pytest.approx(-0.7791)
    assert scan.metadata['Atten'] == pytest.approx(30)
    assert scan('Transmission') == pytest.approx(0.005684, abs=1e-6)


@only_dls_file_system
def test_scan_times():
    from mmg_toolbox import data_file_reader
    import datetime

    scan = data_file_reader(DIR + '/i10/i10-921636.nxs')
    start_time, end_time = scan.times('start_time', 'end_time')
    assert isinstance(start_time, datetime.datetime)
    assert isinstance(end_time, datetime.datetime)


