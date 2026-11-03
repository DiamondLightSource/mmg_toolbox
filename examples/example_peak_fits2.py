"""
mmg_toolbox example
Example script to perform multi-peak fitting on a sequence of scans
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

data_dir = '/dls/science/groups/das/ExampleData/i16/azimuths'
scan_numbers = range(1108607, 1108678)

exp = Experiment(data_dir, instrument='i16')
exp.plot.set_plot_defaults()

scans = exp.scans(*scan_numbers)
# Fitting
amplitude = []
amplitude_err = []
metadata = []
for scan in scans:
    scan.fit.multi_peak_fit(
        xaxis='axes',
        yaxis='signal / Transmission',
        npeaks=1,
        min_peak_power=None,
        peak_distance_idx=6,
        model='Gaussian',
        background='Slope'
    )
    print(scan.fit.fit_report())
    amp, err = scan.fit.fit_parameter('amplitude')
    amplitude.append(amp)
    amplitude_err.append(err)
    value = scan.get_data('psi', default=0)
    metadata.append(value)

# Get labels of automatic axes
hdf_map = scans[0].map
axes, signal = hdf_map.generate_ids('axes', 'signal')

fig, ax = plt.subplots()
ax.errorbar(metadata, amplitude, amplitude_err, fmt='.-', label=signal)
ax.set_xlabel(axes)
ax.set_ylabel('amplitude')
ax.set_title(exp.generate_scans_title(*scan_numbers))

plt.show()
