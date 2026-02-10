"""
mmg_toolbox tests
Test plotting functions
"""

import os
import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D

import mmg_toolbox.plotting.matplotlib as plots
from mmg_toolbox import Experiment, data_file_reader
from . import only_dls_file_system
from .example_files import DIR, FILES_DICT


def assert_plot(ax: plt.Axes | Axes3D) -> bool:
    ax.figure.savefig('test.png')
    check = os.path.isfile('test.png')
    if check:
        os.remove('test.png')
    return check

def test_matplotlib():
    n_plots = 25
    fig_ax = plots.generate_subplots(n_plots, subplots=(4, 4), suptitle='test')
    assert len(fig_ax) == n_plots

    x = np.arange(-10, 10, 0.1)
    y = x ** 2
    errors = np.sqrt(y + 10)
    lines = plots.plot_line(fig_ax[0][1], x, y, errors, '+-', label='stuff')
    assert len(lines) == 3

    plot_data = [(n, x, y + n) for n in range(10)]
    lines, sm = plots.plot_lines(fig_ax[1][1],*plot_data)
    assert len(lines) == 10
    assert isinstance(sm, plt.cm.ScalarMappable)


@only_dls_file_system
def test_exp_plots():
    exp = Experiment(DIR + '/i16/cm37262-1', instrument='i16')

    ax = exp.plot(-1)
    assert assert_plot(ax)

    rng = range(1032510, 1032521)
    ax = exp.plot(*rng)
    assert assert_plot(ax)
    fig_ax = exp.plot.multi_plot(*rng)
    fig, ax = fig_ax[0]
    assert assert_plot(ax)
    ax = exp.plot.surface_2d(*rng)
    assert assert_plot(ax)
    ax = exp.plot.lines_3d(*rng)
    assert isinstance(ax, Axes3D)
    assert assert_plot(ax)
    ax = exp.plot.surface_3d(*rng)
    assert isinstance(ax, Axes3D)
    assert assert_plot(ax)

@only_dls_file_system
def test_scan_plot():
    # Old file types
    scan = data_file_reader(FILES_DICT['i16 pilatus eta scan, tiff files, no defaults'])
    ax = scan.plot()
    assert assert_plot(ax)
    scan = data_file_reader(FILES_DICT['i16 pilatus eta scan, old nexus format'])
    ax = scan.plot()
    assert assert_plot(ax)
    scan = data_file_reader(FILES_DICT['i16 pilatus hkl scan, new nexus format'])
    ax = scan.plot()
    assert assert_plot(ax)
    # processed msmapper file
    scan = data_file_reader(DIR + "/i16/processed/1109527_msmapper.nxs")
    ax = scan.plot()
    assert assert_plot(ax)
    # Plotting methods
    scan = data_file_reader(FILES_DICT['i16 pilatus hkl scan, new nexus format'])
    ax = scan.plot.plot('axes', 'signal')
    assert assert_plot(ax)
    scan = data_file_reader(FILES_DICT['i10 pimte new scan'])
    ax = scan.plot.image()
    assert assert_plot(ax)
    scan = data_file_reader(FILES_DICT['i16 merlin 2d delta gam calibration'])
    ax = scan.plot.map2d('delta', 'gamma')
    assert assert_plot(ax)