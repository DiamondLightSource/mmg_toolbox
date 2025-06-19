"""
Spectra scan

=== DATA MODEL ===




Sn = Spectra(energy, signal, mode, process)
D = Scan(Sn, Sn, Metadata, processing_steps)

M = MultiScan(D, D, D, Metadata, processing_steps)
S = Subtraction(M1, M2)
"""
from __future__ import annotations

from inspect import signature
import inspect
from functools import wraps
from typing_extensions import Self
import datetime
import numpy as np
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import h5py

from mmg_toolbox import __version__
from mmg_toolbox.polarisation import pol_subtraction_label
import mmg_toolbox.spectra_analysis as spa
import mmg_toolbox.nexus_writer as nw


def get_func_doc(fn):
    sig = signature(fn)
    doc = next(iter(fn.__doc__.splitlines()), 'background function')
    args = ". args: " + ', '.join(str(par) for name, par in sig.parameters.items() if name not in ['energy', 'signal'])
    return doc + args

BACKGROUND_FUNCTIONS = {
    # description: (en, sig, *args, **kwargs) -> bkg, norm, fit
    'flat': spa.subtract_flat_background,  # ev_from_start
    'norm': spa.normalise_background,  # ev_from_start
    'linear': spa.fit_linear_background,  # ev_from_start
    'curve': spa.fit_curve_background,  # ev_from_start
    'exp': spa.fit_exp_background,  # ev_from_start, ev_from_end
    'step': spa.fit_step_background,  # ev_from_start
    'double_edge_step': spa.fit_double_edge_step_background,  # l3_energy, l2_energy, peak_width_ev
    'poly_edges': spa.fit_spectra_background, # *step_energies, peak_width_ev
    'exp_edges': spa.fit_spectra_exp_background, # *step_energies, peak_width_ev
}
BACKGROUND_DOCSTRINGS = {
    # name: next(iter(fn.__doc__.splitlines()), 'background function') for name, fn in BACKGROUND_FUNCTIONS.items()
    # name: f"{fn.__name__}{str(inspect.signature(fn))}" for name, fn in BACKGROUND_FUNCTIONS.items()
    name: get_func_doc(fn) for name, fn in BACKGROUND_FUNCTIONS.items()
}


class Spectra:
    """
    An energy spectra, containing:

    :param energy: n-length array
    :param signal: n-length array
    :param background: n-length array (*or None)
    :param parents: list of Spectra or Scan objects (*or None)
    :param mode: str name of the spectra for plots
    :param process_label: str label of the process
    :param process: str describing a process done to the spectra
    """
    def __init__(self, energy: np.ndarray, signal: np.ndarray,
                 background: np.ndarray | None = None,
                 parents: list[Self] | None = None,
                 mode: str = '', process_label: str = 'raw', process: str = ''):
        if parents is None:
            parents = []
        self.parents = parents
        self.energy = energy
        self.signal = signal
        if energy.shape != signal.shape:
            raise Exception(f"the shape of energy[{energy.shape}] and signal[{signal.shape}] must match")
        self.background = background
        if background is not None and background.shape != energy.shape:
            raise Exception(f"the shape of energy[{energy.shape}] and background[{background.shape}] must match")
        self.process_label = process_label
        self.process = process
        self.mode = mode

    """SPECTRA PROPERTIES"""

    def __repr__(self):
        return f"Spectra('{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}, process_label='{self.process_label}')"

    def edge_label(self, edges=spa.SEARCH_EDGES):
        return spa.energy_range_edge_label(self.energy.min(), self.energy.max(), search_edges=edges)

    def edges(self, search_edges=spa.SEARCH_EDGES):
        return spa.xray_edges_in_range(self.energy.min(), self.energy.max(), search_edges=search_edges)

    def signal_at_energy(self, energy1: float, energy2: float | None = None) -> float:
        """Return averaged signal between energy values"""
        idx1 = np.argmin(np.abs(self.energy - energy1))
        if energy2 is None:
            idx2 = idx1 + 1
        else:
            idx2 = np.argmin(np.abs(self.energy - energy2))
        return float(np.mean(self.signal[idx1:idx2]))

    def signal_peak(self) -> float:
        return np.max(abs(self.signal))

    def signal_jump(self, ev_from_start=5., ev_from_end=None) -> float:
        return spa.signal_jump(self.energy, self.signal, ev_from_start, ev_from_end)

    """SPECTRA OPERATIONS - RETURNS PROCESSED SPECTRA"""

    def __add__(self, other) -> Spectra:
        if issubclass(type(other), Spectra):
            return SpectraAverage(self, other)
        return Spectra(self.energy, self.signal + other, self.background, mode=self.mode,
                       parents=[self], process_label='add_value', process=f"{self.mode} + {other}")

    def __mul__(self, other) -> Spectra:
        if issubclass(type(other), Spectra):
            raise TypeError("Cannot multiply Spectra")
        return Spectra(self.energy, self.signal * other, self.background, mode=self.mode,
                       parents=[self], process_label='multiply', process=f'{self.mode} * {other}')

    def __sub__(self, other) -> Spectra:
        if other in self.parents:
            # remove other, recalculate average
            return SpectraAverage(*(parent for parent in self.parents if parent != other))
        if issubclass(type(other), Spectra):
            # subtract new spectra from this spectra
            return SpectraSubtraction(self, other)
        return Spectra(self.energy, self.signal - other, self.background, mode=self.mode,
                       parents=[self], process_label='subtract_value', process=f'{self.mode}-{other}')

    def divide_by_signal_at_energy(self, energy1: float, energy2: float | None = None) -> Spectra:
        """Divide spectra by signal"""
        value = self.signal_at_energy(energy1, energy2)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = "divide_by_signal_at_energy"
        process = f"normalise  to signal at energy between {energy1:.0f} and {energy2} eV\n"
        process += f"energy1 = {energy1}\n"
        process += f"energy2 = {energy2}\n"
        process += f"Spectra.signal_at_energy(energy1, energy2) = {value}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_preedge(self, ev_from_start: float = 5) -> Spectra:
        """Divide by average of raw_signals at start"""
        value = spa.preedge_signal(self.energy, self.signal, ev_from_start)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = 'divide_by_preedge'
        process = f"normalise signal to signal in the pre-edge region in first {ev_from_start} eV\n"
        process += f"mean(Spectra.signal[:{ev_from_start}]) = {value}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_postedge(self, ev_from_end: float = 5) -> Spectra:
        """Divide by average of raw_signals at start"""
        value = spa.postedge_signal(self.energy, self.signal, ev_from_end)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = 'divide_by_postedge'
        process = f"normalise signal to signal in the post-edge region in last {ev_from_end} eV\n"
        process += f"mean(Spectra.signal[:{ev_from_end} eV]) = {value}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    def norm_to_peak(self) -> Spectra:
        peak = self.signal_peak()
        sig = self.signal / peak
        bkg = self.background / peak if self.background is not None else None
        proc_label = 'norm_to_peak'
        process = f"normalise signal to the maximum peak height\n"
        process += f"max(Spectra.signal) = {peak}\n"
        process += f"Spectra.signal = signal / {peak:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    def norm_to_jump(self, ev_from_start=5., ev_from_end=None) -> Spectra:
        jump = abs(self.signal_jump(ev_from_start, ev_from_end))
        sig = self.signal / jump
        bkg = self.background / jump if self.background is not None else None
        proc_label = 'norm_to_jump'
        process = f"normalise signal to the jump in signal between start and end of spectra\n"
        process += f"ev_from_start = {ev_from_start}\n"
        process += f"ev_from_end = {ev_from_end}\n"
        process += f"jump(Spectra.signal) = {jump}\n"
        process += f"Spectra.signal = signal / {jump:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    def remove_background(self, name='flat', *args, **kwargs) -> Spectra:
        """
        Return new Spectra object with background removed
        """
        bkg_fun = BACKGROUND_FUNCTIONS[name]
        bkg_doc = BACKGROUND_DOCSTRINGS[name]
        bkg, norm, fit = bkg_fun(self.energy, self.signal, *args, **kwargs)
        sig = (self.signal - bkg) / norm
        proc_label = f"{name}"
        process = f"Background removal '{name}', using function: \n    {bkg_doc}\n"
        process += f"args: {str(args)}\n"
        process += f"kwargs: {str(kwargs)}\n"
        process += f"\nFit Report:\n{fit.fit_report() if fit is not None else 'None'}\n"
        process += f"\nResults:\n  <bkg> = {np.mean(bkg)}\n  norm = {norm}\nsignal = (signal - bkg) / norm\n"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)
    remove_background.__doc__ += (
            "available functions:\n" +
            '\n'.join(f"'{name}': {doc}" for name, doc in BACKGROUND_DOCSTRINGS.items())
    )

    def auto_edge_background(self, peak_width_ev: float = 5.) -> Spectra:
        """
        Remove generic xray absorption background from spectra
        """
        edges = self.edges()
        edge_energies = [energy for lbl, energy in edges]
        bkg, jump, fit = spa.fit_spectra_background(self.energy, self.signal, *edge_energies, peak_width_ev=peak_width_ev)
        sig = (self.signal - bkg) / jump
        proc_label = f"Auto_edge_background"
        process = f"Background removal 'poly_edges', using function: \n    {BACKGROUND_DOCSTRINGS['poly_edges']}\n"
        process += f"peak_width_ev = {peak_width_ev}\n"
        edge_str = '\n'.join(f"  {lbl}: {energy}" for lbl, energy in edges)
        process += f"Edges:\n {edge_str}"
        process += f"\nFit Report:\n{fit.fit_report() if fit is not None else 'None'}\n"
        process += f"\nResults:\n  <bkg> = {np.mean(bkg)}\n  norm = {jump}\nsignal = (signal - bkg) / norm\n"
        return Spectra(self.energy, sig, parents=[self], background=bkg,
                       process_label=proc_label, process=process, mode=self.mode)

    """SPECTRA NEXUS OUTPUT"""

    def create_nxnote(self, parent: h5py.Group, name: str, sequence_index: int | None = None) -> h5py.Group:
        note = nw.add_nxnote(
            root=parent,
            name=name,
            description=f"{self.mode} {self.process_label}",
            data=self.process,
            sequence_index=sequence_index
        )
        return note

    def create_nxdata(self, parent: h5py.Group, name: str, default: bool = False) -> h5py.Group:
        """NXxas NXdata entry, inlcuding energy, absorped beam and mode"""
        data = nw.add_nxdata(parent, name, axes=['energy'], signal='absorbed_beam')
        nw.add_nxfield(data, 'mode', self.mode)
        nw.add_nxfield(data, 'energy', self.energy, units='eV')
        nw.add_nxfield(data, 'absorbed_beam', self.signal, units='')
        if default:
            parent.attrs['default'] = name
        return data

    """SPECTRA PLOT FUNCTIONS"""

    def plot(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.mode} {self.process_label}"
        return ax.plot(self.energy, self.signal, *args, **kwargs)

    def plot_bkg(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        if self.background is None:
            return []
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.mode} {self.process_label} bkg"
        return ax.plot(self.energy, self.background, *args, **kwargs)

    def plot_parents(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        """Plot all parents on the current axes"""
        if ax is None:
            ax = plt.gca()
        pl = []
        label = kwargs.get('label', '')
        for parent in self.parents:
            if issubclass(type(parent), Spectra):
                kwargs['label'] = parent.mode + label
                pl += ax.plot(parent.energy, parent.signal, *args, **kwargs)
        return pl

    def create_figure(self) -> plt.Figure:
        """Create figure with spectra plot"""
        fig, ax1 = plt.subplots(1, 1)
        self.plot_parents(ax1)
        self.plot_bkg(ax1)
        self.plot(ax1)

        ax1.set_xlabel('E [eV]')
        ax1.set_ylabel('signal')
        ax1.legend()
        return fig


class SpectraSubtraction(Spectra):
    """Difference between two spectra"""

    def __init__(self, spectra1: Spectra, spectra2: Spectra):
        if spectra1.mode != spectra2.mode:
            raise ValueError('Spectra1 and spectra2 must have same mode')
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
        label = next((s.mode for s in parents))
        process_label = 'subtraction'
        process = "Subtraction of spectra S1 - S2:\n" + "\n".join(
            f'  S{n + 1}: ' + repr(s) for n, s in enumerate(parents))
        super().__init__(av_energy, difference, av_bkg, parents,
                         process_label=process_label, mode=label, process=process)

    def __repr__(self):
        return (
            f"SpectraSubtraction('{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}," +
            f"process_label='{self.process_label}')"
        )

    def average_subtracted_spectra(self):
        spectra1, spectra2 = self.parents
        average = spectra1 + spectra2
        return average

    def calculate_sum_rules(self, n_holes: float) -> tuple[float, float]:
        difference = self.signal
        average = self.average_subtracted_spectra().signal
        orb = spa.orbital_angular_momentum(self.energy, average, difference, n_holes)
        spin = spa.spin_angular_momentum(self.energy, average, difference, n_holes)
        return orb, spin

    def sum_rules_report(self, n_holes: float, element: str = '') -> str:
        orb, spin = self.calculate_sum_rules(n_holes)
        report = f"{element} n_holes = {n_holes}\nL = {orb:.3f} μB\nS = {spin:.3f} μB"
        return report

    def create_sum_rules_nxnote(self, n_holes: float, parent: h5py.Group,
                                name: str, sequence_index: int | None = None, element: str = '') -> h5py.Group:
        note = nw.add_nxnote(
            root=parent,
            name=name,
            description=f"{self.mode} {self.process_label} Sum Rules",
            data=self.sum_rules_report(n_holes, element),
            sequence_index=sequence_index
        )
        return note


class SpectraAverage(Spectra):
    """Averaged Spectra"""
    def __init__(self, *spectra: Spectra):
        mode = next(iter(s.mode for s in spectra if s.mode is not None), '')
        process_label = 'average'
        spectra = [s for s in spectra if s.mode == mode]
        # avoid average of average by using parents of previously averaged spectra
        parents = []
        for s in spectra:
            if len(s.parents) > 1:
                parents += s.parents
            else:
                parents.append(s)
        av_energy = spa.average_energy_scans(*(s.energy for s in parents))
        av_signal = spa.average_energy_spectra(av_energy, *((s.energy, s.signal) for s in parents))
        if all(s.background is None for s in parents):
            av_bkg = None
        else:
            bkg_spectra = ((s.energy, s.background) for s in parents if s.background is not None)
            av_bkg = spa.average_energy_spectra(av_energy, *bkg_spectra)
        label = next((s.mode for s in parents))
        process = "Average of spectra:\n" + "\n".join('  ' + repr(s) for s in parents)
        super().__init__(av_energy, av_signal, av_bkg, parents, mode=label,
                         process_label=process_label, process=process)

    def __repr__(self):
        return (
            f"SpectraAverage('{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}," +
            f"process_label='{self.process_label}')"
        )


class Metadata:
    filename: str = ''
    beamline: str = ''
    scan_no: int = 0
    start_date_iso: str = ''
    end_date_iso: str = ''
    cmd: str = ''
    pol: str = 'pc'
    sample_name: str = ''
    temp: float = 300
    mag_field: float = 0

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)

    def __str__(self):
        return str(self.__dict__)


class XasMetadata(Metadata):
    default_mode: str = 'tey'
    element: str = ''
    edge: str = ''
    energy: np.ndarray = np.arange(10)
    monitor: np.ndarray = np.ones(10)
    raw_signals: dict[str, np.ndarray] = {'tey': np.zeros(10)}


def spectra_method_decorator(target_cls):
    for name, method in inspect.getmembers(Spectra, predicate=inspect.isfunction):
        if name in ['divide_by_signal_at_energy', 'divide_by_preedge', 'divide_by_postedge', 'norm_to_peak',
                      'norm_to_jump', 'remove_background', 'auto_edge_background']:
            @wraps(method)
            def fn(self, *args, _method=method, **kwargs):
                self.parents = (self.copy(), *self.parents)
                self.spectra = {n: _method(s, *args, **kwargs) for n, s in self.spectra.items()}
                self.process_label = next(iter(self.spectra.values())).process_label
            setattr(target_cls, name, fn)

        elif name in ['create_nxnote', 'create_nxdata', 'plot', 'plot_bkg', 'plot_parents']:
            @wraps(method)
            def fn(self, *args, _method=method, **kwargs):
                return [_method(s, *args, **kwargs) for s in self.spectra.values()]
            setattr(target_cls, name, fn)

    return target_cls


@spectra_method_decorator
class SpectraContainer:
    """
    Container for Spectra and metadata
    """

    def __init__(self, name: str, spectra: dict[str, Spectra | SpectraSubtraction],
                 *parents: Self, metadata: XasMetadata = XasMetadata()):
        self.name = name
        self.process_label = next(iter(spectra.values())).process_label
        self.parents = parents
        self.spectra = spectra
        self.metadata = metadata

    def __repr__(self):
        return f"SpectraContainer('{self.name}', '{self.process_label}', {list(self.spectra)})"

    def __iter__(self):
        return self.spectra.__iter__()

    def __getitem__(self, item):
        return self.spectra[item]

    def __add__(self, other):
        if issubclass(type(other), SpectraContainer):
            # average Spectra
            spectra = {n: s + other.spectra[n] for n, s in self.spectra.items() if n in other.spectra}
        else:
            # add float or array to Spectra
            spectra = {n: s + other for n, s in self.spectra.items()}
        return SpectraContainer(self.name, spectra, self, *self.parents, metadata=self.metadata)

    def __sub__(self, other):
        if issubclass(type(other), SpectraContainer):
            # Subtract Spectra
            return SpectraContainerSubtraction(self, other)
        else:
            # Subtract float or array
            spectra = {n: s - other for n, s in self.spectra.items()}
            return SpectraContainer(self.name, spectra, self, *self.parents, metadata=self.metadata)

    def __mul__(self, other):
        if issubclass(type(other), SpectraContainer):
            raise Exception('Cannot multiply SpectraContainer')
        else:
            # multiply Spectra by float or array
            spectra = {n: s * other for n, s in self.spectra.items()}
            return SpectraContainer(self.name, spectra, self, *self.parents, metadata=self.metadata)

    def copy(self, name=None):
        """Create copy of spectra container using new name"""
        name = name or self.name
        return SpectraContainer(name, self.spectra, *self.parents, metadata=self.metadata)

    def label(self):
        # return f"{self.name} {self.process_label}"
        return self.process_label.replace('/', '').replace(' ', '')

    def analysis_steps(self):
        return {sc.label(): sc.spectra for sc in list(reversed(self.parents)) + [self]}

    def nx_entry(self, nexus: h5py.File, name='entry', default=True) -> h5py.Group:
        entry = nw.add_nxentry(nexus, name, definition='NXxas')
        nw.add_nxfield(entry, 'entry_identifier', self.metadata.scan_no)
        nw.add_nxfield(entry, 'start_time', self.metadata.start_date_iso)
        nw.add_nxfield(entry, 'end_time', self.metadata.end_date_iso)
        nw.add_nxfield(entry, 'scan_command', self.metadata.cmd)
        nw.add_nxfield(entry, 'mode', self.metadata.default_mode)
        nw.add_nxfield(entry, 'element', self.metadata.element)
        nw.add_nxfield(entry, 'edge', self.metadata.edge)
        if default:
            nexus.attrs['default'] = name
        return entry

    def nx_instrument(self, entry: h5py.Group) -> h5py.Group:
        energy = self.metadata.energy
        monitor = self.metadata.monitor
        raw_signals = self.metadata.raw_signals
        mode = self.metadata.default_mode

        instrument = nw.add_nxinstrument(root=entry, name='instrument', instrument_name=self.metadata.beamline)
        nw.add_nxsource(instrument, 'source')
        nw.add_nxmono(instrument, 'mono', energy_ev=energy)
        nw.add_nxdetector(instrument, 'incoming_beam', data=monitor)
        nw.add_nxdetector(instrument, 'absorbed_beam', data=raw_signals[mode])
        for name, signal in raw_signals.items():
            nw.add_nxdetector(instrument, name, data=signal)
        return instrument

    def nx_sample(self, entry: h5py.Group) -> h5py.Group:
        sample = nw.add_nxsample(
            root=entry,
            name='sample',
            sample_name=self.metadata.sample_name,
            chemical_formula='',
            temperature_k=self.metadata.temp,
            magnetic_field_t=self.metadata.mag_field,
            electric_field_v=0,
            mag_field_dir='z',
            electric_field_dir='z',
            sample_type='sample',
            description=''
        )
        energy = self.metadata.energy
        nw.add_nxbeam(
            root=sample,
            name='beam',
            incident_energy_ev=float(np.mean(energy)),
            polarisation_label=self.metadata.pol,
            beam_size_um=None
        )
        return sample

    def nx_process(self, entry: h5py.Group) -> h5py.Group:
        # NXprocess - read dat
        input_filename = self.metadata.filename
        if input_filename.endswith('.dat'):
            read_dat = nw.add_nxprocess(
                root=entry,
                name='read_dat',
                program='mmg_toolbox',
                version=__version__,
                date=str(datetime.datetime.now()),
                sequence_index=1,
            )
            nw.add_nxnote(
                root=read_dat,
                name='dat_file',
                data=open(input_filename, 'r').read(),
                filename=input_filename,
                description='DLS SRS format',
                sequence_index=1
            )

        # NXProcess
        process = nw.add_nxprocess(
            root=entry,
            name='process',
            program='mmg_toolbox',
            version=__version__,
            date=str(datetime.datetime.now()),
            sequence_index=2 if self.metadata.filename.endswith('.dat') else 1,
        )
        return process

    def nx_analysis_steps(self, entry: h5py.Group, process: h5py.Group):
        analysis_steps = self.analysis_steps()
        for n, (name, spectra) in enumerate(analysis_steps.items()):
            spectra[self.metadata.default_mode].create_nxnote(process, name, n + 1)

        # NXdata groups
        for name, spectra in analysis_steps.items():
            mode_spectra = spectra[self.metadata.default_mode]
            data = mode_spectra.create_nxdata(entry, name, default=True)
            aux_signals = []
            for signal, spec in spectra.items():
                nw.add_nxfield(data, signal, spec.signal, units='')
                aux_signals.append(signal)
                if spec.background is not None:
                    name = f"{signal}_background"
                    nw.add_nxfield(data, name, spec.background, units='')
                    aux_signals.append(name)
            data.attrs['auxiliary_signals'] = aux_signals

    def nx_main_entry(self, nexus: h5py.File, name='entry', default=True):
        entry = self.nx_entry(nexus, name=name, default=default)
        self.nx_instrument(entry)
        self.nx_sample(entry)
        process = self.nx_process(entry)
        self.nx_analysis_steps(entry, process)

    def _nx_add_items(self, nexus: h5py.File):
        nw.add_entry_links(nexus, self.metadata.filename)
        self.nx_main_entry(nexus)

    def write_nexus(self, nexus_filename: str):
        with h5py.File(nexus_filename, 'w') as nxs:
            self._nx_add_items(nxs)
        print(f'Created {nexus_filename}')

    def create_figure(self):
        fig, axs = plt.subplots(1, len(self.spectra))

        for ax, s in zip(axs, self.spectra.values()):
            s.plot(ax)
            ax.set_xlabel('E [eV]')
            ax.set_ylabel('signal')
            ax.legend()
        return fig


class SpectraContainerSubtraction(SpectraContainer):
    """Special sub-class for subtraction of SpectraContainers - XMCD and XMLD"""
    def __init__(self, spectra_container1: SpectraContainer, spectra_container2: SpectraContainer):
        # subtract each spectra in container
        spectra = {
            name: spectra - spectra_container2.spectra[name]
            for name, spectra in spectra_container1.spectra.items()
            if name in spectra_container2.spectra
        }
        # subtraction name
        if spectra_container1.metadata.pol != spectra_container2.metadata.pol:
            name = pol_subtraction_label(spectra_container1.metadata.pol)
            # rename parents (for display)
            spectra_container1 = spectra_container1.copy(spectra_container1.metadata.pol)
            spectra_container2 = spectra_container2.copy(spectra_container2.metadata.pol)
        else:
            name = 'subtraction'
        # subtraction metadata (merge these?)
        metadata = XasMetadata(**spectra_container1.metadata.__dict__)
        metadata.filename = ''
        super().__init__(name, spectra, spectra_container1, spectra_container2, metadata=metadata)

    def nx_sum_rules_process(self, entry: h5py.Group):
        process = nw.add_nxprocess(
            root=entry,
            name='sum_rules',
            program='mmg_toolbox',
            version=__version__,
            date=str(datetime.datetime.now()),
            sequence_index=2,
        )
        try:
            n_holes = spa.default_n_holes(self.metadata.element)
        except KeyError as ke:
            print(f"Warning: {ke}")
            n_holes = 1
        for n, (name, spectra) in enumerate(self.spectra.items()):
            spectra.create_sum_rules_nxnote(n_holes, process, name, n + 1, element=self.metadata.element)

    def _nx_add_items(self, nexus: h5py.File):
        for parent in self.parents:
            parent.nx_main_entry(nexus, name=parent.name, default=False)
        entry = self.nx_entry(nexus, name=self.name, default=True)
        self.nx_sample(entry)
        process = self.nx_process(entry)
        self.nx_sum_rules_process(entry)
        self.nx_analysis_steps(entry, process)



def average_polarised_scans(*scans: SpectraContainer) -> list[SpectraContainer]:
    """Find unique polarisations and average each scan at that polarisation"""
    pol_scans = {
        pol: [scan for scan in scans if scan.metadata.pol == pol]
        for pol in {scan.metadata.pol for scan in scans}
    }
    average_scans = {
        pol: sum(scan_list[1:], scan_list[0]) if len(scan_list) > 1 else scan_list[0]
        for pol, scan_list in pol_scans.items()
    }
    # rename containers
    for pol, scan in average_scans.items():
        scan.name = pol
        for spectra in scan.spectra.values():
            spectra.process_label += f"_{pol}"
    return list(average_scans.values())

