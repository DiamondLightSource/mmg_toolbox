"""
mmg_toolbox tests
Test utilities
"""
import numpy as np

from mmg_toolbox.utils import xray_utils, rotations, misc_functions


def test_wavelength():
    assert abs(xray_utils.photon_energy(1.0) - 12.398) < 0.01
    assert abs(xray_utils.photon_wavelength(8) - 1.55) < 0.01
    assert abs(xray_utils.wavevector(1.0) - 6.283) < 0.01


def test_rotation():
    rotation = rotations.rotation_t_matrix(30, (1, 1, 0))
    translation = rotations.translation_t_matrix(5, (0, 0, 1))
    total = translation @ rotation
    vec = (1, 1, 1)
    new_vec1 = rotations.transform_by_t_matrix(vec, rotation)
    new_vec2 = rotations.transform_by_t_matrix(new_vec1, translation)
    new_vec3 = rotations.transform_by_t_matrix(vec, total)
    assert np.allclose(new_vec2, new_vec3)



