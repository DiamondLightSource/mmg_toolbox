"""
SpectraContainer object

=== DATA MODEL ===
spectra = Spectra(energy, signal, mode, process)
metadata = XasMetadata(scan_no=1234, default_mode='tey', sample_name='Fe')
scan = SpectraContainer('name', {'mode': spectra}, metadata=metadata)
scan2 = scan + 2  # add 2 to signal of each contained mode
scan.remove_background()  # apply operation to each contained mode, store previous version in scan.parents
"""
from __future__ import annotations

import inspect
from functools import wraps
import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox.utils.polarisation import pol_subtraction_label
from .spectra import Spectra, SpectraSubtraction


class Metadata:
    filename: str = ''
    beamline: str = ''
    scan_no: int = 0
    start_date_iso: str = ''
    end_date_iso: str = ''
    cmd: str = ''
    pol: str = 'pc'
    pol_angle: float = 0.0
    sample_name: str = ''
    temp: float = 300
    mag_field: float = 0
    pitch: float = 0  # 0 == sample surface normal to beam

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
    """Add methods from Spectra to SpectraContainer"""
    for name, method in inspect.getmembers(Spectra, predicate=inspect.isfunction):
        if name in ['divide_by_signal_at_energy', 'divide_by_preedge', 'divide_by_postedge', 'norm_to_peak',
                    'norm_to_jump', 'remove_background', 'auto_edge_background']:
            @wraps(method)
            def fn(self, *args, _method=method, **kwargs):
                self.parents = (self.copy(), *self.parents)
                self.spectra = {n: _method(s, *args, **kwargs) for n, s in self.spectra.items()}
                self.process_label = next(iter(self.spectra.values())).process_label
            setattr(target_cls, name, fn)

        elif name in ['plot', 'plot_bkg', 'plot_parents']:
            @wraps(method)
            def fn(self, *args, _method=method, **kwargs):
                return [_method(s, *args, **kwargs) for s in self.spectra.values()]
            setattr(target_cls, name, fn)

    return target_cls


# @spectra_method_decorator
class SpectraContainer:
    """
    Container for Spectra and metadata
    """

    def __init__(self, name: str, spectra: dict[str, Spectra | SpectraSubtraction],
                 *parents: SpectraContainer, metadata: XasMetadata = XasMetadata()):
        self.name = name
        self.process_label = next(iter(spectra.values())).process_label
        self.parents = parents
        self.spectra = spectra
        self.metadata = metadata

    def __repr__(self):
        return f"SpectraContainer('{self.name}', '{self.process_label}', {list(self.spectra)})"

    def __str__(self):
        meta_str = (
                f"{self.metadata.filename}\n" +
                f"{self.metadata.start_date_iso}\n" +
                f"{self.metadata.cmd}\n" +
                f"mode: '{self.metadata.default_mode}', signals: {list(self.spectra)}\n" +
                f"E = {np.mean(self.metadata.energy):.2f} eV -> {self.metadata.element} {self.metadata.edge}\n" +
                f"   --- Sample: {self.metadata.sample_name} ---\n" +
                f"T = {self.metadata.temp:.2f} K\n" +
                f"B = {self.metadata.mag_field:.2f} T\n" +
                f"Pol = '{self.metadata.pol}'"
        )
        return meta_str

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

    def write_nexus(self, nexus_filename: str):
        from .nexus_writer import write_xas_nexus
        write_xas_nexus(self, nexus_filename)

    def create_figure(self):
        fig, axs = plt.subplots(1, len(self.spectra))

        for ax, s in zip(axs.flat, self.spectra.values()):
            s.plot(ax)
            ax.set_xlabel('E [eV]')
            ax.set_ylabel('signal')
            ax.legend()
        return fig

    def create_background_figure(self):
        """Plot background subtracted scans"""
        fig, axes = plt.subplots(2, 2)

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            spectra.plot_parents(ax=axes[0, n])
            spectra.plot_bkg(ax=axes[0, n])
            axes[0, n].set_ylabel(mode)

            spectra.plot(ax=axes[1, n], label=self.name)
            axes[1, n].set_ylabel(mode)

        for ax in axes.flat:
            ax.set_xlabel('E [eV]')
            ax.legend()

    ### Spectra Processing ###

    def _process_spectra(self, method: str, *args, **kwargs) -> SpectraContainer:
        """wrapper function for spectra processing"""
        spectra = {
            mode: getattr(spec, method)(*args, **kwargs)
            for mode, spec in self.spectra.items()
        }
        parents = (self.copy(), *self.parents)
        process_label = next(iter(spectra.values())).process_label
        scan = SpectraContainer(self.name, spectra, *parents, metadata=self.metadata)
        scan.process_label = process_label
        return scan

    def divide_by_signal_at_energy(self, energy1: float, energy2: float | None = None) -> SpectraContainer:
        """Divide spectra by signal"""
        return self._process_spectra('divide_by_signal_at_energy', energy1, energy2)

    def divide_by_preedge(self, ev_from_start: float = 5) -> SpectraContainer:
        """Divide by average of raw_signals at start"""
        return self._process_spectra('divide_by_preedge', ev_from_start)

    def divide_by_postedge(self, ev_from_end: float = 5) -> SpectraContainer:
        """Divide by average of raw_signals at end"""
        return self._process_spectra('divide_by_postedge', ev_from_end)

    def norm_to_peak(self) -> SpectraContainer:
        """Normalise the spectra to the highest point"""
        return self._process_spectra('norm_to_peak')

    def norm_to_jump(self, ev_from_start: float = 5, ev_from_end: float | None = None) -> SpectraContainer:
        """Normalise the spectra to the jump between edges"""
        return self._process_spectra('norm_to_jump', ev_from_start, ev_from_end)

    def remove_background(self, name='flat', *args, **kwargs) -> SpectraContainer:
        """remove background using various methods"""
        return self._process_spectra('remove_background', name, *args, **kwargs)

    def auto_edge_background(self, peak_width_ev: float = 5.) -> SpectraContainer:
        """Remove generic xray absorption background from spectra"""
        return self._process_spectra('auto_edge_background', peak_width_ev)


class SpectraContainerSubtraction(SpectraContainer):
    """Special subclass for subtraction of SpectraContainers - XMCD and XMLD"""
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

    def calculate_sum_rules(self, n_holes: float, mode: str | None = None) -> tuple[float, float]:
        """
        Calculate sum rules of XMCD spectra from integration

            orb, spin = spectra.calculate_sum_rules(n_holes)

        Parameters
        :param n_holes: number of holes in absorbing ion
        :param mode: select which detection mode to use (None for default)
        :returns: orb, spin sum rule values for the detector mode
        """
        spectra = self.spectra[mode or self.metadata.default_mode]
        return spectra.calculate_sum_rules(n_holes)

    def sum_rules_report(self, n_holes: float, mode: str | None = None) -> str:
        """
        Calculate sum rules of XMCD spectra and return report

            print(spectra.sum_rules_report(n_holes))

        Parameters
        :param n_holes: number of holes in absorbing ion
        :param mode: select which detection mode to use (None for default)
        :returns: str
        """
        spectra = self.spectra[mode or  self.metadata.default_mode]
        return spectra.sum_rules_report(n_holes)

    def sum_rules_plot(self):
        """Create figure of subtraction plots shwoing different integration regions"""
        fig, axs = plt.subplots(1, len(self.spectra), squeeze=False)

        for ax, s in zip(axs[0], self.spectra.values()):
            s.plot_sum_rules(ax)
            ax.set_xlabel('E [eV]')
            ax.set_ylabel('signal')
            ax.legend()
        return fig


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
        scan.parents = pol_scans[pol]
        for spectra in scan.spectra.values():
            spectra.process_label += f"_{pol}"
    return list(average_scans.values())

