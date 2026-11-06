"""
MultiEdgeFit Functions

Based on VirtualBeamline by Mario Delgado Jaime
"""

from typing import Any

import numpy as np
from lmfit import Model, Parameters

from .multi_edge_fit_functions import background_three_region, double_l_edge
from .multi_edge_fit_parameters import (
    edge_energy,
    energy_reference,
    get_atomic_system,
    get_spin_orbit,
    midedge_slope,
    postedge_slope,
    preedge_slope,
    transition_points,
)


class BackgroundThreeRegionModel(Model):
    """LMFit model for :func:`background_three_region`.

    The spectrum energy and signal are independent variables; the slopes, transition
    energies, and reference energy are fitted parameters. :meth:`guess` uses the
    project's existing edge and slope estimators to initialize all six parameters.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(background_three_region, independent_vars=["energy"], **kwargs)

    def guess(self, data: np.ndarray, x: np.ndarray, **kwargs: Any) -> Parameters:
        """
        Estimate all background parameters from energy and signal arrays.

                Estimated parameters:
                - ``m1``: linear fit to the pre-edge region, ending about 10 eV before the
                    estimated L3 edge.
                - ``m2``: linear fit around the midpoint between L3 and L2; for elements other
                    than Cu, Co, and Ni, this is set equal to ``m1``.
                - ``m3``: linear fit to the post-edge region, starting about 10 eV after L2.
                - ``t1``: estimated L3 edge energy from the signal derivative extrema.
                - ``t2``: estimated L2 edge energy, calculated from ``t1`` and the element's
                    spin-orbit splitting.
                - ``e_ref``: the second energy sample, used as the background reference energy.

        :param data: the signal array (y-axis)
        :param x: the energy array (x-axis)
        :return: Parameters object
        """
        energy = np.asarray(x, dtype=float)
        signal = np.asarray(data, dtype=float)
        if energy.ndim != 1 or signal.ndim != 1 or energy.shape != signal.shape:
            raise ValueError("energy and signal must be one-dimensional arrays of matching shape")
        if energy.size < 3:
            raise ValueError("at least three energy and signal points are required to guess parameters")

        e0 = edge_energy(energy, signal)
        atomic_system = get_atomic_system(energy)
        spin_orbit, _ = get_spin_orbit(atomic_system)
        e_ref = energy_reference(energy)
        m1 = preedge_slope(energy, signal, e0)
        m2 = midedge_slope(energy, signal, e0, spin_orbit)
        m3 = postedge_slope(energy, signal, e0, spin_orbit)
        t1, t2 = transition_points(e0, spin_orbit)

        if atomic_system[:2] not in {"Cu", "Co", "Ni"}:
            m2 = m1

        _max_slope = max(m1, m2, m3)
        _min_slope = min(m1, m2, m3)

        idx = int(np.argmin(np.abs(energy - e_ref)))
        initial_intercept = float(signal[idx])

        # value, vary, min, max
        params: dict[str, dict[str, float | bool]] = {
            'e_shift': {
                'value': e_ref,
                'min': e_ref,
                'max': e0 - 8,
                'vary': True
            },
            'intercept': {
                'value': initial_intercept,
                'min': initial_intercept * 0.1,
                'max': initial_intercept * 10,
                'vary': True
            },
            'm1': {
                'value': m1,
                'min': m1 * 0.5,
                'max': m1 * 1.5,
                'vary': True
            },
            'm2': {
                'value': m2,
                'min': _min_slope * 0.5,  # why is this different?
                'max': _max_slope * 1.5,
                'vary': True
            },
            'm3': {
                'value': m3,
                'min': m3 * 0.5,
                'max': m3 * 1.5,
                'vary': True
            },
            't1': {
                'value': t1,
                'min': t1 - 2,
                'max': t1 + 3,
                'vary': True
            },
            't2': {
                'value': t2,
                'min': t2 - 2,
                'max': t2 + 3,
                'vary': True
            }
        }

        return self.make_params(False, **params)


class DoubleLEdgeModel(Model):
    """LMFit model for the combined L3/L2 edge-step function.

    :meth:`guess` estimates the edge intensity and L3 energy from the supplied data,
    uses the element's tabulated spin-orbit splitting, and initializes line-shape
    parameters from the project's standard starting values.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(double_l_edge, independent_vars=["energy"], **kwargs)

    def guess(self, data: np.ndarray, x: np.ndarray, **kwargs: Any) -> Parameters:
        """Estimate starting values for the double L-edge parameters.

        Estimated parameters:
        - ``intensity_l3``: estimated from the difference between the median upper and
          lower signal tails, divided by the combined edge-height factor of 1.5.
        - ``e0_l3``: estimated from the midpoint of the largest and smallest signal
          derivative locations, using the project's edge-energy estimator.
        - ``spin_orbit_2p``: read from the atomic-parameter table for the element
          identified from the mean energy.
        - ``gaussian_fraction``: initialized to 0 (Lorentzian/arctangent line shape).
        - ``width_l3``: initialized to the project's standard L3 half-width of 0.3 eV.
        - ``width_l2``: initialized to the project's standard L2 half-width of 0.5 eV.
        - ``l2_intensity_ratio``: initialized to the function default of 0.5.
        - ``l2_energy_factor``: initialized to the function default of 1.5.

        :param data: measured edge signal (y-axis)
        :param x: energy array (x-axis)
        :return: initialized LMFit parameters
        """
        energy = np.asarray(x, dtype=float)
        signal = np.asarray(data, dtype=float)
        if energy.ndim != 1 or signal.ndim != 1 or energy.shape != signal.shape:
            raise ValueError("energy and signal must be one-dimensional arrays of matching shape")
        if energy.size < 3:
            raise ValueError("at least three energy and signal points are required to guess parameters")

        tail_size = max(1, energy.size // 10)
        signal_step = float(np.median(signal[-tail_size:]) - np.median(signal[:tail_size]))
        intensity_l3 = abs(signal_step) / 1.5

        e0_l3 = edge_energy(energy, signal)
        atomic_system = get_atomic_system(energy)
        spin_orbit_2p, _ = get_spin_orbit(atomic_system)

        # value, vary, min, max
        params: dict[str, dict[str, float | bool]] = {
            'e0_l3': {
                'value': e0_l3,
                'min': e0_l3 - 1.5,
                'max': e0_l3 + 4,
                'vary': True
            },
            'intensity_l3': {
                'value': intensity_l3,
                'min': intensity_l3 * 0.5,
                'max': intensity_l3 * 2,
                'vary': True
            },
            'gaussian_fraction': {
                'value': 0,
                'min': 0,
                'max': 1,
                'vary': True
            },
            'width_l3': {
                'value': 0.3,
                'min': 0.2,
                'max': 0.5,
                'vary': True
            },
            'width_l2': {
                'value': 0.5,
                'min': 0.3,
                'max': 1,
                'vary': True
            },
            'spin_orbit_2p': {
                'value': spin_orbit_2p,
                'min': spin_orbit_2p - 0.1,
                'max': spin_orbit_2p + 0.1,
                'vary': False
            },
            'l2_intensity_ratio': {
                'value': 0.5,
                'min': 0.1,
                'max': 1.0,
                'vary': False
            },
            'l2_energy_factor': {
                'value': 1.5,
                'min': 1.0,
                'max': 2.0,
                'vary': False
            },
        }
        return self.make_params(False, **params)


