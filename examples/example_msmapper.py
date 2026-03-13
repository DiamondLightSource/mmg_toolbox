"""
mmg_toolbox example
Example script to run msmapper to remap detector images into reciprocal space
"""

import os
import json
import subprocess
import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox import data_file_reader

MSMAPPER = '/dls_sw/apps/msmapper/1.9/msm/msmapper'

filename = "/dls/science/groups/das/ExampleData/hdfmap_tests/i16/1109527.nxs"
output = "/dls/science/groups/das/ExampleData/hdfmap_tests/i16/processed/1109527_msmapper.nxs"

# load scan
scan = data_file_reader(filename)
print(scan)

# [optional] Determine detector pixel positions
central_pixel = [
    scan.map.scannables_length() // 2,
    int(scan('pil3_centre_j')),
    int(scan('pil3_centre_i')),
]
print(f"Central pixel: {central_pixel}")
pixel_file = output.replace('_msmapper.nxs', '_pixels.nxs')
bean = {
    "inputs": [filename],
    "output": pixel_file,
    "outputMode": "Coords_HKL",
    "pixelIndexes": [[0, 0, 0], [1, 1, 1], [2, 2, 2], central_pixel],
}
bean_file = output.replace('.nxs', '_bean.json')
print(f"\nCreating msmapper bean at: {bean_file}")
json.dump(bean, open(bean_file, 'w'), indent=4)

print('\n\n############### RUNNING MSMAPPER ################')
result = subprocess.run([MSMAPPER, '-bean', bean_file])
result.check_returncode()
print('############## FINISHED MSMAPPER ################\n\n')

# Get output
pixel_map = data_file_reader(pixel_file)
coords = pixel_map('/processed/reciprocal_space/coordinates')
print(coords)

# Compare with expected hkl
expected_hkl = scan('array([h,k,l])')
msmapper_hkl = coords[-1]
print(f"Expected hkl: {expected_hkl}")
print(f"msmapper hkl: {msmapper_hkl}")
print(f"Difference: {np.sum(np.abs(msmapper_hkl - expected_hkl)):.4f}")


"-----------------------------------------------------------------------"

# main msmapper run
bean = {
        "inputs": [filename],  # Filename of scan file
        "output": output,  # Output filename - must be in processing directory, or somewhere you can write to
        "splitterName": "gaussian",  # one of the following strings "nearest", "gaussian", "negexp", "inverse"
        "splitterParameter": 2.0,  # splitter's parameter is distance to half-height of the weight function.
        # If you use None or "" then it is treated as "nearest"
        "scaleFactor": 2.0,
        # the oversampling factor for each image; to ensure that are no gaps in between pixels in mapping
        "step": [0.002],
        # a single value or list if 3 values and determines the lengths of each side of the voxels in the volume
        # "start": start,  # location in HKL space of the bottom corner of the array.
        # "shape": shape,  # size of the array to create for reciprocal space volume
        "reduceToNonZero": True  # True/False, if True, attempts to reduce the volume output
    }
bean_file = output.replace('.nxs', '_bean.json')
print(f"\nCreating msmapper bean at: {bean_file}")
json.dump(bean, open(bean_file, 'w'), indent=4)

print('\n\n############### RUNNING MSMAPPER ################')
result = subprocess.run([MSMAPPER, '-bean', bean_file])
result.check_returncode()
print('############## FINISHED MSMAPPER ################\n\n')

# Get output
remap = data_file_reader(output)

with remap.map.load_hdf() as hdf:
    # the following are links to the original scan file
    scan_command = remap.map.get_data(hdf, '/entry0/scan_command')  # str
    crystal = remap.map.get_data(hdf, '/entry0/sample/name')  # str
    temp = remap.map.get_data(hdf, '/entry0/instrument/temperature_controller/Tsample')  # float
    # this is the processed data
    haxis = remap.map.get_data(hdf, '/processed/reciprocal_space/h-axis')  # 1D array, length n
    kaxis = remap.map.get_data(hdf, '/processed/reciprocal_space/k-axis')  # 1D array, length m
    laxis = remap.map.get_data(hdf, '/processed/reciprocal_space/l-axis')  # 1D array, length o
    volume = remap.map.get_data(hdf, '/processed/reciprocal_space/volume')  # 3D array, shape [n,m,o]
    # detector parameters
    pixel_size = remap.map.get_data(hdf, '/entry0/instrument/pil3_100k/module/fast_pixel_direction')  # float, mm
    detector_distance = remap.map.get_data(hdf, '/entry0/instrument/pil3_100k/transformations/origin_offset')  # float, mm

print(f"Loaded file: {filename} with volume shape: {volume.shape}")

# average angle subtended by each pixel
solid_angle = pixel_size ** 2 / detector_distance ** 2  # sr
print(f'Each pixel is normalised by the solid angle: {solid_angle: .4g} sr')

volume = volume * solid_angle

# Plot summed cuts
plt.figure(figsize=(18, 8), dpi=60)
title = f"{filename} '{crystal}' {temp:.3g} K\n{scan_command}"
plt.suptitle(title, fontsize=18)

plt.subplot(131)
plt.plot(haxis, volume.sum(axis=1).sum(axis=1))
plt.xlabel('h-axis (r.l.u.)', fontsize=16)
plt.ylabel('sum axes [1,2]', fontsize=16)

plt.subplot(132)
plt.plot(kaxis, volume.sum(axis=0).sum(axis=1))
plt.xlabel('k-axis (r.l.u.)', fontsize=16)
plt.ylabel('sum axes [0,2]', fontsize=16)

plt.subplot(133)
plt.plot(laxis, volume.sum(axis=0).sum(axis=0))
plt.xlabel('l-axis (r.l.u.)', fontsize=16)
plt.ylabel('sum axes [0,1]', fontsize=16)

# Plot summed images
plt.figure(figsize=(18, 8), dpi=60)
title = f"{filename}\n{crystal} {temp:.3g} K: {scan_command}"
plt.suptitle(title, fontsize=20)
plt.subplots_adjust(wspace=0.3)

plt.subplot(131)
K, H = np.meshgrid(kaxis, haxis)
plt.pcolormesh(H, K, volume.sum(axis=2), shading='auto')
plt.xlabel('h-axis (r.l.u.)', fontsize=16)
plt.ylabel('k-axis (r.l.u.)', fontsize=16)
plt.axis('image')
#plt.colorbar()

plt.subplot(132)
L, H = np.meshgrid(laxis, haxis)
plt.pcolormesh(H, L, volume.sum(axis=1), shading='auto')
plt.xlabel('h-axis (r.l.u.)', fontsize=16)
plt.ylabel('l-axis (r.l.u.)', fontsize=16)
plt.axis('image')
#plt.colorbar()

plt.subplot(133)
L, K = np.meshgrid(laxis, kaxis)
plt.pcolormesh(K, L, volume.sum(axis=0), shading='auto')
plt.xlabel('k-axis (r.l.u.)', fontsize=16)
plt.ylabel('l-axis (r.l.u.)', fontsize=16)
plt.axis('image')
plt.colorbar()

plt.show()
