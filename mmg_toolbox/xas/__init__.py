"""
X-Ray Absorption Spectroscopy (XAS) tools
"""


from .absorption_edges import Edge, MultiEdge, Element, xray_edges_in_range, find_spectra_edge, get_edges
from .metadata import XasMetadata
from .spectra import Spectra, SpectraSubtraction, SpectraAverage
from .spectra_container import SpectraContainer, SpectraContainerSubtraction, SpectraContainerAverage
from .container_functions import average_scans, average_polarised_scans, polarised_pairs, pair_scans, find_similar_measurements
from .nxxas_loader import load_xas_scans, create_xas_scan

__all__ = [
    'Spectra', 'SpectraSubtraction', 'SpectraAverage',
    'SpectraContainer', 'SpectraContainerSubtraction', 'SpectraContainerAverage',
    'load_xas_scans', 'create_xas_scan', 'find_similar_measurements',
    'average_scans', 'average_polarised_scans', 'polarised_pairs', 'pair_scans',
    'XasMetadata', 'Element', 'Edge', 'MultiEdge', 'find_spectra_edge', 'xray_edges_in_range', 'get_edges'
]
