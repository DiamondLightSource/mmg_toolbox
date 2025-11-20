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


" --------------------------------------------------------------------- "
" --------------------------- Wavevectors ----------------------------- "
" --------------------------------------------------------------------- "


def wavevector(wavelength_a):
    """Return wavevector = 2pi/lambda"""
    return 2 * Const.pi / wavelength_a


def resolution2energy(res, twotheta=180.):
    """
    Calcualte the energy required to achieve a specific resolution at a given two-theta
    :param res: measurement resolution in A (==d-spacing)
    :param twotheta: Bragg angle in Degrees
    :return: float
    """
    theta = twotheta * Const.pi / 360  # theta in radians
    return (Const.h * Const.c * 1e10) / (res * np.sin(theta) * Const.e * 2 * 1000.)


def diffractometer_twotheta(delta=0, gamma=0):
    """Return the Bragg 2-theta angle for diffractometer detector rotations delta (vertical) and gamma (horizontal)"""
    delta = np.deg2rad(delta)
    gamma = np.deg2rad(gamma)
    twotheta = np.arccos(np.cos(delta) * np.cos(gamma))
    return np.rad2deg(twotheta)


def you_normal_vector(eta=0, chi=90, mu=0):
    """
    Determine the normal vector using the You diffractometer angles
      you_normal_vector(0, 0, 0) = [1, 0, 0]
      you_normal_vector(0, 90, 0) = [0, 1, 0]
      you_normal_vector(90, 90, 0) = [0, 0, -1]
      you_normal_vector(0, 0, 90) = [0, 0, -1]
    :param eta: angle (deg) along the x-axis
    :param mu: angle (deg) about the z-axis
    :param chi: angle deg) a
    :return: array
    """
    eta = np.deg2rad(eta)
    chi = np.deg2rad(chi)
    mu = np.deg2rad(mu)
    normal = np.array([np.sin(mu) * np.sin(eta) * np.sin(chi) + np.cos(mu) * np.cos(chi),
                       np.cos(eta) * np.sin(chi),
                       -np.cos(mu) * np.sin(eta) * np.sin(chi) - np.sin(mu) * np.cos(chi)])
    return normal


def wavevector_i(wavelength_a):
    """
    Returns a 3D wavevector for the initial wavevector
    """
    k = wavevector(wavelength_a)
    return np.array([0, 0, k])


def wavevector_f(wavelength_a, delta=0, gamma=0):
    """
    Returns a 3D wavevector for the final wavevector
    """
    k = wavevector(wavelength_a)
    sd = np.sin(np.deg2rad(delta))
    sg = np.sin(np.deg2rad(gamma))
    cd = np.cos(np.deg2rad(delta))
    cg = np.cos(np.deg2rad(gamma))
    return k * np.array([sg * cd, sd, cg * cd])


def wavevector_t(wavelength_a, delta=0, gamma=0):
    """
    Returns the wavevector transfer in inverse-Angstroms
      Q = kf - ki
    """
    ki = wavevector_i(wavelength_a)
    kf = wavevector_f(wavelength_a, delta, gamma)
    return kf - ki


def polarisation_sigma(delta=0, gamma=0):
    """
    Returns the scattered polerisation vector in the sigma' channel
    """
    sd = np.sin(np.deg2rad(delta))
    sg = np.sin(np.deg2rad(gamma))
    cd = np.cos(np.deg2rad(delta))
    cg = np.cos(np.deg2rad(gamma))
    return np.array([cg, 0, -sg])


def polarisation_pi(delta=0, gamma=0):
    """
    Returns the scattered polerisation vector in the Pi' channel
    """
    sd = np.sin(np.deg2rad(delta))
    sg = np.sin(np.deg2rad(gamma))
    cd = np.cos(np.deg2rad(delta))
    cg = np.cos(np.deg2rad(gamma))
    return np.array([-sg * sd, cd, -cg * sd])


