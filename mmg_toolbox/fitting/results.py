"""
lmfit results interpreter
"""

import numpy as np

from lmfit.model import ModelResult, Model
from matplotlib import pyplot as plt

from mmg_toolbox.utils.misc_functions import stfm
from .models import PEAK_PARS

__all__ = ['peak_results', 'peak_results_str', 'peak_results_fit', 'peak_results_plot', 'Peak', 'FitResults']

class R:
    lmfit = 'lmfit'
    npeaks = 'npeaks'
    peak_prefixes = 'peak_prefixes'
    peak_models = 'peak_models'
    chisqr = 'chisqr'
    xdata = 'xdata'
    ydata = 'ydata'
    weights = 'weights'
    yerror = 'yerror'
    yfit = 'yfit'
    amplitude = 'amplitude'
    center = 'center'
    fwhm = 'fwhm'
    height = 'height'
    sigma = 'sigma'
    background = 'background'
    stderr_amplitude = 'stderr_amplitude'
    stderr_center = 'stderr_center'
    stderr_fwhm = 'stderr_fwhm'
    stderr_height = 'stderr_height'
    stderr_sigma = 'stderr_sigma'
    stderr_background = 'stderr_background'


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
    peak_prefx = [mod.prefix for mod in res.model.components if 'bkg' not in mod.prefix]
    peak_models = [mod for mod in res.model.components if 'bkg' not in mod.prefix]
    npeaks = len(peak_prefx)
    nn = 1 / len(peak_prefx) if len(peak_prefx) > 0 else 1  # normalise by number of peaks
    comps = res.eval_components()
    fit_dict = {
        R.lmfit: res,
        R.npeaks: npeaks,
        R.peak_prefixes: peak_prefx,
        R.peak_models: peak_models,
        R.chisqr: res.chisqr,
        R.xdata: res.userkws['x'],
        R.ydata: res.data,
        R.weights: res.weights,
        R.yerror: 1 / res.weights if res.weights is not None else 0 * res.data,
        R.yfit: res.best_fit,
    }
    for comp_prefx, comp in comps.items():
        fit_dict['%sfit' % comp_prefx] = comp
    for pname, param in res.params.items():
        ename = 'stderr_' + pname
        fit_dict[pname] = param.value
        fit_dict[ename] = param.stderr or 0
    totals = {
        R.amplitude: np.sum([res.params['%samplitude' % pfx].value for pfx in peak_prefx]),
        R.center: np.mean([res.params['%scenter' % pfx].value for pfx in peak_prefx]),
        R.sigma: np.mean([res.params['%ssigma' % pfx].value for pfx in peak_prefx]),
        R.height: np.mean([res.params['%sheight' % pfx].value for pfx in peak_prefx]),
        R.fwhm: np.mean([res.params['%sfwhm' % pfx].value for pfx in peak_prefx]),
        R.background: np.mean(comps['bkg_']) if 'bkg_' in comps else 0.0,
        R.stderr_amplitude: np.sqrt(np.sum([fit_dict['stderr_%samplitude' % pfx] ** 2 for pfx in peak_prefx])),
        R.stderr_center: np.sqrt(np.sum([fit_dict['stderr_%scenter' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        R.stderr_sigma: np.sqrt(np.sum([fit_dict['stderr_%ssigma' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        R.stderr_height: np.sqrt(np.sum([fit_dict['stderr_%sheight' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        R.stderr_fwhm: np.sqrt(np.sum([fit_dict['stderr_%sfwhm' % pfx] ** 2 for pfx in peak_prefx])) * nn,
        R.stderr_background: np.std(comps['bkg_']) if 'bkg_' in comps else 0.0,
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
    peak_prefx = [mod.prefix for mod in res.model.components if 'bkg' not in mod.prefix]
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
    out += '      amplitude = %s\n' % stfm(fit_dict[R.amplitude], fit_dict[R.stderr_amplitude])
    out += '         center = %s\n' % stfm(fit_dict[R.center], fit_dict[R.stderr_center])
    out += '         height = %s\n' % stfm(fit_dict[R.height], fit_dict[R.stderr_height])
    out += '          sigma = %s\n' % stfm(fit_dict[R.sigma], fit_dict[R.stderr_sigma])
    out += '           fwhm = %s\n' % stfm(fit_dict[R.fwhm], fit_dict[R.stderr_fwhm])
    out += '     background = %s\n' % stfm(fit_dict[R.background], fit_dict[R.stderr_background])
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


class Peak:
    """
    Peak object
    """

    def __init__(self, result: ModelResult, model: Model, amplitude: float, center: float, height: float, fwhm: float,
                 stderr_amplitude: float, stderr_center: float, stderr_height: float, stderr_fwhm: float, **kwargs):
        self._result = result
        self.model = model
        self.prefix = model.prefix
        self.model_name = model._name
        self.params = PEAK_PARS
        self.amplitude = amplitude
        self.center = center
        self.height = height
        self.fwhm = fwhm
        self.stderr_amplitude = stderr_amplitude
        self.stderr_center = stderr_center
        self.stderr_height = stderr_height
        self.stderr_fwhm = stderr_fwhm
        for name, value in kwargs.items():
            setattr(self, name, value)
            if name.startswith('stderr_') and hasattr(self, name[7:]):
                self.params.append(name[7:])

    def __repr__(self):
        pars = ', '.join(f"{p}={self.get_string(p)}" for p in self.params)
        return f"Peak('{self.prefix}', '{self.model_name}', {pars})"

    def get_value(self, name: str) -> tuple[float | None, float]:
        """Returns fit parameter value and associated error"""
        err_name = f"stderr_{name}"
        if not hasattr(self, err_name):
            return None, 0
        value = getattr(self, name)
        error = getattr(self, err_name)
        return value, error

    def get_string(self, name: str) -> str:
        """Returns fit parameter string including error in standard form"""
        value, error = self.get_value(name)
        if value is None:
            return '--'
        return stfm(value, error)

    def fit_data(self, x_data: np.ndarray | None = None, ntimes=10) -> tuple[np.ndarray, np.ndarray]:
        """Returns interpolated x, y fit arrays"""
        old_x = self._result.userkws['x'] if x_data is None else x_data
        xfit = np.linspace(np.min(old_x), np.max(old_x), np.size(old_x) * ntimes)
        yfit = self.model.eval(x=xfit)
        return xfit, yfit

    def label(self) -> str:
        return f"{self.model_name} ({self.prefix})"

    def plot(self, axes: plt.Axes, x_data: np.ndarray | None = None, ntimes=10):
        """Plot peak fit results"""
        xfit, yfit = self.fit_data(x_data, ntimes)
        axes.plot(xfit, yfit, label=self.label())


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
    npeaks: int
    peak_prefixes: list[str]
    peak_models: list[Model]
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
    chisqr: float  # Chi^2 of fit,
    xdata: np.ndarray  # x-data used for fit,
    ydata: np.ndarray  # y-data used for fit,
    yfit: np.ndarray  # y-fit values,
    weights: np.ndarray  # res.weights,
    yerror: np.ndarray  # 1 / res.weights if res.weights is not None else 0 * res.data,

    def __init__(self, results: ModelResult):
        self.res = results
        self._res = peak_results(results)
        self.params = PEAK_PARS
        for name, value in self._res.items():
            setattr(self, name, value)

    def __repr__(self):
        pars = ', '.join(f"{p}={self.get_string(p)}" for p in self.params)
        return f"FitResults(npeaks={self.npeaks}, {pars})"

    def __str__(self):
        return peak_results_str(self.res)

    def __getitem__(self, item: int | slice) -> Peak | list[Peak]:
        if isinstance(item, slice):
            return [self.get_peak(n) for n in range(*item.indices(len(self)))]
        else:
            return self.get_peak(item)

    def __len__(self):
        return self.npeaks

    def peak_name(self, number) -> tuple[str, str]:
        prefix = self.peak_prefixes[number]
        return prefix, "stderr_" + prefix

    def get_peak(self, number: int) -> Peak:
        if number >= self.npeaks:
            raise IndexError('Not enough peaks')
        prefix, stderr = self.peak_name(number)
        pars = {p: self._res.get(prefix + p, 0) for p in self.params}
        stderr = {f"stderr_{p}": self._res.get(stderr + p, 0) for p in self.params}
        return Peak(
            result=self.res,
            model=self.peak_models[number],
            **pars,
            **stderr
        )

    def get_value(self, name: str) -> tuple[float | None, float]:
        """Returns fit parameter value and associated error"""
        err_name = f"stderr_{name}"
        value = self._res.get(name, None)
        error = self._res.get(err_name, 0)
        return value, error

    def get_string(self, name: str) -> str:
        """Returns fit parameter string including error in standard form"""
        value, error = self.get_value(name)
        return stfm(value, error)

    def results(self) -> dict:
        """Returns dict of peak fit results"""
        return self._res

    def fit_data(self, x_data: np.ndarray | None = None, ntimes=10) -> tuple[np.ndarray, np.ndarray]:
        """Returns interpolated x, y fit arrays"""
        return peak_results_fit(self.res, ntimes=ntimes, x_data=x_data)

    def plot(self, axes=None, xlabel=None, ylabel=None, title=None):
        """Plot peak fit results"""
        return peak_results_plot(self.res, axes, xlabel, ylabel, title)

