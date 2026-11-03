# Peak Fitting
[lmfit](https://lmfit.github.io/lmfit-py/index.html) is used to perform fits, 
however specific wrappers are provided for peak fitting.

## multipeakfit
A wrapper is provided for multipeak fitting, providing a simple and powerful tool for most uses.
```python
import numpy as np
import matplotlib.pyplot as plt
from mmg_toolbox.fitting import multipeakfit, gauss

# Create an interesting spectrum
x = np.arange(200, 300, 0.1)
background = 6.0
peaks = [
    dict(height=60, cen=250, fwhm=23),
    dict(height=12, cen=230, fwhm=5),
    dict(height=30, cen=280, fwhm=30),
]
y = np.ones_like(x) * background
for peak in peaks:
    y += gauss(x, **peak)

# Fit peak
result = multipeakfit(x, y, min_peak_power=0, peak_distance_idx=3)

# View Results
print(result)
result.plot()

# Evaluate results
print(f"\n\nNumber of peaks fit: {len(result)}")
print(f"Total amplitude: {result.amplitude: .2f} +/- {result.stderr_amplitude: .2f}")
for peak in result:
    print(f"Peak {peak.model_name} has amplitude: {peak.amplitude:.1f}, and width: {peak.fwhm:.3}")

plt.show()
```

The result object contains all the fitted data and information about the fit.

## Scan wrappers
A specific wrapper is provided within the scan object for fitting data directly from a file. Fit results are
stored within the scan object namespace.

```python
from mmg_toolbox import data_file_reader

scan = data_file_reader('12345.nxs')

result = scan.fit.multi_peak_fit()

# Results are stored inside the scan namespace
amplitude, height, fwhm, centre, bkg = scan('amplitude, height, fwhm, center, background')
# Errors are also stored with prefix 'stderr_'
std_amp, std_fwhm = scan('stderr_amplitude, stderr_fwhm')
# Fitted data is also stored
x_data, y_data, y_error, y_fit = scan('xdata, ydata, yerror, yfit')
# Individual peak peak and background data can be aquired from the prefixes
peak_prefixes = scan('peak_prefixes')  # e.g. ['p1_', 'p2_']
peak_amplitudes = scan(','.join(f"{prefix}amplitude" for prefix in peak_prefixes))
peak_fit_arrays = scan(','.join(f"{prefix}fit" for prefix in peak_prefixes))
# you could now plot this with plt.plot(x_data, peak_fit_arrays)
```

Here is an example fitting peaks to many scans, extracting the fit results from the scan objects:

```python
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

data_dir = '/experiment/data/dir'
scan_numbers = [12345, 12346, 12348]

exp = Experiment(data_dir, instrument='i16')
exp.plot.set_plot_defaults()

scans = exp.scans(*scan_numbers)
# Fitting
for scan in scans:
    result = scan.fit.multi_peak_fit(
        xaxis='axes',  # default scan axes
        yaxis='signal',  # default scan values
        npeaks=1,
        min_peak_power=None,
        peak_distance_idx=6,
        model='Gaussian',
        background='Slope'
    )
    print(result)
    amp, err = scan.fit.fit_parameter('amplitude')

# Extract the data from the scan objects
metadata, amplitude, amplitude_err = exp.join_scan_arrays(*scans, data_fields=['Ta', 'amplitude', 'stderr_amplitude'])

fig, ax = plt.subplots()
ax.errorbar(metadata, amplitude, amplitude_err, fmt='.-', label='Ta')
ax.set_xlabel('Ta')
ax.set_ylabel('amplitude')
ax.set_title(exp.generate_scans_title(*scan_numbers))

plt.show()
```