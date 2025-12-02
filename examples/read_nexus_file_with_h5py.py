import numpy as np
import h5py
import matplotlib.pyplot as plt

file = '/dls/i16/data/2025/cm40634-12/1106663.nxs'

with h5py.File(file, 'r') as hdf:
    scan_command = hdf['/entry/scan_command'].asstr()[...]  # str
    crystal = hdf['/entry/sample/name'].asstr()[...]  # str
    temp = hdf['/entry/sample/temperature'][...]  # float
    temp_units = hdf['/entry/sample/temperature'].attrs.get('units', '')
    unit_cell = np.reshape(hdf['/entry/sample/unit_cell'], -1)  # 1D array, length 6
    energy = hdf['/entry/sample/beam/incident_energy'][...]  # # float
    ubmatrix = hdf['/entry/sample/ub_matrix'][0]  # 3D array, shape (3,3)
    pixel_size = hdf['/entry/instrument/pil3_100k/module/fast_pixel_direction'][...]  # float, mm
    detector_distance = hdf['/entry/instrument/pil3_100k/transformations/origin_offset'][...]  # float, mm

    # Get the default scan axes
    measurement = hdf['/entry/measurement']
    axes = measurement.attrs['axes'][0]
    signal = measurement.attrs['signal']
    axes_data = measurement[axes][...]  # ndarray
    signal_data = measurement[signal][...]  # ndarray

# Plot the data
fig, ax = plt.subplots()
ax.plot(axes_data, signal_data)
ax.set_xlabel(axes)
ax.set_ylabel(signal)
ax.set_title(f"{file}: {crystal}, T = {temp:.2f} {temp_units}")
plt.show()