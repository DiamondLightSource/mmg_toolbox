"""
Functions for writing Nexus files
"""

import h5py
import numpy as np
import datetime

from hdfmap.nexus import default_nxentry

from mmg_toolbox.file_functions import get_scan_number
from mmg_toolbox.polarisation import polarisation_label_to_stokes
from mmg_toolbox.xray_utils import photon_wavelength


def add_nxfield(root: h5py.Group, name: str, data, **attrs) -> h5py.Dataset:
    """Create NXfield for storing data"""
    field = root.create_dataset(name, data=data)
    field.attrs.update(attrs)
    return field


def add_nxentry(root: h5py.File, name: str, definition: str | None = None) -> h5py.Group:
    """Create NXentry group"""
    entry = root.create_group(name, track_order=True)
    entry.attrs['NX_class'] = "NXentry"
    if definition is not None:
        add_nxfield(entry, 'definition', definition)
    return entry


def add_nxinstrument(root: h5py.Group, name: str, instrument_name: str) -> h5py.Group:
    """Create NXinstrument group"""
    instrument = root.create_group(name, track_order=True)
    instrument.attrs['NX_class'] = "NXinstrument"
    name = instrument.create_dataset('name', data=instrument_name)
    name.attrs['short_name'] = instrument_name
    return instrument


def add_nxsource(root: h5py.Group, name: str, source_name: str = 'dls', source_type: str = 'Synchrotron X-ray Source',
                 probe: str = 'x-ray', energy_gev: float = 3.0) -> h5py.Group:
    """
    Create NXsource group for DLS
    """
    source = root.create_group(name, track_order=True)
    source.attrs['NX_class'] = "NXsource"
    dls = 'Diamond Light Source'
    name = source.create_dataset('name', data=dls if source_name.lower() == 'dls' else source_name)
    name.attrs['short_name'] = source_name
    source.create_dataset('type', data=source_type)
    source.create_dataset('probe', data=probe)
    en = source.create_dataset('energy', data=energy_gev)
    en.attrs['units'] = 'GeV'
    return source


def add_nxmono(root: h5py.Group, name: str, energy_ev: np.ndarray) -> h5py.Group:
    """
    Create NXmonochromator group
    """
    mono = root.create_group(name, track_order=True)
    mono.attrs['NX_class'] = "NXmonochromator"
    en = mono.create_dataset('energy', data=energy_ev)
    en.attrs['units'] = 'eV'
    return mono


def add_nxdetector(root: h5py.Group, name: str, data: np.ndarray) -> h5py.Group:
    """
    Create NXdetector group
    """
    detector = root.create_group(name, track_order=True)
    detector.attrs['NX_class'] = "NXdetector"
    detector.create_dataset('data', data=data)
    return detector


def add_nxbeam(root: h5py.Group, name: str, incident_energy_ev: float, polarisation_label: str = 'lh',
               beam_size_um: tuple[float, float] | None = None) -> h5py.Group:
    """Create NXbeam group"""
    beam = root.create_group(name, track_order=True)
    beam.attrs['NX_class'] = "NXbeam"
    # Fields
    add_nxfield(beam, 'incident_energy', incident_energy_ev, units='eV')
    wl = photon_wavelength(incident_energy_ev / 1000.)
    add_nxfield(beam, 'incident_wavelength', wl, units='angstrom')
    pol_stokes = polarisation_label_to_stokes(polarisation_label)
    add_nxfield(beam, 'incident_polarization_stokes', pol_stokes)
    if beam_size_um is not None:
        add_nxfield(beam, 'extent', beam_size_um, units='μm')
    return beam


def add_nxsample(root: h5py.Group, name: str, sample_name: str = '', chemical_formula: str = '',
                 temperature_k: float = 300, magnetic_field_t: float = 0, electric_field_v: float = 0,
                 mag_field_dir: str = 'z', electric_field_dir: str = 'z',
                 sample_type: str = 'sample', description: str = '') -> h5py.Group:
    """Create NXsample group"""
    sample = root.create_group(name, track_order=True)
    sample.attrs['NX_class'] = "NXsample"
    # fields
    add_nxfield(sample, 'name', sample_name)
    add_nxfield(sample, 'chemical_formula', chemical_formula)
    add_nxfield(sample, 'type', sample_type)
    add_nxfield(sample, 'description', description)
    add_nxfield(sample, 'temperature', temperature_k, units='K')
    add_nxfield(sample, 'magnetic_field', magnetic_field_t, units='T', direction=mag_field_dir)
    add_nxfield(sample, 'electric_field', electric_field_v, units='V', direction=electric_field_dir)
    return sample


def add_nxdata(root: h5py.Group, name: str, axes: list[str], signal: str) -> h5py.Group:
    """
    Create NXdata group

    xvals = np.arange(10)
    yvals = 3 + xvals ** 2
    group = NXdata(entry, 'xydata', axes=['x'], signal='y')
    xdata = NXfield(group, 'x', xvals, units='mm')
    ydata = NXfield(group, 'y' yvals, units='')
    """
    group = root.create_group(name, track_order=True)
    group.attrs.update({
        'NX_class': "NXdata",
        'axes': axes,
        'signal': signal,
    })
    return group


def add_nxmonitor(root: h5py.Group, name: str, data: np.ndarray | str) -> h5py.Group:
    """
    Create NXmonitor group with monitor signal
    """
    group = root.create_group(name, track_order=True)
    group.attrs.update({
        'NX_class': "NXdata",
    })
    if isinstance(data, str):
        group['data'] = h5py.SoftLink(data)
    else:
        group.create_dataset('data', data=data)
    return group


def add_nxnote(root: h5py.Group, name: str, description: str, data: str | None = None,
               filename: str | None = None, sequence_index: int | None = None) -> h5py.Group:
    """
    add NXnote to parent group
    """
    note = root.create_group(name, track_order=True)
    note.attrs['NX_class'] = 'NXnote'
    note.create_dataset('type', data='text/plain')
    note.create_dataset('description', data=str(description))
    if filename:
        note.create_dataset('file_name', data=str(filename))
    if data:
        note.create_dataset('data', data=data.encode('utf-8'))
    if sequence_index:
        note.create_dataset('sequence_index', data=int(sequence_index))
    return note


def add_nxprocess(root: h5py.Group, name: str, program: str,
                  version: str, date: str | None = None, sequence_index: int | None = None) -> h5py.Group:
    """
    Create NXprocess group

    Example:
    entry = add_nxentry(root, 'processed')
    process = add_nxprocess(entry, 'process', program='Python', version='1.0')
    add_nxnote(process, 'step_1',
            description='First step',
            data='details',
            sequence_index=1
    )
    add_nxnote(process, 'step_2',
            description='Second step',
            data='details',
            sequence_index=2
    )
    data = add_nxdata(process, 'result', axes=['x'], signal='y')
    xdata = add_nxfield(group, 'x', xvals, units='mm')
    ydata = add_nxfield(group, 'y' yvals, units='')
    """
    if date is None:
        date = str(datetime.datetime.now())

    group = root.create_group(name, track_order=True)
    group.attrs['NX_class'] = 'NXprocess'
    if sequence_index:
        group.create_dataset('sequence_index', data=int(sequence_index))
    group.create_dataset('program', data=str(program))
    group.create_dataset('version', data=str(version))
    group.create_dataset('date', data=str(date))
    return group


def add_entry_links(root: h5py.File, *filenames: str):
    """
    Add entry links to nexus file
    """
    # Add links to previous files
    for n, filename in enumerate(filenames):
        if not h5py.is_hdf5(filename):
            continue
        with h5py.File(filename) as nxs:
            entry_path = default_nxentry(nxs)
        number = get_scan_number(filename) or n + 1
        label = str(number)
        root[label] = h5py.ExternalLink(filename, entry_path)






