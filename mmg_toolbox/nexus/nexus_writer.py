"""
Functions for writing Nexus files
"""

import h5py
import numpy as np
import datetime
import json

from hdfmap.nexus import default_nxentry

import mmg_toolbox.nexus.nexus_names as nn
from mmg_toolbox.utils.file_functions import get_scan_number
from mmg_toolbox.nexus.nexus_transformations import TransformationAxis, RotationAxis, TranslationAxis, get_depends_on
from mmg_toolbox.utils.polarisation import polarisation_label_to_stokes, analyser_jones_matrix
from mmg_toolbox.utils.xray_utils import photon_wavelength


def add_nxclass(root: h5py.Group, name: str, nx_class: str) -> h5py.Group:
    """Create NXclass group"""
    group = root.create_group(name, track_order=True)
    group.attrs[nn.NX_CLASS] = nx_class
    return group


def add_nxfield(root: h5py.Group, name: str, data, **attrs) -> h5py.Dataset:
    """Create NXfield for storing data"""
    field = root.create_dataset(name, data=data)
    field.attrs.update(attrs)
    return field


def add_nxentry(root: h5py.File, name: str, definition: str | None = None) -> h5py.Group:
    """Create NXentry group"""
    entry = add_nxclass(root, name, nn.NX_ENTRY)
    if definition is not None:
        add_nxfield(entry, nn.NX_DEFINITION, definition)
    return entry


def add_nxinstrument(root: h5py.Group, name: str, instrument_name: str) -> h5py.Group:
    """Create NXinstrument group"""
    instrument = add_nxclass(root, name, nn.NX_INST)
    add_nxfield(instrument, nn.NX_NAME, instrument_name, short_name=instrument_name)
    return instrument


def add_nxsource(root: h5py.Group, name: str, source_name: str = 'dls', source_type: str = 'Synchrotron X-ray Source',
                 probe: str = 'x-ray', energy_gev: float = 3.0) -> h5py.Group:
    """
    Create NXsource group for DLS
    """
    source = add_nxclass(root, name, nn.NX_SOURCE)
    dls = 'Diamond Light Source'
    add_nxfield(source, nn.NX_NAME, dls if source_name.lower() == 'dls' else source_name,
                short_name=dls)
    add_nxfield(source, 'type', source_type)
    add_nxfield(source, 'probe', probe)
    add_nxfield(source, 'energy', energy_gev, units='GeV')
    return source


def add_nxinsertion_device(root: h5py.Group, name: str, id_type: str = 'undulator', gap: float = 7.0,
                           harmonic: int = 7) -> h5py.Group:
    """
    Create NXinsertion_device group
    """
    group = add_nxclass(root, name, nn.NX_ID)
    add_nxfield(group, 'id_type', id_type)
    add_nxfield(group, 'gap', gap, units='mm')
    add_nxfield(group, 'harmonic', harmonic)
    return group


def add_nxmono(root: h5py.Group, name: str, energy_ev: float | np.ndarray, units='eV') -> h5py.Group:
    """
    Create NXmonochromator group
    """
    mono = add_nxclass(root, name, nn.NX_MONO)
    add_nxfield(mono,'energy', energy_ev, units=units)
    return mono


def add_nxcrystal(root: h5py.Group, name: str, usage: str, crystal_type: str, d_spacing: float,
                  reflection: tuple[int, int, int] = (1, 1, 1), order_no: int = 1) -> h5py.Group:
    """
    Create NXcrystal group
    Used for monochromators and analyser crystals

    :param root: h5py group
    :param name: name of crystal
    :param usage: 'Bragg' or 'Laue'
    :param crystal_type: Chemical formula or substance, e.g. Si, HOPG, multilayer
    :param d_spacing: spacing between crystals in Angstrom
    :param reflection: reflection index in Miller-indices (h,k,l)
    :param order_no: order of the reflection, n*(h,k,l)
    :return: NXcrystal group
    """
    crystal = add_nxclass(root, name, nn.NX_XTL)
    add_nxfield(crystal, 'usage', usage)
    add_nxfield(crystal, 'type', crystal_type)
    add_nxfield(crystal, 'd_spacing', d_spacing, units='angstrom')
    add_nxfield(crystal, 'reflection', np.array(reflection, dtype=int).reshape(3))
    add_nxfield(crystal,'order_no', int(order_no))
    return crystal


def add_nxdetector(root: h5py.Group, name: str, data: np.ndarray,
                   detector_distance_mm: float = 1000, pixel_size_mm: float = 0.055,
                   depends_on: str | h5py.Group | None = None,
                   transformations: list[TransformationAxis] | None = None) -> h5py.Group:
    """
    Create NXdetector group
    """
    detector = add_nxclass(root, name, nn.NX_DET)
    add_nxfield(detector, 'data', data)
    add_nxfield(detector, 'type', 'ccd')
    module = add_nxclass(root, 'module', nn.NX_MODULE)

    if transformations is None:
        transformations = (TranslationAxis('detector_offset', detector_distance_mm, vector=(0, 0, 1)),)
    add_nxtransformations(detector, 'transformations', *transformations, depends_on=depends_on)
    path = detector[nn.NX_DEPON][...]

    # Add module directions
    add_nxfield(module, nn.NX_MODULE_ORIGIN, (0, 0))
    add_nxfield(module, nn.NX_MODULE_SIZE, data.shape[-2:])
    add_nxfield(module, nn.NX_MODULE_OFFSET, 0, units='mm', transformation_type=nn.NX_TTRAN,
                vector=(0, 0, 0), offset=(0, 0, 0), offset_units='mm', depends_on=path)
    add_nxfield(module, nn.NX_MODULE_FAST, pixel_size_mm, units='mm', transformation_type=nn.NX_TTRAN,
                vector=(0, 0, 0), offset=(0, 0, 0), offset_units='mm', depends_on=path)
    add_nxfield(module, nn.NX_MODULE_SLOW, pixel_size_mm, units='mm', transformation_type=nn.NX_TTRAN,
                vector=(0, 0, 0), offset=(0, 0, 0), offset_units='mm', depends_on=path)
    return detector


def add_nxbeam(root: h5py.Group, name: str, incident_energy_ev: float, polarisation_label: str = 'lh',
               beam_size_um: tuple[float, float] | None = None) -> h5py.Group:
    """Create NXbeam group"""
    beam = add_nxclass(root, name, nn.NX_BEAM)
    # Fields
    add_nxfield(beam, nn.NX_EN, incident_energy_ev, units='eV')
    wl = photon_wavelength(incident_energy_ev / 1000.)
    add_nxfield(beam, nn.NX_WL, wl, units='angstrom')
    pol_stokes = polarisation_label_to_stokes(polarisation_label)
    add_nxfield(beam, nn.NX_STOKES, pol_stokes)
    if beam_size_um is not None:
        add_nxfield(beam, nn.NX_BSIZE, beam_size_um, units='μm')
    return beam


def add_nxsample(root: h5py.Group, name: str, sample_name: str = '', chemical_formula: str = '',
                 temperature_k: float = 300, magnetic_field_t: float = 0, electric_field_v: float = 0,
                 mag_field_dir: str = 'z', electric_field_dir: str = 'z',
                 sample_type: str = 'sample', description: str = '') -> h5py.Group:
    """Create NXsample group"""
    sample = add_nxclass(root, name, nn.NX_SAMPLE)
    # fields
    add_nxfield(sample, 'name', sample_name)
    add_nxfield(sample, 'chemical_formula', chemical_formula)
    add_nxfield(sample, 'type', sample_type)
    add_nxfield(sample, 'description', description)
    add_nxfield(sample, 'temperature', temperature_k, units='K')
    add_nxfield(sample, 'magnetic_field', magnetic_field_t, units='T', direction=mag_field_dir)
    add_nxfield(sample, 'electric_field', electric_field_v, units='V', direction=electric_field_dir)
    return sample


def add_nxdata(root: h5py.Group, name: str, axes: list[str], signal: str, *auxilliary_signals: str) -> h5py.Group:
    """
    Create NXdata group

    xvals = np.arange(10)
    yvals = 3 + xvals ** 2
    group = NXdata(entry, 'xydata', axes=['x'], signal='y')
    xdata = add_nxfield(group, 'x', xvals, units='mm')
    ydata = add_nxfield(group, 'y' yvals, units='')
    """
    group = add_nxclass(root, name, nn.NX_DATA)
    group.attrs.update({
        nn.NX_AXES: axes,
        nn.NX_SIGNAL: signal,
        nn.NX_AUXILIARY: auxilliary_signals,
    })
    return group


def add_nxmonitor(root: h5py.Group, name: str, data: np.ndarray | str) -> h5py.Group:
    """
    Create NXmonitor group with monitor signal
    """
    group = add_nxclass(root, name, nn.NX_MON)
    if isinstance(data, str):
        group['data'] = h5py.SoftLink(data)
    else:
        group.create_dataset('data', data=data)
    return group


def add_nxnote(root: h5py.Group, name: str, description: str, data: str | dict | None = None,
               filename: str | None = None, sequence_index: int | None = None) -> h5py.Group:
    """
    add NXnote to parent group
    """
    note = add_nxclass(root, name, nn.NX_NOTE)
    if isinstance(data, dict):
        note.create_dataset('type', data='application/json')
    else:
        note.create_dataset('type', data='text/plain')
    note.create_dataset('description', data=str(description))
    if filename:
        note.create_dataset('file_name', data=str(filename))
    if data:
        if isinstance(data, dict):
            note.create_dataset('data', data=json.dumps(data))
        else:
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

    group = add_nxclass(root, name, nn.NX_PROC)
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


def add_channel_cut_mono(instrument: h5py.Group, name: str, energy: float | np.ndarray,
                         d_spacing: float, crystal_type: str = 'Si', units: str = 'eV',
                         reflection: tuple[int, int, int] = (1, 1, 1), order_no: int = 1):
    """
    Add channel cut mono
    """
    # create mono
    mono = add_nxmono(instrument, name, energy, units)
    # Add crystals
    add_nxcrystal(
        root=mono,
        name='crystal1',
        usage='Bragg',
        d_spacing=d_spacing,
        crystal_type=crystal_type,
        reflection=reflection,
        order_no=order_no
    )
    add_nxcrystal(
        root=mono,
        name='crystal2',
        usage='Bragg',
        d_spacing=d_spacing,
        crystal_type=crystal_type,
        reflection=reflection,
        order_no=order_no
    )


def add_analyser_detector(instrument: h5py.Group, name: str, data: np.ndarray,
                          d_spacing: float, crystal_type: str = 'HOPG',
                          reflection: tuple[int, int, int] = (0, 0, 1), order_no: int = 1,
                          bragg: float = 90, stokes: float = 0,
                          sample_analyser_distance_mm: float = 1000, analyser_det_distance_mm: float = 50,
                          pixel_size_mm: float = 0.1, depends_on: str | h5py.Group = '.'
                          ):
    """
    Add analyser detector
    """
    xtl = add_nxcrystal(
        root=instrument,
        name=f"{name}_analyser",
        usage='Bragg',
        d_spacing=d_spacing,
        crystal_type=crystal_type,
        reflection=reflection,
        order_no=order_no,
    )

    # Transformations - Analyser
    ana_trans = TranslationAxis(name='origin', value=sample_analyser_distance_mm, vector=(0, 0, 1))
    rot_stokes = RotationAxis(name='Stokes', value=stokes, vector=(0, 0, 1))
    add_nxtransformations(xtl, 'transformations', ana_trans, rot_stokes, depends_on=depends_on)

    # Transformations - Detector
    det_trans = TranslationAxis(name='origin_offset', value=analyser_det_distance_mm, vector=(0, 0, 1))
    det_bragg = RotationAxis(name='tthp', value=bragg, vector=(-1, 0, 0))
    # Add detector
    detector = add_nxdetector(
        root=instrument,
        name=name,
        data=data,
        detector_distance_mm=analyser_det_distance_mm,
        pixel_size_mm=pixel_size_mm,
        depends_on=xtl,
        transformations=[det_bragg, det_trans],
    )
    # Add Jones matrix
    jones = analyser_jones_matrix(crystal_bragg=bragg, rotation=stokes)
    add_nxfield(detector, 'polarization_analyser_jones_matrix', jones)


def add_6circle_diffractometer(instrument: h5py.Group, name: str, phi: np.ndarray, chi: np.ndarray, eta: np.ndarray,
                               mu: np.ndarray, delta: np.ndarray, gamma: np.ndarray) -> h5py.Group:
    """6-circle Euler diffractometer"""
    from mmg_toolbox.diffraction.diffcalc import euler2kappa, KALPHA
    kphi, kappa, ktheta = euler2kappa(phi, chi, eta, mode=1, kalpha=KALPHA)

    # Positions
    diff = add_nxclass(instrument, name, 'NXcollection')
    add_nxfield(diff, 'kphi', kphi, units='degrees')
    add_nxfield(diff, 'kappa', kappa, units='degrees')
    add_nxfield(diff, 'ktheta', ktheta, units='degrees')
    add_nxfield(diff, 'kalpha', KALPHA, units='degrees')
    add_nxfield(diff, 'phi', phi, units='degrees')
    add_nxfield(diff, 'chi', chi, units='degrees')
    add_nxfield(diff, 'eta', eta, units='degrees')
    add_nxfield(diff, 'mu', mu, units='degrees')
    add_nxfield(diff, 'delta', delta, units='degrees')
    add_nxfield(diff, 'gamma', gamma, units='degrees')

    # Transformations
    phi = RotationAxis('phi', phi, vector=(0, 1, 0))
    chi = RotationAxis('chi', chi, vector=(0, 0, 1))
    eta = RotationAxis('eta', eta, vector=(-1, 0, 0))
    mu = RotationAxis('mu', mu, vector=(0, 1, 0))
    delta = RotationAxis('delta', delta, vector=(-1, 0, 0))
    gamma = RotationAxis('gamma', gamma, vector=(0, 1, 0))

    add_nxtransformations(diff, 'sample', phi, chi, eta, mu, delta, gamma)
    del diff['depends_on']
    add_nxtransformations(diff, 'detector_arm', delta, gamma)
    del diff['depends_on']
    return diff


def add_6circle_diffractometer_kappa(instrument: h5py.Group, name: str,
                                     kphi: np.ndarray, kappa: np.ndarray, ktheta: np.ndarray,
                                     mu: np.ndarray, delta: np.ndarray, gamma: np.ndarray,
                                     kalpha: float,) -> h5py.Group:
    """6-circle Kappa diffractometer"""
    from mmg_toolbox.diffraction.diffcalc import kappa2euler
    phi, chi, eta = kappa2euler(ktheta, kappa, kphi, mode=1, kalpha=kalpha)

    # Positions
    diff = add_nxclass(instrument, name, 'NXcollection')
    add_nxfield(diff, 'kphi', kphi, units='degrees')
    add_nxfield(diff, 'kappa', kappa, units='degrees')
    add_nxfield(diff, 'ktheta', ktheta, units='degrees')
    add_nxfield(diff, 'kalpha', kalpha, units='degrees')
    add_nxfield(diff, 'phi', phi, units='degrees')
    add_nxfield(diff, 'chi', chi, units='degrees')
    add_nxfield(diff, 'eta', eta, units='degrees')
    add_nxfield(diff, 'mu', mu, units='degrees')
    add_nxfield(diff, 'delta', delta, units='degrees')
    add_nxfield(diff, 'gamma', gamma, units='degrees')

    # Transformations
    phi = RotationAxis('phi', phi, vector=(0, 1, 0))
    chi = RotationAxis('chi', chi, vector=(0, 0, 1))
    eta = RotationAxis('eta', eta, vector=(-1, 0, 0))
    mu = RotationAxis('mu', mu, vector=(0, 1, 0))
    delta = RotationAxis('delta', delta, vector=(-1, 0, 0))
    gamma = RotationAxis('gamma', gamma, vector=(0, 1, 0))

    add_nxtransformations(diff, 'sample', phi, chi, eta, mu, delta, gamma)
    del diff['depends_on']
    add_nxtransformations(diff, 'detector_arm', delta, gamma)
    del diff['depends_on']
    return diff


############################################################
################### NXTransformations ######################
############################################################


def add_nxtransformations(root: h5py.Group, name: str, *transformations: TransformationAxis,
                          depends_on: str | h5py.Group | None = None) -> h5py.Group:
    """
    Add NXtransformations group
    Adds a depends_on dataset to the given group and a sub-group called 'transformations'
    """
    depends_on_ds = root.create_dataset(nn.NX_DEPON, data='.')
    if len(transformations) == 0:
        depends_on_ds[...] = get_depends_on(depends_on)
        return root
    group = add_nxclass(root, name, nn.NX_TRAN)
    axes = []
    for t in transformations:
        axis = add_nxfield(
            root=group,
            name=t.name,
            data=t.value,
            units=t.units,
            transformation_type=t.type,
            vector=t.vector,
            offset=t.offset,
            offset_units=t.offset_units,
            depends_on='.'
        )
        axes.append(axis)

    # Assign depends on pointers
    for axis, do in zip(axes, axes[1:]):
        axis.attrs[nn.NX_DEPON] = do.name
    # Point group depends_on dataset to the first transformation in the chain
    depends_on_ds[...] = axes[0].name
    # Point the last transformation towards an external transformation dataset
    if depends_on is not None:
        if isinstance(depends_on, h5py.Group):
            if nn.NX_DEPON in depends_on:
                depends_on = depends_on[nn.NX_DEPON].asstr()[...]
            else:
                raise Exception(f"group: {depends_on.name} does not contain 'depends_on'")
        axes[-1].attrs[nn.NX_DEPON] = depends_on  # path of transformation dataset
    return group


