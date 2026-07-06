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

from mmg_toolbox.utils.polarisation import pol_subtraction_label, PolLabels
from mmg_toolbox.xas import spectra_analysis as spa
from mmg_toolbox.xas.spectra import Spectra, SpectraSubtraction
from mmg_toolbox.xas.metadata import XasMetadata, merge_xas_metadata


class SpectraContainer:
    """
    Container for Spectra objects and metadata

    Attributes
    :param name: name of this Scan (usually the scan number)
    :param spectra: dict of Spectra objects for different detectors
    :param parents: list of SpectraContainer objects for parent processes
    :param metadata: XasMetadata object containing regularised scan metadata

    Selected Behaviours (see Docs for full list)
    print(spectra1) : displays contained spectra, metadata and previous analysis steps
    spectra1 + spectra2 : Averages contained spectra on a regular energy grid
    spectra1 - spectra2 : Subtracts spectra on an interpolated energy grid
    spectra1.trim(ev_from_start=1) : trim contained spectra by 1 eV
    spectra1.divide_by_preedge() : divide contained spectra by preedge signal
    spectra1.remove_background(type) : Subtract background using various methods
    spectra1.analysis_steps_str() : returns a formatted string of previous analysis steps
    spectra1.create_background_figure() : create a matplotlib figure of all contained spectra
    spectra1.create_background_figure() : create a matplotlib figure including background subtraction
    spectra1.write_nexus('filename.nxs') : write a processed NeXus file
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
            metadata = XasMetadata(energy=s.energy, raw_signals={'tey': s.signal}, monitor=np.ones_like(s.signal),
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
        return (
            f"{self.name} " +
            f"{self.metadata.element}{self.metadata.edge} " +
            f"T={round(self.metadata.temp, 1):.3g}K " +
            f"'{self.metadata.pol}' " +
            f"B={round(self.metadata.mag_field, 5):+.3g}T"
        )

    def find_edges(self, search_edges: list[str] | None = spa.SEARCH_EDGES) -> dict[str, float]:
        """Return list of edges within the energy range"""
        return next(iter(self.spectra.values())).edges(search_edges=search_edges)

    def get_edges(self) -> dict[str, float]:
        """Return list of edges from metadata"""
        return spa.get_edge_energies(self.metadata.element + self.metadata.edge)

    def get_arrays(self, mode: str | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Return energy, signal arrays of chosen mode"""
        mode = mode or self.metadata.default_mode
        spectra = self.spectra[mode]
        return spectra.energy, spectra.signal

    def get_all_arrays(self) -> np.ndarray[tuple[int, ...], np.dtype[np.float64]]:
        """Return energy, signal arrays of all modes"""
        energy = self.spectra[self.metadata.default_mode].energy
        signals = np.array([spectra.signal for spectra in self.spectra.values()])
        return np.array([energy, *signals])

    def get_raw_metadata(self, field: str):
        """Recursively get raw metadata from top level parent"""
        if self.parents:
            return next(iter(self.parents)).get_raw_metadata(field)
        return getattr(self.metadata, field)

    def get_raw_filename(self) -> str:
        """Recursively look through the parents for a raw filename"""
        return self.get_raw_metadata('filename')

    def analysis_steps(self) -> dict[str, dict[str, Spectra]]:
        """Return ordered dictionary of processing steps from parent objects"""
        return {
            label: spectra for sc in self.parents for label, spectra in sc.analysis_steps().items()
        } | {
            f"{self.process_label.replace('/', '').replace(' ', '')}": self.spectra
        }

    def analysis_steps_str(self) -> str:
        """Return string of analysis steps"""
        steps = self.analysis_steps()
        return '\n'.join(
            f"=== {n}. {label} ===\n{next(iter(spectra.values())).process}"
            for n, (label, spectra) in enumerate(steps.items())
        )

    def write_nexus(self, nexus_filename: str):
        """Write all spectra to NeXus file (.nxs)"""
        from .nexus_writer import write_xas_nexus
        write_xas_nexus(self, nexus_filename)

    def write_csv(self, csv_filename: str, mode: str | None = None) -> None:
        """
        Write spectra to csv file

            spectra.write_csv('xas_spectra.csv')  # spectra contains modes TEY and TFY
            energy, tey, tfy = np.loadtxt('xas_spectra.csv', delimiter=',').T

        :param csv_filename: filename to write
        :param mode: mode to write, or None to write all mode spectra to single file
        """
        header = f"{self.name} {self.process_label}"
        if mode is None:
            array = self.get_all_arrays().T
            header += '\nenergy, ' + ', '.join(self.spectra.keys())
        else:
            spectra = self.spectra[mode]
            array = np.transpose([spectra.energy, spectra.signal])
            header += f"\nenergy, {mode}"
        np.savetxt(csv_filename, array, delimiter=', ', header=header)
        print(f"Saved {csv_filename}")

    ### Plots ###

    def add_edge_lines(self, ax: plt.Axes):
        """Add absorption edge lines to a plot"""
        for edge_label, energy in self.get_edges().items():
            ax.axvline(energy, color='k', alpha=0.3)
            ax.text(energy, 0.9, edge_label, color='k', alpha=0.3,
                    ha='right', va='top', transform=ax.get_xaxis_transform())

    def create_figure(self, **kwargs) -> plt.Figure:
        """
        Create matplotlib figure showing each spectra in a separate axes

        :param kwargs: kwargs to pass to plt.figure
        :return: matplotlib Figure
        """
        fig, axs = plt.subplots(1, len(self.spectra), squeeze=False, **kwargs)

        for ax, s in zip(axs.flat, self.spectra.values()):
            self.add_edge_lines(ax=ax)
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
        fig, axes = plt.subplots(2, len(self.spectra), squeeze=False, **kwargs)
        fig.tight_layout()

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            spectra.plot_parents(ax=axes[0, n])
            spectra.plot_bkg(ax=axes[0, n])
            axes[0, n].set_ylabel(mode)
            self.add_edge_lines(axes[0, n])
            spectra.plot(ax=axes[1, n], label=self.name)
            axes[1, n].set_ylabel(mode)

        for ax in axes.flat:
            ax: plt.Axes
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
        process_label = next(iter(spectra.values())).process_label
        scan = SpectraContainer(self.name, spectra, self.copy(), metadata=self.metadata)
        scan.process_label = process_label
        return scan

    def trim(self, ev_from_start=1., ev_from_end=None) -> SpectraContainer:
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

    def divide_by_peak(self) -> SpectraContainer:
        """Normalise the spectra to the highest point"""
        return self._process_spectra('divide_by_peak')

    def divide_by_jump(self, ev_from_start: float = 5, ev_from_end: float | None = None) -> SpectraContainer:
        """Normalise the spectra to the jump between edges"""
        return self._process_spectra('divide_by_jump', ev_from_start, ev_from_end)

    def divide_by_background(self, name='flat', *args, **kwargs) -> SpectraContainer:
        """
        Divide by background using various methods

          spectra = spectra.divide_by_background('flat', ev_from_start=5)

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
            name1, name2 = m1.pol, m2.pol
        elif abs(m1.mag_field + m2.mag_field) < 0.1:
            # magnetisation flip - XMCD
            name = 'field ' + pol_subtraction_label(m1.pol)
            name1, name2 = f"B={m1.mag_field:+.1g}", f"B={m2.mag_field:+.1g}"
        elif m1.pol == PolLabels.linear_arbitrary and abs(m1.pol_angle - m2.pol_angle) > 89:
            # rotate linear polarisation - XMLD
            name = PolLabels.linear_dichroism
            name1, name2 = f"{m1.pol}({m1.pol_angle:+.1g})", f"{m2.pol}({m2.pol_angle:+.1g})"
        else:
            name = 'subtraction'
            name1 = name2 = None
        # rename parents (for display)
        self.spectra1 = spectra_container1.copy(name1)
        self.spectra2 = spectra_container2.copy(name2)
        # spectra process label
        for spectrum in spectra.values():
            spectrum.process_label = name
        # subtraction metadata (merge these?)
        metadata = merge_xas_metadata(m1, m2)
        super().__init__(name, spectra, self.spectra1, self.spectra2, metadata=metadata)

    def __str__(self):
        s = super().__str__()
        return s + '\n' + self.sum_rules_report()

    def label(self):
        p1, p2 = self.parents
        if 'field' in self.process_label:
            static = f"'{self.metadata.pol}'"
        else:
            static = f"B={round(self.metadata.mag_field, 5):+.3g}T"
        return (
            f"{p1.metadata.scan_no}-{p2.metadata.scan_no} {self.process_label} " +
            f"{self.metadata.element}{self.metadata.edge} " +
            f"T={round(self.metadata.temp, 1):.3g}K " + static
        )

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
        try:
            n_holes = spa.d_electron_holes(self.metadata.element) if n_holes is None else n_holes
        except ValueError:
            return f"=== Sum Rules not available for element {self.metadata.element} ===\n"
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
        fig, axes = plt.subplots(2, len(self.spectra), squeeze=False, sharex=True, **kwargs)
        fig.tight_layout(h_pad=0, w_pad=0.1)
        signal_ratio = self.calculate_signal_ratio()

        for parent in self.parents:
            for n, (mode, spectra) in enumerate(parent.spectra.items()):
                self.add_edge_lines(axes[0, n])
                spectra.plot(ax=axes[0, n], label=parent.name)
                axes[0, n].set_ylabel(mode)

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            self.add_edge_lines(axes[1, n])
            spectra.plot_sum_rules(ax=axes[1, n])
            axes[1, n].set_ylabel(self.name)
            idx = abs(spectra.signal).argmax()
            x, y = spectra.energy[idx], spectra.signal[idx]
            axes[1, n].text(x, y, f"max signal = {signal_ratio[mode]:.2%}")

        for ax in axes.flat:
            ax: plt.Axes
            ax.set_xlabel('E [eV]')
            ax.legend()
        return fig

    def create_combined_axes(self, mode: str | None = None, axes: plt.Axes | None = None) -> plt.Axes:
        """
        Create matplotlib axes of subtraction plot and XAS in same axes

        :param mode: select which detection mode to use (None for default)
        :param axes: axes to plot on
        :return: matplotlib Axes
        """
        selected_mode = mode or self.metadata.default_mode
        axes = axes or plt.subplot()
        signal_ratio = self.calculate_signal_ratio()

        for parent in self.parents:
            for n, (mode, spectra) in enumerate(parent.spectra.items()):
                if mode != selected_mode:
                    continue
                spectra.plot(ax=axes, label=parent.name)

        for n, (mode, spectra) in enumerate(self.spectra.items()):
            if mode != selected_mode:
                continue
            spectra.plot_sum_rules(ax=axes)
            axes.set_ylabel(self.name)
            idx = abs(spectra.signal).argmax()
            x, y = spectra.energy[idx], spectra.signal[idx]
            axes.text(x, y, f"max signal = {signal_ratio[mode]:.2%}")

        self.add_edge_lines(axes)
        axes.set_xlabel('E [eV]')
        axes.legend()
        return axes

    def write_csv(self, csv_filename: str, mode: str | None = None) -> None:
        """
        Write spectra to csv file

            spectra.write_csv('xmcd_spectra.csv', mode='tey')  # spectra contains modes TEY and TFY
            energy, xas_tey1, xas_tey2, xmcd = np.loadtxt('xmcd_spectra.csv', delimiter=',').T

        :param csv_filename: filename to write
        :param mode: mode to write, or None to write all mode spectra to single file
        """
        header = f"{self.name} {self.process_label}"
        if mode is None:
            array = self.get_all_arrays()
            energy = array[0]
            xmcd = array[1:]
            xas1 = self.spectra1.get_all_arrays()[1:]
            xas2 = self.spectra2.get_all_arrays()[1:]
            array = np.array([energy, *xas1, *xas2, *xmcd]).T
            keys = self.spectra.keys()
            header += '\n' + ', '.join(
                ['energy'] +
                [f'xas1_{self.spectra1.name}_{k}' for k in keys] +
                [f'xas2_{self.spectra2.name}_{k}' for k in keys] +
                [f'{self.name}_{k}' for k in keys]
            )
        else:
            spectra = self.spectra[mode]
            xas1 = self.spectra1.spectra[mode]
            xas2 = self.spectra2.spectra[mode]
            array = np.transpose([spectra.energy, xas1.signal, xas2.signal, spectra.signal])
            header += f"\nenergy, {self.spectra1.name}, {self.spectra2.name}, {self.name}"
        np.savetxt(csv_filename, array, delimiter=', ', header=header)
        print(f"Saved {csv_filename}")

