"""
X-Ray Absorption Spectroscopy (XAS) tools
"""


from .spectra_analysis import xray_edges_in_range, energy_range_edge_label
from .metadata import XasMetadata
from .spectra import Spectra, SpectraSubtraction, SpectraAverage
from .spectra_container import SpectraContainer, SpectraContainerSubtraction
from .container_functions import average_scans, average_polarised_scans, polarised_pairs, pair_scans
from .nxxas_loader import load_xas_scans, create_xas_scan, find_similar_measurements

__all__ = [
    'Spectra', 'SpectraSubtraction', 'SpectraAverage', 'SpectraContainer', 'SpectraContainerSubtraction',
    'load_xas_scans', 'create_xas_scan', 'find_similar_measurements',
    'average_scans', 'average_polarised_scans', 'polarised_pairs', 'pair_scans',
    'xray_edges_in_range', 'energy_range_edge_label',
    'XasMetadata'
]
