"""
Assess various metadata fields accross mmg beamlines
"""

from datetime import datetime
from mmg_toolbox.beamline_metadata.config import BEAMLINE_CONFIG, C
from mmg_toolbox.beamline_metadata.hdfmap_generic import HdfMapXASMetadata as M
from mmg_toolbox.utils.env_functions import get_dls_visits
from mmg_toolbox import Experiment

metadata_fields = {
    'polarisation': ['polarisation', 'incident_polarization', 'incident_polarization_stokes'],
    'temperature': [M.temp],
    'mag_field': ['sample_magnetic_field', M.field_x,
                  M.field_y, M.field_z],
}

print(f"MMG Beamlines Metadata: {datetime.today()}\n")

for beamline in BEAMLINE_CONFIG:
    visits = get_dls_visits(beamline, max_visits=3, omit_empty=True)
    print(f"\n######## Beamline: {beamline}: Visits: {len(visits)} ########\n")
    for visit, path in visits.items():
        exp = Experiment(path, instrument=beamline)
        scan, = exp.scans(-1)
        print(f"\n============ {beamline}: {visit}: {scan.filename} ============")
        with scan.load_hdf() as hdf:
            ev = lambda p: scan.map.eval(hdf, p)
            print(f"Endstation: {ev(M.endstation)}")
            print(f"cmd: {ev(M.cmd)}")
            print(f"Date: {ev(M.date)}")
            print(f"{'name':40} : {'path':60} : value")
            for name, keys in metadata_fields.items():
                for key in keys:
                    print(f"{key[:40]:40} : {ev('_'+  key):60} : {ev(key)}")

