"""
mmg_toolbox example
Example script showing how to extract metadata from NeXus files
"""

from mmg_toolbox import Experiment, metadata

# if beamline matches one of the in-built beamline configs,
# various metadata will be pre-populated
beamline = 'i16'

exp = Experiment(r"D:\I16_Data\mm22052-1", instrument=beamline)

# print all scans in folder
m = f"{metadata.scanno}, {metadata.start}, {metadata.cmd}, {metadata.energy}, {metadata.temp}"
for scan in exp[:10]:
    scn, start, cmd, energy, temp = scan(m)
    print(f"{start:%Y-%m-%d %H:%M} {scn} E={energy:.3f}, T={temp:.1f} K, {cmd}")


scan = exp.scan(776058)

# printing the scan displays a beamline dependent string containing
# various metadata, defined at mmg_toolbox.beamline_metadata.metadata_strings
print(scan)

# access metadata or scan data by accessing the scan namespace
cmd = scan('scan_command')
# or create formatted strings
energy_str = scan.format('Energy = {incident_energy:.2f} {incident_energy@units?("keV")}')
# note that '@' is used to access dataset attributes and ?() is used to handle missing fields
print(energy_str)

# The map of metadata names associated with the scan can be found in scan.map
metadata_names = list(scan.map.metadata.keys())



