"""
scan fit manager for Scan objects
"""

import numpy as np
from lmfit.model import ModelResult, Model, Parameters
from lmfit.models import LinearModel

from mmg_toolbox.nexus.nexus_scan import NexusScan
from .functions import peak_ratio, find_peaks
from .results import FitResults
from .fit_functions import peakfit, multipeakfit, generate_model, generate_model_script

__all__ = ['ScanFitManager']


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
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, errors = (data[k] for k in ('xdata', 'ydata', 'yerror'))

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
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, errors, xname, yname = (data[k] for k in ('xdata', 'ydata', 'yerror', 'xlabel', 'ylabel'))

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
        data = self.scan.get_plot_data(xaxis, yaxis)
        xdata, ydata, errors, xname, yname = (data[k] for k in ('xdata', 'ydata', 'yerror', 'xlabel', 'ylabel'))

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

