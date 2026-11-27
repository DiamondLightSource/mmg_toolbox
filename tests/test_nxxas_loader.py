"""Tests for XAS scans written to NeXus files."""

import h5py
import numpy as np
from numpy.testing import assert_array_equal

from mmg_toolbox.xas import create_xas_scan
from mmg_toolbox.xas.nxxas_loader import get_absorption_edge, load_from_nxs


def test_write_and_reload_absorption_edge(tmp_path):
    energy = np.linspace(705., 730., 51)
    monitor = np.full_like(energy, 2.)
    signal = np.linspace(1., 3., energy.size)
    scan = create_xas_scan(
        "1234", energy, monitor, {"tey": signal}, scan_no=1234, element_edge="FeL3"
    )
    filename = str(tmp_path / "scan.nxs")
    scan.write_nexus(filename)

    reloaded = load_from_nxs(filename)

    assert (reloaded.metadata.element, reloaded.metadata.edge) == ("Fe", "L3")
    assert_array_equal(reloaded.metadata.energy, energy)
    assert_array_equal(reloaded.spectra["tey"].signal, signal / monitor)


def test_read_legacy_edge_and_scalar_fallback(tmp_path):
    with h5py.File(tmp_path / "legacy.nxs", "w") as hdf:
        entry = hdf.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"
        entry["definition"] = "NXxas"
        entry["element"] = "Fe"
        entry["edge"] = "L2"
        edge = entry.create_group("absorption")
        edge.attrs["NX_class"] = "NXedge"
        edge["name"] = "L3"

        assert get_absorption_edge(entry) == ("Fe", "L3")

        del entry["absorption"]
        assert get_absorption_edge(entry) == ("Fe", "L2")
