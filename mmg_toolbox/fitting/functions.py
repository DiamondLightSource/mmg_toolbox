"""
Peak functions
"""

import numpy as np


__all__ = ['poisson_errors', 'peak_ratio', 'gen_weights', 'gauss', 'group_adjacent', 'find_peaks', 'find_peaks_str', 'max_index']


def poisson_errors(y: np.ndarray) -> np.ndarray:
    """Default error function for counting statistics"""
    return np.sqrt(np.abs(y) + 1)


def peak_ratio(y: np.ndarray, yerror: np.ndarray | None = None) -> float:
    """
    Return the ratio signal / error for given dataset
    From Blessing, J. Appl. Cryst. (1997). 30, 421-426 Equ: (1) + (6)
      peak_ratio = (sum((y-bkg)/dy^2)/sum(1/dy^2)) / sqrt(i/sum(1/dy^2))
    :param y: array of y data
    :param yerror: array of errors on data, or None to calcualte np.sqrt(y+0.001)
    :return: float ratio signal / err
    """
    if yerror is None:
        yerror = poisson_errors(y)
    bkg = np.min(y)
    wi = 1 / yerror ** 2
    signal = np.sum(wi * (y - bkg)) / np.sum(wi)
    err = np.sqrt(len(y) / np.sum(wi))
    return signal / err


def gen_weights(yerrors=None) -> np.ndarray | None:
    """
    Generate weights for fitting routines
    :param yerrors: array(n) or None
    :return: array(n) or None
    """
    if yerrors is None or np.all(np.abs(yerrors) < 0.001):
        weights = None
    else:
        yerrors = np.asarray(yerrors, dtype=float)
        yerrors[yerrors < 1] = 1.0
        weights = 1 / yerrors
        weights = np.abs(np.nan_to_num(weights))
    return weights


def gauss(x: np.ndarray, y: np.ndarray | None = None,
          height: float = 1, cen: float = 0, fwhm: float = 0.5,
          bkg: float = 0, cen_y: float | None = None,
          fwhm_y: float | None = None) -> np.ndarray:
    """
    Define Gaussian distribution in 1 or 2 dimensions

        y[1xn] = gauss(x[1xn], height=10, cen=0, fwhm=1, bkg=0)
           - OR -
        Z[nxm] = gauss(x[1xn], y[1xm], height=100, cen=4, fwhm=5, bkg=30)

    From http://fityk.nieto.pl/model.html

    height is related to amplitude (area) by:
        height = (area / fwhm) * sqrt(4*ln(2)/pi) ~ 0.94 * area / fwhm
        area = height * fwhm /  sqrt(4*ln(2)/pi) ~ 1.06 * height * fwhm
        - or for 2D -
        area = height * fwhm_x * fwhm_y * (pi / 4*ln(2))
    sigma is related to fwhm by:
        fwhm = 2 * sqrt(2*ln(2)) * sigma
        sigma = fwhm / (2*sqrt(2*ln(2)))

    :param x: [1xn] array of values, defines size of gaussian in dimension 1
    :param y: None* or [1xm] array of values, defines size of gaussian in dimension 2
    :param height: peak height
    :param cen: peak centre
    :param fwhm: peak full width at half-max
    :param bkg: background
    :param cen_y: peak centre in y-axis (None to use cen)
    :param fwhm_y: peak full width in y-axis (None to use fwhm)
    :returns: [1xn array] Gassian distribution
    - or, if y is not None: -
    :returns: [nxm array] 2D Gaussian distribution
    """

    cen_x = cen
    fwhm_x = fwhm
    if cen_y is None:
        cen_y = cen
    if fwhm_y is None:
        fwhm_y = fwhm
    if y is None:
        y = cen_y

    x = np.asarray(x, dtype=float).reshape([-1])
    y = np.asarray(y, dtype=float).reshape([-1])
    X, Y = np.meshgrid(x, y)
    g = height * np.exp(
        -np.log(2) * (
                ((X - cen_x) ** 2) / (fwhm_x / 2) ** 2 +
                ((Y - cen_y) ** 2) / (fwhm_y / 2) ** 2
        )
    ) + bkg

    if len(y) == 1:
        g = g.reshape([-1])
    return g


def group_adjacent(values: np.ndarray, close: float = 10):
    """
    Average adjacent values in array, return grouped array and indexes to return groups to original array

    E.G.
     grp, idx = group_adjacent([1,2,3,10,12,31], close=3)
     grp -> [2, 11, 31]
     idx -> [[0,1,2], [3,4], [5]]

    :param values: array of values to be grouped
    :param close: float
    :return grouped_values: float array(n) of grouped values
    :return indexes: [n] list of lists, each item relates to an averaged group, with indexes from values
    """
    # Check distance between good peaks
    dist_chk = []
    dist_idx = []
    gx = 0
    dist = [values[gx]]
    idx = [gx]
    while gx < len(values) - 1:
        gx += 1
        if (values[gx] - values[gx - 1]) < close:
            dist += [values[gx]]
            idx += [gx]
        else:
            dist_chk += [np.mean(dist)]
            dist_idx += [idx]
            dist = [values[gx]]
            idx = [gx]
    dist_chk += [np.mean(dist)]
    dist_idx += [idx]
    return np.array(dist_chk), dist_idx


def local_maxima_1d(y: np.ndarray) -> np.ndarray:
    """
    Find local maxima in 1d array
    Returns points with central point higher than neighboring points.

    Copied from scipy.signal._peak_finding_utils
    https://github.com/scipy/scipy/blob/v1.7.1/scipy/signal/_peak_finding_utils.pyx

    :param y: list or array
    :return: array of peak indexes
    """
    y = np.asarray(y, dtype=float).reshape(-1)

    # Preallocate, there can't be more maxima than half the size of `y`
    midpoints = np.empty(y.shape[0] // 2, dtype=np.intp)
    m = 0  # Pointer to the end of valid area in allocated arrays
    i = 1  # Pointer to current sample, first one can't be maxima
    i_max = y.shape[0] - 1  # Last sample can't be maxima
    while i < i_max:
        # Test if previous sample is smaller
        if y[i - 1] < y[i]:
            i_ahead = i + 1  # Index to look ahead of current sample

            # Find next sample that is unequal to x[i]
            while i_ahead < i_max and y[i_ahead] == y[i]:
                i_ahead += 1

            # Maxima is found if next unequal sample is smaller than x[i]
            if y[i_ahead] < y[i]:
                left_edge = i
                right_edge = i_ahead - 1
                midpoints[m] = (left_edge + right_edge) // 2
                m += 1
                # Skip samples that can't be maximum
                i = i_ahead
        i += 1
    return midpoints[:m]


def find_local_maxima(y: np.ndarray, yerror: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Find local maxima in 1d arrays, returns index of local maximums, plus
    estimation of the peak power for each maxima and a classification of whether the maxima is greater than
    the standard deviation of the error.

    E.G.
        index, power, isgood = find_local_maxima(ydata)
        maxima = ydata[index[isgood]]
        maxima_power = power[isgood]

    Peak Power:
      peak power for each maxima is calculated using the peak_ratio algorithm for each maxima and adjacent points
    Good Peaks:
      Maxima are returned Good if:  power > (max(y) - min(y)) / std(yerror)

    :param y: array(n) of data
    :param yerror: array(n) of errors on data, or None to use default error function (sqrt(abs(y)+1))
    :return index: array(m<n) of indexes in y of maxima
    :return power: array(m) of estimated peak power for each maxima
    :return isgood: bool array(m) where True elements have power > power of the array
    """

    if yerror is None or np.all(np.abs(yerror) < 0.1):
        yerror = poisson_errors(y)
    else:
        yerror = np.asarray(yerror, dtype=float)
    yerror[yerror < 1] = 1.0
    bkg = np.min(y)
    wi = 1 / yerror ** 2

    index = local_maxima_1d(y)
    # average nearest 3 points to peak
    power = np.array([np.sum(wi[m - 1:m + 2] * (y[m - 1:m + 2] - bkg)) / np.sum(wi[m - 1:m + 2]) for m in index])
    # Determine if peak is good
    isgood = power > (np.max(y) - np.min(y)) / (np.std(yerror) + 1)
    return index, power, isgood


def find_peaks(y: np.ndarray, yerror: np.ndarray | None = None,
               min_peak_power: float | None = None, peak_distance_idx: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """
    Find peak shaps in linear-spaced 1d arrays with poisson like numerical values

    E.G.
      index, power = find_peaks(ydata, yerror, min_peak_power=None, peak_distance_idx=10)
      peak_centres = xdata[index]  # ordered by peak strength

    :param y: array(n) of data
    :param yerror: array(n) of errors on data, or None to use default error function (sqrt(abs(y)+1))
    :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :return index: array(m) of indexes in y of peaks that satisfy conditions
    :return power: array(m) of estimated power of each peak
    """
    # Get all peak positions
    midpoints, peak_signals, chk = find_local_maxima(y, yerror)

    if min_peak_power is None:
        good_peaks = chk
    else:
        good_peaks = peak_signals >= min_peak_power

    # select indexes of good peaks
    peaks_idx = midpoints[good_peaks]
    peak_power = peak_signals[good_peaks]
    if len(peaks_idx) == 0:
        return peaks_idx, peak_power

    # Average peaks close to each other
    group_idx, group_signal_idx = group_adjacent(peaks_idx, peak_distance_idx)
    peaks_idx = np.round(group_idx).astype(int)
    peak_power = np.array([np.sum(peak_power[ii]) for ii in group_signal_idx])

    # sort peak order by strength
    power_sort = np.argsort(peak_power)[::-1]
    return peaks_idx[power_sort], peak_power[power_sort]


def find_peaks_str(x: np.ndarray, y: np.ndarray, yerror: np.ndarray | None = None,
                   min_peak_power: float | None = None, peak_distance_idx: int = 6) -> str:
    """
    Find peak shaps in linear-spaced 1d arrays with poisson like numerical values

    E.G.
      index, power = find_peaks(ydata, yerror, min_peak_power=None, peak_distance_idx=10)
      peak_centres = xdata[index]  # ordered by peak strength

    :param x: array(n) of data
    :param y: array(n) of data
    :param yerror: array(n) of errors on data, or None to use default error function (sqrt(abs(y)+1))
    :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :return index: array(m) of indexes in y of peaks that satisfy conditions
    :return power: array(m) of estimated power of each peak
    """
    index, power = find_peaks(y, yerror, min_peak_power, peak_distance_idx)
    x_vals = x[index]
    out = f"Find Peaks:\n len: {len(x)}, max: {np.max(y):.5g}, min: {np.min(y):.5g}\n\n"
    out += '\n'.join(f"  {idx:4} {_x:10.5}  power={pwr:.3}" for idx, _x, pwr in zip(index, x_vals, power))
    return out


def max_index(array: np.ndarray) -> tuple[int, ...]:
    """Return the index of the largest value in an array."""
    max_idx = np.nanargmax(array)
    return np.unravel_index(max_idx, array.shape)

