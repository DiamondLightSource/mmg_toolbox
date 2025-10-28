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
import datetime
import numpy as np
import h5py
import matplotlib.pyplot as plt

from mmg_toolbox.nexus import nexus_writer as nw
from . import spectra_analysis as spa
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
                f"   Sample: '{self.metadata.sample_name}'\n" +
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

    def nx_entry(self, nexus: h5py.File, name='entry', default=True) -> h5py.Group:
        entry = nw.add_nxentry(nexus, name, definition='NXxas')
        nw.add_nxfield(entry, 'entry_identifier', self.metadata.scan_no)
        nw.add_nxfield(entry, 'start_time', self.metadata.start_date_iso)
        nw.add_nxfield(entry, 'end_time', self.metadata.end_date_iso)
        nw.add_nxfield(entry, 'scan_command', self.metadata.cmd)
        nw.add_nxfield(entry, 'mode', self.metadata.default_mode)
        nw.add_nxfield(entry, 'element', self.metadata.element)
        nw.add_nxfield(entry, 'edge', self.metadata.edge)
        nw.add_nxfield(entry, 'polarization_label', self.metadata.pol)
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
        from mmg_toolbox import __version__

        # NXprocess - read dat
        input_filename = self.metadata.filename
        if input_filename.endswith('.dat'):
            read_dat = nw.add_nxprocess(
                root=entry,
                name='read_dat',
                program='xmcd_analysis_functions',
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

    def nx_sum_rules_process(self, entry: h5py.Group):
        from mmg_toolbox import __version__
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

