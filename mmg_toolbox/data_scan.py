"""
Spectra scan
"""
from __future__ import annotations

import os
import numpy as np
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import hdfmap

from .env_functions import get_scan_number
from .misc_functions import numbers2string


class Scan:
    def __init__(self, filename: str, hdf_map: hdfmap.NexusMap | None = None,
                 scan_names: dict | None = None, metadata_names: dict | None = None):
        if scan_names is None:
            scan_names = {}
        if metadata_names is None:
            metadata_names = {}
        self.filename = os.path.abspath(filename)
        self.basename = os.path.basename(filename)
        self.scan_number = get_scan_number(filename)
        self.map = hdfmap.create_nexus_map(filename) if hdf_map is None else hdf_map
        # default_scan = np.ones(self.map.scannables_shape())

        with hdfmap.load_hdf(filename) as nxs:
            self.scan_data = {
                name: self.map.eval(nxs, expr) for name, expr in scan_names.items()
            }
            self.metadata = {
                name: self.map.format_hdf(nxs, expr) for name, expr in metadata_names.items()
            }

    def __repr__(self):
        return f"Scan<{self.scan_number}>"

    def eval(self, expression: str, default=None):
        """Open file and evaluate namespace string"""
        return self.map.eval(self.map.load_hdf(), expression, default=default)

    def format(self, expression: str, default=None):
        """Open file and evaluate namespace format string"""
        return self.map.format_hdf(self.map.load_hdf(), expression, default=default)

    def test(self):
        print('Scan method: ', repr(self))


class Process:
    """
    Container for process, such as multiple scans
    """
    def __init__(self, description: str, *parents: Scan | Process, **kwargs):
        self.parents = list(parents)
        self.description = description
        self.processed_data = kwargs

    def scan_numbers(self):
        numbers = [parent.scan_number for parent in self.parents if hasattr(parent, 'scan_number')]
        if numbers:
            return numbers2string(numbers)
        return ''

    def __repr__(self):
        return f"Process('{self.description}', {self.scan_numbers()})"

