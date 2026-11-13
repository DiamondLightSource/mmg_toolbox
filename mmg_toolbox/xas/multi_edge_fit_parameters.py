"""
MultiEdgeFit Functions

Based on VirtualBeamline by Mario Delgado Jaime
"""

# from __future__ import annotations

import numpy as np
import json
from pathlib import Path
from numpy.typing import ArrayLike, NDArray

from .multi_edge_fit_functions import background_three_region, double_l_edge


DATA_DIR = Path(__file__).parent.parent / 'data'
ATOMIC_PARS_FILE = DATA_DIR / 'atomic_parameters.json'


def get_atomic_parameters() -> dict[str, list[float]]:
    """Open atomic parameters file"""
    return json.load(open(ATOMIC_PARS_FILE))


def nan2avg(array: NDArray[np.float64]) -> NDArray[np.float64]:
    """Replace nan values in array with the average of the nearby values"""
    new_array = 1.0 * array
    for i, value in enumerate(array):
        if np.isnan(value):
            if i == 0:
                new_array[i] = array[i + 1] - (array[i + 2] - array[i + 1])
            elif i == len(array) - 1:
                new_array[i] = array[i - 1] + (array[i - 1] - array[i - 2])
            else:
                new_array[i] = (array[i + 1] + array[i - 1]) / 2
    return new_array


def prepare_component(energy: ArrayLike, raw_signal: ArrayLike, monitor: ArrayLike) -> tuple[
    NDArray[np.float64], NDArray[np.float64]]:
    """Prepare arrays"""
    energy = np.asarray(energy, dtype=np.float64)
    raw_signal = np.asarray(raw_signal, dtype=np.float64)
    monitor = np.asarray(monitor, dtype=np.float64)
    energy = nan2avg(energy)
    signal = nan2avg(raw_signal / monitor)
    return energy, signal


def prepare_components(energy1: ArrayLike, raw_signal1: ArrayLike, monitor1: ArrayLike,
                       energy2: ArrayLike, raw_signal2: ArrayLike, monitor2: ArrayLike) -> tuple[
    NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Interpolate energy and divide signal by monitor"""
    energy1, signal1 = prepare_component(energy1, raw_signal1, monitor1)
    energy2, signal2 = prepare_component(energy2, raw_signal2, monitor2)

    _min = abs(min(energy2) - min(energy1))
    _max = abs(max(energy2) - max(energy1))
    if _min < 1 and _max < 1:
        signal2 = np.interp(energy1, energy2, signal2)
        energy2 = energy1
    return energy1, signal1, energy2, signal2


def edge_energy(energy: np.ndarray, signal: np.ndarray) -> float:
    """
    Estimate first edge energy, E0, using measured signal

    Returns energy in eV

    See VirtualBL.m:SetParams:

        dIdE = diff(app.Component1.RawData.Y)./diff(app.Component1.RawData.X);
        [~, idx1] = max(dIdE);
        [~, idx2] = min(dIdE);
        idxE = round((idx1 + idx2)/2);
        E0 = app.Component1.RawData.X(idxE);

    """
    dIdE = np.gradient(signal, energy)
    idx1 = np.argmax(dIdE)
    idx2 = np.argmin(dIdE)
    edge_idx = (idx1 + idx2) // 2
    return energy[edge_idx - 1]


def l2_edge_energy(l3_edge: float, soc: float) -> float:
    """
    Return an estimate of the energy of the L2 edge
    based on the energy of the L3 edge and the Spin orbit coupling
    """
    return l3_edge + 1.5 * soc


def get_atomic_system(energy: np.ndarray) -> str:
    """
    Return atomic system using edge energy
    """
    avg = np.mean(energy)

    if avg < 500:  # Ti 4+
        return 'Ti4+'
    elif 500 <= avg < 550:  # V3+
        return 'V3+'
    elif 550 <= avg < 630:  # Cr3+
        return 'Cr3+'
    elif 630 <= avg < 690:  # Mn2+
        return 'Cr3+'
    elif 690 <= avg < 750:  # Fe2+
        return 'Fe2+'
    elif 750 <= avg < 830:  # Co2+
        return 'Co2+'
    elif 830 <= avg < 890:  # Ni2:
        return 'Ni2+'
    else:  # Cu2+
        return 'Cu2+'


def get_spin_orbit(atomic_system: str) -> tuple[float, int]:
    """
    Return Spin Orbit energy and number of d-electrons
    """
    atomic_parameters = get_atomic_parameters()[atomic_system]
    return atomic_parameters[1], int(atomic_parameters[2])


def energy_reference(energy: np.ndarray) -> float:
    """
    Energy Reference - point at which to specify the initial background
    """
    return energy[1]  # this would be better as a mean


def preedge_slope(energy: np.ndarray, signal: np.ndarray, edge_en: float | None = None) -> float:
    """
    Quasilinear Region 1
    Slope of region from minimum energy to edge (E0)

        [~, idx2] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current-10)));
        x = app.Component1.RawData.X(1:idx2);
        y = app.Component1.RawData.Y(1:idx2);
        p = polyfit(x,y,1);

    """
    if edge_en is None:
        edge_en = edge_energy(energy, signal)

    index = np.argmin(np.abs(energy - (edge_en - 10)))
    p0, p1 = np.polyfit(energy[:index], signal[:index], 1)
    return p0


def postedge_slope(energy: np.ndarray, signal: np.ndarray,
                   edge_en: float | None = None, soc: float | None = None) -> float:
    """
    Quasilinear Region 3
    Slope of region from L2 edge to max energy

        [~, idx1] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current+1.5*app.Params.SOC2p.Current+10)));
        x = app.Component1.RawData.X(idx1:end);
        y = app.Component1.RawData.Y(idx1:end);
        p = polyfit(x,y,1);

    """
    if edge_en is None:
        edge_en = edge_energy(energy, signal)
    if soc is None:
        atsym = get_atomic_system(energy)
        soc, nd = get_spin_orbit(atsym)
    max_en = l2_edge_energy(edge_en, soc)
    index = np.argmin(np.abs(energy - (max_en + 10)))
    p0, p1 = np.polyfit(energy[index:], signal[index:], 1)
    return p0


def midedge_slope(energy: np.ndarray, signal: np.ndarray,
                  edge_en: float | None = None, soc: float | None = None) -> float:
    """
    Quasilinear Region 2
    Slope of background region between L3 and L2.
    Only used for elements Cu, Co, Fe, Ni

        [~, idx1] = min(abs(app.Component1.RawData.X-(app.Params.AvgEnergy-1)));
        [~, idx2] = min(abs(app.Component1.RawData.X-(app.Params.AvgEnergy+1)));
        x = app.Component1.RawData.X(idx1:idx2);
        y = app.Component1.RawData.Y(idx1:idx2);
        p = polyfit(x,y,1);
        app.Params.m12.Current = p(1);

    """
    if edge_en is None:
        edge_en = edge_energy(energy, signal)
    if soc is None:
        atsym = get_atomic_system(energy)
        soc, nd = get_spin_orbit(atsym)
    avg_en = edge_en + soc
    index1 = np.argmin(np.abs(energy - (avg_en - 1)))
    index2 = np.argmin(np.abs(energy - (avg_en + 1)))
    p0, p1 = np.polyfit(energy[index1:index2], signal[index1:index2], 1)
    return p0


def transition_points(l3_edge: float, soc: float) -> tuple[float, float]:
    """
    Return the transition points in eV
    """
    return l3_edge, l2_edge_energy(l3_edge, soc)


def edge_jump(energy: np.ndarray, signal: np.ndarray,
              m1: float, m2: float, m3: float,
              t1: float, t2: float, e_ref: float) -> float:
    """
    Calculate edge jump

        x = app.Component1.RawData.X;
        b = Background(x,1,C, m1, m2, m3, T1, T2, ERef);
        y = app.Component1.RawData.Y-b;
        [~, idx2] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current+1.5*app.Params.SOC2p.Current+10)));
        [~, idx1] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current-10)));
        app.Params.Int1.Current = abs( mean(y(idx2:end)) - mean(y(1:idx1)) )/1.5;

    :param energy: energy array
    :param signal: signal array
    :param m1: pre-l3-edge gradient
    :param m2: post-l3-edge gradient
    :param t1: l3 edge energy
    :e_ref: energy reference
    :returns: float edge jump energy
    """
    idx = int(np.argmin(np.abs(energy - e_ref)))
    initial_intercept = float(signal[idx])
    background = background_three_region(energy, m1, m2, m3, t1, t2, e_ref, initial_intercept)
    y = signal - background

    print(f"Background: {background.shape}, min={background.min():.3f}, max={background.max():.3f}")
    print(f"sig-bkg: {y.shape}, min={y.min():.3f}, max={y.max():.3f}")

    index1 = np.argmin(np.abs(energy - t1 - 10))
    index2 = np.argmin(np.abs(energy - t2 + 10))
    return abs(np.mean(y[index2:]) - np.mean(y[:index1])) / 1.5
