"""
lmfit fit wrappers
"""

import numpy as np
from lmfit.model import ModelResult, Model, Parameters

from .functions import gen_weights, find_peaks
from .models import get_default_model, get_peak_model, get_background_model
from .results import FitResults, peak_results_str, peak_results_plot

__all__ = ['modelfit', 'peakfit', 'peak2dfit', 'generate_model', 'generate_model_script', 'multipeakfit']


def modelfit(xvals: np.ndarray, yvals: np.ndarray, yerrors: np.ndarray | None = None,
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
        model = get_default_model()

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

    peak_mod = get_peak_model(model)()
    bkg_mod = get_background_model(background)(prefix='bkg_')

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
                   initial_parameters: dict | None = None, fix_parameters: dict | None = None) -> tuple[
    Model, Parameters]:
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
    peak_centers = {'p%d_center' % (n + 1): xvals[peak_idx[n]] for n in range(len(peak_idx))}
    if npeaks is None:
        npeaks = len(peak_centers)

    if initial_parameters is None:
        initial_parameters = {}
    if fix_parameters is None:
        fix_parameters = {}

    peak_mod = get_peak_model(model)
    bkg_mod = get_background_model(background)

    mod = bkg_mod(prefix='bkg_')
    for n in range(npeaks):
        mod += peak_mod(prefix='p%d_' % (n + 1))

    pars = mod.make_params()

    # initial parameters
    min_wid = float(np.mean(np.diff(xvals)))
    max_wid = xvals.max() - xvals.min()
    area = (yvals.max() - yvals.min()) * (3 * min_wid)
    percentile = np.linspace(0, 100, npeaks + 2)
    for n in range(1, npeaks + 1):
        pars['p%d_amplitude' % n].set(value=area / npeaks, min=0)
        pars['p%d_sigma' % n].set(value=3 * min_wid, min=min_wid, max=max_wid)
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
        peak_mod = get_peak_model(model)
        bkg_mod = get_background_model(background)
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
                 method: str = 'leastsq', remove_peaks: bool = True,
                 print_result: bool = False, plot_result: bool = False) -> FitResults:
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
    :param min_peak_power: float, only return peaks with power greater than this. If None compares against std(y)
    :param peak_distance_idx: int, group adjacent maxima if closer in index than this
    :param model: str or lmfit.Model, specify the peak model 'Gaussian','Lorentzian','Voight'
    :param background: str, specify the background model: 'slope', 'exponential'
    :param initial_parameters: None or dict of initial values for parameters
    :param fix_parameters: None or dict of parameters to fix at positions
    :param method: str method name, from lmfit fitting methods
    :param remove_peaks: bool, remove peaks consistent with zero and fit again
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
    print(f"Fitting with {len(mod.components) - 1} peaks")
    res = mod.fit(yvals, pars, x=xvals, weights=weights, method=method)
    # Remove peaks consistent with zero
    if remove_peaks and len(mod.components) > 2:
        peak_models = [(m, m.prefix) for m in mod.components if 'bkg' not in m.prefix]
        new_mod = next(m for m in mod.components if 'bkg' in m.prefix)
        for peak_model, prefix in peak_models:
            param = res.params[f"{prefix}amplitude"]
            amplitude = param.value
            stderr = param.stderr or 0
            if amplitude > 2 * stderr:
                new_mod += peak_model

        if len(new_mod.components) < len(mod.components):
            new_pars = new_mod.make_params()
            for par in new_pars:
                res_par = res.params[par]
                new_pars[par].set(value=res_par.value, vary=res_par.vary,
                                  min=res_par.min, max=res_par.max, expr=res_par.expr)
            print(f"Refitting with {len(new_mod.components) - 1} peaks")
            res = new_mod.fit(yvals, new_pars, x=xvals, weights=weights, method=method)

    if print_result:
        print(peak_results_str(res))
    if plot_result:
        peak_results_plot(res)
    return FitResults(res)

