"""
Functions to read XAS data from files and write NXxas NeXus files
"""

import h5py
import datetime
import numpy as np
from mmg_toolbox import __version__
from mmg_toolbox.spectra_analysis import energy_range_edge_label
import mmg_toolbox.nexus_writer as nw
from mmg_toolbox.spectra_scan import Spectra


def generate_analysis_steps(**kwargs: Spectra) -> dict[str, dict[str, Spectra]]:
    """
    Generate analysis steps for single set of spectra
    """
    return {name: {spectra.mode if spectra.mode else 'tey': spectra} for name, spectra in kwargs.items()}


def analyse_nxxas(energy: np.ndarray, signals: dict[str, np.ndarray], monitor: np.ndarray) -> dict[str, dict[str, Spectra]]:
    """
    Analyser spectra
    """
    # check spectra
    for detector, array in signals.items():
        if len(array) != len(energy):
            print(f"Removing signal '{detector}' as the length is wrong")
            signals.pop(detector)
        if np.max(array) < 0.1:
            print(f"Removing signal '{detector}' as the values are 0")
            signals.pop(detector)
    if len(signals) == 0:
        raise ValueError("No raw_signals found")

    # perform Analysis steps
    steps = {}
    steps['raw'] = {
        name: Spectra(energy, signal / monitor, mode=name, process_label='raw', process=f"{name} / monitor")
        for name, signal in signals.items()
    }
    # 2. divide by pre-edge
    pre_edge_ev = 5
    steps['preedge'] = {name: s.divide_by_preedge(pre_edge_ev) for name, s in steps['raw'].items()}
    # 3. fit background
    peak_width_ev = 10
    corrected_spectra = {name: s.auto_edge_background(peak_width_ev) for name, s in steps['preedge'].items()}
    # Extract fitted background
    bkg_spectra = {
        name: Spectra(s.energy, s.background, mode=s.mode, process_label='background', process=s.process)
        for name, s in corrected_spectra.items()
    }
    steps['background'] = bkg_spectra
    steps['result'] = corrected_spectra
    return steps


def write_nxxas(input_filename: str, output_filename: str,
                energy: np.ndarray, raw_signals: dict[str, np.ndarray], monitor: np.ndarray,
                beamline: str, scan_no: int, start_date_iso: str, end_date_iso: str, cmd: str,
                default_mode: str, pol: str, sample_name: str, temp: float, mag_field: float,
                analysis_steps: dict[str, dict[str, Spectra]]):
    """
    Create NXxas NeXus file
    """
    if default_mode not in raw_signals:
        raise KeyError(f"mode '{default_mode}' is not available in {list(raw_signals.keys())}")
    element, edge = energy_range_edge_label(energy.min(), energy.max())

    # Create Nexus file
    with h5py.File(output_filename, 'w') as nxs:
        nw.add_entry_links(nxs, input_filename)
        entry = nw.add_nxentry(nxs, 'entry', definition='NXxas')
        nw.add_nxfield(entry, 'entry_identifier', scan_no)
        nw.add_nxfield(entry, 'start_time', start_date_iso)
        nw.add_nxfield(entry, 'end_time', end_date_iso)
        nw.add_nxfield(entry, 'scan_command', cmd)
        nw.add_nxfield(entry, 'mode', default_mode)
        nw.add_nxfield(entry, 'element', element)
        nw.add_nxfield(entry, 'edge', edge)

        instrument = nw.add_nxinstrument(root=entry, name='instrument', instrument_name=beamline)
        nw.add_nxsource(instrument, 'source')
        nw.add_nxmono(instrument, 'mono', energy_ev=energy)
        nw.add_nxdetector(instrument, 'incoming_beam', data=monitor)
        nw.add_nxdetector(instrument, 'absorbed_beam', data=raw_signals[default_mode])
        for name, signal in raw_signals.items():
            nw.add_nxdetector(instrument, name, data=signal)

        sample = nw.add_nxsample(
            root=entry,
            name='sample',
            sample_name=sample_name,
            chemical_formula='',
            temperature_k=temp,
            magnetic_field_t=mag_field,
            electric_field_v=0,
            mag_field_dir='z',
            electric_field_dir='z',
            sample_type='sample',
            description=''
        )
        nw.add_nxbeam(
            root=sample,
            name='beam',
            incident_energy_ev=float(np.mean(energy)),
            polarisation_label=pol,
            beam_size_um=None
        )

        # NXprocess - read dat
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
            sequence_index=2 if input_filename.endswith('.dat') else 1,
        )
        for n, (name, spectras) in enumerate(analysis_steps.items()):
            spectras[default_mode].create_nxnote(process, name, n + 1)

        # NXdata groups
        for name, spectras in analysis_steps.items():
            data = nw.add_nxdata(entry, name, axes=['energy'], signal=default_mode)
            nw.add_nxfield(data, 'energy', energy, units='eV')
            for signal, spec in spectras.items():
                nw.add_nxfield(data, signal, spec.signal, units='')
            entry.attrs['default'] = name

    print(f'Created {output_filename}')


def write_nxxas_alternate(input_filename: str, output_filename: str,
                          energy: np.ndarray, raw_signals: dict[str, np.ndarray], monitor: np.ndarray,
                          beamline: str, scan_no: int, start_date_iso: str, end_date_iso: str, cmd: str,
                          default_mode: str, pol: str, sample_name: str, temp: float, mag_field: float,
                          analysis_steps: dict[str, dict[str, Spectra]]):
    """
    Create NXxas NeXus file
    """
    if default_mode not in raw_signals:
        raise KeyError(f"mode '{default_mode}' is not available in {list(raw_signals)}")
    element, edge = energy_range_edge_label(energy.min(), energy.max())

    # Create Nexus file
    with h5py.File(output_filename, 'w') as nxs:
        nw.add_entry_links(nxs, input_filename)
        nxs.attrs['default'] = default_mode

        # links
        instrument = None
        sample = None
        read_dat = None

        for mode_name in next(iter(analysis_steps.values())):
            entry = nw.add_nxentry(nxs, mode_name, definition='NXxas')
            nw.add_nxfield(entry, 'entry_identifier', scan_no)
            nw.add_nxfield(entry, 'start_time', start_date_iso)
            nw.add_nxfield(entry, 'end_time', end_date_iso)
            nw.add_nxfield(entry, 'scan_command', cmd)
            nw.add_nxfield(entry, 'mode', mode_name)
            nw.add_nxfield(entry, 'element', element)
            nw.add_nxfield(entry, 'edge', edge)

            if instrument is None:
                instrument = nw.add_nxinstrument(root=entry, name='instrument', instrument_name=beamline)
                nw.add_nxsource(instrument, 'source')
                nw.add_nxmono(instrument, 'mono', energy_ev=energy)
                nw.add_nxdetector(instrument, 'incoming_beam', data=monitor)
                nw.add_nxdetector(instrument, 'absorbed_beam', data=raw_signals[mode_name])
                for name, signal in raw_signals.items():
                    nw.add_nxdetector(instrument, name, data=signal)
            else:
                entry['instrument'] = h5py.SoftLink(instrument.name)

            if sample is None:
                sample = nw.add_nxsample(
                    root=entry,
                    name='sample',
                    sample_name=sample_name,
                    chemical_formula='',
                    temperature_k=temp,
                    magnetic_field_t=mag_field,
                    electric_field_v=0,
                    mag_field_dir='z',
                    electric_field_dir='z',
                    sample_type='sample',
                    description=''
                )
                nw.add_nxbeam(
                    root=sample,
                    name='beam',
                    incident_energy_ev=float(np.mean(energy)),
                    polarisation_label=pol,
                    beam_size_um=None
                )
            else:
                entry['sample'] = h5py.SoftLink(sample.name)

            # NXmonitor
            nw.add_nxmonitor(entry, 'monitor', monitor)

            # NXprocess - read dat
            if input_filename.endswith('.dat'):
                if read_dat is None:
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
                else:
                    entry['read_dat'] = h5py.SoftLink(read_dat.name)

            # NXProcess
            process = nw.add_nxprocess(
                root=entry,
                name='process',
                program='mmg_toolbox',
                version=__version__,
                date=str(datetime.datetime.now()),
                sequence_index=1 if read_dat is None else 2,
            )
            for n, (name, spectras) in enumerate(analysis_steps.items()):
                spectras[mode_name].create_nxnote(process, name, n + 1)

            # NXxas NXdata groups
            for n, (name, spectras) in enumerate(analysis_steps.items()):
                spectras[mode_name].create_nxdata(entry, name, default=True)

    print(f'Created {output_filename}')


def create_quanty_simulation_entry(root: h5py.File, name: str, element: str, edge: str, parameters: dict,
                                   quanty_output: str, energy: np.ndarray, signals: dict[str, np.ndarray],
                                   sum_rule_analysis: str):
    """
    Create Quanty Simulation NeXus entry
    """
    entry = nw.add_nxentry(root, name, definition='NXxas')
    nw.add_nxfield(entry, 'mode', 'simulation')
    nw.add_nxfield(entry, 'element', element)
    nw.add_nxfield(entry, 'edge', edge)

    nw.add_nxsample(
        root=entry,
        name='sample',
        sample_name=element,
        chemical_formula=element,
        temperature_k=parameters.get('temperature_k', 0),
        magnetic_field_t=parameters.get('magnetic_field_t', 0),
        mag_field_dir='z',
    )

    # NXProcess
    process = nw.add_nxprocess(
        root=entry,
        name='process',
        program='Quanty',
        version='Quanty Version',
        date=str(datetime.datetime.now()),
        sequence_index=1,
    )
    nw.add_nxnote(
        root=process,
        name='quanty_input',
        description="Quanty Simulation Parameters",
        data=str(parameters),
        sequence_index=1,
    )
    nw.add_nxnote(
        root=process,
        name='quanty_output',
        description="Quanty Simulation Output",
        data=quanty_output,
        sequence_index=2,
    )
    nw.add_nxnote(
        root=process,
        name='sum_rules',
        description="Sum Rules",
        data=sum_rule_analysis,
        sequence_index=3,
    )

    # NXdata
    for name, signal in signals.items():
        data = nw.add_nxdata(entry, name, ['energy'], 'data')
        nw.add_nxfield(data, 'energy', energy, units='eV')
        nw.add_nxfield(data, 'data', signal)
    entry.attrs['default'] = name


def write_nx_xmcd(*input_filenames: str, output_filename: str,
                  energy: np.ndarray, signals: dict[str, np.ndarray],
                  beamline: str, mode: str,
                  sample_name: str, temp: float, mag_field: float,
                  sum_rule_analysis: str, simulation: dict):
    """
    Create NXxas XMCD NeXus file
    """
    if mode not in signals:
        raise KeyError(f"mode '{mode}' is not available in {list(signals.keys())}")
    element, edge = energy_range_edge_label(energy.min(), energy.max())

    polarisations = {'nc': ['file.nxs'], 'pc': ['file.nxs']}
    subtraction_type = 'xmcd' if 'nc' in polarisations else 'xmld'
    if len(polarisations) != 2:
        raise Exception('Wrong number of polarisations')

    # Create Nexus file
    with h5py.File(output_filename, 'w') as nxs:
        nw.add_entry_links(nxs, *input_filenames)

        if simulation:
            create_quanty_simulation_entry(nxs, name='simulation', **simulation)

        measurement = nw.add_nxentry(nxs, 'measurement', definition='NXxas_xmcd')
        nw.add_nxfield(measurement, 'mode', mode)
        nw.add_nxfield(measurement, 'element', element)
        nw.add_nxfield(measurement, 'edge', edge)

        instrument = nw.add_nxinstrument(root=measurement, name='instrument', instrument_name=beamline)
        nw.add_nxsource(instrument, 'source')
        nw.add_nxmono(instrument, 'mono', energy_ev=energy)

        nw.add_nxsample(
            root=measurement,
            name='sample',
            sample_name=sample_name,
            chemical_formula='',
            temperature_k=temp,
            magnetic_field_t=mag_field,
            electric_field_v=0,
            mag_field_dir='z',
            electric_field_dir='z',
            sample_type='sample',
            description=''
        )

        # NXProcess
        process = nw.add_nxprocess(
            root=measurement,
            name='process',
            program='mmg_toolbox',
            version=__version__,
            date=str(datetime.datetime.now()),
            sequence_index=1,
        )
        for n, (pol, files) in enumerate(polarisations.items()):
            nw.add_nxnote(
                root=process,
                name=pol,
                description=f"average of {mode} scans with polarisation {pol}",
                data='\n'.join(files),
                sequence_index=n + 1,
            )
        nw.add_nxnote(
            root=process,
            name=subtraction_type,
            description=f"Subtraction of polarisation states:\n    {list(polarisations)[0]} - {list(polarisations)[1]}",
            data='\n'.join(files),
            sequence_index=3,
        )
        nw.add_nxnote(
            root=process,
            name='sum_rules',
            description="Sum Rules",
            data=sum_rule_analysis,
            sequence_index=4,
        )

        for n, (pol, files) in enumerate(polarisations.items()):
            signal = get_from_files(files)
            data = nw.add_nxdata(measurement, pol, axes=['energy'], signal='absorbed_beam')
            nw.add_nxfield(data, 'mode', mode)
            nw.add_nxfield(data, 'energy', energy, units='eV')
            nw.add_nxfield(data, 'absorbed_beam', signal, units='')

        subtraction = get_from_files(polarisations)
        data = nw.add_nxdata(measurement, subtraction_type, axes=['energy'], signal='data')
        nw.add_nxfield(data, 'mode', mode)
        nw.add_nxfield(data, 'energy', energy, units='eV')
        nw.add_nxfield(data, 'data', subtraction, units='')
        measurement.attrs['default'] = subtraction_type


    print(f'Created {output_filename}')

