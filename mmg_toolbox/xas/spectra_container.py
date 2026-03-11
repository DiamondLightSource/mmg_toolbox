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

import numpy as np
import matplotlib.pyplot as plt

from mmg_toolbox.utils.polarisation import pol_subtraction_label, check_polarisation, opposite_polarisations, PolLabels
from .spectra import Spectra, SpectraSubtraction, spa


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


class SpectraContainer:
    """
    Container for Spectra and metadata
    """

    def __init__(self, name: str, spectra: dict[str, Spectra | SpectraSubtraction],
                 *parents: SpectraContainer, metadata: XasMetadata = None):
        self.name = name
        self.process_label = next(iter(spectra.values())).process_label
        self.parents = parents
        self.spectra = spectra
        if metadata is None:
            m, s = next(iter(spectra.items()))
            element, edge = spa.energy_range_edge_label(s.energy.min(), s.energy.max())
            metadata = XasMetadata(energy=s.energy, signal=s.signal, monitor=np.ones_like(s.signal),
                                   default_mode=m, element=element, edge=edge)
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
        proc_str = '  --- Processing ---\n' + self.analysis_steps_str() if self.parents else ''
        return meta_str + '\n' + proc_str

    def __iter__(self):
        return self.spectra.__iter__()

    def __getitem__(self, item):
        return self.spectra[item]

    def __add__(self, other):
        if issubclass(type(other), SpectraContainer):
            # average Spectra
            spectra = {n: s + other.spectra[n] for n, s in self.spectra.items() if n in other.spectra}
            return SpectraContainer(self.name, spectra, self, other, metadata=self.metadata)
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
        return SpectraContainer(name, self.spectra.copy(), *self.parents, metadata=self.metadata)

    def label(self):
        # return f"{self.name} {self.process_label}"
        return self.process_label.replace('/', '').replace(' ', '')

    def find_edges(self, search_edges: list[str] | None = spa.SEARCH_EDGES) -> dict[str, float]:
        """Return list of edges within the energy range"""
        return next(iter(self.spectra.values())).edges(search_edges=search_edges)

    def get_edges(self) -> dict[str, float]:
        """Return list of edges from metadata"""
        return spa.get_edge_energies(self.metadata.element + self.metadata.edge)

    def analysis_steps(self) -> dict[str, dict[str, Spectra]]:
        """Return ordered dictionary of processing steps from parent objects"""
        return {sc.label(): sc.spectra for sc in list(reversed(self.parents)) + [self]}

    def analysis_steps_str(self) -> str:
        """Return string of analysis steps"""
        steps = self.analysis_steps()
        return '\n'.join(
            f"=== {n}. {label} ===\n{next(iter(spectra.values())).process}"
            for n, (label, spectra) in enumerate(steps.items())
        )

    def write_nexus(self, nexus_filename: str):
        from .nexus_writer import write_xas_nexus
        write_xas_nexus(self, nexus_filename)

    def create_figure(self, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure showing each spectra in a separate axes

        :param kwargs: kwargs to pass to plt.figure
        :return: matplotlib Figure
        """
        fig, axs = plt.subplots(1, len(self.spectra), squeeze=False, **kwargs)

        for ax, s in zip(axs.flat, self.spectra.values()):
            s.plot(ax)
            ax.set_xlabel('E [eV]')
            ax.set_ylabel('signal')
            ax.legend()
        return fig

    def create_background_figure(self, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure showing each spectra and background subtraction in separate axes

        :param kwargs: kwargs to pass to plt.figure
        :return: matplotlib Figure
        """
        fig: plt.Figure
        axes: np.ndarray[plt.Axes, np.object_]
        fig, axes = plt.subplots(2, len(self.spectra), squeeze=False, **kwargs)
        fig.tight_layout()

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            spectra.plot_parents(ax=axes[0, n])
            spectra.plot_bkg(ax=axes[0, n])
            axes[0, n].set_ylabel(mode)
            for edge_label, energy in self.get_edges().items():
                axes[0, n].axvline(energy, color='k', alpha=0.3)
                axes[0, n].text(energy, 0.9, edge_label, color='k', alpha=0.3,
                                ha='right', va='top',
                                transform=axes[0, n].get_xaxis_transform())

            spectra.plot(ax=axes[1, n], label=self.name)
            axes[1, n].set_ylabel(mode)

        for ax in axes.flat:
            ax.set_xlabel('E [eV]')
            ax.legend()
        return fig

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

    def trim(self, ev_from_start=5., ev_from_end=None) -> SpectraContainer:
        """Trim spectra between energies"""
        return self._process_spectra('trim', ev_from_start, ev_from_end)

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
        """
        Remove background using various methods

          spectra = spectra.remove_background('flat', ev_from_start=5)

        Background options
        | Option | parameters |
        |  ---   | ---------- |
        | 'flat' | ev_from_start |
        | 'norm' | ev_from_start |
        | 'linear' | ev_from_start |
        | 'curve' | ev_from_start |
        | 'exp' | ev_from_start, ev_from_end |
        | 'step' | ev_from_start |
        | 'double_edge_step' | l3_energy, l2_energy, peak_width_ev |
        | 'poly_edges' | *step_energies, peak_width_ev |
        | 'exp_edges' | *step_energies, peak_width_ev |

        :param name: the name of the background to remove e.g. 'flat', 'linear', 'curve', 'exp', 'step', 'double_edge_step', 'poly_edges'
        :param args: additional positional arguments
        :param kwargs: additional keyword arguments
        :return: processed SpectraContainer object
        """
        return self._process_spectra('remove_background', name, *args, **kwargs)

    def auto_edge_background(self, peak_width_ev: float = 5., edges: dict[str, float] | None = None) -> SpectraContainer:
        """Remove generic xray absorption background from spectra"""
        return self._process_spectra('auto_edge_background', peak_width_ev, edges)


class SpectraContainerSubtraction(SpectraContainer):
    """Special subclass for subtraction of SpectraContainers - XMCD and XMLD"""
    def __init__(self, spectra_container1: SpectraContainer, spectra_container2: SpectraContainer):
        # subtract each spectra in container
        spectra = {
            name: spectra - spectra_container2.spectra[name]
            for name, spectra in spectra_container1.spectra.items()
            if name in spectra_container2.spectra
        }
        m1 = spectra_container1.metadata
        m2 = spectra_container2.metadata

        # subtraction name
        if m1.pol != m2.pol:
            # Polarisation flip - XMCD or XMLD
            name = pol_subtraction_label(m1.pol)
            # rename parents (for display)
            spectra_container1 = spectra_container1.copy(m1.pol)
            spectra_container2 = spectra_container2.copy(m2.pol)
            for spectrum in spectra.values():
                spectrum.process_label = name
        elif abs(m1.mag_field + m2.mag_field) < 0.1:
            # magnetisation flip - XMCD
            name = 'field ' + pol_subtraction_label(m1.pol)
            # rename parents (for display)
            spectra_container1 = spectra_container1.copy(f"B={m1.mag_field:+.1g}")
            spectra_container2 = spectra_container2.copy(f"B={m2.mag_field:+.1g}")
            for spectrum in spectra.values():
                spectrum.process_label = name
        elif m1.pol == PolLabels.linear_arbitrary and abs(m1.pol_angle - m2.pol_angle) > 89:
            # rotate linear polarisation - XMLD
            name = PolLabels.linear_dichroism
            # rename parents (for display)
            spectra_container1 = spectra_container1.copy(f"{m1.pol}({m1.pol_angle:+.1g})")
            spectra_container2 = spectra_container2.copy(f"{m2.pol}({m2.pol_angle:+.1g})")
            for spectrum in spectra.values():
                spectrum.process_label = name
        else:
            name = 'subtraction'
        # subtraction metadata (merge these?)
        metadata = XasMetadata(**m1.__dict__)
        metadata.filename = ''
        super().__init__(name, spectra, spectra_container1, spectra_container2, metadata=metadata)

    def __str__(self):
        s = super().__str__()
        return s + '\n' + self.sum_rules_report()

    def calculate_signal_ratio(self) -> dict[str, float]:
        """Return the maximum signal as a ratio of the average parent spectra"""
        parent = {
            mode: np.mean([
                abs(parent.spectra[mode].signal).max() for parent in self.parents
            ])
            for mode in self.spectra.keys()
        }
        return {
            mode: abs(spectra.signal).max() / float(parent[mode])
            for mode, spectra in self.spectra.items()
        }

    def calculate_sum_rules(self, n_holes: float | None = None, mode: str | None = None) -> tuple[float, float]:
        """
        Calculate sum rules of XMCD spectra from integration

            orb, spin = spectra.calculate_sum_rules(n_holes)

        Parameters
        :param n_holes: number of holes in absorbing ion
        :param mode: select which detection mode to use (None for default)
        :returns: orb, spin sum rule values for the detector mode
        """
        spectra = self.spectra[mode or self.metadata.default_mode]
        n_holes = spa.d_electron_holes(self.metadata.element) if n_holes is None else n_holes
        return spectra.calculate_sum_rules(n_holes)

    def sum_rules_report(self, n_holes: float | None = None, mode: str | None = None) -> str:
        """
        Calculate sum rules of XMCD spectra and return report

            print(spectra.sum_rules_report(n_holes))

        Parameters
        :param n_holes: number of holes in absorbing ion
        :param mode: select which detection mode to use (None for default)
        :returns: str
        """
        spectra = self.spectra[mode or  self.metadata.default_mode]
        n_holes = spa.d_electron_holes(self.metadata.element) if n_holes is None else n_holes
        report = "=== Sum Rules === \n"
        report += f"{self.metadata.default_mode} signal = {self.calculate_signal_ratio()[self.metadata.default_mode]:.2%}\n"
        report += spectra.sum_rules_report(n_holes, self.metadata.element)
        return report

    def create_sum_rules_figure(self, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure of subtraction plots showing different integration regions

        :param kwargs: kwargs to pass to plt.figure
        :return: matplotlib Figure
        """
        fig: plt.Figure
        axes: np.ndarray[plt.Axes, np.object_]
        fig, axes = plt.subplots(2, len(self.spectra), squeeze=False, **kwargs)
        fig.tight_layout(h_pad=0.1, w_pad=0.1)
        signal_ratio = self.calculate_signal_ratio()

        for parent in self.parents:
            for n, (mode, spectra) in enumerate(parent.spectra.items()):
                for edge_label, energy in self.get_edges().items():
                    axes[0, n].axvline(energy, color='k', alpha=0.3)
                    axes[0, n].text(energy, 0.9, edge_label, color='k', alpha=0.3,
                                    ha='right', va='top',
                                    transform=axes[0, n].get_xaxis_transform())
                spectra.plot(ax=axes[0, n], label=parent.name)
                axes[0, n].set_ylabel(mode)

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            for edge_label, energy in self.get_edges().items():
                axes[1, n].axvline(energy, color='k', alpha=0.3)
                axes[1, n].text(energy, 0.9, edge_label, color='k', alpha=0.3,
                                ha='right', va='top',
                                transform=axes[1, n].get_xaxis_transform())
            spectra.plot_sum_rules(ax=axes[1, n])
            axes[1, n].set_ylabel(self.name)
            idx = abs(spectra.signal).argmax()
            x, y = spectra.energy[idx], spectra.signal[idx]
            axes[1, n].text(x, y, f"max signal = {signal_ratio[mode]:.2%}")

        for ax in axes.flat:
            ax.set_xlabel('E [eV]')
            ax.legend()
        return fig


def average_polarised_scans(*scans: SpectraContainer) -> tuple[SpectraContainer, SpectraContainer | None]:
    """
    Find unique polarisations and average each scan at that polarisation
    Spectra are only separated by polarisation, all spectra with the same polarisation
    are averaged together.

        pol1, pol2 = average_polarised_scans(*scans)

    :param scans: list of SpectraContainer objects
    :return: pol1, (pol2|None) SpectraContainer objects for opposite polarisations
    """
    pols = opposite_polarisations(scans[0].metadata.pol, scans[0].metadata.pol_angle)
    pol_scans = [
        [scan for scan in scans if check_polarisation(scan.metadata.pol) == pol]
        for pol in pols
    ]

    # average spectra containers
    av_scans = [
        sum(_scans[1:], _scans[0]) if len(_scans) > 1 else _scans[0]
        for _scans in pol_scans
    ]

    # rename containers
    for pol, scan, pol_scans in zip(pols, av_scans, pol_scans):
        scan.name = pol
        scan.parents = pol_scans
        for spectra in scan.spectra.values():
            spectra.process_label += f"_{pol}"
    if len(pol_scans) == 1:
        return av_scans[0], None
    return av_scans[0], av_scans[1]

