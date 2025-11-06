"""
Functions to load data from i06-1 and i10-1 beamline XAS measurements
"""

import numpy as np
import h5py
import datetime

from mmg_toolbox.utils.file_functions import get_scan_number
from mmg_toolbox.utils.file_reader import read_dat_file
from mmg_toolbox.utils.polarisation import check_polarisation
from mmg_toolbox.nexus.nexus_functions import nx_find, nx_find_all, nx_find_data
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapXASMetadata as Md

from .spectra_analysis import energy_range_edge_label
from .spectra import Spectra
from .spectra_container import SpectraContainer, XasMetadata


def create_xas_scan(name, energy: np.ndarray, monitor: np.ndarray, raw_signals: dict[str, np.ndarray],
                    filename: str = '', beamline: str = '', scan_no: int = 0, start_date_iso: str = '',
                    end_date_iso: str = '', cmd: str = '', default_mode: str = 'tey', pol: str = 'pc',
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
            raw_signals.pop(detector)
        if np.max(array) < 0.1:
            print(f"Removing signal '{detector}' as the values are 0")
            raw_signals.pop(detector)
    if len(raw_signals) == 0:
        raise ValueError("No raw_signals found")

    # perform Analysis steps
    spectra = {
        name: Spectra(energy, signal / monitor, mode=name, process_label='raw', process=f"{name} / monitor")
        for name, signal in raw_signals.items()
    }
    metadata = {
        'filename': filename,
        'beamline': beamline,
        'scan_no': scan_no,
        'start_date_iso': start_date_iso,
        'end_date_iso': end_date_iso,
        'cmd': cmd,
        'default_mode': default_mode,
        'pol': pol,
        'sample_name': sample_name,
        'temp': temp,
        'mag_field': mag_field,
        'pitch': pitch,
        'element': element,
        'edge': edge,
        'energy': energy,
        'raw_signals': raw_signals,
        'monitor': monitor,
    }
    m = XasMetadata(**metadata)
    return SpectraContainer(name, spectra, metadata=m)


def load_from_dat(filename: str, sample_name='', element_edge=None) -> SpectraContainer:
    # read file
    scan = read_dat_file(filename)

    # read Scan data
    scannables = scan.keys()
    mode = 'tey'
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


def load_from_nxs(filename: str, sample_name=None, element_edge=None) -> SpectraContainer:
    # read file
    with h5py.File(filename, 'r') as hdf:
        # read Scan data
        mode = nx_find(hdf, 'NXxas', 'NXdata', 'mode')
        if mode:
            # NXxas application definition
            energy = nx_find_data(hdf, 'NXxas', 'NXdata', 'axes')
            monitor = nx_find_data(hdf, 'NXxas', 'NXmonitor', 'signal')
            signals = {
                nx_find_data(grp, 'mode'): nx_find_data(grp, 'signal')
                for grp in nx_find_all(hdf, 'NXxas', 'NXdata')
            }
        else:
            mode = 'tey'
            energy = nx_find_data(hdf, 'NXdata', 'axes')
            if '/entry/instrument/fesData/C1' in hdf:
                # i06-1 old nexus
                monitor = hdf['/entry/instrument/fesData/C2'][()]
                signals = {
                    'tey': hdf['/entry/instrument/fesData/C1'][()],
                    'tfy': hdf['/entry/instrument/fesData/C3'][()],
                }
                if signals['tfy'].max() < 0.1:
                    signals['tfy'] = hdf['/entry/instrument/fesData/C4'][()]
            elif '/entry/mcse16/data' in hdf:
                # i10-1 old nexus
                monitor = hdf['/entry/mcse16/data'][()]
                signals = {
                    'tey': hdf['/entry/mcse17/data'][()],
                    'tfy': hdf['/entry/mcse19/data'][()],
                }
            else:
                nxdata = nx_find(hdf, 'NXdata')
                fields = list(nxdata.keys())
                raise ValueError(f'Unknown data fields: {fields}')

        # read Metadata - currently only works for i06-1!
        beamline = nx_find_data(hdf, 'NXinstrument', 'name', default='?')
        pol = nx_find_data(hdf, 'NXinsertion_device', 'polarisation', default='?')
        temp = nx_find_data(hdf, '/entry/instrument/scm/T_sample', default=300)
        mag_field = nx_find_data(hdf, '/entry/instrument/scm/field_z', default=0)
        cmd = nx_find_data(hdf, 'scan_command', default='')
        start_date_iso = nx_find_data(hdf, 'start_time', default='')
        end_date_iso = nx_find_data(hdf, 'end_time', default=start_date_iso)
        scan_no = nx_find_data(hdf, 'entry_identifier', default=get_scan_number(filename))

        if sample_name is None:
            sample_name = nx_find_data(hdf, 'NXsample', 'name', default='')

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
        default_mode=mode,
        pol=pol,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        element_edge=element_edge
    )


def load_from_nxs_using_hdfmap(filename: str, sample_name=None, element_edge=None) -> SpectraContainer:
    """Load ScanContainer"""
    import hdfmap

    with hdfmap.load_hdf(filename) as hdf:
        # HdfMap creates data-path namespace
        m = hdfmap.NexusMap()
        m.populate(hdf)

        # scan data
        scan_no = m.eval(hdf, 'entry_identifier', default=get_scan_number(filename))
        energy = m.eval(hdf, Md.energy)
        monitor = m.eval(hdf, Md.monitor)
        mode = 'tey'
        signals = {
            'tey': m.eval(hdf, Md.tey),
            'tfy': m.eval(hdf, Md.tfy),
        }
        # metadata
        beamline = m.eval(hdf, 'f"{beamline}_{end_station}" if end_station else instrument_name')
        start_date_iso = m.eval(hdf, 'str(start_time)')
        end_date_iso = m.eval(hdf, 'str(end_time)')
        cmd = m.eval(hdf, Md.cmd)
        pol = check_polarisation(m.eval(hdf, Md.pol))
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
        default_mode=mode,
        pol=pol,
        sample_name=sample_name,
        temp=temp,
        mag_field=mag_field,
        pitch=pitch,
        element_edge=element_edge
    )


def load_xas_scans(*filenames: str, sample_name='') -> list[SpectraContainer]:
    """Load scans from a list of filenames, return {'pol': [scan1, scan2, ...]}"""
    scans = [
        load_from_dat(filename, sample_name=sample_name)
        if filename.endswith('.dat') else load_from_nxs_using_hdfmap(filename)
        for filename in filenames
    ]
    return scans


def find_similar_measurements(*filenames: str, temp_tol=1., field_tol=0.1) -> list[SpectraContainer]:
    """
    Find similar measurements based on energy, temperature and field.

    Each measurement is compared to the first one in the list, using energy, temperature and field tolerances.

    The polarisation is also checked to be similar (lh, lv or cl, cr).

    Scans with different or missing metadata are removed from the list.

    :param filenames: List of filenames to compare
    :param temp_tol: Tolerance for temperature comparison (default: 0.1 K)
    :param field_tol: Tolerance for field comparison (default: 0.1 T)
    :return: List of similar measurements
    """
    from mmg_toolbox.nexus.nexus_reader import find_matching_scans
    ini_scan = load_xas_scans(filenames[0])[0]
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
    else:
        raise ValueError(f"Unknown polarisation: {pol}")

    similar = []
    for filename in filenames:
        try:
            scan = load_xas_scans(filename)[0]
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

