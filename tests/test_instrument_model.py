"""
mmg_toolbox tests
Test NXtransformations and instrument model
"""

from pytest import approx
from mmg_toolbox.nexus.instrument_model import NXInstrumentModel
from mmg_toolbox.nexus.nexus_reader import read_nexus_file
from . import only_dls_file_system
from .example_files import DIR

@only_dls_file_system
def test_instrument_model():
    f = DIR + 'i16/1116988.nxs'
    scan = read_nexus_file(f)
    model = scan.instrument_model()
    assert isinstance(model, NXInstrumentModel)
    print(model.string)
    assert len(model.string.splitlines()) == 47
    s = "Rotating sample about [-1.  0.  0.] by 25.792 deg  | /entry/sample/transformations/phi"
    assert s in model.string


@only_dls_file_system
def test_pixel2hkl():
    f = "/dls/science/groups/das/ExampleData/i16/msmapper_test/1161043.nxs"
    scan = read_nexus_file(f)
    model = scan.instrument_model()

    frames, ii, jj = model.shape()
    assert (frames, ii, jj) == (59, 195, 487)
    # central frame, pixel hkl = (1.0, 0.99, 8.0)
    h, k, l = model.hkl((frames // 2, ii // 2, jj // 2))
    assert (h, k, l) == approx((0.999464, 0.990797, 7.996309))
    h, k, l = model.pixel2hkl(0, 0, 10)
    assert (h, k, l) == approx((0.870875, 0.994514, 7.834503))
    border_hkl = model.detector_border_hkl(frames // 2)
    assert border_hkl.shape == (195 + 195 + 487 + 487, 3)
    frame_hkl = model.frame_pixels_hkl(None)
    assert frame_hkl.shape == (ii * jj, 3)
    # all_hkl = model.all_pixels_hkl()  # this is very slow, takes about 1 min
    # assert all_hkl.shape == (frames * ii * jj, 3)

    ij = (0, 0), (1, 1), (2, 2), (3, 3), (195, 487)
    hkl = model._hkl(0, *ij)
    assert hkl.shape == (len(ij), 3)
    for n, (i, j) in enumerate(ij):
        assert hkl[n] == approx(model.hkl((0, i, j)))