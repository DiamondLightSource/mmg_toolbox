"""
Create an idealised nexus file for I16
"""

import h5py
import datetime
import numpy as np
import mmg_toolbox.nexus_writer as nw
from mmg_toolbox.diffcalc import UB
from mmg_toolbox.fitting import gauss


# Metadata
scan_number = 12345
start_time = datetime.datetime.now().isoformat()
end_time = datetime.datetime.now().isoformat()
cmd = 'scan l 6.9 7.1 0.01 pol 90 merlin 1'
sample = 'mySample'
energy = 8 # keV
stokes = 90

# Calculate angles using DiffCalc
ub = UB()
ub.latt(2.85, 2.85, 10.8, 90, 90, 120)
ub.add_reflection('ref1', (0, 0, 6), eta=55, chi=92, delta=51, energy_kev=8)
ub.add_orientation('or1', hkl=(1, 0, 0), xyz=(0, 1, 0))
ub.calcub('ref1', 'or1')
ub.con('gamma',0, 'mu',0, 'bisect')
ub.set_lab_transformation(np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]]))  # transforms from Diffractometer axis to lab

scan_range_l = np.arange(6.9, 7.101, 0.01)
angles = [ub.hkl2angles((0, 0, float(lval)), energy) for lval in scan_range_l]
phi, chi, eta, mu, delta, gamma = (
    np.array([_angles[axis] for _angles in angles])
    for axis in ['phi', 'chi', 'eta', 'mu', 'delta', 'gamma']
)
hkl = np.array([
    ub.angles2hkl(phi[n], chi[n], eta[n], mu[n], delta[n], gamma[n], energy_kev=energy)
    for n in range(len(angles))
])
# 3D Gauss
det_size = (101, 101)
gauss1d = gauss(scan_range_l, height=1000, cen=6.98, fwhm=0.02, bkg=0)
gauss2d = gauss(np.arange(det_size[0]), np.arange(det_size[1]), height=1, cen=41, fwhm=15, bkg=0, cen_y=35)
images = np.array([
    g * gauss2d + np.random.rand(det_size[0], det_size[1]) for g in gauss1d
])
image_sum = images.sum(axis=2).sum(axis=1)
monitor = np.ones_like(image_sum)

# Create NeXus File
with h5py.File(f"i16_{scan_number}.nxs", 'w') as hdf:
    entry = nw.add_nxentry(hdf, name='entry', definition='NXrexs')
    nw.add_nxfield(entry, 'entry_identifier', scan_number)
    nw.add_nxfield(entry, 'start_time', start_time)
    nw.add_nxfield(entry, 'end_time', end_time)
    nw.add_nxfield(entry, 'scan_command', cmd)
    hdf.attrs['default'] = entry.name

    # Instrument
    instrument = nw.add_nxinstrument(entry, 'instrument', 'i16')
    nw.add_nxsource(instrument, name='source', source_name='dls', source_type='Synchrotron X-ray Source',
                    probe='x-ray', energy_gev=3.0)
    nw.add_nxinsertion_device(instrument, 'insertion_device', id_type='undulator', gap=9.0, harmonic=7)
    nw.add_channel_cut_mono(
        instrument=instrument,
        name='mono',
        energy=energy,
        d_spacing=3.13541611,
        crystal_type='Si',
        units='keV',
        reflection=(1, 1, 1),
        order_no=1
    )
    nw.add_nxmonitor(instrument, 'monitor', monitor)
    diff = nw.add_6circle_diffractometer(
        instrument=instrument,
        name='diffractometer',
        phi=phi,
        chi=chi,
        eta=eta,
        mu=mu,
        delta=delta,
        gamma=gamma,
    )
    diff_sample_axis = diff['sample/phi']
    det_arm_axis = diff['detector_arm/delta']
    nw.add_analyser_detector(
        instrument=instrument,
        name='detector',
        data=images,
        d_spacing=6.711,
        crystal_type='HOPG',
        reflection=(0, 0, 1),
        order_no=6,
        bragg=87.70516,
        stokes=stokes,
        sample_analyser_distance_mm=1000,
        analyser_det_distance_mm=50,
        pixel_size_mm=0.055,
        depends_on=det_arm_axis.name
    )

    # Sample
    sample = nw.add_nxsample(
        root=entry,
        name='sample',
        sample_name=sample,
        chemical_formula='',
        sample_type='sample',
        description='single crystal sample',
        temperature_k=300,
        electric_field_v=0,
        magnetic_field_t=0,
        mag_field_dir='z',
        electric_field_dir='z'
    )
    nw.add_nxfield(sample, 'unit_cell', ub.lp())
    nw.add_nxfield(sample, 'ub_matrix', ub.ub_matrix())
    nw.add_nxfield(sample, 'orientation_matrix', ub.orientation_matrix())
    # Diffcalc
    nw.add_nxnote(
        root=sample,
        name='diffcalc',
        description='DiffCalc JSON',
        data=ub.asdict(),
    )
    # beam
    beam = nw.add_nxbeam(
        root=sample,
        name='beam',
        beam_size_um=(200, 30),
        incident_energy_ev=energy * 1000,
        polarisation_label='lh'
    )
    # add sample transformations
    nw.add_nxfield(sample, 'depends_on', diff_sample_axis.name)

    # data
    plot_data = nw.add_nxdata(entry, 'data', axes=['l'], signal='total')
    nw.add_nxfield(plot_data, 'h', hkl[:, 0])
    nw.add_nxfield(plot_data, 'k', hkl[:, 1])
    nw.add_nxfield(plot_data, 'l', hkl[:, 2])
    nw.add_nxfield(plot_data, 'phi', phi)
    nw.add_nxfield(plot_data, 'chi', chi)
    nw.add_nxfield(plot_data, 'eta', eta)
    nw.add_nxfield(plot_data, 'mu', mu)
    nw.add_nxfield(plot_data, 'delta', delta)
    nw.add_nxfield(plot_data, 'gamma', gamma)
    nw.add_nxfield(plot_data, 'monitor', monitor)
    nw.add_nxfield(plot_data, 'total', image_sum)



print('Finished!')