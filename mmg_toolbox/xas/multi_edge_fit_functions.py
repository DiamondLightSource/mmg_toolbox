"""
MultiEdgeFit Functions

Based on VirtualBeamline by Mario Delgado Jaime
"""

# from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import erf


def edge_step(
    x: ArrayLike,
    intensity: float,
    centre: float,
    gaussian_fraction: float,
    width: float,
) -> NDArray[np.float64]:
    """Evaluate the empirical cumulative edge-step function.

    MATLAB source: `Edge.m`, MATLAB function `Edge(X, I1, O1, G1, W1)`.

    The MATLAB function is::

        E = I1*((1-G1)*(1/pi*atan((X-O1)/W1)+1/2) ...
             + G1/2*(1+erf((X-O1)/(W1/(sqrt(2*log(2)))*sqrt(2)))))

    Parameters
    ----------
    x:
        Energy axis.
    intensity:
        Edge intensity, corresponding to `I1` in MATLAB.
    centre:
        Edge inflection/centre energy, corresponding to `O1` in MATLAB.
    gaussian_fraction:
        Fraction of the cumulative Gaussian contribution, corresponding to `G1`.
        A value of 0 gives the arctangent form; a value of 1 gives the error-function form.
    width:
        Half-width parameter, corresponding to `W1` in MATLAB.

    Returns
    -------
    numpy.ndarray
        Edge-step contribution evaluated on `x`.
    """
    x_arr = np.asarray(x, dtype=float)
    if width <= 0:
        raise ValueError("width must be positive")
    lorentz_cdf = (1.0 / np.pi) * np.arctan((x_arr - centre) / width) + 0.5
    sigma = width / np.sqrt(2.0 * np.log(2.0))
    gaussian_cdf = 0.5 * (1.0 + erf((x_arr - centre) / (sigma * np.sqrt(2.0))))
    return intensity * ((1.0 - gaussian_fraction) * lorentz_cdf + gaussian_fraction * gaussian_cdf)


def double_l_edge(
    energy: ArrayLike,
    intensity_l3: float,
    e0_l3: float,
    spin_orbit_2p: float,
    gaussian_fraction: float,
    width_l3: float,
    width_l2: float,
    l2_intensity_ratio: float = 0.5,
    l2_energy_factor: float = 1.5,
) -> NDArray[np.float64]:
    """Evaluate the double L3/L2 edge jump used by the VirtualBeamline model.

    MATLAB source: expression strings in `VBL.m` and `VirtualBL.m`, composed from
    `Edge.m` / MATLAB function `Edge`.

    The MATLAB code repeatedly constructs expressions of the form::

        Edge(x, Int1, E0, Gauss, L3) + Edge(x, Int1/2, E0 + 1.5*SOC, Gauss, L2)

    Parameters are intentionally explicit rather than represented as generated strings.
    """
    return edge_step(energy, intensity_l3, e0_l3, gaussian_fraction, width_l3) + edge_step(
        energy,
        intensity_l3 * l2_intensity_ratio,
        e0_l3 + l2_energy_factor * spin_orbit_2p,
        gaussian_fraction,
        width_l2,
    )


def background_three_region(
    energy: ArrayLike,
    m1: float,
    m2: float,
    m3: float,
    t1: float,
    t2: float,
    e_shift: float,
    intercept: float
) -> NDArray[np.float64]:
    """Evaluate the three-region empirical background model.

    MATLAB source: `Background.m`, MATLAB function `Background(x, Type, varargin)`
    for `Type == 1`.

    The original MATLAB code obtains `y_ref` by loading `temp_VBL.mat` and sampling the
    active data set at `ERef`. This Python replacement removes the hidden file dependency:
    callers pass `y_ref` explicitly.

    :param energy: energy array
    :param m1: pre-l3-edge gradient
    :param m2: mid-l3-l2-edge gradient
    :param m3: post-l2-edge gradient
    :param t1: l3 edge energy
    :param t2: l2 edge energy
    :param e_shift: energy reference
    :param intercept: initial level of the background
    """
    x_arr = np.asarray(energy, dtype=float)
    f1 = m1 * (x_arr - e_shift) + intercept
    f2 = m2 * (x_arr - t1) + m1 * (t1 - e_shift) + intercept
    f3 = m3 * (x_arr - t2) + m2 * (t2 - t1) + m1 * (t1 - e_shift) + intercept

    # Add function values to different regions
    out = np.empty_like(x_arr, dtype=float)
    left = x_arr < t1
    mid = (x_arr >= t1) & (x_arr < t2)
    right = x_arr >= t2
    out[left] = f1[left]
    out[mid] = f2[mid]
    out[right] = f3[right]
    return out