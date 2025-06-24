"""
Generic metadata from NeXus files for use by HdfMap
"""

class HdfMapXASMetadata:
    """HdfMap Eval commands for I06 & I10 metadata"""
    cmd = '(cmd|user_command|scan_command)'
    date = 'start_time'
    pol = 'polarisation?("lh")'
    iddgap = 'iddgap'
    rowphase = 'idutrp if iddgap == 100 else iddtrp'
    beamline = 'beamline|instrument_name'
    endstation = 'end_station|instrument_name'
    mode = '"tey"'  # currently grabs the last NXdata.mode, not the first
    temp = '(T_sample|itc3_device_sensor_temp|lakeshore336_cryostat|lakeshore336_sample?(300))'
    rot = '(scmth|xabs_theta|ddiff_theta|em_pitch|hfm_pitch?(0))'
    field = 'np.sqrt(field_x?(0)**2 + field_y?(0)**2 + field_z?(0)**2)'
    field_x = 'field_x?(0)'
    field_y = 'field_y?(0)'
    field_z = '(magnet_field|ips_demand_field|field_z?(0))'
    energy = '(fastEnergy|pgm_energy|energye|energyh|energy)'
    monitor = '(C2|ca62sr|mcs16|macr16|mcse16|macj316|mcsh16|macj216)'
    tey = '(C1|ca61sr|mcs17|macr17|mcse17|macj317|mcsh17|macj217)'
    tfy = '(C3|ca63sr|mcs18|macr18|mcse18|macj318|mcsh18|macaj218)'

