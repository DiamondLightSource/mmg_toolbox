"""
mmg_toolbox tests
Test ROI expressions
"""
import numpy as np

from mmg_toolbox.nexus.nexus_scan import NexusScan, load_nexus_scan
from . import only_dls_file_system


def test_unravel_index():
    # useful test to play with numpy unravel index
    a = np.zeros((31, 101, 61))
    a[15, 51, 31] = 1
    a[1, 1, 1] = 10

    rmnj, rmnk = (20, 21)
    b = a[:, rmnj:60, rmnk:43]

    i, j, k = np.unravel_index(np.argmax(b), b.shape)
    assert (i, j + rmnj, k + rmnk) == (15, 51, 31)


def test_background_subtraction():
    # check the correct way to average the background
    a = np.ones((31, 101, 101))
    b = 1 * a
    a[15, 45:55, 45:55] = 10
    b[:, 45:55, 45:55] = 0
    roi = a[:, 45:55, 45:55]
    bkg = a[:, 40:60, 40:60]
    bkg2 = b[:, 40:60, 40:60]
    area = roi.shape[1] * roi.shape[2]
    assert area == 100
    assert (roi[15].max(), roi[15].min()) == (10, 10)
    assert (bkg.max(), bkg.min()) == (10, 1)
    assert bkg.shape[1] == roi.shape[1] * 2
    assert roi.shape[1] * roi.shape[2] == (bkg.shape[1] * bkg.shape[2])/4
    roi_total = roi.sum(axis=(1,2))
    bkg_total = bkg.sum(axis=(1,2)) - roi_total
    bkg_compare = bkg2.sum(axis=(1,2))
    assert np.allclose(bkg_total, bkg_compare)
    assert roi_total[15] == 10 * area
    assert bkg_total[15].sum() == 3 * roi.shape[1] * roi.shape[2]
    roi_rmbkg = roi_total - (bkg_total / 3)
    assert (roi_rmbkg.max(), roi_rmbkg.min()) == (9 * area, 0)
    c = np.zeros_like(roi_total)
    c[15] = 900  # signal 10 - background 1
    assert np.allclose(roi_rmbkg, c)


@only_dls_file_system
def test_roi_expression():
    f = '/dls/science/groups/das/ExampleData/i16/temp_dep/1160565.nxs'
    scan = NexusScan(f)

    expr = """
    ***
    def around_max(a, dj, dk):
        _, j, k = unravel_index(argmax(a), a.shape)
        mn_j = max(j-dj//2, 0)
        mn_k = max(k-dk//2, 0)
        mx_j = min(j+dj//2 + dj % 2, a.shape[1]-1)
        mx_k = min(k+dk//2 + dk % 2, a.shape[2]-1)
        return j, k, a[:, mn_j:mx_j, mn_k:mx_k]

    ***
    vol=zeros((31,27,41))
    vol[15,5,5]
    j, k, roi = around_max(vol, 31, 43)
    roi
    """

    assert scan(expr).shape == (31, 16, 22)


@only_dls_file_system
def test_roi_region_expression():
    f = '/dls/science/groups/das/ExampleData/i16/temp_dep/1160565.nxs'
    scan = NexusScan(f)

    header = """
    ***
    def around_max(a, dj, dk, rj, rk, drj, drk):
        rmn_j = max(rj-drj//2, 0)
        rmn_k = max(rk-drk//2, 0)
        rmx_j = min(rj+(drj+1)//2, a.shape[1]-1)
        rmx_k = min(rk+(drk+1)//2, a.shape[2]-1)
        search = a[:, rmn_j:rmx_j, rmn_k:rmx_k]
    
        i, j, k = unravel_index(argmax(search), search.shape)
        i, j, k = i, j+rmn_j, k+rmn_k
        mn_j = max(j-dj//2, 0)
        mn_k = max(k-dk//2, 0)
        mx_j = min(j+(dj+1)//2, a.shape[1]-1)
        mx_k = min(k+(dk+1)//2, a.shape[2]-1)
        roi = a[:, mn_j:mx_j, mn_k:mx_k]
        box = array([[mn_j, mn_k], [mn_j, mx_k], [mx_j, mx_k], [mx_j, mn_k], [mn_j, mn_k]])
        return roi, box, (i, j, k)
    
    vol=zeros((31,101,101))
    vol[1,2,3] = 100
    vol[15,51,41] = 10
    ***
    """

    expr = header + """
    roi, box, (i, j, k) = around_max(vol, 31, 43, 51, 51, 41, 41)
    i,j,k
    """

    assert scan(expr) == (15, 51, 41)


@only_dls_file_system
def test_roi():
    f = '/dls/science/groups/das/ExampleData/i16/temp_dep/1160565.nxs'
    scan = NexusScan(f)
    scan.add_roi('new_roi', cen_i='pil3_centre_j', cen_j='pil3_centre_i', wid_i=35, wid_j=45)
    roi = scan('new_roi')
    assert roi.shape == (81, 35, 45)
    roi_total, roi_max, roi_min, roi_mean = scan('new_roi_total, new_roi_max, new_roi_min, new_roi_mean')
    assert roi_total.shape == roi_max.shape == roi_min.shape == roi_mean.shape == (81,)
    roi_bkg, roi_rmbkg = scan('new_roi_bkg, new_roi_rmbkg')
    assert roi_rmbkg[0] < roi_total[0]
    norm = float(np.mean(roi_total[:5] + roi_bkg[:5])) / 2
    assert np.mean(roi_total[:5] - roi_bkg[:5]) / norm < 0.1
    assert abs(np.mean(roi_rmbkg)) / norm < 0.1

    # import matplotlib.pyplot as plt
    # plt.figure()
    # plt.plot(roi_total, label='total')
    # plt.plot(roi_bkg, label='bkg')
    # plt.plot(roi_rmbkg, label='rmbkg')
    # plt.legend()
    # plt.show()
    # assert False


@only_dls_file_system
def test_peak_roi():
    f = '/dls/science/groups/das/ExampleData/i16/temp_dep/1160565.nxs'
    scan = NexusScan(f)
    scan.add_peak_roi('peak_roi', wid_i=30, wid_j=30, image_name='IMAGE',
                      rgn_cen_i='pil3_centre_j', rgn_cen_j='pil3_centre_i',
                      rgn_wid_i=101, rgn_wid_j=101)

    pi, pj, pk = scan('peak_roi_pos')
    assert (pi, pj, pk) == (39, 107, 237)
    total, rmbkg, bkg = scan('peak_roi_total, peak_roi_rmbkg, peak_roi_bkg')
    assert total.shape == rmbkg.shape == bkg.shape == (81, )
    assert rmbkg.max() < total.max()
    assert abs(rmbkg.min()) < 0.1 * total.min()
    ax_values, ax_name = scan.get_plot_axis('peak_roi_rmbkg')
    assert ax_name == 'peak_roi_rmbkg'

    # import matplotlib.pyplot as plt
    # plt.figure()
    # plt.plot(total, label='total')
    # plt.plot(bkg, label='bkg')
    # plt.plot(rmbkg, label='rmbkg')
    # plt.legend()
    # plt.show()
    # assert False