"""
Crystal Lattice functions for diffraction
"""

import numpy as np

from ..utils.units import unit_converter


def wavevector(wavelength, units='angstrom'):
    """Return wavevector = 2pi/lambda"""
    wavelength_a = unit_converter(wavelength, units, 'angstrom')
    return 2 * np.pi / wavelength_a


def calqmag(twotheta, wavelength, wl_units='angstrom'):
    """
    Calculate |Q| at a particular 2-theta (deg) for energy in keV
     magQ = calqmag(twotheta, wavelength_a=1.5)
    """
    wavelength_a = unit_converter(wavelength, wl_units, 'angstrom')
    theta = twotheta * np.pi / 360  # theta in radians
    magq = np.sin(theta) * 4 * np.pi / wavelength_a
    return magq


def cal2theta(qmag, wavelength, wl_units='angstrom'):
    """
    Calculate 2theta of |Q| in degrees
     twotheta = cal2theta(q_mag, wavelength_a=1.5)
    """
    wavelength_a = unit_converter(wavelength, wl_units, 'angstrom')
    tth = 2 * np.arcsin(qmag * wavelength_a / (4 * np.pi))
    tth = tth * 180 / np.pi
    return tth


def caldspace(twotheta, wavelength, wl_units='angstrom'):
    """
    Calculate d-spacing from two-theta
     dspace = caldspace(tth, wavelength_a=1.5)
    """
    wavelength_a = unit_converter(wavelength, wl_units, 'angstrom')
    qmag = calqmag(twotheta, wavelength_a)
    dspace = q2dspace(qmag)
    return dspace


def q2dspace(qmag):
    """
    Calculate |Q| in inverse Angstroms from d-spacing in Angstroms
         dspace = q2dspace(Qmag)
    """
    return 2 * np.pi / qmag


def dspace2q(dspace):
    """
    Calculate d-spacing in Angstroms from |Q| in inverse Angstroms
         Qmag = q2dspace(dspace)
    """
    return 2 * np.pi / dspace


def bragg_en(energy, d_space, en_units='keV'):
    """Returns the Bragg angle for a given d-space at given photon energy in keV"""
    energy_kev = unit_converter(energy, en_units, 'keV')
    return np.rad2deg(np.arcsin(6.19922 / (energy_kev * d_space)))


def bragg_wl(wavelength, d_space, wl_units='angstrom'):
    """Returns the Bragg angle for a given d-space at given wavelength in Angstroms"""
    wavelength_a = unit_converter(wavelength, wl_units, 'angstrom')
    d_space = np.rad2deg(np.arcsin(wavelength_a / (2 * d_space)))
    return unit_converter(d_space, 'angstrom', wl_units)


def bragg(d_space, wavelength=None, energy=None, wl_units='angstrom', en_units='keV'):
    """Returns the photon Bragg angle in Degrees for a given d-space in Angstroms"""
    if wavelength is None:
        return bragg_en(energy, d_space, en_units=en_units)
    else:
        return bragg_wl(wavelength, d_space, wl_units=wl_units)


def scherrer_size(fwhm, twotheta, wavelength_a, shape_factor=0.9):
    """
    Use the Scherrer equation to calculate the size of a crystallite from a peak width
      L = K * lambda / fwhm * cos(theta)
    See: https://en.wikipedia.org/wiki/Scherrer_equation
    :param fwhm: full-width-half-maximum of a peak, in degrees
    :param twotheta: 2*Bragg angle, in degrees
    :param wavelength_a: incident beam wavelength, in Angstroms
    :param shape_factor: dimensionless shape factor, dependent on shape of crystallite
    :return: float, crystallite domain size in Angstroms
    """

    delta_theta = np.deg2rad(fwhm)
    costheta = np.cos(np.deg2rad(twotheta / 2.))
    return shape_factor * wavelength_a / (delta_theta * costheta)


def scherrer_fwhm(size, twotheta, wavelength_a, shape_factor=0.9):
    """
    Use the Scherrer equation to calculate the size of a crystallite from a peak width
      L = K * lambda / fwhm * cos(theta)
    See: https://en.wikipedia.org/wiki/Scherrer_equation
    :param size: crystallite domain size in Angstroms
    :param twotheta: 2*Bragg angle, in degrees
    :param wavelength_a: incident beam wavelength, in Angstroms
    :param shape_factor: dimensionless shape factor, dependent on shape of crystallite
    :return: float, peak full-width-at-half-max in degrees
    """
    costheta = np.cos(np.deg2rad(twotheta / 2.))
    return np.rad2deg(shape_factor * wavelength_a / (size * costheta))


def bmatrix(a: float, b: float | None = None, c: float | None = None,
            alpha: float = 90., beta: float = 90., gamma: float = 90.) -> np.ndarray:
    """
    Calculate the B matrix as defined in Busing&Levy Acta Cyst. 22, 457 (1967)
    Creates a matrix to transform (hkl) into a cartesian basis:
        (qx,qy,qz)' = B.(h,k,l)'       (where ' indicates a column vector)

    The B matrix is related to the reciprocal basis vectors:
        (astar, bstar, cstar) = 2 * np.pi * B.T
    Where cstar is defined along the z axis

    The B matrix is related to the real-space unit vectors:
        (vec_a, vec_b, vec_c) = B^-1 = inv(B)
    Where vec_b is defined along the y axis

    :param a: lattice parameter a in Angstroms
    :param b: lattice parameter b in Angstroms
    :param c: lattice parameter c in Angstroms
    :param alpha: lattice angle alpha in degrees
    :param beta: lattice angle beta in degrees
    :param gamma: lattice angle gamma in degrees
    :returns: [3x3] array B matrix in inverse-Angstroms (no 2pi)
    """
    if b is None:
        b = a
    if c is None:
        c = a
    alpha1 = np.deg2rad(alpha)
    alpha2 = np.deg2rad(beta)
    alpha3 = np.deg2rad(gamma)

    beta1 = np.arccos((np.cos(alpha2) * np.cos(alpha3) - np.cos(alpha1)) / (np.sin(alpha2) * np.sin(alpha3)))
    beta2 = np.arccos((np.cos(alpha1) * np.cos(alpha3) - np.cos(alpha2)) / (np.sin(alpha1) * np.sin(alpha3)))
    beta3 = np.arccos((np.cos(alpha1) * np.cos(alpha2) - np.cos(alpha3)) / (np.sin(alpha1) * np.sin(alpha2)))

    b1 = 1 / (a * np.sin(alpha2) * np.sin(beta3))
    b2 = 1 / (b * np.sin(alpha3) * np.sin(beta1))
    b3 = 1 / (c * np.sin(alpha1) * np.sin(beta2))

    c1 = b1 * b2 * np.cos(beta3)
    c2 = b1 * b3 * np.cos(beta2)
    c3 = b2 * b3 * np.cos(beta1)

    bm = np.array([
        [b1, b2 * np.cos(beta3), b3 * np.cos(beta2)],
        [0, b2 * np.sin(beta3), -b3 * np.sin(beta2) * np.cos(alpha1)],
        [0, 0, 1 / c]
    ])
    return bm


def reciprocal_lattice(a_vec: np.ndarray, b_vec: np.ndarray, c_vec: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate the reciprocal lattice vectors from real lattice vectors

    :param a_vec: [3x1] basis vector a in Angstroms
    :param b_vec: [3x1] basis vector b in Angstroms
    :param c_vec: [3x1] basis vector c in Angstroms
    :returns: [3x1], [3x1], [3x1]  reciprocal lattice vectors
    """
    astar, bstar, cstar = 2 * np.pi * np.linalg.inv([a_vec, b_vec, c_vec]).T
    return astar, bstar, cstar

