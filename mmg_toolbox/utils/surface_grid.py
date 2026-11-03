"""
Functions to define 2D grids based on coordinates
"""

import numpy as np
from scipy.interpolate import griddata
from typing import Literal

Array = np.ndarray | list


def _prepare_coordinates(x: Array | tuple[list, list, list], y: Array | None = None, z: Array | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x)
    if y is None and x.ndim == 2:
        if x.shape[0] > 3 and x.shape[1] == 3:
           x, y, z = x[:, 0], x[:, 1], x[:, 2]
        elif x.shape[1] > 3 and x.shape[0] == 3:
           x, y, z = x[0, :], x[1, :], x[2, :]
        else:
            raise ValueError(f"Coordinate array must have 3 dimensions, got {x.shape}")
    else:
        x = x.flatten()
        y = np.asarray(y).flatten()
        z = np.asarray(z).flatten()
        if x.shape != y.shape or x.shape != z.shape:
            raise ValueError(f"Coordinate arrays must have the same size, got x={x.shape}, y={y.shape}, z={z.shape}")
    return x, y, z


def coordinates_to_grid(x: Array | tuple[list, list, list], y: Array | None = None, z: Array | None = None):
    """
    Convert coordinates to grid coordinates

        X, Y, Z = coordinates_to_grid(x, y, z)

    :param x: array of coordinates, either x=(n,) or x=(n,3).
    :param y: array of y coordinates, or None if x=(n,3)
    :param z: array of z coordinates, or None if x=(n,3)
    :return: x,y,z grid coordinates, each with shape ~(a,b) where a+b ~ n
    """
    x, y, z = _prepare_coordinates(x, y, z)

    x_diff = abs(np.diff(x))
    x_space = min(x_diff[x_diff > 0]) / 2  # reduce spacing to ensure rounding is unique
    y_diff = abs(np.diff(y))
    y_space = min(y_diff[y_diff > 0]) / 2

    x_unique, x_index, x_inv = np.unique(np.round(x / x_space), return_index=True, return_inverse=True)
    y_unique, y_index, y_inv = np.unique(np.round(y / y_space), return_index=True, return_inverse=True)

    grid_z = np.full((len(y_unique), len(x_unique)), np.nan)
    grid_z[y_inv, x_inv] = z
    grid_x, grid_y = np.meshgrid(x[x_index], y[y_index])
    return grid_x, grid_y, grid_z


def interpolate_to_grid(x: Array | tuple[list, list, list], y: Array | None = None, z: Array | None = None,
                        grid_shape: tuple[int, int] | None = None,
                        method: Literal["nearest", "linear", "cubic"] = "linear") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert coordinates to grid coordinates

        X, Y, Z = interpolate_to_grid(x, y, z, (101, 101))

    :param x: array of coordinates, either x=(n,) or x=(n,3).
    :param y: array of y coordinates, or None if x=(n,3)
    :param z: array of z coordinates, or None if x=(n,3)
    :param grid_shape: grid shape, (x, y)
    :param method: interpolation method for scipy.interpolate.griddata. One of: "nearest", "linear", "cubic"
    :return: x,y,z grid coordinates, each with shape ~(a,b) where a+b ~ n
    """
    x, y, z = _prepare_coordinates(x, y, z)

    # Create grid
    grid_shape = grid_shape or (len(x), len(x))
    grid_shape = (grid_shape, grid_shape) if isinstance(grid_shape, int) else grid_shape
    x_range = np.linspace(np.min(x), np.max(x), grid_shape[0])
    y_range = np.linspace(np.min(y), np.max(y), grid_shape[1])
    grid_x, grid_y = np.meshgrid(x_range, y_range)
    grid_z = griddata((x, y), z, (grid_x, grid_y), method=method)
    return grid_x, grid_y, grid_z