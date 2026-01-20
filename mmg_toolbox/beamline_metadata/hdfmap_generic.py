"""
Generic metadata from NeXus files for use by HdfMap
"""

class HdfMapNexus:
    """HdfMap Eval commands for any nexus file"""
    instrument = 'NXinstrument_name?("beamline")'
    sample = 'NXsample_name?("none")'
    date = 'NXentry_start_time'
    start = 'NXentry_start_time'
    stop = 'NXentry_end_time'
    scanno = 'NXentry_entry_identifier?(0)'


class HdfMapMMGMetadata(HdfMapNexus):
    """HdfMap Eval commaands for all MMG beamlines"""
    cmd = '(cmd|user_command|scan_command)'
    temp = '(T_sample|Tsample|itc3_device_sensor_temp|lakeshore336_cryostat|lakeshore336_sample?(300))'
    beamline = '(beamline|instrument_name)'
    endstation = '(end_station|instrument_name)'
    field = 'sqrt(field_x?(0)**2 + field_y?(0)**2 + field_z?(0)**2)'
    field_x = 'field_x?(0)'
    field_y = 'field_y?(0)'
    field_z = '(magnet_field|ips_demand_field|field_z?(0))'
    energy = '(fastEnergy|pgm_energy|energye|energyh|incident_energy|energy)'
    pol = 'polarisation?("lh")'
    pol_angle = 'linear_arbitrary_angle?(0.0)'


class HdfMapXASMetadata(HdfMapMMGMetadata):
    """HdfMap Eval commands for I06 & I10 metadata"""
    # iddgap = 'idd_gap'
    # rowphase = 'idu_trp if idd_gap == 100 else idd_trp'
    mode = '"tey"'  # currently grabs the last NXdata.mode, not the first
    rot = '(scmth|xabs_theta|ddiff_theta|em_pitch|hfm_pitch?(0))'
    monitor = '(i0|C2|ca62sr|mcs16|macr16|mcse16|macj316|mcsh16|macj216)'
    tey = '(tey|C1|ca61sr|mcs17|macr17|mcse17|macj317|mcsh17|macj217)'
    tfy = '(fdu|C3|ca63sr|mcs18|macr18|mcse18|macj318|mcsh18|macaj218)'

