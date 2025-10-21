"""
Functions for finding and reading files
"""

import os
import datetime
import typing
import h5py
import hdfmap
import numpy as np
from hdfmap.eval_functions import dataset2str, dataset2data
from PIL import Image

from mmg_toolbox.utils.misc_functions import consolidate_numeric_strings, regex_number


def list_files(folder_directory: str, extension='.nxs') -> list[str]:
    """Return list of files in directory with extension, returning list of full file paths ordered by modified time"""
    # return [os.path.join(folder_directory, file) for file in os.listdir(folder_directory) if file.endswith(extension)]
    try:
        return sorted(
            (file.path for file in os.scandir(folder_directory) if file.is_file() and file.name.endswith(extension)),
            key=lambda x: os.path.getmtime(x)
        )
    except (FileNotFoundError, PermissionError, OSError):
        return []


def display_timestamp(timestamp: float) -> str:
    """Return string representation of file timestamp"""
    return datetime.datetime.fromtimestamp(timestamp).strftime('%a %d-%b-%Y %H:%M')


def list_path_time(directory: str) -> list[tuple[str, float]]:
    """
    Return list of folders in diectory, along with modified time
        [(path, modified_time(s), nfiles), ...] = list_path_time_files('/folder/path', '.nxs')
    :param directory: directory to look in
    :return: [(path, timestamp), ...]
    """
    folders = [('.', os.stat(directory).st_mtime)]
    for f in os.scandir(directory):
        if f.is_dir():
            try:
                folders.append((f.path, f.stat().st_mtime))
            except PermissionError or FileNotFoundError:
                pass
    return sorted(folders, key=lambda x: x[0])


def list_folder_file_names(directory: str) -> tuple[list[str], list[str]]:
    """
    Return list of subdirectory and file names of given folder
    :param directory: directory to look in
    :return: folder_names, file_names
    """
    folders = []
    files = []
    for f in os.scandir(directory):
        if f.is_dir():
            try:
                folders.append(f.name)
            except PermissionError or FileNotFoundError:
                pass
        elif f.is_file():
            try:
                files.append(f.name)
            except PermissionError or FileNotFoundError:
                pass
    return folders, files


def folder_summary(directory: str) -> str:
    """Generate summary of folder"""
    folder_names, file_names = list_folder_file_names(directory)

    # subdirectories
    if len(folder_names) > 10:
        folder_names = consolidate_numeric_strings(*folder_names)
    if len(folder_names) > 30:
        subdirs_str = ""
    else:
        subdirs_str = '\n'.join(
            f"  {name}" for name in folder_names
        ) + '\n'
    # files
    files_str = '\n'.join(consolidate_numeric_strings(*file_names))
    file_ext = [os.path.splitext(file) for file in file_names]
    all_ext = {ext for name, ext in file_ext}
    file_types = {
        ext: (lst := [n for n, e in file_ext if e == ext], len(lst))
        for ext in all_ext
    }
    file_type_str = '\n'.join(
        f"  {ext}: {n}" for ext, (lst, n) in file_types.items()
    )
    summary = (
        f"Folder: {os.path.abspath(directory)}\n" +
        f"Modified: {display_timestamp(os.stat(directory).st_mtime)}\n\n" +
        f"Sub-Directories: {len(folder_names)}\n{subdirs_str}" +
        f"\nFiles: {len(file_names)}\n{files_str}\n" +
        f"\nFile-types:\n{file_type_str}"
    )
    return summary


def folder_summary_line(directory: str, extention='.nxs') -> str:
    """Generate summary of folder on a single line"""
    files = list_files(directory, extension=extention)
    ini = display_timestamp(os.path.getmtime(next(iter(files), directory)))
    fnl = display_timestamp(os.path.getmtime(next(reversed(files), directory)))
    return f"Files: {len(files)}, {ini} -> {fnl}"


def get_hdf_value(hdf_filename: str, hdf_address: str, default_value: typing.Any = '') -> typing.Any:
    """
    Open HDF file and return value from single dataset
    :param hdf_filename: str filename of hdf file
    :param hdf_address: str hdf address specifier of dataset
    :param default_value: Any - returned value if hdf_address is not available in file
    :return [dataset is array]: str "{type} {shape}"
    :return [dataset is not array]: output of dataset[()]
    :return [dataset doesn't exist]: default_value
    """
    try:
        with hdfmap.load_hdf(hdf_filename) as hdf:
            dataset = hdf.get(hdf_address)
            if isinstance(dataset, h5py.Dataset):
                return dataset2data(dataset)
            return default_value
    except Exception:
        return default_value


def get_hdf_string(hdf_filename: str, hdf_address: str, default_value: str = '') -> str:
    """
    Open HDF file and return value from single dataset
    :param hdf_filename: str filename of hdf file
    :param hdf_address: str hdf address specifier of dataset
    :param default_value: Any - returned value if hdf_address is not available in file
    :return [dataset is array]: str "{type} {shape}"
    :return [dataset is not array]: str output of dataset[()]
    :return [dataset doesn't exist]: default_value
    """
    try:
        with hdfmap.load_hdf(hdf_filename) as hdf:
            dataset = hdf.get(hdf_address)
            if isinstance(dataset, h5py.Dataset):
                return dataset2str(dataset)
            return default_value
    except Exception:
        return default_value


def hdfobj_string(hdf_filename: str, hdf_address: str) -> str:
    """Generate string describing object in hdf file"""
    with hdfmap.load_hdf(hdf_filename) as hdf:
        obj = hdf.get(hdf_address)
        if not obj:
            return ''
        try:
            link = repr(hdf.get(hdf_address, getlink=True))
        except RuntimeError:
            link = 'No link'
        myclass = hdf.get(hdf_address, getclass=True)
        out = f"{obj.name}\n"
        out += f"{repr(obj)}\n"
        out += f"{link}\n"
        out += f"{repr(myclass)}\n"
        out += '\nattrs:\n'
        out += '\n'.join([f"{key}: {obj.attrs[key]}" for key in obj.attrs])
        if isinstance(obj, h5py.Dataset):
            out += '\n\n--- Data ---\n'
            out += f"Shape: {obj.shape}\nSize: {obj.size}\nValues:\n"
            if obj.size > 1000:
                out += '---To large to view---'
            else:
                out += str(obj[()])
    return out


def read_tiff(image_filename: str) -> np.ndarray:
    """Read a tiff image, returning numpy array"""
    image = Image.open(image_filename)
    return np.array(image)


def get_scan_number(filename: str) -> int:
    """Return scan number from scan filename"""
    filename = os.path.basename(filename)
    match = regex_number.search(filename)
    if match:
        return int(match[0])
    return 0


def replace_scan_number(filename: str, new_number: int) -> str:
    """Replace scan number in filename"""
    path, filename = os.path.split(filename)
    new_filename = regex_number.sub(str(new_number), filename)
    return os.path.join(path, new_filename)
