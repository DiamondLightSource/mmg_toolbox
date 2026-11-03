"""
mmg_toolbox example
Example script to show how to copy files with their linked data
"""

import os
from mmg_toolbox import Experiment

data_dir = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/cm37262-1'
scan_numbers = range(1032124, 1032214)

exp = Experiment(data_dir, instrument='i16')
scans = exp.scans(*scan_numbers)
filenames = [scan.filename for scan in scans]
old_file_size = sum(os.path.getsize(filename) for filename in filenames)

new_data_directory = 'example_data'

os.makedirs(new_data_directory)
exp.copy_files(new_data_directory, *scan_numbers, merge_links=True)

new_exp = Experiment(new_data_directory, instrument='i16')
new_scans = new_exp.scans(*scan_numbers)
new_filenames = [scan.filename for scan in new_scans]
new_file_size = sum(os.path.getsize(filename) for filename in new_filenames)

print(f"Old file size - {len(filenames)} files: {old_file_size*1e-6} MB (doesn't include image data)")
print(f"New file size - {len(new_filenames)} files: {new_file_size*1e-6} MB (includes image data with lossless image compression)")

