"""
Functions for writing Nexus files
"""

import h5py
import numpy as np
import datetime

from hdfmap.nexus import default_nxentry

from mmg_toolbox import __version__
from mmg_toolbox.env_functions import get_scan_number


def NXentry(root: h5py.File, name: str) -> h5py.Group:
    """Create NXentry group"""
    entry = root.create_group(name)
    entry.attrs['NX_class'] = "NXentry"
    return entry


def NXfield(root: h5py.Group, name: str, data, **attrs) -> h5py.Dataset:
    """Create NXfield for storing data"""
    field = root.create_dataset(name, data=data)
    field.attrs.update(attrs)
    return field


def NXdata(root: h5py.Group, name: str, axes: list[str], signal: str) -> h5py.Group:
    """
    Create NXdata group

    xvals = np.arange(10)
    yvals = 3 + xvals ** 2
    group = NXdata(entry, 'xydata', axes=['x'], signal='y')
    xdata = NXfield(group, 'x', xvals, units='mm')
    ydata = NXfield(group, 'y' yvals, units='')
    """
    group = root.create_group(name)
    group.attrs.update({
        'NX_class': "NXdata",
        'axes': axes,
        'signal': signal,
    })
    return group


def NXnote(root: h5py.Group, name: str, description: str, data: str,
           filename: str | None = None, sequence_index: int | None = None) -> h5py.Group:
    """
    add NXnote to parent group
    """
    note = root.create_group(name)
    note.attrs['NX_class'] = 'NXnote'
    note.create_dataset('type', data='text/html')
    note.create_dataset('description', data=str(description))
    if filename:
        note.create_dataset('file_name', data=str(filename))
    note.create_dataset('data', data=str(data))
    return note


def NXprocess(root: h5py.Group, name: str, program: str,
              version: str, date: str | None = None, sequence_index: int | None = None) -> h5py.Group:
    """
    Create NXprocess group

    Example:
    entry = NXentry(root, 'processed')
    process = NXprocess(entry, 'process', program='Python', version='1.0')
    NXnote(process, 'step_1',
            description='First step',
            data='details',
            sequence_index=1
    )
    NXnote(process, 'step_2',
            description='Second step',
            data='details',
            sequence_index=2
    )
    data = NXdata(process, 'result', axes=['x'], signal='y')
    xdata = NXfield(group, 'x', xvals, units='mm')
    ydata = NXfield(group, 'y' yvals, units='')
    """
    if date is None:
        date = str(datetime.datetime.now())

    group = root.create_group(name)
    group.attrs['NX_class'] = 'NXprocess'
    if sequence_index:
        group.create_dataset('sequence_index', data=int(sequence_index))
    group.create_dataset('program', data=str(program))
    group.create_dataset('sequence_index', data=int(sequence_index))
    group.create_dataset('version', data=str(version))
    group.create_dataset('date', data=str(date))
    return group


def add_entry_links(root: h5py.File, *filenames: str):
    """
    Add entry links to nexus file
    """
    # Add links to previous files
    for n, filename in enumerate(filenames):
        with h5py.File(filename) as nxs:
            entry_path = default_nxentry(nxs)
        number = get_scan_number(filename) or n + 1
        label = str(number)
        root[label] = h5py.ExternalLink(filename, entry_path)


def add_xas_processing(root: h5py.File, energy: np.ndarray, signal: np.ndarray,
                       details: str = '', name: str = 'processing'):
    """
    Populate Nexus file with processed data
    """

    # Add processing group
    processing = NXentry(root, name)
    processing.attrs['default'] = 'data'

    process = NXprocess(
        root=processing,
        name='process',
        program='mmg_toolbox',
        sequence_index=1,
        version=__version__
    )
    NXnote(
        root=process,
        name='background',
        description='background subtraction',
        data=details,
        sequence_index=2
    )
    xas = NXdata(
        root=processing,
        name='data',
        axes=['energy'],
        signal='intensity'
    )
    NXfield(xas, 'energy', energy, units='eV')
    NXfield(xas, 'intensity', signal, units='')


def create_xmcd_nexus(filename: str, scan_files: list[str], energy: np.ndarray,
                      pol1: np.ndarray, pol2: np.ndarray, xmcd: np.ndarray, details: str = ''):
    """
    Create Nexus file for xmcd spectra
    """
    with h5py.File(filename, 'w') as nxs:
        nxs['default'] = 'xmcd'
        add_entry_links(nxs, *scan_files)

        add_xas_processing(nxs, energy, pol1, details, name='pol1')
        add_xas_processing(nxs, energy, pol2, details, name='pol2')
        add_xas_processing(nxs, energy, xmcd, details, name='xmcd')



