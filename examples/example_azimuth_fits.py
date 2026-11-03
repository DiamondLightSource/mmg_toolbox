"""
mmg_toolbox example
Example script to perform multi-peak fitting on a sequence of scans
"""

import matplotlib.pyplot as plt
from lmfit.models import SineModel
from mmg_toolbox import Experiment
from mmg_toolbox.fitting import modelfit

data_dir = '/dls/science/groups/das/ExampleData/i16/azimuths'
scan_numbers = range(1108607, 1108678)

exp = Experiment(data_dir, instrument='i16')
exp.plot.set_plot_defaults()

scans = exp.scans(*scan_numbers)
# Fitting
for scan in scans:
    result = scan.fit.multi_peak_fit(
        xaxis='axes',
        yaxis='signal / Transmission',
        npeaks=1,
        min_peak_power=None,
        peak_distance_idx=6,
        model='Gaussian',
        background='Slope'
    )

# Extract the data from the scan objects
metadata, amplitude, amplitude_err = exp.join_scan_arrays(*scans, data_fields=['psi', 'amplitude', 'stderr_amplitude'])

# Fit resulting curve
sin_fit = modelfit(metadata, amplitude, amplitude_err, model=SineModel())
print(sin_fit.fit_report())

# Get labels of automatic axes
signal = scans[0].replace_default_names('signal / Transmission')

# Create plot
fig, ax = plt.subplots()
ax.errorbar(metadata, amplitude, amplitude_err, fmt='.-', label=signal)
ax.plot(metadata, sin_fit.best_fit, 'r-', label='Fit')
ax.set_xlabel('psi [Deg]')
ax.set_ylabel('amplitude')
ax.legend()
ax.set_title(exp.generate_scans_title(*scan_numbers))

plt.show()
