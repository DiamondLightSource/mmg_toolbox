# Peak Fitting
[lmfit](https://lmfit.github.io/lmfit-py/index.html) is used to perform fits, 
however specific wrappers are provided for peak fitting.

```python
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

data_dir = '/experiment/data/dir'
scan_numbers = [12345, 12346, 12348]

exp = Experiment(data_dir, instrument='i16')
exp.plot.set_plot_defaults()

scans = exp.scans(*scan_numbers)
# Fitting
amplitude = []
amplitude_err = []
metadata = []
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
    amplitude.append(amp)
    amplitude_err.append(err)
    value, = scan.get_data('Ta', default=0)
    metadata.append(value)

fig, ax = plt.subplots()
ax.errorbar(metadata, amplitude, amplitude_err, fmt='.-', label='Ta')
ax.set_xlabel('Ta')
ax.set_ylabel('amplitude')
ax.set_title(exp.generate_scans_title(*scan_numbers))


plt.show()
```