"""
Functions to load data from i06-1 and i10-1 beamline XAS measurements
"""

import numpy as np
import h5py
import datetime
from collections import defaultdict
from mmg_toolbox.env_functions import get_scan_number
from mmg_toolbox.dat_file_reader import read_dat_file
from mmg_toolbox.polarisation import check_polarisation
from mmg_toolbox.spectra_analysis import energy_range_edge_label
from mmg_toolbox.nexus_functions import nx_find, nx_find_all, nx_find_data
from mmg_toolbox.spectra_scan import Spectra, SpectraContainer, XasMetadata


def create_scan(name, energy: np.ndarray, monitor: np.ndarray, raw_signals: dict[str, np.ndarray],
                filename: str = '', beamline: str = '', scan_no: int = 0, start_date_iso: str = '',
                end_date_iso: str = '', cmd: str = '', default_mode: str = 'tey', pol: str = 'pc',
                sample_name: str = '', temp: float = 300, mag_field: float = 0):
    """
    Function to load data from i06-1 and i10-1 beamline XAS measurements
    """
    # Check spectra
    if default_mode not in raw_signals:
        raise KeyError(f"mode '{default_mode}' is not available in {list(raw_signals.keys())}")
    element, edge = energy_range_edge_label(energy.min(), energy.max())

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
        'element': element,
        'edge': edge,
        'energy': energy,
        'raw_signals': raw_signals,
        'monitor': monitor,
    }
    m = XasMetadata(**metadata)
    return SpectraContainer(name, spectra, metadata=m)


def convert_to_nxxas(filename: str, nexus_filename: str, alt_nexus=False):
    """Create NeXus file from nxs for dat file"""
    if filename.endswith('.dat'):
        scan = load_from_dat(filename)
    else:
        scan = load_from_nxs(filename)
    scan.write_nexus(nexus_filename)


def load_from_dat(filename: str, sample_name='') -> SpectraContainer:
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

    return create_scan(
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
        mag_field=mag_field
    )


def load_from_nxs(filename: str):
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
                raise ValueError(f'Unknown data fields: {list(nx_find(hdf, 'NXdata').keys())}')

        # read Metadata
        beamline = nx_find_data(hdf, 'NXinstrument', 'name', default='?')
        pol = nx_find_data(hdf, 'NXinsertion_device', 'polarisation', default='?')
        temp = nx_find_data(hdf, '/entry/instrument/scm/T_sample', default=300)
        mag_field = nx_find_data(hdf, '/entry/instrument/scm/field_z', default=0)
        cmd = nx_find_data(hdf, 'scan_command', default='')
        start_date_iso = nx_find_data(hdf, 'start_time', default='')
        end_date_iso = nx_find_data(hdf, 'end_time', default=start_date_iso)
        sample_name = nx_find_data(hdf, 'NXsample', 'name', default='')
        scan_no = nx_find_data(hdf, 'entry_identifier', default=get_scan_number(filename))

    return create_scan(
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
        mag_field=mag_field
    )


def load_polarised_scans(*filenames: str, sample_name='') -> dict[str, list[SpectraContainer]]:
    """Load scans from a list of filenames, return {'pol': [scan1, scan2, ...]}"""
    scans = [
        load_from_dat(filename, sample_name=sample_name)
        if filename.endswith('.dat') else load_from_nxs(filename)
        for filename in filenames
    ]
    pol_scans = defaultdict(list)
    for scan in scans:
        pol_scans[scan.metadata.pol].append(scan)
    return pol_scans
