"""
X-ray scattering utility funcitons
"""

import numpy as np

# Constants
class Const:
    pi = np.pi  # mmmm tasty Pi
    e = 1.6021733E-19  # C  electron charge
    h = 6.62606868E-34  # Js  Plank consant
    c = 299792458  # m/s   Speed of light
    u0 = 4 * pi * 1e-7  # H m-1 Magnetic permeability of free space
    me = 9.109e-31  # kg Electron rest mass
    mn = 1.6749e-27 # kg Neutron rest mass
    Na = 6.022e23  # Avagadro's No
    A = 1e-10  # m Angstrom
    r0 = 2.8179403227e-15  # m classical electron radius = e^2/(4pi*e0*me*c^2)
    Cu = 8.048  # Cu-Ka emission energy, keV
    Mo = 17.4808  # Mo-Ka emission energy, keV


def photon_wavelength(energy_kev):
    """
    Converts energy in keV to wavelength in A
     wavelength_a = photon_wavelength(energy_kev)
     lambda [A] = h*c/E = 12.3984 / E [keV]
    """

    # Electron Volts:
    E = 1000 * energy_kev * Const.e

    # SI: E = hc/lambda
    lam = Const.h * Const.c / E
    wavelength = lam / Const.A
    return wavelength


def photon_energy(wavelength_a):
    """
    Converts wavelength in A to energy in keV
     energy_kev = photon_energy(wavelength_a)
     Energy [keV] = h*c/L = 12.3984 / lambda [A]
    """

    # SI: E = hc/lambda
    lam = wavelength_a * Const.A
    E = Const.h * Const.c / lam

    # Electron Volts:
    energy = E / Const.e
    return energy / 1000.0


def wavevector(wavelength_a):
    """Return wavevector = 2pi/lambda"""
    return 2 * np.pi / wavelength_a


def bmatrix(a, b=None, c=None, alpha=90., beta=90., gamma=90.):
    """
    Calculate the B matrix as defined in Busing&Levy Acta Cyst. 22, 457 (1967)
    Creates a matrix to transform (hkl) into a cartesian basis:
        (qx,qy,qz)' = B.(h,k,l)'       (where ' indicates a column vector)

    The B matrix is related to the reciprocal basis vectors:
        (astar, bstar, cstar) = 2 * np.pi * B.T
    Where cstar is defined along the z axis

    The B matrix is related to the real-space unit vectors:
        (A, B, C) = B^-1 = inv(B)

    :param a: lattice parameter a in Anstroms
    :param b: lattice parameter b in Anstroms
    :param c: lattice parameter c in Anstroms
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