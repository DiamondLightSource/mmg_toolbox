"""
MultiEdgeFit Functions

Based on VirtualBeamline by Mario Delgado Jaime
"""

# from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from . import MultiEdge


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
        edge = MultiEdge.from_spectra(energy, signal)
        soc = edge.element.spin_orbit
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
        edge = MultiEdge.from_spectra(energy, signal)
        soc = edge.element.spin_orbit
    avg_en = edge_en + soc
    index1 = np.argmin(np.abs(energy - (avg_en - 1)))
    index2 = np.argmin(np.abs(energy - (avg_en + 1)))
    p0, p1 = np.polyfit(energy[index1:index2], signal[index1:index2], 1)
    return p0

# TODO: not really sure this is needed
def transition_points(l3_edge: float, soc: float) -> tuple[float, float]:
    """
    Return the transition points in eV
    """
    return l3_edge, l2_edge_energy(l3_edge, soc)


def l3_edge_jump(energy: np.ndarray, signal: np.ndarray, l3_edge: float, l2_edge: float) -> float:
    """
    Calculate edge jump at the L3 edge, which is 2/3 of the total L3/L2 edge jump

        x = app.Component1.RawData.X;
        b = Background(x,1,C, m1, m2, m3, T1, T2, ERef);
        y = app.Component1.RawData.Y-b;
        [~, idx2] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current+1.5*app.Params.SOC2p.Current+10)));
        [~, idx1] = min(abs(app.Component1.RawData.X-(app.Params.E0.Current-10)));
        app.Params.Int1.Current = abs( mean(y(idx2:end)) - mean(y(1:idx1)) )/1.5;

    :param energy: energy array in eV
    :param signal: signal array
    :param l3_edge: l3 edge energy un eV
    :param l2_edge: l2 edge energy in eV
    :returns: float edge jump energy
    """

    # The edge jump is calculated as the difference between the average
    # of the background subtracted signal 10eV below the L3 and the average of the signal
    # 10eV above L2, divided by 3/2
    index1 = np.argmin(np.abs(energy - l3_edge + 10))
    index2 = np.argmin(np.abs(energy - l2_edge - 10))
    return abs(np.mean(signal[index2:]) - np.mean(signal[:index1])) / 1.5
