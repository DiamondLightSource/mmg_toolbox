"""
NeXus Writer for processed XAS spectra
"""

import datetime
import numpy as np
import h5py

from mmg_toolbox.nexus import nexus_writer as nw
from . import spectra_analysis as spa
from .spectra_container import SpectraContainer, SpectraContainerSubtraction


def write_xas_nexus(scan: SpectraContainer | SpectraContainerSubtraction, nexus_filename: str):
    """Write a Nexus file based on XAS spectra."""
    if isinstance(scan, SpectraContainerSubtraction):
        writer = XasSubtractionNexusWriter(scan)
    else:
        writer = XasNexusWriter(scan)
    writer.write_nexus(nexus_filename)


class XasNexusWriter:
    """
    NeXus Writer for processed XAS spectra
    """

    def __init__(self, scan: SpectraContainer):
        self.scan = scan
        self.metadata = scan.metadata

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
            beam_size_um=None,
            arbitrary_polarisation_angle=self.metadata.pol_angle,
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
        analysis_steps = self.scan.analysis_steps()
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


class XasSubtractionNexusWriter(XasNexusWriter):
    """
    NeXus Writer for processed subtracted XAS spectra, e.g. xmcd
    """
    def __init__(self, scan: SpectraContainerSubtraction,):
        super().__init__(scan)

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
            n_holes = spa.d_electron_holes(self.metadata.element)
        except KeyError as ke:
            print(f"Warning: {ke}")
            n_holes = 1
        for n, (name, spectra) in enumerate(self.scan.spectra.items()):
            spectra.create_sum_rules_nxnote(n_holes, process, name, n + 1, element=self.metadata.element)

    def _nx_add_items(self, nexus: h5py.File):
        for parent in self.scan.parents:
            parent.nx_main_entry(nexus, name=parent.name, default=False)
        entry = self.nx_entry(nexus, name=self.scan.name, default=True)
        self.nx_sample(entry)
        process = self.nx_process(entry)
        self.nx_sum_rules_process(entry)
        self.nx_analysis_steps(entry, process)
