"""
Specific beamline metadata
"""

META_LABEL = "{(cmd|scan_command)}"

META_STRING = """
{filename}
{filepath}
{start_time}
cmd = {(cmd|scan_command)}
axes = {_axes}
signal = {_signal}
detector = {_IMAGE.split('/')[-2] if '/' in _IMAGE else 'none'}
shape = {axes.shape}
"""

I06_1_META_STRING = META_STRING + """
endstation: {end_station}
sample = {sample_name}
energy = {mean((energyh|incident_energy)):.0f} eV
pol = {polarisation}
field = {field_x?(0)**2 + field_y?(0)**2 + field_z?(0)**2:.2f} T
temp = {(lakeshore336_cryostat|itc3_device_sensor_temp?(300)):.2f} K
sample y pos = {scm_y?(0):.2f} 
pitch = {m7_pitch?(0):.2f}
"""

I10_1_META_STRING = META_STRING + """
endstation: {endstation}
sample = {sample_name}
energy = {mean(energyh?(0)):.0f} eV
pol = {polarisation}
field = {(magnet_field|ips_demand_field?(0)):.2f} T
temp = {(lakeshore336_cryostat|itc3_device_sensor_temp?(300)):.2f} K
sample y pos = {(em_y|hfm_y?(0)):.2f} 
pitch = {(em_pitch|hfm_pitch?(0)):.2f}
"""

I16_META_STRING = META_STRING + """
sample = {sample_name}
energy = {mean(incident_energy):.0f} eV
pol = {stokes:.2f} analyser: {analyser_name}({analyser_order}) {pa_detector_name}
temp = {Tsample?(300):.2f} K

hkl = ({mean(diffractometer_sample_h):.2g},{mean(diffractometer_sample_k):.2g},{mean(diffractometer_sample_l):.2g})
psi = {mean(diffractometer_sample_psi):.2f} Deg, azir=({diffractometer_sample_azih},{diffractometer_sample_azik},{diffractometer_sample_azil})
sx = {mean(sx):6.2f}, sy = {mean(sy):6.2f}, sz = {mean(sz):6.2f} mm
eta = {mean(diffractometer_sample_eta):6.2f}, chi = {mean(diffractometer_sample_chi):6.2f}, phi = {mean(diffractometer_sample_phi):6.2f}, mu = {mean(diffractometer_sample_mu):6.2f}  Deg
delta = {mean(diffractometer_sample_delta):6.2f}, gamma = {mean(diffractometer_sample_gam):6.2f}  Deg

Atten = {Atten} ({100 * Transmission: .3g} %)
ss = [{s5xgap:.3g}, {s5ygap:.3g}]
ds = [{s7xgap:.3g}, {s7ygap:.3g}]
"""

BEAMLINE_META = {
    'i06': META_STRING,
    'i06-1': I06_1_META_STRING,
    'i06-2': META_STRING,
    'i10': META_STRING,
    'i10-1': I10_1_META_STRING,
    'i16': I16_META_STRING,
    'i21': META_STRING,
}