# Regions of Interest (ROIs)
It is possible to define custom ROIs programatically using the Scan and Experiment objects. 
ROIs are added to the namespace of a `NexusScan` object and only generate the arrays
when being evaluated, making them very efficient. 

An ROI is defined by its name in the Scan namespace and by default there are a number of
versions of the ROI that can be generated once defined:

| Expression       | Description                                                            |
|------------------|------------------------------------------------------------------------|
| `*name*`         | returns the whole ROI array as a HDF5 dataset                          |
| `*name*_total`   | returns the sum of each image in the ROI array                         |
| `*name*_max`     | returns the max of each image in the ROI array                         |
| `*name*_min`     | returns the min of each image in the ROI array                         |
| `*name*_mean`    | returns the mean of each image in the ROI array                        |
| `*name*_bkg`     | returns the background ROI array (area around ROI)                     |
| `*name*_rmbkg`   | returns the total with background subtracted                           |
| `*name*_box`     | returns the pixel positions of the ROI corners                         |
| `*name*_bkg_box` | returns the pixel positions of the background ROI                      |
| `*name*_rgn_box` | *peak only* returns pixel positions of Peak search region              |
| `*name*_pos`     | *peak only* returns n,i,j position of the largest pixel in the dataset |


## Single Scan ROI definition
The `NexusScan` object has an `add_roi` function and this can be used
to define a set of ROI expression that we add to the namespace of HdfMap. The ROI expression
will only be evaluated when requested, so data is not read when defining the ROI.

```python
import matplotlib.pyplot as plt
from mmg_toolbox import data_file_reader

scan = data_file_reader('scan_file.nxs')

# Define ROI
# scans with the pilatus have shape (n, i, j), where n in the number of points,
# i is the fast (short) axis and j is the slow (long axis)
# see help(scan.add_roi)
scan.add_roi(
    name='nroi1',
    cen_i='pil3_centre_j',  # pil3_centre_j is a value inside the NeXus file defining the detector centre
    cen_j='pil3_centre_i',  # can also be given as integers
    wid_i=80,
    wid_j=20,
    image_name='pil3_100k'  # detector name, use 'IMAGE' if you're not sure.
)

# 'nroi1' defines a set of parameters in the scan object, accessible the the eval interface
roi_total, roi_max, roi_min, roi_mean = scan('nroi1_total, nroi1_max, nroi1_min, nroi1_mean')
roi_bkg, roi_rmbkg = scan('nroi1_bkg, nroi1_rmbkg')  # background definition and removal from nroi1
roi_box, roi_bkg_box = scan('nroi1_box, nroi1_bkg_box')  # coordinates of the box
roi_volume = scan('nroi1')  # returns (n,80,20) array

# Plot the ROI on an image
fig1, ax = plt.subplots(figsize=(12, 4), dpi=100)
ax = scan.plot.image(index=None, log=True, colorbar=True, axes=ax)
ax.plot(roi_box[:, 1], roi_box[:, 0], 'w-', lw=2, label='nroi1')
ax.plot(roi_bkg_box[:, 1], roi_bkg_box[:, 0], 'r-', lw=1, label='nroi1_bkg')
ax.legend()

# Plot the scan
ax = scan.plot.plot('axes', ['nroi1_total', 'nroi1_bkg', 'nroi1_rmbkg'])
plt.show()
```

## Peak Finding ROI
Rather than defining the centre of the ROI, you can define an ROI centred on the maximum 
pixel in a given region of the detector.

```python
import matplotlib.pyplot as plt
from mmg_toolbox import data_file_reader

scan = data_file_reader('scan_file.nxs')

# Define ROI
# scans with the pilatus have shape (n, i, j), where n in the number of points,
# i is the fast (short) axis and j is the slow (long axis)
# see help(scan.add_peak_roi)
scan.add_peak_roi(
    name='peak_roi1',
    wid_i=80,
    wid_j=20,
    image_name='IMAGE',  # detector name, use 'IMAGE' if you're not sure.
    rgn_cen_i=101,  # coordinates of the region in which to 
    rgn_cen_j=210,  # find the maximum pixel
    rgn_wid_i=101,
    rgn_wid_j=101
)

# 'peak_roi1' defines a set of parameters in the scan object, accessible the the eval interface
roi_total, roi_bkg, roi_rmbkg = scan('peak_roi1_total, peak_roi1_bkg, peak_roi1_rmbkg')
peak_n, peak_i, peak_j = scan('peak_roi1_pos')  # index of max pixel
region_box = scan('peak_roi1_rgn_box')  # lines around peak search region
```

## Multi-File ROI definition
The `Experiment` object contains an `add_roi` function. This adds ROI parameters to the configuration so
they are added to every scan that is loaded.
```python
import matplotlib.pyplot as plt
from mmg_toolbox import Experiment

exp = Experiment('/dls/science/groups/das/ExampleData/i16/2dscans_2026/1144250.nxs')

# add ROI to all scans
exp.add_roi('nroi1', 'pil3_centre_j', 'pil3_centre_i+20', 100, 30)
exp.add_roi('nroi2', 'pil3_centre_j', 'pil3_centre_i-20', 100, 30)
exp.add_roi('peak_roi1', 'pil3_centre_j', 'pil3_centre_i', 30, 30, peak_search=True, peak_region_i=61, peak_region_j=101)

scan, = exp.scans(1144250)
roi1_total, roi2_total = scan('nroi1_total, nroi2_total')

# Plot ROI values for range of scans
fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=100)
exp.plot.multi_lines(*range(1144250, 1144260), yaxis='nroi1_total / Transmission', value='sx', axes=ax1)
exp.plot.multi_lines(*range(1144250, 1144260), yaxis='nroi2_total / Transmission', value='sx', axes=ax2)
fig2.tight_layout()
plt.show()
```