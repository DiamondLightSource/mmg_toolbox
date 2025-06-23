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