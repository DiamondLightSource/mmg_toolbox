

from .hdfmap_generic import HdfMapMMGMetadata, HdfMapXASMetadata, HdfMapNexus

__all__ = ['metadata', 'xas_metadata', 'nexus_metadata']

metadata = HdfMapMMGMetadata
xas_metadata = HdfMapXASMetadata
nexus_metadata = HdfMapNexus

