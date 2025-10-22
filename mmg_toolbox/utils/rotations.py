import numpy as np


def norm_vector(vector, min_mag=0.001):
    mag = np.linalg.norm(vector)
    if mag < min_mag:
        mag = 1.
    return np.divide(vector, mag)


def rot_matrix(angle_rad: float, axis=(0, 0, 1)):
    """
    Generate rotation matrix about arbitary axis
    https://en.wikipedia.org/wiki/Rotation_matrix#Rotation_matrix_from_axis_and_angle
    """
    axis = norm_vector(axis)
    ux, uy, uz = axis
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    c1 = 1 - c
    r = np.array([
        [
            (ux * ux * c1) + c,
            (uy * ux * c1) - uz * s,
            (uz * ux * c1) + uy * s
        ],
        [
            (ux * uy * c1) + uz * s,
            (uy * uy * c1) + c,
            (uz * uy * c1) - ux * s,
        ],
        [
            (ux * uz * c1) - uy * s,
            (uy * uz * c1) + ux * s,
            (uz * uz * c1) + c,
        ]
    ])
    return r


def rotation_t_matrix(value=0.0, vector=(0, 0, 1), offset=(0, 0, 0)):
    """
    Create 4x4 transformation matrix including a rotation
    """
    t = np.eye(4)
    t[:3, :3] = rot_matrix(angle_rad=value, axis=vector)
    t[:3, 3] = offset
    return t


def translation_t_matrix(value=0.0, vector=(0, 0, 1), offset=(0, 0, 0)):
    """
    Create 4x4 transformation matrix including a translation
    """
    t = np.eye(4)
    translation = value * np.reshape(vector, 3) + np.reshape(offset, 3)
    t[:3, 3] = translation
    return t


def rotate_by_matrix(xyz, angle_deg=0.0, axis=(0, 0, 1)):
    r = rot_matrix(np.deg2rad(angle_deg), axis)
    xyz = np.reshape(xyz, (-1, 3))
    return np.dot(r, xyz.T).T


def transform_by_t_matrix(xyz, t_matrix):
    xyz = np.reshape(xyz, (-1, 3))
    return (np.dot(t_matrix[:3, :3], xyz.T) + t_matrix[:3, 3:]).T
