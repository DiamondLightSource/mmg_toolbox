"""
Fitting functions using lmfit

See: https://lmfit.github.io/lmfit-py/builtin_models.html

Use of peakfit:
from fitting import peakfit
fit = peakfit(xdata, ydata)  # returns lmfit object
print(fit)
fit.plot()
"""

import numpy as np
from lmfit.models import (
    GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, LinearModel, ExponentialModel,
    SineModel
)
from lmfit.model import ModelResult, Model, Parameters
from .misc_functions import stfm
from ..nexus.nexus_scan import NexusScan

# https://lmfit.github.io/lmfit-py/builtin_models.html#peak-like-models
MODELS = {
    'gaussian': GaussianModel,
    'lorentz': LorentzianModel,
    'voight': VoigtModel,
    'pvoight': PseudoVoigtModel,
    'linear': LinearModel,
    'exponential': ExponentialModel,
    'SineModel': SineModel,
}  # list of available lmfit models

PEAK_MODELS = {
    'gaussian': ['gaussian', 'gauss'],
    'voight': ['voight', 'voight model'],
    'pvoight': ['pseudovoight', 'pvoight'],
    'lorentz': ['lorentz', 'lorentzian', 'lor'],
}  # alternaive names for peaks

BACKGROUND_MODELS = {
    'linear': ['flat', 'slope', 'linear', 'line', 'straight'],
    'exponential': ['exponential', 'curve']
}  # alternaive names for background models

# https://lmfit.github.io/lmfit-py/fitting.html#fit-methods-table
METHODS = {
    'leastsq': 'Levenberg-Marquardt',
    'nelder': 'Nelder-Mead',
    'lbfgsb': 'L-BFGS-B',
    'powell': 'Powell',
    'cg': 'Conjugate Gradient',
    'newton': 'Newton-CG',
    'cobyla': 'COBYLA',
    'bfgsb': 'BFGS',
    'tnc': 'Truncated Newton',
    'trust-ncg': 'Newton CG trust-region',
    'trust-exact': 'Exact trust-region',
    'trust-krylov': 'Newton GLTR trust-region',
    'trust-constr': 'Constrained trust-region',
    'dogleg': 'Dogleg',
    'slsqp': 'Sequential Linear Squares Programming',
    'differential_evolution': 'Differential Evolution',
    'brute': 'Brute force method',
    'basinhopping': 'Basinhopping',
    'ampgo': 'Adaptive Memory Programming for Global Optimization',
    'shgo': 'Simplicial Homology Global Ooptimization',
    'dual_annealing': 'Dual Annealing',
    'emcee': 'Maximum likelihood via Monte-Carlo Markov Chain',
}


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
          bkg: float = 0, cen_y: float | None = None) -> np.ndarray:
    """
    Define Gaussian distribution in 1 or 2 dimensions

        y[1xn] = gauss(x[1xn], height=10, cen=0, fwhm=1, bkg=0)
           - OR -
        Z[nxm] = gauss(x[1xn], y[1xm], height=100, cen=4, fwhm=5, bkg=30)

    From http://fityk.nieto.pl/model.html


    :param x: [1xn] array of values, defines size of gaussian in dimension 1
    :param y: None* or [1xm] array of values, defines size of gaussian in dimension 2
    :param height: peak height
    :param cen: peak centre
    :param fwhm: peak full width at half-max
    :param bkg: background
    :param cen_y: peak centre in y-axis (None to use cen)
    :returns: [1xn array] Gassian distribution
    - or, if y is not None: -
    :returns: [nxm array] 2D Gaussian distribution
    """

    if cen_y is None:
        cen_y = cen
    if y is None:
        y = cen_y

    x = np.asarray(x, dtype=float).reshape([-1])
    y = np.asarray(y, dtype=float).reshape([-1])
    X, Y = np.meshgrid(x, y)
    g = height * np.exp(-np.log(2) * (((X - cen) ** 2 + (Y - cen) ** 2) / (fwhm / 2) ** 2)) + bkg

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
    power = np.array([np.sum(wi[m-1:m+2] * (y[m-1:m+2] - bkg)) / np.sum(wi[m-1:m+2]) for m in index])
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


def peak_results(res: ModelResult) -> dict:
    """
    Generate dict of fit results, including summed totals
    totals = peak_results(res)
    totals = {
        'lmfit': lmfit_result (res),
        'npeaks': number of peak models used,
        'chisqr': Chi^2 of fit,
        'xdata': x-data used for fit,
        'ydata': y-data used for fit,
        'yfit': y-fit values,
        'weights': res.weights,
        'yerror': 1 / res.weights if res.weights is not None else 0 * res.data,
        # plus data from components, e.g.
        'p1_amplitude': Peak 1 area,
        'p1_fwhm': Peak 1 full-width and half-maximum
        'p1_center': Peak 1 peak position
        'p1_height': Peak 1 fitted height,
        # plus data for total fit:
        'amplitude': Total summed area,
        'center': average centre of peaks,
        'height': average height of peaks,
        'fwhm': average FWHM of peaks,
        'background': fitted background,
        # plut the errors on all parameters, e.g.
        'stderr_amplitude': error on 'amplitude',
    }
    :param res: lmfit fit result - ModelResult
    :return: {totals: (value, error)}
    """
    peak_prefx = [mod.prefix for mod in res.components if 'bkg' not in mod.prefix]
    npeaks = len(peak_prefx)
    nn = 1 / len(peak_prefx) if len(peak_prefx) > 0 else 1  # normalise by number of peaks
    comps = res.eval_components()
    # TODO: standardise these keys
    fit_dict = {
        'lmfit': res,
        'npeaks': npeaks,
        'chisqr': res.chisqr,
        'xdata': res.userkws['x'],
        'ydata': res.data,
        'weights': res.weights,
        'yerror': 1 / res.weights if res.weights is not None else 0 * res.data,
        'yfit': res.best_fit,
    }
    for comp_prefx, comp in comps.items():
        fit_dict['%sfit' % comp_prefx] = comp
    for pname, param in res.params.items():
        ename = 'stderr_' + pname
        fit_dict[pname] = param.value
        fit_dict[ename] = param.stderr if param.stderr is not None else 0
    totals = {
        'amplitude': np.sum([res.params['%samplitude' % pfx].value for pfx in peak_prefx]),
        'center': np.mean([res.params['%scenter' % pfx].value for pfx in peak_prefx]),
        'sigma': np.mean([res.params['%ssigma' % pfx].value for pfx in peak_prefx]),
        'height': np.mean([res.params['%sheight' % pfx].value for pfx in peak_prefx]),
        'fwhm': np.mean([res.params['%sfwhm' % pfx].value for pfx in peak_prefx]),
        'background': np.mean(comps['bkg_']) if 'bkg_' in comps else 0.0,
        'stderr_amplitude': np.sqrt(np.sum([fit_dict['stderr_%samplitude' % pfx] ** 2 for pfx in peak_prefx])),
        'stderr_center': np.sqrt(np.sum([fit_dict['stderr_%scenter' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        'stderr_sigma': np.sqrt(np.sum([fit_dict['stderr_%ssigma' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        'stderr_height': np.sqrt(np.sum([fit_dict['stderr_%sheight' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        'stderr_fwhm': np.sqrt(np.sum([fit_dict['stderr_%sfwhm' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        'stderr_background': np.std(comps['bkg_']) if 'bkg_' in comps else 0.0,
    }
    fit_dict.update(totals)
    return fit_dict


def peak_results_str(res: ModelResult) -> str:
    """
    Generate output str from lmfit results, including totals
    :param res: lmfit_result
    :return: str
    """
    fit_dict = peak_results(res)
    out = 'Fit Results\n'
    out += '%s\n' % res.model.name
    out += 'Npeaks = %d\n' % fit_dict['npeaks']
    out += 'Method: %s => %s\n' % (res.method, res.message)
    out += 'Chisqr = %1.5g\n' % res.chisqr
    # Peaks
    peak_prefx = [mod.prefix for mod in res.components if 'bkg' not in mod.prefix]
    for prefx in peak_prefx:
        out += '\nPeak %s\n' % prefx
        for pn in res.params:
            if prefx in pn:
                out += '%15s = %s\n' % (pn, stfm(fit_dict[pn], fit_dict['stderr_%s' % pn]))

    out += '\nBackground\n'
    for pn in res.params:
        if 'bkg' in pn:
            out += '%15s = %s\n' % (pn, stfm(fit_dict[pn], fit_dict['stderr_%s' % pn]))

    out += '\nTotals\n'
    out += '      amplitude = %s\n' % stfm(fit_dict['amplitude'], fit_dict['stderr_amplitude'])
    out += '         center = %s\n' % stfm(fit_dict['center'], fit_dict['stderr_center'])
    out += '         height = %s\n' % stfm(fit_dict['height'], fit_dict['stderr_height'])
    out += '          sigma = %s\n' % stfm(fit_dict['sigma'], fit_dict['stderr_sigma'])
    out += '           fwhm = %s\n' % stfm(fit_dict['fwhm'], fit_dict['stderr_fwhm'])
    out += '     background = %s\n' % stfm(fit_dict['background'], fit_dict['stderr_background'])
    return out


def peak_results_fit(res: ModelResult, ntimes: int = 10, x_data: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate xfit, yfit data, interpolated to give smoother variation
    :param res: lmfit_result
    :param ntimes: int, number of points * old number of points
    :param x_data: x data to interpolate or None to use data from fit
    :return: xfit, yfit
    """
    old_x = res.userkws['x'] if x_data is None else x_data
    xfit = np.linspace(np.min(old_x), np.max(old_x), np.size(old_x) * ntimes)
    yfit = res.eval(x=xfit)
    return xfit, yfit


def peak_results_plot(res: ModelResult, axes=None, xlabel: str = None, ylabel: str = None, title: str = None):
    """
    Plot peak results
    :param res: lmfit result
    :param axes: None or matplotlib axes
    :param xlabel: None or str
    :param ylabel: None or str
    :param title: None or str
    :return: matplotlib figure or axes
    """
    xdata = res.userkws['x']
    if title is None:
        title = res.model.name

    if axes:
        ax = res.plot_fit(ax=axes, xlabel=xlabel, ylabel=ylabel)
        # Add peak components
        comps = res.eval_components(x=xdata)
        for component in comps.keys():
            ax.plot(xdata, comps[component], label=component)
            ax.legend()
        return ax

    fig = res.plot(xlabel=xlabel, ylabel=ylabel)
    try:
        fig, grid = fig  # Old version of LMFit
    except TypeError:
        pass

    ax1, ax2 = fig.axes
    ax1.set_title(title, wrap=True)
    # Add peak components
    comps = res.eval_components(x=xdata)
    for component in comps.keys():
        ax2.plot(xdata, comps[component], label=component)
        ax2.legend()
    fig.set_figwidth(8)
    # fig.show()
    return fig


class FitResults:
    """
    FitResults Class
    Wrapper for lmfit results object with additional functions specific to i16_peakfit

    res = model.fit(ydata, x=xdata)  # lmfit ouput
    fitres = FitResults(res)

    --- Parameters ---
    fitres.res  # lmfit output
    # data from fit:
    fitres.npeaks # number of peak models used,
    fitres.chisqr  # Chi^2 of fit,
    fitres.xdata  # x-data used for fit,
    fitres.ydata  # y-data used for fit,
    fitres.yfit  # y-fit values,
    fitres.weights  # res.weights,
    fitres.yerror  # 1 / res.weights if res.weights is not None else 0 * res.data,
    # data from components, e.g.
    fitres.p1_amplitude  # Peak 1 area,
    fitres.p1_fwhm  # Peak 1 full-width and half-maximum
    fitres.p1_center  # Peak 1 peak position
    fitres.p1_height  # Peak 1 fitted height,
    # data for total fit:
    fitres.amplitude  # Total summed area,
    fitres.center  # average centre of peaks,
    fitres.height  # average height of peaks,
    fitres.fwhm  # average FWHM of peaks,
    fitres.background  # fitted background,
    # errors on all parameters, e.g.
    fitres.stderr_amplitude  # error on 'amplitude

    --- Functions ---
    print(fitres)  # prints formatted str with results
    ouputdict = fitres.results()  # creates ouput dict
    xdata, yfit = fitres.fit(ntimes=10)  # interpolated fit results
    fig = fitres.plot(axes, xlabel, ylabel, title)  # create plot
    """
    amplitude: float
    center: float
    height: float
    fwhm: float
    background: float
    stderr_amplitude: float
    stderr_center: float
    stderr_height: float
    stderr_fwhm: float
    stderr_background: float

    def __init__(self, results: ModelResult):
        self.res = results
        self._res = peak_results(results)
        for name in self._res:
            setattr(self, name, self._res[name])

    def __str__(self):
        return peak_results_str(self.res)

    def get_value(self, name: str) -> tuple[float | None, float]:
        """Returns fit parameter value and associated error"""
        err_name = f"stderr_{name}"
        value = self._res.get(name, None)
        error = self._res.get(err_name, 0)
        return value, error

    def results(self) -> dict:
        """Returns dict of peak fit results"""
        return self._res

    def fit_data(self, x_data: np.ndarray | None = None, ntimes=10) -> tuple[np.ndarray, np.ndarray]:
        """Returns interpolated x, y fit arrays"""
        return peak_results_fit(self.res, ntimes=ntimes, x_data=x_data)

    def plot(self, axes=None, xlabel=None, ylabel=None, title=None):
        """Plot peak fit results"""
        return peak_results_plot(self.res, axes, xlabel, ylabel, title)


def modelfit(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray | None =None, 
             model=None | Model, initial_parameters: dict | None = None, 
             fix_parameters: dict | None = None, method: str = 'leastsq', 
             print_result: bool = False, plot_result: bool = False) -> ModelResult:
    """
    Fit x,y data to a model from lmfit
    E.G.:
      res = modelfit(x, y, model='Gauss')
      print(res.fit_report())
      res.plot()
      val = res.params['amplitude'].value
      err = res.params['amplitude'].stderr

    Model:
     from lmfit import models
     model1 = model.GaussianModel()
     model2 = model.LinearModel()
     model = model1 + model2
     res = model.fit(y, x=x)

    Provide initial guess:
      res = modelfit(x, y, model=VoightModel(), initial_parameters={'center':1.23})

    Fix parameter:
      res = modelfit(x, y, model=VoightModel(), fix_parameters={'sigma': fwhm/2.3548200})

    :param xvals: array(n) position data
    :param yvals: array(n) intensity data
    :param yerrors: None or array(n) - error data to pass to fitting function as weights: 1/errors^2
    :param model: lmfit.Model
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :param method: str method name, from lmfit fitting methods
    :param print_result: if True, prints the fit results using fit.fit_report()
    :param plot_result: if True, plots the results using fit.plot()
    :return: lmfit.model.ModelResult < fit results object
    """

    xvals = np.asarray(xvals, dtype=float).reshape(-1)
    yvals = np.asarray(yvals, dtype=float).reshape(-1)
    weights = gen_weights(yerrors)

    if initial_parameters is None:
        initial_parameters = {}
    if fix_parameters is None:
        fix_parameters = {}

    if model is None:
        model = GaussianModel() + LinearModel()

    pars = model.make_params()

    # user input parameters
    for ipar, ival in initial_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=True)
    for ipar, ival in fix_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=False)

    res = model.fit(yvals, pars, x=xvals, weights=weights, method=method)

    if print_result:
        print(res.fit_report())
    if plot_result:
        res.plot()
    return res


def peakfit(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray | None = None, 
            model: str = 'Voight', background: str = 'slope',
            initial_parameters: dict | None = None, fix_parameters: dict | None = None, 
            method: str = 'leastsq', print_result: bool = False, plot_result: bool = False) -> FitResults:
    """
    Fit x,y data to a peak model using lmfit

    E.G.:
      res = peakfit(x, y, model='Gauss')
      print(res)
      res.plot()
      val = res.params['amplitude'].value
      err = res.params['amplitude'].stderr

    Peak Models:
     Choice of peak model: 'Gaussian', 'Lorentzian', 'Voight',' PseudoVoight'
    Background Models:
     Choice of background model: 'slope', 'exponential'

    Peak Parameters:
     'amplitude', 'center', 'sigma', pvoight only: 'fraction'
     output only: 'fwhm', 'height'
    Background parameters:
     'bkg_slope', 'bkg_intercept', or for exponential: 'bkg_amplitude', 'bkg_decay'

    Provide initial guess:
      res = peakfit(x, y, model='Voight', initial_parameters={'center': 1.23})

    Fix parameter:
      res = peakfit(x, y, model='gauss', fix_parameters={'sigma': fwhm/2.3548200})

    :param xvals: array(n) position data
    :param yvals: array(n) intensity data
    :param yerrors: None or array(n) - error data to pass to fitting function as weights: 1/errors^2
    :param model: str, specify the peak model: 'Gaussian','Lorentzian','Voight'
    :param background: str, specify the background model: 'slope', 'exponential'
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :param method: str method name, from lmfit fitting methods
    :param print_result: if True, prints the fit results using fit.fit_report()
    :param plot_result: if True, plots the results using fit.plot()
    :return: fit result object
    """

    xvals = np.asarray(xvals, dtype=float).reshape(-1)
    yvals = np.asarray(yvals, dtype=float).reshape(-1)
    weights = gen_weights(yerrors)

    if initial_parameters is None:
        initial_parameters = {}
    if fix_parameters is None:
        fix_parameters = {}

    peak_mod = None
    bkg_mod = None
    for model_name, names in PEAK_MODELS.items():
        if model.lower() in names:
            peak_mod = MODELS[model_name]()
    for model_name, names in BACKGROUND_MODELS.items():
        if background.lower() in names:
            bkg_mod = MODELS[model_name](prefix='bkg_')

    pars = peak_mod.guess(yvals, x=xvals)
    pars += bkg_mod.make_params()
    # pars += bkg_mod.make_params(intercept=np.min(yvals), slope=0)
    # pars['gamma'].set(value=0.7, vary=True, expr='') # don't fix gamma

    # user input parameters
    for ipar, ival in initial_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=True)
    for ipar, ival in fix_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=False)

    mod = peak_mod + bkg_mod
    res = mod.fit(yvals, pars, x=xvals, weights=weights, method=method)

    if print_result:
        print(peak_results_str(res))
    if plot_result:
        peak_results_plot(res)
    return FitResults(res)


def peak2dfit(xdata: np.ndarray, ydata: np.ndarray, image_data: np.ndarray, 
              initial_parameters: dict | None = None, fix_parameters: dict | None = None,
              print_result: bool = False, plot_result: bool = False):
    """
    Fit Gaussian Peak in 2D
    *** requires lmfit > 1.0.3 ***
        Not yet finished!
    :param xdata:
    :param ydata:
    :param image_data:
    :param initial_parameters:
    :param fix_parameters:
    :param print_result:
    :param plot_result:
    :return:
    """
    print('Not yet finished...')
    pass


def generate_model(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray | None = None,
                   npeaks: int | None = None, min_peak_power: float | None = None, peak_distance_idx: int = 6,
                   model: str = 'Gaussian', background: str = 'slope', 
                   initial_parameters: dict | None = None, fix_parameters: dict | None = None) -> tuple[Model, Parameters]:
    """
    Generate lmfit profile models
    See: https://lmfit.github.io/lmfit-py/builtin_models.html#example-3-fitting-multiple-peaks-and-using-prefixes
    E.G.:
      mod, pars = generate_model(x, y, npeaks=1, model='Gauss', backgroud='slope')

    Peak Search:
     The number of peaks and initial peak centers will be estimated using the find_peaks function. If npeaks is given,
     the largest npeaks will be used initially. 'min_peak_power' and 'peak_distance_idx' can be input to tailor the
     peak search results.
     If the peak search returns < npeaks, fitting parameters will initially choose npeaks equally distributed points

    Peak Models:
     Choice of peak model: 'Gaussian', 'Lorentzian', 'Voight',' PseudoVoight'
    Background Models:
     Choice of background model: 'slope', 'exponential'

    :param xvals: array(n) position data
    :param yvals: array(n) intensity data
    :param yerrors: None or array(n) - error data to pass to fitting function as weights: 1/errors^2
    :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
    :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :param model: str or lmfit.Model, specify the peak model 'Gaussian','Lorentzian','Voight'
    :param background: str, specify the background model: 'slope', 'exponential'
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :return: model, parameters
    """
    xvals = np.asarray(xvals, dtype=float).reshape(-1)
    yvals = np.asarray(yvals, dtype=float).reshape(-1)

    # Find peaks
    peak_idx, peak_pow = find_peaks(yvals, yerrors, min_peak_power, peak_distance_idx)
    peak_centers = {'p%d_center' % (n+1): xvals[peak_idx[n]] for n in range(len(peak_idx))}
    if npeaks is None:
        npeaks = len(peak_centers)

    if initial_parameters is None:
        initial_parameters = {}
    if fix_parameters is None:
        fix_parameters = {}

    peak_mod = None
    bkg_mod = None
    for model_name, names in PEAK_MODELS.items():
        if model.lower() in names:
            peak_mod = MODELS[model_name]
    for model_name, names in BACKGROUND_MODELS.items():
        if background.lower() in names:
            bkg_mod = MODELS[model_name]

    mod = bkg_mod(prefix='bkg_')
    for n in range(npeaks):
        mod += peak_mod(prefix='p%d_' % (n+1))

    pars = mod.make_params()

    # initial parameters
    min_wid = np.mean(np.diff(xvals))
    max_wid = xvals.max() - xvals.min()
    area = (yvals.max() - yvals.min()) * (3 * min_wid)
    percentile = np.linspace(0, 100, npeaks + 2)
    for n in range(1, npeaks+1):
        pars['p%d_amplitude' % n].set(value=area/npeaks, min=0)
        pars['p%d_sigma' % n].set(value=3*min_wid, min=min_wid, max=max_wid)
        pars['p%d_center' % n].set(value=np.percentile(xvals, percentile[n]), min=xvals.min(), max=xvals.max())
    # find_peak centers
    for ipar, ival in peak_centers.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=True)
    # user input parameters
    for ipar, ival in initial_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=True)
    for ipar, ival in fix_parameters.items():
        if ipar in pars:
            pars[ipar].set(value=ival, vary=False)
    return mod, pars


def generate_model_script(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray = None,
                          npeaks: int | None = None, min_peak_power: float | None = None, peak_distance_idx: int = 6,
                          model: str = 'Gaussian', background: str = 'slope', 
                          initial_parameters: dict | None = None, fix_parameters: dict | None = None,
                          only_lmfit: bool = False) -> str:
    """
    Generate script to create lmfit profile models
    E.G.:
      string = generate_mode_stringl(x, y, npeaks=1, model='Gauss', backgroud='slope')

    :param xvals: array(n) position data
    :param yvals: array(n) intensity data
    :param yerrors: None or array(n) - error data to pass to fitting function as weights: 1/errors^2
    :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
    :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :param model: str or lmfit.Model, specify the peak model 'Gaussian','Lorentzian','Voight'
    :param background: str, specify the background model: 'slope', 'exponential'
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :param only_lmfit: if True, only include lmfit imports
    :return: str
    """

    data = "xdata = np.array(%s)\n" % list(xvals)
    data += "ydata = np.array(%s)\n" % list(yvals)
    if yerrors is None or np.all(np.abs(yerrors) < 0.001):
        data += 'yerrors = None\n'
        data += 'weights = None\n\n'
    else:
        data += "yerrors = np.array(%s)\n" % list(yerrors)
        data += "yerrors[yerrors < 1] = 1.0\n"
        data += "weights = 1 / yerrors\n\n"

    if initial_parameters is None:
        initial_parameters = {}
    if fix_parameters is None:
        fix_parameters = {}
    params = "initial = %s\nfixed = %s\n" % (initial_parameters, fix_parameters)

    if not only_lmfit:
        out = "import numpy as np\nfrom mmg_toolbox import fitting\n\n"
        out += data
        out += '%s\n' % params
        out += "mod, pars = fitting.generate_model(xdata, ydata, yerrors,\n" \
               "                                   npeaks=%s, min_peak_power=%s, peak_distance_idx=%s,\n" \
               "                                   model='%s', background='%s',\n" \
               "                                   initial_parameters=initial, fix_parameters=fixed)\n" % (
                   npeaks, min_peak_power, peak_distance_idx, model, background
               )
    else:
        # Find peaks
        peak_idx, peak_pow = find_peaks(yvals, yerrors, min_peak_power, peak_distance_idx)
        peak_centers = {'p%d_center' % (n + 1): xvals[peak_idx[n]] for n in range(len(peak_idx))}
        for model_name, names in PEAK_MODELS.items():
            if model.lower() in names:
                peak_mod = MODELS[model_name]
        for model_name, names in BACKGROUND_MODELS.items():
            if background.lower() in names:
                bkg_mod = MODELS[model_name]
        peak_name = peak_mod.__name__
        bkg_name = bkg_mod.__name__

        out = "import numpy as np\nfrom lmfit import models\n\n"
        out += data
        out += "%speak_centers = %s\n\n" % (params, peak_centers)
        out += "mod = models.%s(prefix='bkg_')\n" % bkg_name
        out += "for n in range(len(peak_centers)):\n    mod += models.%s(prefix='p%%d_' %% (n+1))\n" % peak_name
        out += "pars = mod.make_params()\n\n"
        out += "# initial parameters\n"
        out += "min_wid = np.mean(np.diff(xdata))\n"
        out += "max_wid = xdata.max() - xdata.min()\n"
        out += "area = (ydata.max() - ydata.min()) * (3 * min_wid)\n"
        out += "for n in range(1, len(peak_centers)+1):\n"
        out += "    pars['p%d_amplitude' % n].set(value=area/len(peak_centers), min=0)\n"
        out += "    pars['p%d_sigma' % n].set(value=3*min_wid, min=min_wid, max=max_wid)\n"
        out += "# find_peak centers\n"
        out += "for ipar, ival in peak_centers.items():\n"
        out += "    if ipar in pars:\n"
        out += "        pars[ipar].set(value=ival, vary=True)\n"
        out += "# user input parameters\n"
        out += "for ipar, ival in initial.items():\n"
        out += "    if ipar in pars:\n"
        out += "        pars[ipar].set(value=ival, vary=True)\n"
        out += "for ipar, ival in fixed.items():\n"
        out += "    if ipar in pars:\n"
        out += "        pars[ipar].set(value=ival, vary=False)\n\n"
    out += "# Fit data\n"
    out += "res = mod.fit(ydata, pars, x=xdata, weights=weights, method='leastsqr')\n"
    out += "print(res.fit_report())\n\n"
    out += "fig, grid = res.plot()\n"
    out += "ax1, ax2 = fig.axes\n"
    out += "comps = res.eval_components()\n"
    out += "for component in comps.keys():\n"
    out += "    ax2.plot(xdata, comps[component], mode=component)\n"
    out += "    ax2.legend()\n\n"
    return out


def multipeakfit(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray | None = None,
                 npeaks: int | None = None, min_peak_power: float | None = None, 
                 peak_distance_idx: int | None = 10, model: str = 'Gaussian', background: str = 'slope', 
                 initial_parameters: dict | None = None, fix_parameters: dict | None = None, 
                 method: str ='leastsq', print_result: bool = False, plot_result: bool = False) -> FitResults:
    """
    Fit x,y data to a model with multiple peaks using lmfit
    See: https://lmfit.github.io/lmfit-py/builtin_models.html#example-3-fitting-multiple-peaks-and-using-prefixes
    
    E.G.:
      res = multipeakfit(x, y, npeaks=None, model='Gauss', plot_result=True)
      val = res.params['p1_amplitude'].value
      err = res.params['p1_amplitude'].stderr

    Peak Search:
     The number of peaks and initial peak centers will be estimated using the find_peaks function. If npeaks is given,
     the largest npeaks will be used initially. 'min_peak_power' and 'peak_distance_idx' can be input to tailor the
     peak search results.
     If the peak search returns < npeaks, fitting parameters will initially choose npeaks equally distributed points

    Peak Models:
     Choice of peak model: 'Gaussian', 'Lorentzian', 'Voight',' PseudoVoight'
    Background Models:
     Choice of background model: 'slope', 'exponential'

    Peak Parameters (%d=number of peak):
    Parameters in '.._parameters' dicts and in output results. Each peak (upto npeaks) has a set number of parameters:
     'p%d_amplitude', 'p%d_center', 'p%d_dsigma', pvoight only: 'p%d_fraction'
     output only: 'p%d_fwhm', 'p%d_height'
    Background parameters:
     'bkg_slope', 'bkg_intercept', or for exponential: 'bkg_amplitude', 'bkg_decay'

    Provide initial guess:
      res = multipeakfit(x, y, model='Voight', initial_parameters={'p1_center':1.23})

    Fix parameter:
      res = multipeakfit(x, y, model='gauss', fix_parameters={'p1_sigma': fwhm/2.3548200})

    :param xvals: array(n) position data
    :param yvals: array(n) intensity data
    :param yerrors: None or array(n) - error data to pass to fitting function as weights: 1/errors^2
    :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
    :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :param model: str or lmfit.Model, specify the peak model 'Gaussian','Lorentzian','Voight'
    :param background: str, specify the background model: 'slope', 'exponential'
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :param method: str method name, from lmfit fitting methods
    :param print_result: if True, prints the fit results using fit.fit_report()
    :param plot_result: if True, plots the results using fit.plot()
    :return: FitResults object
    """
    xvals = np.asarray(xvals, dtype=float).reshape(-1)
    yvals = np.asarray(yvals, dtype=float).reshape(-1)
    weights = gen_weights(yerrors)

    mod, pars = generate_model(xvals, yvals, yerrors,
                               npeaks=npeaks, min_peak_power=min_peak_power, peak_distance_idx=peak_distance_idx,
                               model=model, background=background,
                               initial_parameters=initial_parameters, fix_parameters=fix_parameters)

    # Fit data against model using choosen method
    res = mod.fit(yvals, pars, x=xvals, weights=weights, method=method)

    if print_result:
        print(peak_results_str(res))
    if plot_result:
        peak_results_plot(res)
    return FitResults(res)


"----------------------------------------------------------------------------------------------------------------------"
"------------------------------------------------ ScanFitManager ------------------------------------------------------"
"----------------------------------------------------------------------------------------------------------------------"


class ScanFitManager:
    """
    ScanFitManager
     Holds several functions for automatically fitting scan data

    fit = ScanFitManager(scan)
    fit.peak_ratio(yaxis)  # calculates peak power
    fit.find_peaks(xaxis, yaxis)  # automated peak finding routine
    fit.fit(xaxis, yaxis)  # estimate & fit data against a peak profile model using lmfit
    fit.multi_peak_fit(xaxis, yaxis)  # find peaks & fit multiprofile model using lmfit
    fit.model_fit(xaxis, yaxis, model, pars)  # fit supplied model against data
    fit.fit_results()  # return lmfit.ModelResult for last fit
    fit.fit_values()  # return dict of fit values for last fit
    fit.fit_report()  # return str of fit report
    fit.plot()  # plot last lmfit results
    * xaxis, yaxis are str names of arrays in the scan namespace

    :param scan: babelscan.Scan
    """

    def __init__(self, scan: NexusScan):
        self.scan = scan

    def __call__(self, *args, **kwargs) -> FitResults:
        """Calls ScanFitManager.fit(...)"""
        return self.multi_peak_fit(*args, **kwargs)

    def __str__(self):
        return self.fit_report()

    def peak_ratio(self, yaxis: str = 'signal') -> float:
        """
        Return the ratio signal / error for given dataset
        From Blessing, J. Appl. Cryst. (1997). 30, 421-426 Equ: (1) + (6)
          peak_ratio = (sum((y-bkg)/dy^2)/sum(1/dy^2)) / sqrt(i/sum(1/dy^2))
        :param yaxis: str name or address of array to plot on y axis
        :return: float ratio signal / err
        """
        values = self.scan.eval(yaxis)
        errors = np.sqrt(values + 0.1)
        return peak_ratio(values, errors)

    def find_peaks(self, xaxis: str = 'axes', yaxis: str = 'signal', min_peak_power: float | None = None, 
                   peak_distance_idx: int = 6) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Find peak shaps in linear-spaced 1d arrays with poisson like numerical values
        
        E.G.
          centres, index, power = self.find_peaks(xaxis, yaxis, min_peak_power=None, peak_distance_idx=10)
        
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
        :param peak_distance_idx: int, group adjacent maxima if closer in index than this
        :return centres: array(m) of peak centers in x, equiv. to xdata[index]
        :return index: array(m) of indexes in y of peaks that satisfy conditions
        :return power: array(m) of estimated power of each peak
        """
        xdata, ydata = self.scan.arrays(xaxis, yaxis)
        errors = np.sqrt(ydata + 0.1)
        index, power = find_peaks(ydata, errors, min_peak_power, peak_distance_idx)
        return xdata[index], index, power

    def fit(self, xaxis: str = 'axes', yaxis: str = 'signal', model: str = 'Gaussian', 
            background: str = 'slope', initial_parameters: dict | None = None, 
            fix_parameters: dict | None = None, method: str = 'leastsq', 
            print_result: bool = False, plot_result: bool = False) -> FitResults:
        """
        Fit x,y data to a peak model using lmfit

        E.G.:
          res = self.fit('axes', 'signal', model='Gauss')
          print(res)
          res.plot()
          val1 = res.p1_amplitude
          val2 = res.p2_amplitude

        Peak Models:
         Choice of peak model: 'Gaussian', 'Lorentzian', 'Voight', 'PseudoVoight'
        Background Models:
         Choice of background model: 'flat', 'slope', 'exponential'

        Peak Parameters (%d=number of peak):
         'amplitude', 'center', 'sigma', pvoight only: 'fraction'
         output only: 'fwhm', 'height'
        Background parameters:
         'bkg_slope', 'bkg_intercept', or for exponential: 'bkg_amplitude', 'bkg_decay'
         output only: 'background'
        Uncertainties (errors):
         'stderr_PARAMETER', e.g. 'stderr_amplitude'

        Provide initial guess:
          res = self.fit(x, y, model='Voight', initial_parameters={'p1_center':1.23})

        Fix parameter:
          res = self.fit(x, y, model='gauss', fix_parameters={'p1_sigma': fwhm/2.3548200})

        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param model: str, specify the peak model 'Gaussian','Lorentzian','Voight'
        :param background: str, specify the background model: 'slope', 'exponential'
        :param initial_parameters: None or dict of initial values for parameters
        :param fix_parameters: None or dict of parameters to fix at positions
        :param method: str method name, from lmfit fitting methods
        :param print_result: if True, prints the fit results using fit.fit_report()
        :param plot_result: if True, plots the results using fit.plot()
        :return: FitResult object
        """
        xdata, ydata = self.scan.arrays(xaxis, yaxis)
        errors = self.scan._error_function(ydata)
        xname, yname = self.scan.labels(xaxis, yaxis)

        # lmfit
        res = peakfit(xdata, ydata, errors, model=model, background=background,
                      initial_parameters=initial_parameters, fix_parameters=fix_parameters, method=method)

        output = res.results()
        output.update({
            'lmfit': res.res,
            'fit_result': res.res,
            'fitobj': res,
            'fit': res.res.best_fit,
            f"fit_{yname}": res.res.best_fit,
        })
        self.scan.map.add_local(**output)

        if print_result:
            print(self.scan.title())
            print(res)
        if plot_result:
            res.plot(title=self.scan.title())
        return res

    def multi_peak_fit(self, xaxis: str = 'axes', yaxis: str = 'signal',
                       npeaks: int | None = None, min_peak_power: int | None = None, peak_distance_idx: int = 6,
                       model: str = 'Gaussian', background: str = 'slope',
                       initial_parameters: dict | None = None, fix_parameters: dict | None = None, 
                       method: str = 'leastsq', print_result: bool = False, plot_result: bool = False
                       ) -> FitResults:
        """
        Fit x,y data to a peak model using lmfit

        E.G.:
          res = self.multi_peak_fit('axes', 'signal', npeaks=2, model='Gauss')
          print(res)
          res.plot()
          val1 = res.p1_amplitude
          val2 = res.p2_amplitude

        Peak centers:
         Will attempt a fit using 'npeaks' peaks, with centers defined by defalult by the find_peaks function
          if 'npeaks' is None, the number of peaks will be found by find_peaks()
          if 'npeaks' is greater than the number of peaks found by find_peaks, initial peak centers are evenly
          distrubuted along xdata.

        Peak Models:
         Choice of peak model: 'Gaussian', 'Lorentzian', 'Voight','PseudoVoight'
        Background Models:
         Choice of background model: 'flat', 'slope', 'exponential'

        Peak Parameters (%d=number of peak):
         'p%d_amplitude', 'p%d_center', 'p%d_sigma', pvoight only: 'p%d_fraction'
         output only: 'p%d_fwhm', 'p%d_height'
        Background parameters:
         'bkg_slope', 'bkg_intercept', or for exponential: 'bkg_amplitude', 'bkg_decay'
        Total parameters (always available, output only - sum/averages of all peaks):
         'amplitude', 'center', 'sigma', 'fwhm', 'height', 'background'
        Uncertainties (errors):
         'stderr_PARAMETER', e.g. 'stderr_amplitude'

        Provide initial guess:
          res = self.multi_peak_fit(x, y, model='Voight', initial_parameters={'p1_center':1.23})

        Fix parameter:
          res = self.multi_peak_fit(x, y, model='gauss', fix_parameters={'p1_sigma': fwhm/2.3548200})

        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
        :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
        :param peak_distance_idx: int, group adjacent maxima if closer in index than this
        :param model: str, specify the peak model 'Gaussian','Lorentzian','Voight'
        :param background: str, specify the background model: 'slope', 'exponential'
        :param initial_parameters: None or dict of initial values for parameters
        :param fix_parameters: None or dict of parameters to fix at positions
        :param method: str method name, from lmfit fitting methods
        :param print_result: if True, prints the fit results using fit.fit_report()
        :param plot_result: if True, plots the results using fit.plot()
        :return: FitResults object
        """
        xdata, ydata = self.scan.eval(f"{xaxis}, {yaxis}", default=np.zeros(self.scan.map.scannables_length()))
        errors = np.sqrt(ydata + 0.1)
        xname, yname = self.scan.map.generate_ids(xaxis, yaxis)

        # lmfit
        res = multipeakfit(xdata, ydata, errors, npeaks=npeaks, min_peak_power=min_peak_power,
                           peak_distance_idx=peak_distance_idx, model=model, background=background,
                           initial_parameters=initial_parameters, fix_parameters=fix_parameters, method=method)

        output = res.results()
        output.update({
            'lmfit': res.res,
            'fit_result': res.res,
            'fitobj': res,
            'fit': res.res.best_fit,
            f"fit_{yname}": res.res.best_fit,
        })
        self.scan.map.add_local(**output)

        if print_result:
            print(self.scan.title())
            print(res)
        if plot_result:
            res.plot(title=self.scan.title())
        return res

    def modelfit(self, xaxis: str = 'axis', yaxis: str = 'signal', model: Model | None = None, 
                 pars: Parameters | None = None, method: str = 'leastsq',
                 print_result: bool = False, plot_result: bool = False) -> ModelResult:
        """
        Fit data from scan against lmfit model

        Example:
            from lmfit.models import GaussianModel, LinearModel
            mod = GaussainModel(prefix='p1_') + LinearModel(prefix='bkg_')
            pars = mod.make_params()
            pars['p1_center'].set(value=np.mean(x), min=x.min(), max=x.max())
            res = scan.fit.modelfit('axis', 'signal', mod, pars)
            print(res.fit_report())
            res.plot()
            area = res.params['p1_amplitude'].value
            err = res.params['p1_amplitude'].stderr

        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param model: lmfit.Model - object defining combination of models
        :param pars: lmfit.Parameters - object defining model parameters
        :param method: str name of fitting method to use
        :param print_result: bool, if True, print results.fit_report()
        :param plot_result: bool, if True, generate results.plot()
        :return: lmfit fit results
        """
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, yerror, xname, yname = (data.get(k) for k in ['x', 'y', 'yerror', 'xlabel', 'ylabel'])

        # weights
        if yerror is None or np.all(np.abs(yerror) < 0.001):
            weights = None
        else:
            weights = 1 / np.square(yerror, dtype=float)
            weights = np.nan_to_num(weights)

        # Default model, pars
        if model is None:
            model = LinearModel()
        if pars is None:
            pars = model.guess(ydata, x=xdata)

        # lmfit
        res = model.fit(ydata, pars, x=xdata, weights=weights, method=method)

        fit_dict = {
            'lmfit': res,
            'fit_result': res,
            'fit': res.best_fit,
            f"fit_{yname}": res.best_fit,
        }
        for pname, param in res.params.items():
            ename = 'stderr_' + pname
            fit_dict[pname] = param.value
            fit_dict[ename] = param.stderr

        # Add peak components
        comps = res.eval_components(x=xdata)
        for component in comps.keys():
            fit_dict[f"{component}fit"] = comps[component]
        self.scan.map.add_local(**fit_dict)

        if print_result:
            print(self.scan.title())
            print(res.fit_report())
        if plot_result:
            fig = res.plot(xlabel=xname, ylabel=yname)
            try:
                fig, grid = fig  # Old version of LMFit
            except TypeError:
                pass
            ax1, ax2 = fig.axes
            ax1.set_title(self.scan.title(), wrap=True)
        return res

    def gen_model(self, xaxis: str = 'axes', yaxis: str = 'signal',
                  npeaks: int | None = None, min_peak_power: float | None = None, 
                  peak_distance_idx: int = 6, model: str = 'Gaussian', background: str = 'slope',
                  initial_parameters: dict | None = None, fix_parameters: dict | None = None
                  ) -> tuple[Model, Parameters]:
        """
        Generate lmfit model and parameters

        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
        :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
        :param peak_distance_idx: int, group adjacent maxima if closer in index than this
        :param model: str, specify the peak model 'Gaussian','Lorentzian','Voight'
        :param background: str, specify the background model: 'slope', 'exponential'
        :param initial_parameters: None or dict of initial values for parameters
        :param fix_parameters: None or dict of parameters to fix at positions
        :returns: model, pars
        """
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata = (data[k] for k in ['x', 'y'])
        mod, pars = generate_model(xdata, ydata,
                                   npeaks=npeaks, min_peak_power=min_peak_power, peak_distance_idx=peak_distance_idx,
                                   model=model, background=background,
                                   initial_parameters=initial_parameters, fix_parameters=fix_parameters)
        return mod, pars

    def gen_model_script(self, xaxis: str = 'axes', yaxis: str = 'signal',
                         npeaks: int | None = None, min_peak_power: float | None = None, peak_distance_idx: int = 6,
                         model: str = 'Gaussian', background: str = 'slope',
                         initial_parameters: dict | None = None, fix_parameters: dict | None = None, 
                         only_lmfit: bool = False) -> str:
        """
        Generate script string of fit process
        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
        :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
        :param peak_distance_idx: int, group adjacent maxima if closer in index than this
        :param model: str, specify the peak model 'Gaussian','Lorentzian','Voight'
        :param background: str, specify the background model: 'slope', 'exponential'
        :param initial_parameters: None or dict of initial values for parameters
        :param fix_parameters: None or dict of parameters to fix at positions
        :param only_lmfit: if True, only include imports for lmfit
        :return: str
        """
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, yerror = (data.get(k) for k in ['x', 'y', 'yerror'])
        out = generate_model_script(xdata, ydata, yerror,
                                    npeaks=npeaks, min_peak_power=min_peak_power,
                                    peak_distance_idx=peak_distance_idx,
                                    model=model, background=background,
                                    initial_parameters=initial_parameters, fix_parameters=fix_parameters,
                                    only_lmfit=only_lmfit)
        return out

    def gen_lmfit_script(self, xaxis: str = 'axes', yaxis: str = 'signal',
                         npeaks: int | None = None, min_peak_power: float | None = None, peak_distance_idx: int = 6,
                         model: str = 'Gaussian', background: str = 'slope',
                         initial_parameters: dict | None = None, fix_parameters: dict | None = None, ):
        """
        Generate script string of fit process, using only lmfit

        :param xaxis: str name or address of array to plot on x axis
        :param yaxis: str name or address of array to plot on y axis
        :param npeaks: None or int number of peaks to fit. None will guess the number of peaks
        :param min_peak_power: float, only return peaks with power greater than this. If None compare against std(y)
        :param peak_distance_idx: int, group adjacent maxima if closer in index than this
        :param model: str, specify the peak model 'Gaussian','Lorentzian','Voight'
        :param background: str, specify the background model: 'slope', 'exponential'
        :param initial_parameters: None or dict of initial values for parameters
        :param fix_parameters: None or dict of parameters to fix at positions
        :return: str
        """
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, yerror = (data.get(k) for k in ['x', 'y', 'yerror'])
        out = generate_model_script(xdata, ydata, yerror,
                                    npeaks=npeaks, min_peak_power=min_peak_power,
                                    peak_distance_idx=peak_distance_idx,
                                    model=model, background=background,
                                    initial_parameters=initial_parameters, fix_parameters=fix_parameters,
                                    only_lmfit=True)
        return out

    def fit_parameter(self, parameter_name: str = 'amplitude') -> tuple[float, float]:
        """
        Returns parameter, error from the last run fit
        :param parameter_name: str, name from last fit e.g. 'amplitude', 'center', 'fwhm', 'background'
        :returns:  value, error
        """
        fitobj = self.fit_result()
        return fitobj.get_value(parameter_name)

    def fit_result(self) -> FitResults:
        """
        Returns FitResults object from last fit
        :return: PeakResults obect
        """
        return self.scan('fitobj')

    def fit_report(self) -> str:
        """Return str results of last fit"""
        fitobj = self.fit_result()
        return str(fitobj)

    def plot(self):
        """Plot fit results"""
        fitobj = self.fit_result()
        return fitobj.plot(title=self.scan.title())

