"""
Spectra scan
"""
from __future__ import annotations

import os
from typing_extensions import Self
import numpy as np
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import h5py
import hdfmap

import mmg_toolbox.spectra_analysis as spa
from .nexus_writer import create_xmcd_nexus
from .data_scan import Scan, Process


BACKGROUND_FUNCTIONS = {
    # description: (en, sig, *args, **kwargs) -> spectra, bkg
    'flat': spa.subtract_flat_background,  # ev_from_start
    'norm': spa.normalise_background,  # ev_from_start
    'linear': spa.fit_linear_background,  # ev_from_start
    'curve': spa.fit_curve_background,  # ev_from_start
    'exp': spa.fit_exp_background,  # ev_from_start, ev_from_end
    'step': spa.fit_step_background,  # ev_from_start
    'double_edge_step': spa.fit_double_edge_step_background,  # l3_energy, l2_energy, peak_width_ev
    'poly_double_edge': spa.fit_poly_double_edge_step_background,  # l3_energy, l2_energy, peak_width_ev
}


def get_xas_group(nxs: h5py.File) -> h5py.Group | None:
    """Return an open HDF group object, or None if it doesn't exist"""
    entry = next(group for path, group in nxs.items() if group.attrs.get('NX_class', b'') == b'NXentry')
    nx_xas = next((
        group for path, group in entry.items()
        if group.attrs.get('NX_class', b'') == b'NXsubentry'
           and group.get('definition').asstr()[()] == 'NXxas'
    ), None)
    return nx_xas


def is_nxxas(filename: str):
    """Returns True is scan contains NXXas subentry, False otherwise"""
    if os.path.isfile(filename):
        with hdfmap.load_hdf(filename) as nxs:
            nx_xas = get_xas_group(nxs)
            if nx_xas:
                return True
    return False


class Spectra:
    """
    An energy spectra, containing:

    :param energy: n-length array
    :param signal: n-length array
    :param background: n-length array (*or None)
    :param parents: list of Spectra or Scan objects (*or None)
    :param process: str describing a process done to the spectra
    :param label: str name of the spectra for plots
    """
    def __init__(self, energy: np.ndarray, signal: np.ndarray,
                 background: np.ndarray | None = None,
                 parents: list[Self | Scan] | None = None,
                 process: str = 'raw', label: str = ''):
        self.parents = parents
        self.energy = energy
        self.signal = signal
        if energy.shape != signal.shape:
            raise Exception(f"the shape of energy[{energy.shape}] and signal[{signal.shape}] must match")
        self.background = background
        if background is not None and background.shape != energy.shape:
            raise Exception(f"the shape of energy[{energy.shape}] and background[{background.shape}] must match")
        self.process = process
        self.label = label

    def __repr__(self):
        return f"Spectra('{self.label}', energy=array{self.energy.shape}, signal=array{self.signal.shape}, process={self.process})"

    def __add__(self, other):
        return average_spectra(self, other)

    def __sub__(self, other):
        if other in self.parents:
            # remove other, recalculate average
            return average_spectra(*(parent for parent in self.parents if parent != other))
        # subtract new spectra from this spectra
        return subtract_spectra(self, other)

    def signal_at_energy(self, energy1: float, energy2: float | None = None) -> float:
        """Return averaged signal between energy values"""
        idx1 = np.argmin(np.abs(self.energy - energy1))
        if energy2 is None:
            idx2 = idx1 + 1
        else:
            idx2 = np.argmin(np.abs(self.energy - energy2))
        return float(np.mean(self.signal[idx1:idx2]))

    def divide_by_signal_at_energy(self, energy1: float, energy2: float | None = None) -> Spectra:
        """Divide spectra by signal"""
        value = self.signal_at_energy(energy1, energy2)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc = f'norm to {energy1:.0f} eV'
        return Spectra(self.energy, sig, parents=[self], background=bkg, process=proc, label=self.label)

    def divide_by_preedge(self, ev_from_start: float):
        """Divide by average of signals at start"""
        value = spa.preedge_signal(self.energy, self.signal, ev_from_start)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc = f'norm to pre-edge'
        return Spectra(self.energy, sig, parents=[self], background=bkg, process=proc, label=self.label)

    def divide_by_postedge(self, ev_from_end: float):
        """Divide by average of signals at start"""
        value = spa.postedge_signal(self.energy, self.signal, ev_from_end)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc = f'norm to post-edge'
        return Spectra(self.energy, sig, parents=[self], background=bkg, process=proc, label=self.label)

    def remove_background(self, name='flat', *args, **kwargs) -> Spectra:
        sig, bkg = BACKGROUND_FUNCTIONS[name](self.energy, self.signal, *args, **kwargs)
        return Spectra(self.energy, sig, parents=[self], background=bkg, process=name, label=self.label)

    def norm_to_peak(self) -> Spectra:
        peak = self.signal_peak()
        bkg = self.background / peak if self.background is not None else None
        return Spectra(self.energy, self.signal / peak,
                       parents=[self], background=bkg, process='norm to peak', label=self.label)

    def norm_to_jump(self, ev_from_start=5., ev_from_end=None) -> Spectra:
        jump = abs(self.signal_jump(ev_from_start, ev_from_end))
        bkg = self.background / jump if self.background is not None else None
        return Spectra(self.energy, self.signal / jump,
                       parents=[self], background=bkg, process='norm to jump', label=self.label)

    def signal_peak(self) -> float:
        return np.max(abs(self.signal))

    def signal_jump(self, ev_from_start=5., ev_from_end=None) -> float:
        return spa.signal_jump(self.energy, self.signal, ev_from_start, ev_from_end)

    def plot(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.label} {self.process}"
        return ax.plot(self.energy, self.signal, *args, **kwargs)

    def plot_bkg(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        if self.background is None:
            return []
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.label} {self.process} bkg"
        return ax.plot(self.energy, self.background, *args, **kwargs)

    def plot_parents(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        """Plot all parents on the current axes"""
        if ax is None:
            ax = plt.gca()
        pl = []
        label = kwargs.get('label', '')
        for parent in self.parents:
            if issubclass(type(parent), Spectra):
                kwargs['label'] = parent.label + label
                pl += ax.plot(parent.energy, parent.signal, *args, **kwargs)
        return pl

    def create_figure(self) -> plt.Figure:
        """Create figure with spectra plot"""
        fig, ax1 = plt.subplots(1, 1)
        print(self.label)
        self.plot_parents(ax1)
        self.plot_bkg(ax1)
        self.plot(ax1)

        ax1.set_xlabel('E [eV]')
        ax1.set_ylabel('signal')
        ax1.legend()
        return fig


def xas_process(spectra: Spectra, ev_from_start=5., ev_from_end=None) -> Spectra:
    """
    1. interpolate energy, signals
    2. divide by average of pre-edge signal
    3. divide each signal by linear background of pre-edge, subtract 1
    5. divide by average of pos-edge signal
    6. create a step-function with steps at defined L2 and L3 position.
    7. Subtract step-function from signal
    """
    # 1. interpolate - done beforehand
    # 2. divide by pre-edge
    spectra2 = spectra.divide_by_preedge(ev_from_start)
    # 3. divide by pre-edge linear background
    spectra3 = spectra2.remove_background('linear', ev_from_start=ev_from_start)
    # 4. divide by post-edge
    spectra4 = spectra3.divide_by_postedge(ev_from_end)
    # 5. subtract double-step function




def average_spectra(*spectra: Spectra) -> Spectra:
    """Average multiple spectra"""
    if any(isinstance(p, Spectra) for s in spectra for p in s.parents):
        print('Warning - average of average')
    parents = list(spectra)
    av_energy = spa.average_energy_scans(*(s.energy for s in spectra))
    av_signal = spa.average_energy_spectra(av_energy, *((s.energy, s.signal) for s in spectra))
    if all(s.background is None for s in parents):
        av_bkg = None
    else:
        bkg_spectra = ((s.energy, s.background) for s in parents if s.background is not None)
        av_bkg = spa.average_energy_spectra(av_energy, *bkg_spectra)
    label = next((s.label for s in spectra), '')
    return Spectra(av_energy, av_signal, av_bkg, parents, process='average', label=label)


def subtract_spectra(spectra1, spectra2) -> Spectra:
    """Subtract spectra2 from spectra1"""
    parents = [spectra1, spectra2]
    av_energy = spa.average_energy_scans(spectra1.energy, spectra2.energy)
    signal1 = spa.average_energy_spectra(av_energy, (spectra1.energy, spectra1.signal))
    signal2 = spa.average_energy_spectra(av_energy, (spectra2.energy, spectra2.signal))
    if all(s.background is None for s in parents):
        av_bkg = None
    else:
        bkg_spectra = ((s.energy, s.background) for s in parents if s.background is not None)
        av_bkg = spa.average_energy_spectra(av_energy, *bkg_spectra)
    difference = signal1 - signal2
    label = f"{spectra1.label} - {spectra2.label}"
    return Spectra(av_energy, difference, av_bkg, parents, process='subtraction', label=label)


class _SpectraContainer:
    metadata = {}
    def __init__(self, tey: Spectra, tfy: Spectra, pol: str, **metadata):
        self.tey = tey
        self.tfy = tfy
        self.pol = pol
        self.metadata.update(metadata)

    def __add__(self, other):
        if issubclass(type(other), _SpectraContainer):
            if self.pol != other.pol:
                raise Exception("Polarisations do not match")
            tey = self.tey + other.tey
            tfy = self.tfy + other.tfy
            return SpectraProcess('average', tey, tfy, self, other, pol=self.pol)
        raise TypeError(f"type {type(other)} cannot be added to {type(self)}")

    def __sub__(self, other):
        if issubclass(type(other), _SpectraContainer):
            return SpectraDifference(self, other)
        raise TypeError(f"type {type(other)} cannot be subtracted from {type(self)}")

    def remove_background(self, name='flat', *args, **kwargs) -> SpectraProcess:
        tey = self.tey.remove_background(name, *args, **kwargs)
        tfy = self.tfy.remove_background(name, *args, **kwargs)
        return SpectraProcess(name, tey, tfy, self, pol=self.pol)

    def norm_to_peak(self) -> SpectraProcess:
        tey = self.tey.norm_to_peak()
        tfy = self.tfy.norm_to_peak()
        return SpectraProcess('norm to peak', tey, tfy, self, pol=self.pol)

    def norm_to_jump(self, ev_from_start=5., ev_from_end=None) -> SpectraProcess:
        tey = self.tey.norm_to_jump(ev_from_start, ev_from_end)
        tfy = self.tfy.norm_to_jump(ev_from_start, ev_from_end)
        return SpectraProcess('norm to jump', tey, tfy, self, pol=self.pol)

    def create_figure(self, title: str | None = None):
        """Create plot of spectra"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6])
        if title is None:
            title = self.metadata.get('title', self.pol)
        fig.suptitle(title)
        self.tey.plot(ax1)
        self.tfy.plot(ax2)

        ax1.set_xlabel('E [eV]')
        ax1.set_ylabel('TEY / monitor')
        ax2.set_xlabel('E [eV]')
        ax2.set_ylabel('TFY / monitor')


class SpectraScan(Scan, _SpectraContainer):
    """
    Scan with TEY and TFY spectra
    """
    def __init__(self, filename: str, hdf_map: hdfmap.NexusMap | None = None):
        scan_names = {
            'energy': '(fastEnergy|pgm_energy|energye|energyh)',
            # 'monitor': '(C2|ca62sr|mcs16_data|mcse16_data|mcsh16_data?(1.0))',
            'monitor': '(C2|ca62sr|mcs16|macr16|mcse16|macj316|mcsh16|macj216?(1.0))',
            # 'tey': '(C1|ca61sr|mcs17_data|mcse17_data|mcsh17_data)',
            # 'tfy': '(C3|ca63sr|mcs18_data|mcse18_data|mcsh18_data|mcsd18_data)'
            'tey': '(C1|ca61sr|mcs17|macr17|mcse17|macj317|mcsh17|macj217)',
            'tfy': '(C3|ca63sr|mcs18|macr18|mcse18|macj318|mcsh18|macaj218)',
        }
        metadata_names = {
            "scan": '{filename}',
            "cmd": '{(cmd|user_command|scan_command)}',
            "title": '{title}',
            "endstation": '{end_station}',
            "sample": '{sample_name}',
            "pol": '{polarisation?("lh")}',
            "temperature": '{(T_sample|sample_temperature|lakeshore336_cryostat' +
                           '|lakeshore336_sample|itc3_device_sensor_temp?(300)):.2f} K',
            "field": '{(field_z|sample_field|magnet_field|ips_demand_field?(0)):.2f} T',
            'field_x': 'field_x?(0)',
            'field_y': 'field_y?(0)',
            'field_z': '(magnet_field|ips_demand_field|field_z?(0))',
        }
        Scan.__init__(self, filename, hdf_map, scan_names=scan_names, metadata_names=metadata_names)
        # if 'xas_entry' not in self.map.classes:
        #     raise Exception(f"{self.filename} does not include NXSubEntry 'xas_entry'")
        tey_norm = self.scan_data['tey'] / self.scan_data['monitor']
        tfy_norm = self.scan_data['tfy'] / self.scan_data['monitor']
        pol = self.metadata.get('pol', '')
        tey = Spectra(self.scan_data['energy'], tey_norm, parents=[self], label=f"{self.scan_number} {pol} tey")
        tfy = Spectra(self.scan_data['energy'], tfy_norm, parents=[self], label=f"{self.scan_number} {pol} tfy")
        _SpectraContainer.__init__(self, tey=tey, tfy=tfy, pol=pol)

    def __repr__(self):
        return f"SpectraScan<{self.scan_number}, pol='{self.pol}')>"

    def __str__(self):
        out = self.__repr__() + '\n'
        out += f"  tey: {repr(self.tey)}\n"
        out += f"  tfy: {repr(self.tfy)}\n"
        out += '  Metadata:\n'
        out += '\n'.join(f"   {name}: {val}" for name, val in self.metadata.items())
        return out


class SpectraProcess(Process, _SpectraContainer):
    """Container for Spectra Process"""
    def __init__(self, description: str, tey: Spectra, tfy: Spectra, *parents: _SpectraContainer, **metadata):
        Process.__init__(self, description, *parents)
        _SpectraContainer.__init__(self, tey, tfy, metadata.get('pol', ''))

    def __repr__(self):
        return f"SpectraProcess('{self.description}', " + str(self.parents) + ')'

    def create_figure(self, title: str | None = None):
        """Create plot of spectra"""
        if title is None:
            title = self.description
        super().create_figure(title)


class SpectraDifference(SpectraProcess):
    """Specific SpectraProcess for difference between two Spectra"""
    def __init__(self, spectra1: _SpectraContainer, spectra2: _SpectraContainer):
        if spectra1.pol == spectra2.pol:
            raise Exception("Polarisations must be different")
        tey = subtract_spectra(spectra1.tey, spectra2.tey)
        tfy = subtract_spectra(spectra1.tfy, spectra2.tfy)
        pol = f"{spectra1.pol} - {spectra2.pol}"
        if 'pc' in pol:
            process = 'XMCD'
        elif 'lh' in pol:
            process = 'XMLD'
        else:
            process = pol
        super().__init__(process, tey, tfy, spectra1, spectra2, pol=pol)

        self.spectra1 = spectra1
        self.spectra2 = spectra2

    def create_figure(self, title: str | None = None):
        """Create plot of spectra"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[12, 6], dpi=60)
        if title is None:
            title = self.description
        fig.suptitle(title)

        self.spectra1.tey.plot_parents(ax1)
        self.spectra2.tey.plot_parents(ax1)
        self.tey.plot(ax1)

        self.spectra1.tey.plot_parents(ax2)
        self.spectra2.tey.plot_parents(ax2)
        self.tey.plot(ax2)

        ax1.set_xlabel('E [eV]')
        ax1.set_ylabel('TEY / monitor')
        ax2.set_xlabel('E [eV]')
        ax2.set_ylabel('TFY / monitor')
        ax1.legend()
        ax2.legend()

    def write_nexus(self, filename: str):
        """Create nexus file"""
        create_xmcd_nexus(
            filename=filename,
            scan_files=[],
            energy=self.tey.energy,
            pol1=self.spectra1.tey.signal,
            pol2=self.spectra2.tey.signal,
            xmcd=self.tey.signal,
            details=f'TEY {self.description}'
        )


def find_pol_pairs(*scans: SpectraScan):
    """Find pairs of scans with opposite polarisations"""
    pols = list(set(scan.pol for scan in scans))
    if len(pols) < 2:
        raise Exception('Not enough polarisations!')
    pol1_scans = [scan for scan in scans if scan.pol == pols[0]]
    pol2_scans = [scan for scan in scans if scan.pol == pols[1]]
    return [SpectraDifference(scan1, scan2) for scan1, scan2 in zip(pol1_scans, pol2_scans)]

