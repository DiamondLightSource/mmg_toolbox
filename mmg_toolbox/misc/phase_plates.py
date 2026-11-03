"""
Miscellaneous Data Analysis Functions for Phase Plates
"""

import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox import NexusScan

# TODO: Tidy up code


def scan_phaseplate_normalisation(scan: NexusScan, x_data: str = 'axes', sigma_data: str = '(C1+C3)/2',
                                  pi_data: str = '(C2+C4)/2', monitor: str | None = 'ic1monitor',
                                  normalise_type: str = 'left', show_difference: bool = False,
                                  plot: bool = False) -> tuple[float, float, float, float]:
    x_data, sigma_data, pi_data, monitor = scan(f'{x_data}, {sigma_data}, {pi_data}, {monitor}')
    return phaseplate_normalisation(x_data, sigma_data, pi_data, monitor, normalise_type, show_difference, plot)


def phaseplate_normalisation(x_data: np.ndarray, sigma_data: np.ndarray, pi_data: np.ndarray,
                             monitor: np.ndarray | None = None, normalise_type: str = 'left',
                             show_difference: bool = False, plot: bool = False) -> tuple[float, float, float, float]:
    """
    Normalise polarisation scans and determine crossing points for phase plate scans polarisation scans.
        neg, pos, centre, offset = phaseplate_normalisation(xdata, ydata_sigma, ydata_pi, ydata_monitor)

    xdata = array(n) of scanned data
    sigma_data = array(n) of data in the vertical polarisation channel
    pi_data = array(n) of data in the horizontal polarisation channel
    monitor = array(n) of data to use to normalise sigma and pi (or leave as None)
    normalise_type = min, left*, right, mean, none - method of normalisation of max/min values
    plot = True/ False - create plot
    show_difference=False/ True - display diff on plot

    neg = negative offset
    pos = positive offset
    centre = average point between neg and pos
    offset = offset value from centre to pos
    """
    x_data = np.asarray(x_data)
    sigma_data = np.asarray(sigma_data)
    pi_data = np.asarray(pi_data)
    if monitor is None:
        monitor = np.ones_like(sigma_data)
    else:
        monitor = np.asarray(monitor)

    sigma_data = sigma_data / monitor
    pi_data = pi_data / monitor

    if normalise_type.lower() in ['none']:
        min_sigma = 0
        min_pi = 0
        max_sigma = 1
        max_pi = 1
    elif normalise_type.lower() in ['mean']:
        min_sigma = sigma_data.min()
        min_pi = np.mean(np.append(pi_data[:5], pi_data[-5:]))
        max_sigma = np.mean(np.append(sigma_data[:5], sigma_data[-5:]))
        max_pi = pi_data.max()
    elif normalise_type.lower() in ['right', 'r']:
        min_sigma = sigma_data.min()
        min_pi = np.mean(pi_data[-5:])
        max_sigma = np.mean(sigma_data[-5:])
        max_pi = pi_data.max()
    elif normalise_type.lower() in ['left', 'l', 'start']:
        min_sigma = sigma_data.min()
        min_pi = np.mean(pi_data[:5])
        max_sigma = np.mean(sigma_data[:5])
        max_pi = pi_data.max()
    else:
        min_sigma = sigma_data.min()
        min_pi = pi_data.min()
        max_sigma = sigma_data.max()
        max_pi = pi_data.max()

    # Normalise
    sigma_data = (sigma_data - min_sigma) / np.max(sigma_data - min_sigma)
    pi_data = (pi_data - min_pi) / np.max(pi_data - min_pi)

    # interpolate
    ival = np.linspace(np.min(x_data), np.max(x_data), 100 * len(x_data))
    isigma = np.interp(ival, x_data, sigma_data)
    ipi = np.interp(ival, x_data, pi_data)

    diff = np.abs(isigma - ipi)

    if plot:
        fig, ax1 = plt.subplots()
        plt.plot(x_data, sigma_data, 'b-', lw=2, label=r'$\sigma$')
        plt.plot(x_data, pi_data, 'r-', lw=2, label=r'$\pi$')
        if show_difference:
            plt.plot(ival, diff, 'k-', lw=0.5, label=r'|$\sigma$-$\pi$|')
        plt.legend()

        ax2 = ax1.twinx()
        plt.plot(x_data, monitor, 'g:', lw=2, label='ic1monitor')
        plt.ylabel('ic1monitor')
        ax2.tick_params(axis='y', labelcolor='g')
        ax2.set_ylabel('ic1monitor', color='g')

    # find smallest differences furthest appart
    npoints = 0
    percentile = 0
    while npoints < 2:
        percentile += 1
        minthresh = np.percentile(diff, percentile)
        minxvals = ival[diff < minthresh]
        npoints = len(minxvals)
    neg = minxvals[0]
    pos = minxvals[-1]

    avmid = (pos + neg) / 2
    negoff = neg - avmid
    posoff = pos - avmid
    midpoint = x_data[np.argmin(monitor)]
    print('\n---Polarisation scan---')
    print('Estimated Midpoint: %7.3f' % (midpoint))
    print('   Lower intercept: %8.4f (%+6.4f)' % (neg, negoff))
    print('   Upper intercept: %8.4f (%+6.4f)' % (pos, posoff))
    print('   Actual midpoint: %8.4f' % (avmid))

    if plot:
        plt.sca(ax1)
        plt.axvline(neg, c='k', lw=0.5)
        plt.axvline(pos, c='k', lw=0.5)
        plt.show()
    return neg, pos, avmid, posoff

