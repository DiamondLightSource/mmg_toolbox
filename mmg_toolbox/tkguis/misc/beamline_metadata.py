"""
Specific beamline metadata
"""

META_STRING = """
{filename}
{filepath}
{start_time}
cmd = {scan_command}
axes = {_axes}
signal = {_signal}
shape = {axes.shape}
"""

I10_1_META_STRING = META_STRING + """
endstation: {endstation}
energy = {np.mean(energyh?(0)):.0f} eV
pol = {polarisation}
field = {(magnet_field|ips_demand_field?(0)):.2f} T
temp = {(lakeshore336_cryostat|itc3_device_sensor_temp?(300)):.2f} K
sample y pos = {(em_y|hfm_y?(0)):.2f} 
pitch = {(em_pitch|hfm_pitch?(0)):.2f}
"""

BEAMLINE_META = {
    'i06': META_STRING,
    'i06-1': META_STRING,
    'i06-2': META_STRING,
    'i10': META_STRING,
    'i10-1': I10_1_META_STRING,
    'i16': META_STRING,
    'i21': META_STRING,
}