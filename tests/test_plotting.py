"""
mmg_toolbox tests
Test plotting functions
"""

import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D

import mmg_toolbox.plotting.matplotlib as plots
from mmg_toolbox.utils.experiment import Experiment
from . import only_dls_file_system
from .example_files import DIR


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
    assert isinstance(ax, plt.Axes)

    rng = range(1032510, 1032521)
    ax = exp.plot(*rng)
    assert isinstance(ax, plt.Axes)
    fig_ax = exp.plot.multi_plot(*rng)
    fig, ax = fig_ax[0]
    assert isinstance(ax, plt.Axes)
    ax = exp.plot.surface_2d(*rng)
    assert isinstance(ax, plt.Axes)
    ax = exp.plot.lines_3d(*rng)
    assert isinstance(ax, Axes3D)
    ax = exp.plot.surface_3d(*rng)
    assert isinstance(ax, Axes3D)

