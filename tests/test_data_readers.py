"""
mmg_toolbox tests
Test data readers
"""

import time
from mmg_toolbox.nexus.nexus_scan import NexusScan
from . import only_dls_file_system
from .example_files import DIR, FILES


@only_dls_file_system
def test_multi_expression_time():
    # Check speed of reading a file multiple times vs opening once
    f, desc = FILES[4]
    scan = NexusScan(f)
    names = list(scan.map.combined.keys())[:100]
    t0 = time.time_ns()
    values_multi = [scan.eval(name) for name in names]
    t1 = time.time_ns()
    with scan.map.load_hdf() as hdf:
        values_single = [scan.map.eval(hdf, name) for name in names]
    t2 = time.time_ns()
    values_multi = [scan.eval(name) for name in names]
    t3 = time.time_ns()

    print(f"\nMulti-read time = {(t1 - t0) * 1e-9:.3f} seconds")
    print(f"Single-read time = {(t2 - t1) * 1e-9:.3f} seconds")
    print(f"Multi-read time = {(t3 - t2) * 1e-9:.3f} seconds")
    ratio = (t3 - t2) / (t2 - t1)
    print(f"Single read time is {ratio:.3g} times faster then multi-read")
    assert values_multi == values_single


