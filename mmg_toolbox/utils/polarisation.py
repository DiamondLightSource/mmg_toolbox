"""
Polarisation utilities
"""

import numpy as np
import h5py

from mmg_toolbox.nexus.nexus_functions import nx_find, bytes2str
from mmg_toolbox.nexus.nexus_names import NX_POLARISATION_FIELDS


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
        raise KeyError(f"{pol} contains no polarisation fields")
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


def analyser_jones_matrix(crystal_bragg: float, rotation: float) -> np.ndarray:
    """
    Return the Jones matrix for an analyser crystal
    The Jones matrix [4x4] can be used to operate on a Jones vector [2x1]
    to describe how the polarisation will be analysed.

    The basis chosen in such that x = v X z, where v is vertical and z is the incident beam direction in lab space.

    :param crystal_bragg: Scattering Bragg angle, in degrees
    :param rotation: Rotation angle about the incident beam, in degrees
    :return: Jones matrix [4x4]
    """
    bragg_rad = np.deg2rad(crystal_bragg)
    rot_rad = np.deg2rad(rotation)
    return np.array([
        [np.cos(rot_rad), -np.sin(rot_rad)],
        [np.sin(rot_rad) * np.cos(bragg_rad), np.cos(rot_rad) * np.cos(bragg_rad)]
    ])


#TODO: Check this!
def jones2mueller(jones: np.ndarray) -> np.ndarray:
    """
    Convert Jones matrix [2x2] to Mueller matrix [4x4]
    see https://en.wikipedia.org/wiki/Mueller_calculus
    """
    A = np.array([
        [1, 0, 0, 1],
        [1, 0, 0, -1],
        [0, 1, 1, 0],
        [0, 1j, -1j, 0],
    ], dtype=complex)
    mueller = np.linalg.multi_dot([A, np.kron(jones, np.conj(jones)), np.linalg.inv(A)])
    return mueller


#TODO: Check this!
def apply_jones_to_stokes(S: np.ndarray, J: np.ndarray) -> np.ndarray:
    """
    Applies a Jones matrix to a Stokes vector and returns the resulting Stokes vector.

    Parameters:
    S (array-like): Input Stokes vector [I, Q, U, V]
    J (2x2 array): Jones matrix

    Returns:
    numpy.ndarray: Transformed Stokes vector [I', Q', U', V']
    """
    I, Q, U, V = S

    # Convert Stokes to Jones vector (assuming fully polarized light)
    Ex = np.sqrt((I + Q) / 2)
    Ey = np.sqrt((I - Q) / 2)
    phase = np.arctan2(V, U)
    Ey *= np.exp(1j * phase)
    E = np.array([Ex, Ey])

    # Apply Jones matrix
    E_out = J @ E

    # Convert back to Stokes parameters
    I_out = np.real(E_out[0]*np.conj(E_out[0]) + E_out[1]*np.conj(E_out[1]))
    Q_out = np.real(E_out[0]*np.conj(E_out[0]) - E_out[1]*np.conj(E_out[1]))
    U_out = 2 * np.real(E_out[0]*np.conj(E_out[1]))
    V_out = 2 * np.imag(E_out[0]*np.conj(E_out[1]))

    return np.array([I_out, Q_out, U_out, V_out])


#TODO: Check this!
def analyse_polarisation(stokes_vector: np.ndarray, *jones_matrices: np.ndarray) -> np.ndarray:
    """
    Applies a Jones matrix to a Stokes vector and returns the resulting Stokes vector.

    Parameters:
    stokes_vector (1x4 array): incident beam Stokes parameters P0, P1, P2, P3 (I, Q, U, V)
    jones_matrix (2x2 array): Jones matrix of the optical element
    * multiple jones_matrices can be entered and will be applied in order

    Returns:
    numpy.ndarray: Transformed Stokes vector [I', Q', U', V']
    """
    I, Q, U, V = stokes_vector

    # Convert Stokes to Jones vector (assuming fully polarized light)
    Ex = np.sqrt((I + Q) / 2)
    Ey = np.sqrt((I - Q) / 2)
    phase = np.arctan2(V, U)
    Ey *= np.exp(1j * phase)
    E_in = np.array([Ex, Ey])

    # Apply Jones matrix
    # E_out = jones_matrices[0] @ E_in
    E_out = np.linalg.multi_dot(list(jones_matrices) + [E_in])

    print(f"Ein={E_in} -> Eout={E_out}")

    # Convert back to Stokes parameters
    I_out = np.real(E_out[0]*np.conj(E_out[0]) + E_out[1]*np.conj(E_out[1]))
    Q_out = np.real(E_out[0]*np.conj(E_out[0]) - E_out[1]*np.conj(E_out[1]))
    U_out = 2 * np.real(E_out[0]*np.conj(E_out[1]))
    V_out = 2 * np.imag(E_out[0]*np.conj(E_out[1]))

    return np.array([I_out, Q_out, U_out, V_out])


#TODO: Check this!
def stokes_to_lab_vector(S, beam_direction, reference_plane):
    """
    ***CHECK THIS!!!***
    Converts Stokes parameters to a 3D polarization vector in lab space.

    Parameters:
    S (array-like): Stokes vector [I, Q, U, V]
    beam_direction (array-like): 3D unit vector of beam propagation direction
    reference_plane (array-like): 3D vector defining the reference plane (e.g., horizontal)

    Returns:
    numpy.ndarray: 3D polarization vector in lab space
    """
    # Normalize input vectors
    k = np.array(beam_direction, dtype=float)
    k /= np.linalg.norm(k)
    ref = np.array(reference_plane, dtype=float)
    ref -= np.dot(ref, k) * k  # Make ref orthogonal to k
    ref /= np.linalg.norm(ref)

    # Define orthonormal basis for transverse plane
    s = ref  # s-polarization (in reference plane)
    p = np.cross(k, s)  # p-polarization (perpendicular to s and k)

    # Convert Stokes to Jones vector (assuming fully polarized light)
    I, Q, U, V = S
    Ex = np.sqrt((I + Q) / 2)
    Ey = np.sqrt((I - Q) / 2)
    phase = np.arctan2(V, U)
    Ey *= np.exp(1j * phase)
    E = np.array([Ex, Ey])

    # Construct 3D polarization vector in lab frame
    E_lab = E[0] * s + E[1] * p

    return E_lab

