"""
mmg_toolbox tests
Test utilities
"""
import numpy as np

from mmg_toolbox.diffraction import lattice
from mmg_toolbox.utils import xray_utils, rotations, misc_functions, units


def test_wavelength():
    assert abs(xray_utils.photon_energy(1.0) - 12.398) < 0.01
    assert abs(xray_utils.photon_wavelength(8) - 1.55) < 0.01
    assert abs(lattice.wavevector(1.0) - 6.283) < 0.01


def test_rotation():
    rotation = rotations.rotation_t_matrix(30, (1, 1, 0))
    translation = rotations.translation_t_matrix(5, (0, 0, 1))
    total = translation @ rotation
    vec = (1, 1, 1)
    new_vec1 = rotations.transform_by_t_matrix(vec, rotation)
    new_vec2 = rotations.transform_by_t_matrix(new_vec1, translation)
    new_vec3 = rotations.transform_by_t_matrix(vec, total)
    assert np.allclose(new_vec2, new_vec3)

    phi, eta, chi, mu = 0, 25.5 / 2, 90, 0
    r1 = rotations.rotmatrix_diffractometer(phi, chi, eta, mu)
    r2 = np.dot(
        rotations.rotmatrix_x(mu), np.dot(
            rotations.rotmatrix_z(-eta), np.dot(
                rotations.rotmatrix_y(chi), rotations.rotmatrix_z(-phi)
            )
        )
    )
    assert np.sum(np.abs(r1 - r2)) < 0.01


def test_lattice_orientation():
    np.set_printoptions(precision=3, suppress=True)
    phi, eta, chi, mu = 0, 25.5 / 2, 90, 0
    a, b, c, alpha, beta, gamma = 2.85, 2.85, 10.8, 90, 90, 120.
    b_matrix = lattice.bmatrix(a, b, c, alpha, beta, gamma)
    u_matrix = np.eye(3)
    r_matrix = rotations.rotmatrix_diffractometer(phi, chi, eta, mu)
    lab_transform = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])  # Diffcalc -> DLS
    avec, bvec, cvec = np.linalg.inv(b_matrix)
    # example magnetic moment
    mx, my, mz = 0, 0, 3
    momentmag = np.sqrt(np.sum(np.square([mx, my, mz])))
    momentxyz = np.dot([mx, my, mz], [avec, bvec, cvec])
    moment = momentmag * momentxyz / np.sqrt(np.sum(np.square(momentxyz)))  # broadcast n*1 x n*3 = n*3
    moment[np.isnan(moment)] = 0.
    # Convert to lab coordinates
    moment_lab1 = np.dot(lab_transform, np.dot(r_matrix, np.dot(u_matrix, moment)))
    print(f"\n\nMoment in lab coordinates (in uB): {moment_lab1}")

    # alternative approach
    ub_matrix = np.dot(u_matrix, b_matrix)
    ub_rl_matrix = np.dot(lab_transform, np.dot(r_matrix, ub_matrix))
    momentmag = np.sqrt(np.sum(np.square([mx, my, mz])))
    momentxyz = np.dot([mx, my, mz], np.linalg.inv(ub_rl_matrix))
    moment_lab2 = momentmag * momentxyz / np.sqrt(np.sum(np.square(momentxyz)))  # broadcast n*1 x n*3 = n*3
    moment_lab2[np.isnan(moment_lab2)] = 0.
    print(f"Moment in lab coordinates (in uB): {moment_lab2}")
    momentuvw = np.linalg.norm(moment_lab2) * np.dot(moment_lab2, ub_rl_matrix) / np.linalg.norm(np.dot(moment_lab2, ub_rl_matrix))
    print(f"Moment in crystal (in uB): {momentuvw}")
    assert np.sum(np.abs(moment_lab1 - moment_lab2)) < 0.001
    assert np.sum(np.abs(momentuvw - [mx, my, mz])) < 0.001


def test_scattering_plane():
    energy_kev = 8
    hkl = [1, 0, 6]
    a, b, c, alpha, beta, gamma = 2.85, 2.85, 10.8, 90, 90, 120.

    b_matrix = lattice.bmatrix(a, b, c, alpha, beta, gamma)
    wl = xray_utils.photon_wavelength(energy_kev)
    dspace = 1 / np.linalg.norm(np.dot(hkl, b_matrix))
    tth = lattice.bragg_wl(wl, dspace)
    assert abs(tth - 33.743) < 0.001
    tth2 = lattice.bragg(dspace, energy=energy_kev, en_units='keV')
    assert abs(tth2 - tth) < 0.001

    det_delta, det_gamma = tth, 0
    ki = xray_utils.wavevector_i(wl)
    kf = xray_utils.wavevector_f(wl, det_delta, det_gamma)
    q = kf - ki

    wv_transfer = xray_utils.wavevector_t(wl, det_delta, det_gamma)
    assert np.sum(np.abs(wv_transfer - q)) < 0.001

def test_units():
    distance = units.unit_converter(10, 'nm', 'A')
    assert distance == 100
    energy = units.unit_converter(8, 'keV', 'eV')
    assert energy == 8000


def test_misc_functions():
    assert misc_functions.stfm(35.25, 0.01) == '35.25 (1)'
    assert misc_functions.stfm(110.25, 5) == '110 (5)'
    assert misc_functions.stfm(1.5632e6,1.53e4) == '1.56(2)E+6'

    # misc_functions.numbers2string()


