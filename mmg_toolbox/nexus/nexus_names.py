
# Groups
NX_ENTRY = 'NXentry'
NX_DATA = 'NXdata'
NX_INST = 'NXinstrument'
NX_DET = 'NXdetector'
NX_SAMPLE = 'NXsample'
NX_XTL = 'NXcrystal'
NX_MODULE = 'NXdetector_module'
NX_BEAM = 'NXbeam'
NX_SOURCE = 'NXsource'
NX_ID = 'NXinsertion_device'
NX_MONO = 'NXmonochromator'
NX_MON = 'NXmonitor'
NX_NOTE = 'NXnote'
NX_PROC = 'NXprocess'
NX_TRAN = 'NXtransformations'

# Fields
NX_WL = 'incident_wavelength'
NX_EN = 'incident_energy'
NX_SHORT_NAME = 'short_name'
NX_NAME = 'name'
NX_SAMPLE_UC = 'unit_cell'
NX_SAMPLE_OM = 'orientation_matrix'
NX_SAMPLE_UB = 'ub_matrix'
NX_STOKES = 'incident_polarization_stokes'
NX_BSIZE = 'extent'
NX_MODULE_ORIGIN = 'data_origin'
NX_MODULE_SIZE = 'data_size'
NX_MODULE_OFFSET = 'module_offset'
NX_MODULE_FAST = 'fast_pixel_direction'
NX_MODULE_SLOW = 'slow_pixel_direction'

# Attributes
NX_CLASS = 'NX_class'
NX_DEFINITION = 'definition'
NX_DEFAULT = 'default'
NX_AXES = 'axes'
NX_SIGNAL = 'signal'
NX_AUXILIARY = 'auxiliary_signals'
NX_DEPON = 'depends_on'
NX_VECTOR = 'vector'
NX_OFFSET = 'offset'
NX_TTYPE = 'transformation_type'
NX_TROT = 'rotation'
NX_TTRAN = 'translation'
NX_UNITS = 'units'
NX_OFFSET_UNITS = 'offset_units'

# Other
ENTRY_CLASSES = ['NXentry', 'NXsubentry']
XAS_DEFINITIONS = ['NXxas', 'NXxas_new']
SEARCH_ATTRS = (NX_CLASS, 'local_name')  # DLS attribute 'local_name' helps match metadata to scan commands

# Polarisation field names inside NeXus groups
# See https://manual.nexusformat.org/classes/base_classes/NXbeam.html#nxbeam
NX_POLARISATION_FIELDS = [
    'incident_polarization_stokes',  # NXbeam
    'incident_polarization',  # NXbeam
    'polarisation',  # DLS specific in NXinsertion_device
]
