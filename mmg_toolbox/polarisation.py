"""
Polarisation utilities
"""

import numpy as np
import h5py

from .nexus_functions import nx_find, bytes2str


# Polarisation field names inside NeXus groups
# See https://manual.nexusformat.org/classes/base_classes/NXbeam.html#nxbeam
NX_POLARISATION_FIELDS = [
    'incident_polarization_stokes',  # NXbeam
    'incident_polarization',  # NXbeam
    'polarisation',  # DLS specific in NXinsertion_device
]


class PolLabels:
    linear_horizontal = 'lh'
    linear_vertical = 'lv'
    circular_left = 'cl'
    circular_right = 'cr'
    circular_positive = 'pc'  # == circular_right
    circular_negative = 'nc'  # == circular_left
    linear_dichroism = 'xmld'
    circular_dichroism = 'xmcd'


def stokes_from_vector(*parameters: float) -> tuple[float, float, float, float]:
    """
    Return the Stokes parameters from an n-length vector
    """
    if len(parameters) == 4:
        p0, p1, p2, p3 = parameters
    elif len(parameters) == 3:
        p0 = 1
        p1, p2, p3 = parameters
    elif len(parameters) == 2:
        # polarisation vector [h, v]
        h, v = parameters
        p0, p3 = 1, 0
        phi = np.arctan2(v, h)
        p1, p2 = np.cos(2*phi), np.sin(2*phi)
    else:
        raise ValueError(f"Stokes parameters wrong length: {parameters}")
    return p0, p1, p2, p3


def polarisation_label_from_stokes(*stokes_parameters: float):
    """Convert Stokes vector to polarisation mode"""
    p0, p1, p2, p3 = stokes_from_vector(*stokes_parameters)
    circular = abs(p3) > 0.1
    if not circular and p1 > 0.9:
        return PolLabels.linear_horizontal
    if not circular and p1 < -0.9:
        return PolLabels.linear_vertical
    if circular and p3 > 0:
        return PolLabels.circular_right
    if circular and p3 < 0:
        return PolLabels.circular_left
    raise ValueError(f"Stokes parameters not recognized: {stokes_parameters}")


def polarisation_label_to_stokes(label: str) -> tuple[float, float, float, float]:
    """Convert polarisation mode to Stokes vector"""
    label = bytes2str(label).strip().lower()
    match label:
        case PolLabels.linear_horizontal:
            return 1, 1, 0, 0
        case PolLabels.linear_vertical:
            return 1, -1, 0, 0
        case PolLabels.circular_right:
            return 1, 0, 0, 1
        case PolLabels.circular_left:
            return 1, 0, 0, -1
        # assume positive-circular is right-handed
        case PolLabels.circular_positive:
            return 1, 0, 0, 1
        case PolLabels.circular_negative:
            return 1, 0, 0, -1
    return 1, 0, 0, 0


def check_polarisation(label: str) -> str:
    """Return regularised polarisation mode"""
    return polarisation_label_from_stokes(*polarisation_label_to_stokes(label))


def get_polarisation(pol: h5py.Dataset | h5py.Group) -> str:
    """
    Return polarisation mode from h5py Dataset, Group or File

    Raises ValueError if polarisation not recognized.

    Example:
        with h5py.File('data.nxs', 'r') as hdf:
            pol = get_polarisation(hdf)
            # -or-
            dataset = nx_find(hdf, 'NXbeam', 'incident_polarization_stokes')
            pol = get_polarisation(dataset)

    Parameters:
    :param pol: h5py.Dataset or h5py.Group object
    :return: polarisation mode
    """
    if isinstance(pol, h5py.Group):
        for label in NX_POLARISATION_FIELDS:
            dataset = nx_find(pol, label)
            if dataset:  # DLS specific polarisation mode
                return get_polarisation(dataset)
    if np.issubdtype(pol.dtype, np.number):
        return polarisation_label_from_stokes(*pol)
    return check_polarisation(pol[()])


def pol_subtraction_label(label: str):
    """Return xmcd or xmld"""
    label = check_polarisation(label)
    if label in [PolLabels.linear_horizontal, PolLabels.linear_vertical]:
        return PolLabels.linear_dichroism
    elif label in [PolLabels.circular_left, PolLabels.circular_right]:
        return PolLabels.circular_dichroism
    else:
        raise ValueError(f"Polarisation label not recognized: {label}")

