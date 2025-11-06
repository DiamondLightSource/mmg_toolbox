"""
Unit conversions
"""
import numpy as np

METERS = {  # conversion to meters
    'km': 1e3, 'm': 1, 'cm': 0.1, 'mm': 1e-3,
    'um': 1e-6, 'μm': 1e-6, 'nm': 1e-9,
    'a': 1e-10, 'A': 1e-10, 'Å': 1e-10, 'angstrom': 1e-10,
}

ENERGY = {  # conversion to eV
    'keV': 1e3, 'eV': 1, 'MeV': 1e6,
}

ANGLE = {  # conversion to degrees
    'deg': np.pi / 180, 'rad': np.pi / 180,
}


def unit_converter(value: float, from_unit: str, to_unit: str):
    """
    Converts a value from one unit to another
    """
    if from_unit in METERS:
        # Distances in meters
        distance = value * METERS[from_unit]
        return distance / METERS[to_unit]
    if from_unit in ENERGY:
        # Energy in eV
        energy = value * ENERGY[from_unit]
        return energy / ENERGY[to_unit]
    if from_unit in ANGLE:
        # Angle in degrees
        angle = value * ANGLE[from_unit]
        return angle / ANGLE[to_unit]
    raise ValueError(f"Unknown unit {from_unit}")