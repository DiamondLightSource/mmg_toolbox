"""
Spectra scan
"""

import os
import numpy as np
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import hdfmap
import mmg_toolbox.spectra_analysis as spa


class Spectra:
    def __init__(self, energy: np.ndarray, signal: np.ndarray):
        self.energy = energy
        self.signal = signal

    def __repr__(self):
        return f"Spectra(energy=array{self.energy.shape}, signal=array{self.signal.shape})"

    def __add__(self, other):
        return combine_spectra(self, other)

    def __sub__(self, other):
        return subtract_spectra(self, other)

    def signal_jump(self, ev_from_start=5., ev_from_end=None) -> float:
        return spa.signal_jump(self.energy, self.signal, ev_from_start, ev_from_end)

    def subtract_flat_background(self, ev_from_start=5.):
        sig, bkg = spa.subtract_flat_background(self.energy, self.signal, ev_from_start)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def normalise_background(self, ev_from_start=5.):
        sig, bkg = spa.normalise_background(self.energy, self.signal, ev_from_start)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_linear_background(self, ev_from_start=5.):
        sig, bkg = spa.fit_linear_background(self.energy, self.signal, ev_from_start)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_curve_background(self, ev_from_start=5.):
        sig, bkg = spa.fit_curve_background(self.energy, self.signal, ev_from_start)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_exp_background(self, ev_from_start=5.):
        sig, bkg = spa.fit_exp_background(self.energy, self.signal, ev_from_start)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_exp_step(self, ev_from_start=5., ev_from_end=5.):
        sig, bkg = spa.fit_exp_step(self.energy, self.signal, ev_from_start, ev_from_end)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_bkg_then_norm_to_peak(self, ev_from_start=5., ev_from_end=5.):
        sig, bkg = spa.fit_bkg_then_norm_to_peak(self.energy, self.signal, ev_from_start, ev_from_end)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def fit_bkg_then_norm_to_jump(self, ev_from_start=5., ev_from_end=5.):
        sig, bkg = spa.fit_bkg_then_norm_to_jump(self.energy, self.signal, ev_from_start, ev_from_end)
        return ProcessedSpectra(self, self.energy, sig, background=bkg)

    def plot(self, ax: Axes | None = None, *args, **kwargs):
        if ax is None:
            ax = plt.gca()
        ax.plot(self.energy, self.signal, *args, **kwargs)


class ProcessedSpectra(Spectra):
    """
    Like spectra but with defined background
    """
    def __init__(self, original: Spectra, processed_energy, processed_signal, background=None):
        self.original = original
        super().__init__(processed_energy, processed_signal)
        self.background = background

    def __repr__(self):
        return f"Processed{self.original}"


class MultiSpectra(Spectra):
    """
    Combination of multiple spectra
    """
    def __init__(self, originals: list[Spectra], energy, signal):
        self.originals = originals
        super().__init__(energy, signal)

    def __add__(self, other):
        if isinstance(other, MultiSpectra):
            return combine_spectra(*(self.originals + other.originals))
        return combine_spectra(*(self.originals + [other]))

    def __repr__(self):
        return f"MultiSpectra({len(self.originals)} Spectra)"

    def __str__(self):
        spectra_str = '\n'.join(f"  {spectra}" for spectra in self.originals)
        return self.__repr__() + "\n" + spectra_str

def combine_spectra(*args: Spectra) -> MultiSpectra:
    """Combine multiple spectra"""
    av_energy = spa.average_energy_scans(*(spectra.energy for spectra in args))
    new_signal = spa.average_energy_spectra(av_energy, *((spectra.energy, spectra.signal) for spectra in args))
    return MultiSpectra(list(args), av_energy, new_signal)


def subtract_spectra(spectra1: Spectra, spectra2: Spectra) -> MultiSpectra:
    """Subtract spectra1 - spectra2"""
    av_energy = spa.average_energy_scans(spectra1.energy, spectra2.energy)
    signal1 = spa.average_energy_spectra(av_energy, (spectra1.energy, spectra1.signal))
    signal2 = spa.average_energy_spectra(av_energy, (spectra2.energy, spectra2.signal))
    return MultiSpectra([spectra1, spectra2], av_energy, signal1 - signal2)


class Scan:
    def __init__(self, filename: str, hdf_map: hdfmap.NexusMap | None = None,
                 scan_names: dict | None = {}, metadata_names: dict | None = {}):
        if scan_names is None:
            scan_names = {}
        if metadata_names is None:
            metadata_names = {}
        self.filename = os.path.abspath(filename)
        self.basename = os.path.basename(filename)
        self.map = hdfmap.create_nexus_map(filename) if hdf_map is None else hdf_map
        default_scan = np.ones(self.map.scannables_shape())

        with hdfmap.load_hdf(filename) as nxs:
            self.scan_data = {
                name: self.map.eval(nxs, expr) for name, expr in scan_names.items()
            }
            self.metadata = {
                name: self.map.format_hdf(nxs, expr) for name, expr in metadata_names.items()
            }

    def __repr__(self):
        return f"Scan('{os.path.basename(self.filename)}')"

    def eval(self, expression: str, default=None):
        """Open file and evaluate namespace string"""
        return self.map.eval(self.map.load_hdf(), expression, default=default)

    def format(self, expression: str, default=None):
        """Open file and evaluate namespace format string"""
        return self.map.format_hdf(self.map.load_hdf(), expression, default=default)


class SpectraScan(Scan):
    """
    Scan with TEY and TFY spectra
    """
    def __init__(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        scan_names = {
            'energy': '(fastEnergy|pgm_energy|energye|energyh)',
            'monitor': '(C2|ca62sr|mcs16_data|mcse16_data|mcsh16_data)',
            'tey': '(C1|ca61sr|mcs17_data|mcse17_data|mcsh17_data)',
            'tfy': '(C3|ca63sr|mcs18_data|mcse18_data|mcsh18_data|mcsd18_data)'
        }
        metadata_names = {
                "scan": '{filename}',
                "cmd": '{(cmd|user_command|scan_command)}',
                "title": '{title}',
                "endstation": '{end_station}',
                "sample": '{sample_name}',
                "energy": '{np.mean((fastEnergy|pgm_energy|energye|energyh)):.2f} eV',
                "pol": '{polarisation?("lh")}',
                "height": '{(em_y|hfm_y):.2f}',
                "pitch": '{(em_pitch|hfm_pitch):.2f}',
                "temperature": '{(T_sample|sample_temperature|lakeshore336_cryostat' +
                               '|lakeshore336_sample|itc3_device_sensor_temp?(300)):.2f} K',
                "field": '{(field_z|sample_field|magnet_field|ips_demand_field?(0)):.2f} T',
            }
        super().__init__(filename, hdf_map, scan_names=scan_names, metadata_names=metadata_names)

        self.tey = ScanSpectra(self, self.scan_data['energy'], self.scan_data['tey'], self.scan_data['monitor'])
        self.tfy = ScanSpectra(self, self.scan_data['energy'], self.scan_data['tfy'], self.scan_data['monitor'])
        self.pol = self.metadata.get('pol', '')

    def __repr__(self):
        return f"SpectraScan('{os.path.basename(self.filename)}', pol={self.pol})"

    def __str__(self):
        out = self.__repr__() + '\n'
        out += f"  tey: {repr(self.tey)}\n"
        out += f"  tfy: {repr(self.tfy)}\n"
        out += '  Metadata:\n'
        out += '\n'.join(f"{name}: {val}" for name, val in self.metadata.items())
        return out

    def __add__(self, other):
        if isinstance(other, SpectraScan):
            return SummedSpectraScans(self, other)
        if isinstance(other, SummedSpectraScans):
            return SummedSpectraScans(*([self] + other.scans))
        raise TypeError(f"type {type(other)} cannot be added to Scan")

    def __sub__(self, other):
        if issubclass(type(other), SpectraScan):
            return SubtractPolarisations(self, other)
        if isinstance(other, SpectraScan):
            return SubtractPolarisations(self, other)
        raise TypeError(f"type {type(other)} cannot be subtracted from Scan")

    def create_figure(self):
        """Create plot of spectra"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6])
        fig.suptitle(self.metadata['title'])
        self.tey.plot(ax1, label='TEY')
        self.tfy.plot(ax2, label='TFY')

        ax1.set_xlabel('E [eV]')
        ax1.set_ylabel('TEY / monitor')
        ax2.set_xlabel('E [eV]')
        ax2.set_ylabel('TFY / monitor')


class ScanSpectra(Spectra):
    """
    Loading spectra from scan
    """
    def __init__(self, scan: Scan, energy, signal, monitor=1.0):
        self.scan = scan
        super().__init__(energy, signal / monitor)
        self.monitor = monitor

    def __repr__(self):
        return 'Scan' + super().__repr__()


class SummedSpectraScans:
    """
    Processing of multiple scans
    """
    def __init__(self, *scans: SpectraScan, **kwargs):
        self.scans = list(scans)
        self.tey = combine_spectra(*(s.tey for s in scans))
        self.tfy = combine_spectra(*(s.tfy for s in scans))
        self.metadata = kwargs

    def __repr__(self):
        return f"SummedScans({len(self.scans)} Scans)"

    def __str__(self):
        scan_str = '\n'.join(f"  {repr(scan)}" for scan in self.scans)
        return self.__repr__() + "\n" + scan_str

    def subtract_flat_background(self, ev_from_start=5.):
        tey = self.tey.subtract_flat_background(ev_from_start)
        tfy = self.tfy.subtract_flat_background(ev_from_start)
        return ProcessScans(self, tey, tfy, 'subtract flat background')

    def normalise_background(self, ev_from_start=5.):
        tey = self.tey.normalise_background(ev_from_start)
        tfy = self.tfy.normalise_background(ev_from_start)
        return ProcessScans(self, tey, tfy, 'normalise background')

    def fit_linear_background(self, ev_from_start=5.):
        tey = self.tey.fit_linear_background(ev_from_start)
        tfy = self.tfy.fit_linear_background(ev_from_start)
        return ProcessScans(self, tey, tfy, 'fit linear background')

    def fit_curve_background(self, ev_from_start=5.):
        tey = self.tey.fit_curve_background(ev_from_start)
        tfy = self.tfy.fit_curve_background(ev_from_start)
        return ProcessScans(self, tey, tfy, 'fit curved background')

    def fit_exp_background(self, ev_from_start=5.):
        tey = self.tey.fit_exp_background(ev_from_start)
        tfy = self.tfy.fit_exp_background(ev_from_start)
        return ProcessScans(self, tey, tfy, 'fit exp. background')

    def fit_exp_step(self, ev_from_start=5., ev_from_end=5.):
        tey = self.tey.fit_exp_step(ev_from_start, ev_from_end)
        tfy = self.tfy.fit_exp_step(ev_from_start, ev_from_end)
        return ProcessScans(self, tey, tfy, 'fit step')

    def fit_bkg_then_norm_to_peak(self, ev_from_start=5., ev_from_end=5.):
        tey = self.tey.fit_bkg_then_norm_to_peak(ev_from_start, ev_from_end)
        tfy = self.tfy.fit_bkg_then_norm_to_peak(ev_from_start, ev_from_end)
        return ProcessScans(self, tey, tfy, 'fit exp. background then norm. to peak')

    def fit_bkg_then_norm_to_jump(self, ev_from_start=5., ev_from_end=5.):
        tey = self.tey.fit_bkg_then_norm_to_jump(ev_from_start, ev_from_end)
        tfy = self.tfy.fit_bkg_then_norm_to_jump(ev_from_start, ev_from_end)
        return ProcessScans(self, tey, tfy, 'fit exp. background then norm. to jump')


class Process:
    """
    Container for process
    """
    def __init__(self, description: str, *parents: type(Scan), **metadata):
        self.parents = list(parents)
        self.description = description
        self.metadata = metadata

class SpectraProcess:
    """Container for Spectra Process"""
    def __init__(self, description: str, tey: ProcessedSpectra, tfy: ProcessedSpectra, *parents: type(Scan), **metadata):
        super().__init__(description, *parents, **metadata)
        self.tey = tey
        self.tfy = tfy
        self.pol = metadata.get('pol', '')


def create_spectra_scan(filename):
    scan_names = {
        'energy': '(fastEnergy|pgm_energy|energye|energyh)',
        'monitor': '(C2|ca62sr|mcs16_data|mcse16_data|mcsh16_data)',
        'tey': '(C1|ca61sr|mcs17_data|mcse17_data|mcsh17_data)',
        'tfy': '(C3|ca63sr|mcs18_data|mcse18_data|mcsh18_data|mcsd18_data)'
    }
    metadata_names = {
        "scan": '{filename}',
        "cmd": '{(cmd|user_command|scan_command)}',
        "title": '{title}',
        "endstation": '{end_station}',
        "sample": '{sample_name}',
        "energy": '{np.mean((fastEnergy|pgm_energy|energye|energyh)):.2f} eV',
        "pol": '{polarisation?("lh")}',
        "height": '{(em_y|hfm_y):.2f}',
        "pitch": '{(em_pitch|hfm_pitch):.2f}',
        "temperature": '{(T_sample|sample_temperature|lakeshore336_cryostat' +
                       '|lakeshore336_sample|itc3_device_sensor_temp?(300)):.2f} K',
        "field": '{(field_z|sample_field|magnet_field|ips_demand_field?(0)):.2f} T',
    }
    scan = Scan(filename, scan_names=scan_names, metadata_names=metadata_names)
    tey = ScanSpectra(scan, scan.scan_data['energy'], scan.scan_data['tey'], scan.scan_data['monitor'])
    tfy = ScanSpectra(scan, scan.scan_data['energy'], scan.scan_data['tfy'], scan.scan_data['monitor'])
    pol = scan.metadata.get('pol', '')
    return SpectraProcess('raw', tey, tfy, )


class ProcessScans:
    """
    Processing of multiple scans
    """
    def __init__(self, scan_obj: SpectraScan | SummedSpectraScans, tey: ProcessedSpectra, tfy: ProcessedSpectra, description: str):
        self.parent = scan_obj
        self.tey = tey
        self.tfy = tfy
        self.metadata = scan_obj.metadata
        self.process_description = description

    def __repr__(self):
        return f"Process{repr(self.parent)}"

    def __str__(self):
        out = self.__repr__() + '\n'
        out += f"  tey: {repr(self.tey)}\n"
        out += f"  tfy: {repr(self.tfy)}\n"
        out += '  Metadata:\n'
        out += '\n'.join(f"    {name}: {val}" for name, val in self.metadata.items())
        return out


def split_polarisations(*scans: SpectraScan) -> tuple[SummedSpectraScans, SummedSpectraScans]:
    """
    Split scans by polarisation
    """
    scans = list(scans)
    pols = [scan.pol for scan in scans]
    unique_pols = list(set(pols))
    if len(unique_pols) < 2:
        raise Exception('only 1 polarisation')
    elif len(unique_pols) > 2:
        print('Warning: other polarisations will be ignored')

    pol1, pol2 = unique_pols
    pol1_scans = SummedSpectraScans(*[scan for scan in scans if scan.pol == pol1], pol=pol1)
    pol2_scans = SummedSpectraScans(*[scan for scan in scans if scan.pol == pol2], pol=pol2)
    return pol1_scans, pol2_scans


class SubtractPolarisations:
    """
    Processing of multiple scans in different pol states
    """
    def __init__(self, pol1: SummedSpectraScans | ProcessScans, pol2: SummedSpectraScans | ProcessScans):

        self.pol1 = pol1.metadata['pol']
        self.pol2 = pol2.metadata['pol']
        self.pol1_scans = pol1
        self.pol2_scans = pol2

        self.tey = subtract_spectra(self.pol1_scans.tey, self.pol2_scans.tey)
        self.tfy = subtract_spectra(self.pol1_scans.tfy, self.pol2_scans.tfy)

    def title(self):
        process = self.pol1_scans.process_description if hasattr(self.pol1_scans, 'process_description') else 'normalised data'
        return f"{self.pol1} - {self.pol2}\n{process}"

    def create_figure(self):
        """Create plot of spectra"""
        fig, ax = plt.subplots(2, 2, figsize=[12, 8])
        fig.suptitle(self.title())

        self.pol1_scans.tey.plot(ax[0, 0], label=f"TEY {self.pol1}")
        self.pol2_scans.tey.plot(ax[0, 0], label=f"TEY {self.pol2}")
        self.pol1_scans.tfy.plot(ax[0, 1], label=f"TFY {self.pol1}")
        self.pol2_scans.tfy.plot(ax[0, 1], label=f"TFY {self.pol2}")

        self.tey.plot(ax[1, 0], label=f"TEY {self.pol1}-{self.pol2}")
        self.tfy.plot(ax[1, 1], label=f"TFY {self.pol1}-{self.pol2}")

        for _ax in ax.flatten():
            _ax.set_xlabel('E [eV]')
            # _ax.set_ylabel('signal / monitor')
            _ax.legend()
