"""
Functions to load data from i06-1 and i10-1 beamline XAS measurements
"""

import numpy as np
import h5py
import hdfmap
import datetime

from mmg_toolbox.utils.file_functions import get_scan_number
from mmg_toolbox.utils.file_reader import read_dat_file
from mmg_toolbox.utils.polarisation import get_polarisation, check_polarisation
from mmg_toolbox.nexus.nexus_functions import nx_find_all, nx_find_data
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapXASMetadata as Md

from .spectra_analysis import energy_range_edge_label
from .spectra import Spectra
from .spectra_container import SpectraContainer, XasMetadata


def is_nxxas(filename: str) -> bool:
    """Return True if the NeXus file contains an entry or sub-entry with application definition NXxas"""
    return bool(nx_find_data(hdfmap.load_hdf(filename), 'NXentry', 'definition') == 'NXxas')


def create_xas_scan(name, energy: np.ndarray, monitor: np.ndarray, raw_signals: dict[str, np.ndarray],
                    filename: str = '', beamline: str = '', scan_no: int = 0, start_date_iso: str = '',
                    end_date_iso: str = '', cmd: str = '', default_mode: str = 'tey',
                    pol: str = 'pc', pol_angle: float = 0.0,
                    sample_name: str = '', temp: float = 300, mag_field: float = 0, pitch: float = 0,
                    element_edge: str | None = None) -> SpectraContainer:
    """
    Function to load data from i06-1 and i10-1 beamline XAS measurements
    """
    # Check spectra
    if default_mode not in raw_signals:
        raise KeyError(f"mode '{default_mode}' is not available in {list(raw_signals.keys())}")
    if element_edge is None:
        element, edge = energy_range_edge_label(energy.min(), energy.max())
    else:
        element, edge = element_edge.split()

    for detector, array in raw_signals.items():
        if len(array) != len(energy):
            print(f"Removing signal '{detector}' as the length is wrong")
        if np.max(array) < 0.1:
            print(f"Removing signal '{detector}' as the values are 0")
    raw_signals = {
        detector: array for detector, array in raw_signals.items()
        if len(array) == len(energy) and array.max() > 0.1
    }

    if len(raw_signals) == 0:
        raise ValueError("No raw_signals found")

    # perform Analysis steps
    spectra = {
        name: Spectra(energy, signal / monitor, label=str(scan_no), mode=name, process_label='raw',
                      process=f"{name} / monitor")
        for name, signal in raw_signals.items()
    }
    metadata = XasMetadata(
        filename=filename,
        beamline=beamline,
        scan_no=scan_no,
        start_date_iso=start_date_iso,
        end_date_iso=end_date_iso,
        cmd=cmd,
        default_mode=default_mode,
        pol=pol,
        pol_angle=pol_angle,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        pitch=pitch,
        element=element,
        edge=edge,
        energy=energy,
        raw_signals=raw_signals,
        monitor=monitor
    )
    return SpectraContainer(name, spectra, metadata=metadata)


def load_from_dat(filename: str, sample_name='', element_edge=None, mode: str | list[str] = 'all') -> SpectraContainer:
    """
    Load XAS Spectra from ASCII .dat file (SRS format)

    Parameters
    :param filename: path to file
    :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
    :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
    :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
    :return: SpectraContainer
    """
    # read file
    scan = read_dat_file(filename)

    # read Scan data
    scannables = scan.keys()
    energy = next(iter(scan.values()))  # fastEnergy or something else
    if 'C1' in scannables:
        signals = {
            'tey': scan['C1'],
            'tfy': scan['C3'],
        }
        monitor = scan['C2']
    elif 'msc19' in scannables:
        signals = {
            'tey': scan['msc19'],
            'tfy': scan['msc18'],
        }
        monitor = scan['msc19']
    else:
        raise ValueError(f"file {filename} does not contain a known signal scannable")

    if isinstance(mode, str):
        if mode == 'default':
            mode = 'tey'
        if mode in signals:
            signals = {mode: signals[mode]}
        else:
            mode = 'tey'
    else:
        signals = {_mode: signals[_mode] for _mode in mode}
        mode = mode[0]

    # read Metadata
    metadata = scan.metadata
    beamline = metadata.get('SRSPRJ', '?').lower()
    pol_from_id = 'pc' if metadata.get('iddtrp', 1) > 0 else 'nc'
    pol = check_polarisation(metadata.get('polarisation', pol_from_id))
    temp = metadata.get('Tsample_mag', 300)
    mag_field = metadata.get('magz', 0)
    cmd = metadata.get('command', '')
    date_str = metadata.get('date', '')
    date = datetime.datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
    date_iso = date.isoformat()
    scan_no = metadata.get('SRSRUN', get_scan_number(filename))

    return create_xas_scan(
        name=str(scan_no),
        energy=energy,
        raw_signals=signals,
        monitor=monitor,
        filename=filename,
        beamline=beamline,
        scan_no=scan_no,
        start_date_iso=date_iso,
        end_date_iso=date_iso,
        cmd=cmd,
        default_mode=mode,
        pol=pol,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        element_edge=element_edge
    )


def load_from_nxs(filename: str, sample_name=None, element_edge=None,
                  mode: str | list[str] = 'all') -> SpectraContainer:
    """
    Load XAS Spectra from NeXus file with NXxas application Definition

    Parameters
    :param filename: path to file
    :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
    :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
    :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
    :return: SpectraContainer
    """
    if isinstance(mode, str):
        mode = [mode]
    # read file
    with h5py.File(filename, 'r') as hdf:
        # Get default mode
        default_mode = mode[0]
        if default_mode.lower() in ['default', 'all']:
            default_mode = str(nx_find_data(hdf, 'NXxas', 'NXdata', 'mode'))
            if default_mode is None:
                raise ValueError(f"NXxas:NXdata:mode not found in {filename}")
            default_mode = default_mode.lower()
        mode = [default_mode.lower() if _mode.lower() == 'default' else _mode.lower() for _mode in mode]

        # read Scan data - NXxas application definition
        energy = nx_find_data(hdf, 'NXxas', 'NXdata', ['axes', 'energy'])
        if energy is None:
            raise ValueError(f"NXxas:NXdata:energy not found in {filename}")
        monitor = nx_find_data(hdf, 'NXxas', 'NXmonitor', ['signal', 'data'])
        if monitor is None:
            raise ValueError(f"NXxas:NXmonitor not found in {filename}")
        signals = {
            str(nx_find_data(grp, 'mode')).lower(): nx_find_data(grp, 'signal')
            for grp in nx_find_all(hdf, 'NXxas', 'NXdata')
            if mode[0] == 'all' or  str(nx_find_data(grp, 'mode')).lower() in mode
        }

        # read Metadata
        sample_name = sample_name or nx_find_data(hdf, 'NXsample', 'name', default='')
        beamline = nx_find_data(hdf, 'NXinstrument', 'name', default='?')
        temp = nx_find_data(hdf, 'NXsample', 'temperature', default=300)
        mag_field = nx_find_data(hdf, 'NXsample', 'magnetic_field', default=0)
        # DLS specific metadata
        cmd = nx_find_data(hdf, 'scan_command', default='')
        start_date_iso = nx_find_data(hdf, 'start_time', default='')
        end_date_iso = nx_find_data(hdf, 'end_time', default=start_date_iso)
        scan_no = nx_find_data(hdf, 'entry_identifier', default=get_scan_number(filename))
        pol = get_polarisation(hdf)
        pol_angle = nx_find_data(hdf, 'linear_arbitrary_angle', default=0)
    return create_xas_scan(
        name=str(scan_no),
        energy=energy,
        raw_signals=signals,
        monitor=monitor,
        filename=filename,
        beamline=beamline,
        scan_no=scan_no,
        start_date_iso=start_date_iso,
        end_date_iso=end_date_iso,
        cmd=cmd,
        default_mode=default_mode,
        pol=pol,
        pol_angle=pol_angle,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        element_edge=element_edge
    )


def load_from_nxs_using_hdfmap(filename: str, sample_name: str | None = None,
                               element_edge: str | None = None, mode: str | list[str] = 'all') -> SpectraContainer:
    """
    Load XAS Spectra from NeXus file with arbitrary application definition

    Parameters
    :param filename: path to file
    :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
    :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
    :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
    :return: SpectraContainer
    """
    if isinstance(mode, str):
        mode = [mode]

    with hdfmap.load_hdf(filename) as hdf:
        # HdfMap creates data-path namespace
        m = hdfmap.NexusMap()
        m.populate(hdf)

        # scan data
        scan_no = m.eval(hdf, 'entry_identifier', default=get_scan_number(filename))
        energy = m.eval(hdf, Md.energy)
        monitor = m.eval(hdf, Md.monitor)
        default_mode = 'tey' if mode[0].lower() in ['default', 'all'] else mode[0]
        mode_spec = {
            'tey': m.eval(hdf, Md.tey),
            'tfy': m.eval(hdf, Md.tfy),
        }
        if mode[0].lower() == 'all':
            use_modes = mode_spec.keys()
        else:
            use_modes = [default_mode if _mode.lower() == 'default' else _mode for _mode in mode]

        signals = {_mode: mode_spec[_mode] for _mode in use_modes}

        # metadata
        beamline = m.eval(hdf, 'f"{beamline}_{end_station}" if end_station else instrument_name')
        start_date_iso = m.eval(hdf, 'str(start_time)')
        end_date_iso = m.eval(hdf, 'str(end_time)')
        cmd = m.eval(hdf, Md.cmd)
        pol = get_polarisation(hdf)
        pol_angle = m.eval(hdf, Md.pol_angle)
        if sample_name is None:
            sample_name = m.eval(hdf, 'sample_name', '')
        temp = m.eval(hdf, Md.temp)
        mag_field = m.eval(hdf, Md.field_z)
        pitch = m.eval(hdf, Md.rot)
    return create_xas_scan(
        name=str(scan_no),
        energy=energy,
        raw_signals=signals,
        monitor=monitor,
        filename=filename,
        beamline=beamline,
        scan_no=scan_no,
        start_date_iso=start_date_iso,
        end_date_iso=end_date_iso,
        cmd=cmd,
        default_mode=default_mode,
        pol=pol,
        pol_angle=pol_angle,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        pitch=pitch,
        element_edge=element_edge
    )


def load_xas_scans(*filenames: str, sample_name: str | None = None, element_edge: str | None = None,
                   mode: str | list[str] = 'all', dls_loader: bool = False) -> list[SpectraContainer]:
    """
    Load XAS Spectra from a list of scan files

    Parameters
    :param filenames: path to file, can be '*.dat' or '*.nxs'
    :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
    :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
    :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
    :param dls_loader: bool, if True uses explicit loading of metadata from DLS MMG beamlines
    :return: SpectraContainer
    """
    scans = [
        load_from_dat(filename, sample_name=sample_name, element_edge=element_edge, mode=mode)
        if filename.endswith('.dat')
        else load_from_nxs(filename, sample_name=sample_name, element_edge=element_edge, mode=mode)
        if not dls_loader and is_nxxas(filename)
        else load_from_nxs_using_hdfmap(filename, sample_name=sample_name, element_edge=element_edge, mode=mode)
        for filename in filenames
    ]
    return scans


def find_similar_measurements(*filenames: str, temp_tol: float = 1., field_tol: float = 0.1,
                              sample_name: str | None = None, element_edge: str | None = None,
                              mode: str | list[str] = 'all', dls_loader: bool = False) -> list[SpectraContainer]:
    """
    Find similar measurements based on energy, temperature and field.

    Each measurement is compared to the first one in the list, using energy, temperature and field tolerances.

    The polarisation is also checked to be similar (lh, lv or cl, cr).

    Scans with different or missing metadata are removed from the list.

    :param filenames: List of filenames to compare
    :param temp_tol: Tolerance for temperature comparison (default: 0.1 K)
    :param field_tol: Tolerance for field comparison (default: 0.1 T)
    :param sample_name: sample name, e.g. 'sample1' or None to load from NeXus file
    :param element_edge: element edge, e.g. 'FeL3' or None to determine from energy range
    :param mode: detector values to load, 'all', 'default' or e.g. 'tey', 'tfy' as specified in file
    :param dls_loader: bool, if True uses explicit loading of metadata from DLS MMG beamlines
    :return: List of similar measurements
    """
    from mmg_toolbox.nexus.nexus_reader import find_matching_scans
    ini_scan, = load_xas_scans(filenames[0], sample_name=sample_name, element_edge=element_edge,
                              mode=mode, dls_loader=dls_loader)
    if len(filenames) == 1:
        filenames = find_matching_scans(filenames[0])
    element = ini_scan.metadata.element
    edge = ini_scan.metadata.edge
    temperature = ini_scan.metadata.temp
    field_z = abs(ini_scan.metadata.mag_field)  # allow +/- field
    pol = ini_scan.metadata.pol
    if pol in ['lh', 'lv']:
        similar_pols = ['lh', 'lv']
    elif pol in ['cl', 'cr']:
        similar_pols = ['cl', 'cr']
    elif pol in ['nc', 'pc']:
        similar_pols = ['nc', 'pc']
    elif pol in ['la']:
        similar_pols = ['la']
    else:
        raise ValueError(f"Unknown polarisation: {pol}")

    similar = []
    for filename in filenames:
        try:
            scan, = load_xas_scans(filename, sample_name=sample_name, element_edge=element_edge,
                                   mode=mode, dls_loader=dls_loader)
        except ValueError as ve:
            print(f"Error loading {filename} as xas_scan: {ve}")
            continue
        m = scan.metadata
        if (
            m.element == element and
            m.edge == edge and
            abs(m.temp - temperature) < temp_tol and
            abs(abs(m.mag_field) - field_z) < field_tol and
            m.pol in similar_pols
        ):
            similar.append(scan)
        else:
            print(f"Measurement {repr(scan)} is not similar to {repr(ini_scan)}")
    return similar

