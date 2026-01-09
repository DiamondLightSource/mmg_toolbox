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

    exp = Experiment(r"D:\I16_Data\mm22052-1", instrument='i16')

    # print all scans in folder
    m = f"{metadata.scanno}, {metadata.start}, {metadata.cmd}, {metadata.energy}, {metadata.temp}"
    for scan in exp[:10]:
        scn, start, cmd, energy, temp = scan(m)
        assert scn > 100
        assert len(cmd) > 10

    scan = exp.scan(776058)
    s = str(scan)
    assert s.count('\n') > 10
    assert 'energy = 8 keV' in s

    energy_str = scan.format('Energy = {incident_energy:.2f} {incident_energy@units?("keV")}')
    assert energy_str == 'Energy = 8.00 keV'
    assert scan.metadata.sy == pytest.approx(-1.6954)
