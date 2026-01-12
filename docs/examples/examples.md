# Examples

### Read a NeXus file
```python
from mmg_toolbox import data_file_reader

scan = data_file_reader('12345.nxs', beamline='i16')  # beamline can be left blank

print(scan)  # displays default metadata for the beamline

scan.plot()  # creates a matplotlib line plot of the scanned data with default axes

scan.plot.image(index=None)  # creates a matplotlib image plot of the centre image of the scan

# scan data
axes, signal = scan('axes, signal / exposure_time')  # expressions use variables inside nexus file

# metadata
temperature = scan('Tsample')
# or
temperature = scan.metadata.Tsample
# metadata as formatted string
print(scan.format('T = {Tsample:.2f} K'))

# image data
image = scan.image(index=0)
stack = scan.volume()  # all images in stack as a volume array
```

### Read scans from a folder
```python
from mmg_toolbox import Experiment

exp = Experiment('/dls/i06/2025/mm1234-1', instrument='i06')  # multiple folders can be added

print(exp)  # displays information about scans in folder

scan = exp.scan(12345)  # use scan number to load scan data

last_scan = exp.scan(-1)  # loads the most recently measured scan

scans = exp.scans(range(12345, 12355, 2))  # returns a list of scan objects

# Automatic multi-scan title
title = exp.generate_scans_title(range(12345, 12355), 'T={Tsample}')

# list all scans
for scan in exp:
    print(scan.format('#{scan_number} {scan_command}'))

# list recent scans
for scan in exp[-5:]:
    print(scan.format('#{scan_number} E={energy:.2f} keV  {scan_command}'))
```

### Plotting
```python
from mmg_toolbox import data_file_reader
from mmg_toolbox.plotting.matplotlib import set_plot_defaults
set_plot_defaults()  # changes the matplotlib defaults to larger fonts, thicker lines etc.

scan = data_file_reader('12345.nxs')

# line plot
scan.plot.plot(xaxis='axes', yaxis='signal')
# multi-line plot
scan.plot.plot(xaxis='axes', yaxis=['signal', 'signal2'])

```