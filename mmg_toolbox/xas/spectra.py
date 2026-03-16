"""
Spectra object

=== DATA MODEL ===
spectra = Spectra(energy, signal, mode, process)
spectra2 = spectra + 2  # adds 2 to signal
spectra3 = spectra.norm_to_peak()
average_spectra = spectra2 + spectra3  # averages spectra signals at interpolated energies
subtracted_spectra = spectra2 - spectra3  # subtracts signals at interpolated energies
"""
from __future__ import annotations

from inspect import signature
import numpy as np
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import h5py

from mmg_toolbox.nexus import nexus_writer as nw
from mmg_toolbox.xas import spectra_analysis as spa


# Build database of spectra functions from spectra_analysis.py
# these will be called by Spectra.remove_background
def get_func_doc(fn):
    sig = signature(fn)
    doc = next(iter(ln for ln in fn.__doc__.splitlines() if ln), 'background function')
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
                 parents: list['Spectra'] | None = None, label: str = '',
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
        self.label = label
        self.process_label = process_label
        self.process = process
        self.mode = mode

    """SPECTRA PROPERTIES"""

    def __repr__(self):
        return f"Spectra('{self.label}', '{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}, process_label='{self.process_label}')"

    def edge_label(self, edges=spa.SEARCH_EDGES) -> tuple[str, str]:
        return spa.energy_range_edge_label(self.energy.min(), self.energy.max(), search_edges=edges)

    def edges(self, search_edges: list[str] | None = spa.SEARCH_EDGES) -> dict[str, float]:
        return spa.xray_edges_in_range(self.energy.min(), self.energy.max(), search_edges=search_edges)

    def energy_index(self, energy: float) -> int:
        """Return the array index closes to the energy value"""
        return int(np.argmin(np.abs(self.energy - energy)))

    def signal_at_energy(self, energy1: float, energy2: float | None = None) -> float:
        """Return averaged signal between energy values"""
        idx1 = self.energy_index(energy1)
        if energy2 is None:
            idx2 = idx1 + 1
        else:
            idx2 = self.energy_index(energy2)
        return float(np.mean(self.signal[idx1:idx2]))

    def signal_peak(self) -> float:
        return np.max(abs(self.signal))

    def signal_jump(self, ev_from_start=5., ev_from_end=None) -> float:
        return spa.signal_jump(self.energy, self.signal, ev_from_start, ev_from_end)

    """SPECTRA OPERATIONS - RETURNS PROCESSED SPECTRA"""

    def __add__(self, other) -> Spectra:
        if issubclass(type(other), Spectra):
            return SpectraAverage(self, other)
        return Spectra(self.energy, self.signal + other, self.background, mode=self.mode, label=self.label,
                       parents=[self], process_label='add_value', process=f"{self.mode} + {other}")

    def __mul__(self, other) -> Spectra:
        if issubclass(type(other), Spectra):
            raise TypeError("Cannot multiply Spectra")
        return Spectra(self.energy, self.signal * other, self.background, mode=self.mode, label=self.label,
                       parents=[self], process_label='multiply', process=f'{self.mode} * {other}')

    def __sub__(self, other) -> Spectra:
        if other in self.parents:
            # remove other, recalculate average
            return SpectraAverage(*(parent for parent in self.parents if parent != other))
        if issubclass(type(other), Spectra):
            # subtract new spectra from this spectra
            return SpectraSubtraction(self, other)
        return Spectra(self.energy, self.signal - other, self.background, mode=self.mode, label=self.label,
                       parents=[self], process_label='subtract_value', process=f'{self.mode}-{other}')

    def trim(self, ev_from_start=5., ev_from_end=None) -> Spectra:
        """Trim spectra between energies"""
        en1 = float(self.energy[0] + ev_from_start)
        en2 = float(self.energy[-1] - (ev_from_end or 0))
        index1 = self.energy_index(en1)
        index2 = self.energy_index(en2)
        s = slice(index1, index2 + 1)
        en = self.energy[s]
        sig = self.signal[s]
        bkg = self.background[s] if self.background is not None else None
        proc_label = "trim"
        process = f"trip spectra between {en1:.2f} and {en2:.2f} eV\n"
        process += f"Spectra.energy = energy[{index1}:{index2}]\n"
        process += f"Spectra.signal = signal[{index1}:{index2}]\n"
        return Spectra(en, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_signal_at_energy(self, energy1: float, energy2: float | None = None) -> Spectra:
        """Divide spectra by signal"""
        value = self.signal_at_energy(energy1, energy2)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = "divide_by_signal_at_energy"
        process = f"normalise  to signal at energy between {energy1:.0f} and {energy2} eV\n"
        process += f"energy1 = {energy1}\n"
        process += f"energy2 = {energy2}\n"
        process += f"Spectra.signal_at_energy(energy1, energy2) = {value:.3f}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_preedge(self, ev_from_start: float = 5) -> Spectra:
        """Divide by average of raw_signals at start"""
        value = spa.preedge_signal(self.energy, self.signal, ev_from_start)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = 'divide_by_preedge'
        process = f"normalise signal to signal in the pre-edge region in first {ev_from_start} eV\n"
        process += f"mean(Spectra.signal[:{ev_from_start}]) = {value:.3f}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_postedge(self, ev_from_end: float = 5) -> Spectra:
        """Divide by average of raw_signals at end"""
        value = spa.postedge_signal(self.energy, self.signal, ev_from_end)
        sig = self.signal / value
        bkg = self.background / value if self.background is not None else None
        proc_label = 'divide_by_postedge'
        process = f"normalise signal to signal in the post-edge region in last {ev_from_end} eV\n"
        process += f"mean(Spectra.signal[:{ev_from_end} eV]) = {value:.3f}\n"
        process += f"Spectra.signal = signal / {value:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_peak(self) -> Spectra:
        """Divide by peak height [max(abs(signal))]"""
        peak = self.signal_peak()
        sig = self.signal / peak
        bkg = self.background / peak if self.background is not None else None
        proc_label = 'norm_to_peak'
        process = f"normalise signal to the maximum peak height\n"
        process += f"max(Spectra.signal) = {peak:.3f}\n"
        process += f"Spectra.signal = signal / {peak:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_jump(self, ev_from_start=5., ev_from_end=None) -> Spectra:
        """Divide by the jump between start and end of spectra"""
        jump = abs(self.signal_jump(ev_from_start, ev_from_end))
        sig = self.signal / jump
        bkg = self.background / jump if self.background is not None else None
        proc_label = 'norm_to_jump'
        process = f"normalise signal to the jump in signal between start and end of spectra\n"
        process += f"ev_from_start = {ev_from_start}\n"
        process += f"ev_from_end = {ev_from_end}\n"
        process += f"jump(Spectra.signal) = {jump:.3f}\n"
        process += f"Spectra.signal = signal / {jump:.3f}"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)

    def divide_by_background(self, name='flat', *args, **kwargs) -> Spectra:
        """
        Return new Spectra object with signal divided by a particular background
        """
        bkg_fun = BACKGROUND_FUNCTIONS[name]
        bkg_doc = BACKGROUND_DOCSTRINGS[name]
        bkg, norm, fit = bkg_fun(self.energy, self.signal, *args, **kwargs)
        sig = self.signal / bkg
        proc_label = f"{name}"
        process = f"Background normalisation '{name}', using function: \n {bkg_fun.__name__}: {bkg_doc}\n"
        process += f"args: {str(args)}\n"
        process += f"kwargs: {str(kwargs)}\n"
        process += f"\nFit Report:\n{fit.fit_report() if fit is not None else 'None'}\n"
        process += f"\nResults:\n <bkg> = {np.mean(bkg):.3f}{bkg.shape}\nsignal = signal / bkg\n"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)
    divide_by_background.__doc__ += (
            "available functions:\n" +
            '\n'.join(f"'{name}': {doc}" for name, doc in BACKGROUND_DOCSTRINGS.items())
    )

    def remove_background(self, name='flat', *args, **kwargs) -> Spectra:
        """
        Return new Spectra object with background removed
        """
        bkg_fun = BACKGROUND_FUNCTIONS[name]
        bkg_doc = BACKGROUND_DOCSTRINGS[name]
        bkg, norm, fit = bkg_fun(self.energy, self.signal, *args, **kwargs)
        sig = (self.signal - bkg) / norm
        proc_label = f"{name}"
        process = f"Background removal '{name}', using function: \n {bkg_fun.__name__}: {bkg_doc}\n"
        process += f"args: {str(args)}\n"
        process += f"kwargs: {str(kwargs)}\n"
        process += f"\nFit Report:\n{fit.fit_report() if fit is not None else 'None'}\n"
        process += f"\nResults:\n <bkg> = {np.mean(bkg):.3f}\n  norm = {norm:.3f}\nsignal = (signal - bkg) / norm\n"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
                       process_label=proc_label, process=process, mode=self.mode)
    remove_background.__doc__ += (
            "available functions:\n" +
            '\n'.join(f"'{name}': {doc}" for name, doc in BACKGROUND_DOCSTRINGS.items())
    )

    def auto_edge_background(self, peak_width_ev: float = 5., edges: dict[str, float] | None = None) -> Spectra:
        """
        Remove generic xray absorption background from spectra
        """
        if edges is None:
            edges = self.edges()
        edge_energies = edges.values()
        bkg, jump, fit = spa.fit_spectra_background(self.energy, self.signal, *edge_energies, peak_width_ev=peak_width_ev)
        sig = (self.signal - bkg) / jump
        proc_label = f"Auto_edge_background"
        process = f"Background removal 'poly_edges': \n {BACKGROUND_DOCSTRINGS['poly_edges']}\n"
        process += f"peak_width_ev = {peak_width_ev}\n"
        edge_str = '\n'.join(f"  {lbl}: {energy}" for lbl, energy in edges.items())
        process += f"Edges:\n {edge_str}"
        process += f"\nFit Report:\n{fit.fit_report() if fit is not None else 'None'}\n"
        process += f"\nResults:\n  <bkg> = {np.mean(bkg)}\n  norm = {jump}\nsignal = (signal - bkg) / norm\n"
        return Spectra(self.energy, sig, parents=[self], background=bkg, label=self.label,
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

    def write_csv(self, csv_filename: str, header: str = ''):
        """Write spectra to csv file"""
        header = header + "\n" if header else ""
        header += f"{self.label} {self.mode} process='{self.process_label}'\nenergy [eV], signal"
        array = self.energy, self.signal
        np.savetxt(csv_filename, array, delimiter=',', header=header)
        print(f"Saved {csv_filename}")


    """SPECTRA PLOT FUNCTIONS"""

    def plot(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        """
        Plot spectra as line on current axes

            spectra.plot()

        :param ax: Matplotlib axes object or None to use plt.gca()
        :param args: args to pass to ax.plot()
        :param kwargs: kwargs to pass to ax.plot()
        :return: list of Line2D objects
        """
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.label} {self.mode} {self.process_label}"
        return ax.plot(self.energy, self.signal, *args, **kwargs)

    def plot_bkg(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        """
        Plot spectra background as line on current axes

            spectra.plot_bkg()

        :param ax: Matplotlib axes object or None to use plt.gca()
        :param args: args to pass to ax.plot()
        :param kwargs: kwargs to pass to ax.plot()
        :return: list of Line2D objects
        """
        if self.background is None:
            return []
        if ax is None:
            ax = plt.gca()
        if 'label' not in kwargs:
            kwargs['label'] = f"{self.label} {self.mode} {self.process_label} bkg"
        return ax.plot(self.energy, self.background, *args, **kwargs)

    def plot_parents(self, ax: Axes | None = None, *args, **kwargs) -> list[plt.Line2D]:
        """
        Plot all parents on the current axes

            spectra.plot_parents()

        :param ax: Matplotlib axes object or None to use plt.gca()
        :param args: args to pass to ax.plot()
        :param kwargs: kwargs to pass to ax.plot()
        :return: list of Line2D objects
        """
        if ax is None:
            ax = plt.gca()
        pl = []
        label = kwargs.get('label', '')
        for parent in self.parents:
            if issubclass(type(parent), Spectra):
                kwargs['label'] = f"{label} {self.label} {self.mode} {self.process_label}".strip()
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
        label = f"{spectra1.label} - {spectra2.label}"
        mode = next((s.mode for s in parents))
        process_label = 'subtraction'
        process = "Subtraction of spectra S1 - S2:\n" + "\n".join(
            f'  S{n + 1}: ' + repr(s) for n, s in enumerate(parents))
        super().__init__(av_energy, difference, av_bkg, parents, label=label,
                         process_label=process_label, mode=mode, process=process)

    def __repr__(self):
        return (
            f"SpectraSubtraction('{self.label}', '{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}," +
            f"process_label='{self.process_label}')"
        )

    def average_subtracted_spectra(self) -> Spectra:
        spectra1, spectra2 = self.parents
        average = spectra1 + spectra2
        return average

    def get_split_energy(self, edges: dict[str, float] | None = None) -> float:
        """return the energy half-way between two edges"""
        if edges is None:
            edges = self.edges()
        if len(edges) != 2:
            raise ValueError('edges must have length 2')
        return sum(edges.values()) / len(edges)

    def calculate_sum_rules(self, n_holes: float, split_energy: float | None = None,
                            edges: dict[str, float] | None = None) -> tuple[float, float]:
        """
        Calculate sum rules of XMCD spectra from integration

            orb, spin = spectra.calculate_sum_rules(n_holes)

        Parameters
        :param n_holes: number of holes in absorbing ion
        :param split_energy: energy half-way between two edges
        :param edges: dictionary of edges
        :returns: (orbital, spin) sum rule values
        """
        energy = self.energy
        difference = self.signal
        average = self.average_subtracted_spectra().signal
        if len(average) != len(energy):
            min_len = min(len(average), len(energy))
            average = average[:min_len]
            energy = energy[:min_len]
            difference = difference[:min_len]
        split = split_energy or self.get_split_energy(edges)
        orb = spa.orbital_angular_momentum(energy, average, difference, n_holes)
        spin = spa.spin_angular_momentum(energy, average, difference, n_holes, split_energy=split)
        return orb, spin

    def plot_sum_rules(self, ax: Axes | None = None, *args, split_energy: float | None = None,
                       edges: dict[str, float] | None = None, **kwargs) -> list[plt.Line2D]:
        """
        Create plots of spectra highlighting integration for sum rules
        """
        energy = self.energy
        difference = self.signal
        # average = self.average_subtracted_spectra().signal
        split_energy = split_energy or self.get_split_energy(edges)
        split_index = np.argmin(np.abs(energy - split_energy))

        ax = ax or plt.subplots(1, 1)[1]
        lines = self.plot(ax, *args, **kwargs)
        ax.fill_between(energy[:split_index], 0, difference[:split_index], color='r')
        ax.fill_between(energy[split_index:], 0, difference[split_index:], color='b')
        return lines

    def sum_rules_report(self, n_holes: float, element: str = '') -> str:
        """
        Calculate sum rules of XMCD spectra and return report

            print(spectra.sum_rules_report(n_holes))

        Parameters
        :param n_holes: number of holes in absorbing ion
        :returns: str
        """
        orb, spin = self.calculate_sum_rules(n_holes)
        report = f"{element} n_holes = {n_holes}\nL = {orb:.3f} μB\nS = {spin:.3f} μB"
        return report

    def create_sum_rules_nxnote(self, n_holes: float, parent: h5py.Group,
                                name: str, sequence_index: int | None = None, element: str = '') -> h5py.Group:
        note = nw.add_nxnote(
            root=parent,
            name=name,
            description=f"{self.label} {self.mode} {self.process_label} Sum Rules",
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
        mode = next((s.mode for s in parents))
        label = '+'.join(s.label for s in spectra)
        process = "Average of spectra:\n" + "\n".join('  ' + repr(s) for s in parents)
        super().__init__(av_energy, av_signal, av_bkg, parents, mode=mode, label=label,
                         process_label=process_label, process=process)

    def __repr__(self):
        return (
            f"SpectraAverage('{self.label}', '{self.mode}', energy=array{self.energy.shape}, signal=array{self.signal.shape}," +
            f"process_label='{self.process_label}')"
        )

