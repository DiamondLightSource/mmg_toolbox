"""
{{title}}
{{description}}

Multi-peak fitting vs {{value}}
{{date}}
"""

import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

data_dir = '{{experiment_dir}}'
scan_numbers = {{scan_numbers}}

exp = Experiment(data_dir, instrument='{{beamline}}')
exp.plot.set_plot_defaults()

scans = exp.scans(*scan_numbers)
# Fitting
amplitude = []
amplitude_err = []
metadata = []
for scan in scans:
    scan.fit.multi_peak_fit(
        xaxis='{{x-axis}}',
        yaxis='{{y-axis}}',
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
    value, = scan.get_data('{{value}}', default=0)
    metadata.append(value)

fig, ax = plt.subplots()
ax.errorbar(metadata, amplitude, amplitude_err, fmt='.-', label='{{y-axis}}')
ax.set_xlabel('{{x-axis}}')
ax.set_ylabel('{{y-axis}}')
ax.set_title(exp.generate_scans_title(*scan_numbers))


plt.show()
