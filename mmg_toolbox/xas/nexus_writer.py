"""
NeXus Writer for processed XAS spectra
"""

import datetime
import numpy as np
import h5py

from mmg_toolbox.nexus import nexus_writer as nw
from . import spectra_analysis as spa
from .spectra import Spectra
from .spectra_container import SpectraContainer, SpectraContainerSubtraction


def write_xas_nexus(scan: SpectraContainer | SpectraContainerSubtraction, nexus_filename: str):
    """Write a Nexus file based on XAS spectra."""
    writer = XasNexusWriter(scan)
    writer.write_nexus(nexus_filename)


class XasNexusWriter:
    """
    NeXus Writer for processed XAS spectra
    """

    def __init__(self, scan: SpectraContainer):
        self.scan = scan
        self.metadata = scan.metadata
        self.n_holes: int | None = None

    def nx_entry(self, nexus: h5py.File, name='entry', default=True) -> h5py.Group:
        entry = nw.add_nxentry(nexus, name, definition='NXxas', default=default)
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
            rotation_angle=self.metadata.pitch,
            sample_type='sample',
            description=''
        )
        energy = self.metadata.energy
        nw.add_nxbeam(
            root=sample,
            name='beam',
            incident_energy_ev=float(np.mean(energy)),
            polarisation_label=self.metadata.pol,
            beam_size_um=None,
            arbitrary_polarisation_angle=self.metadata.pol_angle,
        )
        return sample

    def nx_monitor(self, entry: h5py.Group) -> h5py.Group:
        monitor = nw.add_nxmonitor(
            root=entry,
            name='monitor',
            data=entry.name + '/instrument/incoming_beam/data'
        )
        monitor['mode'] = 'timer'
        monitor['preset'] = self.metadata.count_time
        return monitor

    def nx_data(self, entry: h5py.Group, name: str, spectra: Spectra, default: bool):
        data = spectra.create_nxdata(entry, name, default=default)
        nw.add_nxfield(data, name, spectra.signal, units='')
        if spectra.background is not None:
            nw.add_nxfield(data, "background", spectra.background, units='')
            data.attrs['auxiliary_signals'] = ["background"]

    def nx_all_data(self, entry: h5py.Group, spectra: dict[str, Spectra]):
        for name, spec in spectra.items():
            self.nx_data(entry, name, spec, name == self.scan.metadata.default_mode)

    def nx_processes(self, entry: h5py.Group):
        from mmg_toolbox import __version__

        index = 1
        date = str(datetime.datetime.now())
        # NXprocess - read dat
        input_filename = self.metadata.filename
        if input_filename.endswith('.dat'):
            read_dat = nw.add_nxprocess(
                root=entry,
                name='read_dat',
                program='mmg_toolbox.xas',
                version=__version__,
                date=date,
                sequence_index=index,
            )
            nw.add_nxnote(
                root=read_dat,
                name='dat_file',
                data=open(input_filename, 'r').read(),
                filename=input_filename,
                description='DLS SRS format',
                sequence_index=index
            )
            index += 1

        # raw file - for NXxasproc
        nw.add_nxprocess(
            root=entry,
            name='XAS_data_reduction',  # NXxasproc
            program='mmg_toolbox.xas',
            version=__version__,
            date=date,
            sequence_index=index,
            raw_file=self.scan.get_raw_filename(),
        )
        index += 1

        analysis_steps = self.scan.analysis_steps()
        for name, spectra in analysis_steps.items():
            process = nw.add_nxprocess(
                root=entry,
                name=name,
                program='mmg_toolbox.xas',
                version=__version__,
                date=date,
                sequence_index=index,
            )
            mode_spectra = spectra[self.metadata.default_mode]
            # NXnote
            mode_spectra.create_nxnote(process, 'description')
            # NXparameters
            mode_spectra.create_nxparameters(process, 'parameters')
            # NXdata
            self.nx_all_data(process, spectra)
            index += 1
        self.nx_sum_rules_process(entry, index)

    def nx_sum_rules_process(self, entry: h5py.Group, sequence_index: int):
        from mmg_toolbox import __version__
        if not isinstance(self.scan, SpectraContainerSubtraction):
            return

        if self.n_holes is None:
            try:
                n_holes = spa.d_electron_holes(self.metadata.element)
            except KeyError as ke:
                print(f"Warning: {ke}")
                n_holes = 1
        else:
            n_holes = self.n_holes

        process = nw.add_nxprocess(
            root=entry,
            name='sum_rules',
            program='mmg_toolbox',
            version=__version__,
            date=str(datetime.datetime.now()),
            sequence_index=sequence_index,
            n_holes=n_holes  # parameter
        )
        for n, (name, spectra) in enumerate(self.scan.spectra.items()):
            spectra.create_sum_rules_nxnote(n_holes, process, name, n + 1, element=self.metadata.element)

    def nx_main_entry(self, nexus: h5py.File, name='entry', default=True):
        entry = self.nx_entry(nexus, name=name, default=default)
        self.nx_instrument(entry)
        self.nx_sample(entry)
        self.nx_monitor(entry)
        self.nx_processes(entry)
        self.nx_all_data(entry, self.scan.spectra)

    def _nx_add_items(self, nexus: h5py.File):
        nw.add_entry_links(nexus, self.metadata.filename)
        if len(self.scan.parents) > 1:
            for parent in self.scan.parents:
                parent_writer = XasNexusWriter(parent)
                parent_writer.nx_main_entry(nexus, parent.name)
        self.nx_main_entry(nexus, 'processed' if self.scan.name in nexus else self.scan.name)

    def write_nexus(self, nexus_filename: str):
        with h5py.File(nexus_filename, 'w') as nxs:
            self._nx_add_items(nxs)
        print(f'Created {nexus_filename}')
