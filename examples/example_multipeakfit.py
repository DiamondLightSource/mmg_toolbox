"""
mmg_toolbox example
Example script to perform multi-peak fitting on an arbitary spectra
"""

import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox.fitting import multipeakfit, gauss

# Create an interesting spectrum
x = np.arange(200, 300, 0.1)
background = 6.0
peaks = [
    dict(height=60, cen=250, fwhm=23),
    dict(height=10, cen=220, fwhm=11),
    dict(height=12, cen=230, fwhm=5),
    dict(height=30, cen=280, fwhm=30),
]
y = np.ones_like(x) * background
for peak in peaks:
    y += gauss(x, **peak)


# Fit peak
result = multipeakfit(x, y, min_peak_power=0, peak_distance_idx=3)

# result = multipeakfit(
#     xvals= x,  # array(n) position data
#     yvals= y,  # array(n) intensity data
#     yerrors= np.sqrt(y),  # None or array(n) - error data to pass to fitting function as weights: 1/errors^2
#     npeaks= 3,  # None or int number of peaks to fit. None will guess the number of peaks
#     min_peak_power= 5,  # float, only return peaks with power greater than this. If None compares against std(y)
#     peak_distance_idx= 10,  # int, group adjacent maxima if closer in index than this
#     model= 'Gaussian',  # str or lmfit.Model, specify the peak model 'Gaussian','Lorentzian','Voight'
#     background= 'slope',  # str, specify the background model: 'slope', 'exponential'
#     initial_parameters= {},  # None or dict of initial values for parameters
#     fix_parameters= {},  # None or dict of parameters to fix at positions
#     method= '',  # str method name, from lmfit fitting methods
#     remove_peaks= True,  # bool, remove peaks consistent with zero and fit again
#     print_result=False,  # if True, prints the fit results using fit.fit_report()
#     plot_result=False,  # if True, plots the results using fit.plot()
# )

# View Results
print(result)
result.plot()

# Evaluate results
print(f"\n\nNumber of peaks fit: {len(result)}")
for peak in result:
    print(f"Peak {peak.model_name} has amplitude: {peak.amplitude:.1f}, and width: {peak.fwhm:.3}")

plt.show()