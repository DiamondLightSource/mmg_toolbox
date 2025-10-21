"""
Set of functions for analysing x-ray absorption spectra
"""

import json

import os
import numpy as np
from lmfit.model import ModelResult
from lmfit.models import LinearModel, QuadraticModel, ExponentialModel, StepModel, PolynomialModel

# trapz replaced by trapezoid in Numpy 2.0
try:
    from numpy import trapezoid as trapz
except ImportError:
    from numpy import trapz


EDGE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'xray_edges.json')
SEARCH_EDGES = ('L3', 'L2')


def load_edge_energies(edges=SEARCH_EDGES) -> tuple[np.ndarray, np.ndarray]:
    """
    return arrays of energies and labels for x-ray absorption edges
    :param edges: if not None, only return energies for these edges, e.g. ('L3', 'L2')
    :return: energies[ndarray], labels[ndarray]
    """
    with open(EDGE_FILE, 'r') as infile:
        edge_dict = json.load(infile)
    edge_energies = {
        label: edge['energy'] for label, edge in edge_dict.items()
        if (edge['edge'] in edges if edges else True)
    }
    energies = np.array(list(edge_energies.values()))
    labels = np.array(list(edge_energies.keys()))
    idx = np.argsort(energies)
    return energies[idx], labels[idx]


def xray_edges_in_range(min_energy_ev: float, max_energy_ev: float | None = None,
                        energy_range_ev: float = 10., search_edges: None | tuple[str] = SEARCH_EDGES) -> list[tuple[str, float]]:
    """
    Return all x-ray absorption edges within the range
    :param min_energy_ev: energy to find x-ray absorption edges within
    :param max_energy_ev: energy to find x-ray absorption edges within
    :param energy_range_ev: energy to find x-ray absorption edges within
    :param search_edges: if not None, only return energies for these edges, e.g. ('L3', 'L2')
    :return: list[(edge_label[str], energy[float])]
    """
    if max_energy_ev is None:
        min_energy_ev = min_energy_ev - energy_range_ev / 2
        max_energy_ev = min_energy_ev + energy_range_ev / 2
    energies, labels = load_edge_energies(search_edges)
    idx = (energies > min_energy_ev) * (energies < max_energy_ev)
    return [(str(labels[ii]), float(energies[ii])) for ii in np.flatnonzero(idx)]


def energy_range_edge_label(min_energy_ev: float, max_energy_ev: float | None = None,
                            energy_range_ev: float = 10., search_edges: tuple[str] = SEARCH_EDGES) -> tuple[str, str]:
    """
    Return mode string for x-ray absorption edges in energy range
      raises ValueError is no edges are found or if multiple non-equivalent edges are found

    :param min_energy_ev: energy to find x-ray absorption edges within
    :param max_energy_ev: energy to find x-ray absorption edges within
    :param energy_range_ev: energy to find x-ray absorption edges within
    :param search_edges: if not None, only return energies for these edges, e.g. ('L3', 'L2')
    :return: element, mode strings, e.g. 'Mn', 'L2, L3'
    """
    edges = xray_edges_in_range(min_energy_ev, max_energy_ev, energy_range_ev, search_edges)
    if len(edges) == 1:
        label = edges[0][0]
        element, edge = label.split()
        return element, edge
    if len(edges) == 2:
        label1 = edges[0][0]
        label2 = edges[1][0]
        element1, edge1 = label1.split()
        element2, edge2 = label2.split()
        if element1 != element2:
            raise ValueError(f"xray absorption edges of multiple edges present: {label1}, {label2}")
        return element1, f"{edge1}, {edge2}"
    raise ValueError(f"xray absorption edge not found: {edges} edges at energy {min_energy_ev} eV")


def average_energy_scans(*args: np.ndarray):
    """Return the minimum range covered by all input arguments"""
    min_energy = np.max([np.min(en) for en in args])
    max_energy = np.min([np.max(en) for en in args])
    min_step = np.min([np.min(np.abs(np.diff(en))) for en in args])
    return np.arange(min_energy, max_energy + min_step, min_step)


def average_energy_spectra(energy, *args: tuple[np.ndarray, np.ndarray]):
    """
    Average energy spectra, interpolating at given energy

    E.G.
        energy = average_energy_scans(en1, en2)
        signal = combine_energy_scans(energy, (en1, sig1), (en2, sig2))

    :param energy: (n*1) array of energy values, in eV
    :param args: (mes_energy, mes_signal): pair of (m*1) arrays for energy and measurement raw_signals
    :returns signal: (n*1) array of averaged signal values at points in energy
    """
    data = np.zeros([len(args), len(energy)])
    for n, (en, dat) in enumerate(args):
        data[n, :] = np.interp(energy, en, dat)
    return data.mean(axis=0)


def preedge_signal(energy, signal, ev_from_start=5.) -> float:
    """Return pre-edge signal"""
    return np.mean(signal[energy < np.min(energy) + ev_from_start])


def postedge_signal(energy, signal, ev_from_end=5.) -> float:
    """Return post-edge signal"""
    return np.mean(signal[energy > np.max(energy) - ev_from_end])


def signal_jump(energy, signal, ev_from_start=5., ev_from_end=None) -> float:
    """Return signal jump from start to end"""
    ev_from_end = ev_from_end or ev_from_start
    ini_signal = preedge_signal(energy, signal, ev_from_start)
    fnl_signal = postedge_signal(energy, signal, ev_from_end)
    return fnl_signal - ini_signal


"""
--- BACKGROUND FUNCTIONS ---
All background functions have inputs:
    energy: ndarray[n], signal: ndarray[n], **kwargs
All background functions have outputs:
    bkg: nparray[n], norm: float, None | lmfit.ModelResult
"""


def subtract_flat_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, float, None]:
    """Subtract flat background"""
    bkg = preedge_signal(energy, signal, ev_from_start)
    return bkg * np.ones_like(signal), 1, None


def normalise_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, float, None]:
    """Normalise background to one"""
    bkg = preedge_signal(energy, signal, ev_from_start)
    return np.zeros_like(signal), float(bkg), None


def fit_linear_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, float, ModelResult]:
    """Use lmfit to determine sloping background"""
    model = LinearModel(prefix='bkg_')
    region = energy < np.min(energy) + ev_from_start
    en_region = energy[region]
    sig_region = signal[region]
    pars = model.guess(sig_region, x=en_region)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    return bkg, 1, fit_output


def fit_curve_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, float, ModelResult]:
    """Use lmfit to determine sloping background"""
    model = QuadraticModel(prefix='bkg_')
    # region = (energy < np.min(energy) + ev_from_start) + (energy > np.max(energy) - ev_from_start)
    region = energy < np.min(energy) + ev_from_start
    en_region = energy[region]
    sig_region = signal[region]
    pars = model.guess(sig_region, x=en_region)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    return bkg, 1, fit_output


def fit_exp_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, float, ModelResult]:
    """Use lmfit to determine sloping background"""
    model = ExponentialModel(prefix='bkg_')
    # region = (energy < np.min(energy) + ev_from_start) + (energy > np.max(energy) - ev_from_start)
    region = energy < np.min(energy) + ev_from_start
    en_region = energy[region]
    sig_region = signal[region]
    pars = model.guess(sig_region, x=en_region)
    fit_output = model.fit(sig_region, pars, x=en_region)
    # print('exp background\n:', fit_output.fit_report())
    bkg = fit_output.eval(x=energy)
    return bkg, 1, fit_output


def fit_step_background(energy, signal, ev_from_start=5.)  -> tuple[np.ndarray, float, ModelResult]:  # good?
    """Use lmfit to detemine edge background"""
    model = LinearModel(prefix='bkg_') + StepModel(form='arctan', prefix='edge_')
    region = (energy < np.min(energy) + ev_from_start) + (energy > np.max(energy) - ev_from_start)
    en_region = energy[region]
    sig_region = signal[region]

    guess_jump = signal_jump(energy, signal)
    pars = model.make_params(
        bkg_slope=0.0,
        bkg_intercept=np.min(sig_region),
        edge_amplitude=guess_jump,
        edge_center=np.mean(energy),
        edge_sigma=1.0,
    )
    # bkg_ini = model.eval(pars, x=energy)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    step = fit_output.params['edge_amplitude']
    return bkg, step, fit_output


def fit_double_edge_step_background(energy, signal, l3_energy, l2_energy, peak_width_ev=5.) -> tuple[np.ndarray, float, ModelResult]:
    """Use lmfit to determine sloping background"""
    model = StepModel(form='arctan', prefix='l3_') + StepModel(form='arctan', prefix='l2_')  # form='linear'
    region = (
            (energy < l3_energy - peak_width_ev / 2) +
            np.logical_and(energy > l3_energy + peak_width_ev / 2, energy < l2_energy - peak_width_ev / 2) +
            (energy > l2_energy + peak_width_ev / 2)
    )
    en_region = energy[region]
    sig_region = signal[region]

    guess_jump = signal_jump(energy, signal)
    pars = model.make_params(
        l3_amplitude=0.667 * guess_jump,
        l3_center=l3_energy,
        l3_sigma=2,
        l2_amplitude=0.333 * guess_jump,
        l2_center=l2_energy,
        l2_sigma=2,
    )
    pars['l3_center'].set(min=l3_energy - 1.0, max=l3_energy + 1.0)
    pars['l2_center'].set(min=l2_energy - 1.0, max=l2_energy + 1.0)
    pars['l3_sigma'].set(min=1, max=5)
    # pars['l2_sigma'].set(min=1, max=5)
    pars['l2_sigma'].set(expr='l3_sigma')
    pars['l3_amplitude'].set(min=0.6 * guess_jump, max=0.75 * guess_jump)
    pars['l2_amplitude'].set(expr=f"{guess_jump}-l3_amplitude")
    # bkg_ini = model.eval(pars, x=energy)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    step = fit_output.params['l3_amplitude'] + fit_output.params['l2_amplitude']
    return bkg, step, fit_output


def fit_spectra_background(energy: np.ndarray, signal: np.ndarray, *step_energies: float, peak_width_ev=5.) -> tuple[np.ndarray, float, ModelResult]:
    """
    Generic fit of spectra background using an order-2 polynomial and n-edges, fitted to region with peaks removed

    The returned ModelResult object has the following attributes:
        params['bkg_0']  flat background
        params['bkg_1']  sloping background
        params['bkg_2']  curved background
        params['edgeN_center']  step N centre [in eV]
        params['edgeN_amplitude']  step N height
        params['edgeN_sigma']  step N width [in eV]

    Parameters
    :energy: ndarray[n] of spectra energy in eV
    :signal: ndarray[n] of spectra signal
    :step_energies: list of absorption energy steps, in eV
    :peak_width_ev: float width of absorption peak in eV
    :return: background[ndarray], jump[float], lmfit.ModelResult
    """
    model = PolynomialModel(degree=2, prefix='bkg_')
    region = np.ones_like(energy, dtype=bool)
    for n, edge in enumerate(step_energies):
        model += StepModel(form='arctan', prefix=f'edge{n+1}_')
        region[np.abs(energy - edge) < peak_width_ev] = 0
    en_region = energy[region]
    sig_region = signal[region]

    guess_jump = signal_jump(energy, signal)
    pars = model.make_params(
        bkg_c0=np.min(sig_region),
        bkg_c1=0,
        bkg_c2=0
    )
    for n, edge in enumerate(step_energies):
        pars[f'edge{n+1}_center'].set(value=edge, min=edge - 2.0, max=edge + 2.0)
        pars[f'edge{n+1}_sigma'].set(value=2, min=1, max=3)
        if n > 0:
            pars[f'edge{n + 1}_sigma'].set(expr='edge1_sigma')
        edge_jump = guess_jump * (len(step_energies) - n) / (len(step_energies) + 1)
        pars[f'edge{n + 1}_amplitude'].set(value=edge_jump, min=0.8 * edge_jump, max=1.2 * edge_jump)
    # bkg_ini = model.eval(pars, x=energy)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    jump = 0
    for n, edge in enumerate(step_energies):
        jump += fit_output.params[f'edge{n + 1}_amplitude']
    return bkg, jump, fit_output


def fit_spectra_exp_background(energy: np.ndarray, signal: np.ndarray, *step_energies: float, peak_width_ev=5.) -> tuple[np.ndarray, float, ModelResult]:
    """
    Generic fit of spectra background using an exponential and n-edges, fitted to region with peaks removed

    The returned ModelResult object has the following attributes:
        params['bkg_0']  flat background
        params['bkg_1']  sloping background
        params['bkg_2']  curved background
        params['edgeN_center']  step N centre [in eV]
        params['edgeN_amplitude']  step N height
        params['edgeN_sigma']  step N width [in eV]

    Parameters
    :energy: ndarray[n] of spectra energy in eV
    :signal: ndarray[n] of spectra signal
    :step_energies: list of absorption energy steps, in eV
    :peak_width_ev: float width of absorption peak in eV
    :return: background[ndarray], jump[float],  lmfit.ModelResult
    """
    model = ExponentialModel(prefix='bkg_')
    region = np.ones_like(energy, dtype=bool)
    for n, edge in enumerate(step_energies):
        model += StepModel(form='arctan', prefix=f'edge{n+1}_')
        region[np.abs(energy - edge) < peak_width_ev] = 0
    en_region = energy[region]
    sig_region = signal[region]

    guess_jump = signal_jump(energy, signal)
    pars = model.make_params(
        bkg_amplitude=np.max(sig_region),
        bkg_decay=100.0,
    )
    for n, edge in enumerate(step_energies):
        pars[f'edge{n+1}_center'].set(value=edge, min=edge - 2.0, max=edge + 2.0)
        pars[f'edge{n+1}_sigma'].set(value=2, min=1, max=3)
        if n > 0:
            pars[f'edge{n + 1}_sigma'].set(expr='edge1_sigma')
        edge_jump = guess_jump * (len(step_energies) - n) / (len(step_energies) + 1)
        pars[f'edge{n + 1}_amplitude'].set(value=edge_jump, min=0.8 * edge_jump, max=1.2 * edge_jump)
    # bkg_ini = model.eval(pars, x=energy)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    jump = 0
    for n, edge in enumerate(step_energies):
        jump += fit_output.params[f'edge{n + 1}_amplitude']
    return bkg, jump, fit_output


"""
--- SUM RULES ---
"""


def default_n_holes(element: str) -> float:
    """
    Return the default number of holes for a given element
    """
    elements = {
        'Cu': 1,
        'Ni': 2,
        'Co': 3,
        'Fe': 4,
        'Mn': 5,
        'Cr': 6,
        'V':  7,
        'Ti': 8,
        'Sc': 9,
    }
    if element in elements:
        return elements[element]
    raise KeyError(f'unknown number of holes for {element}')


def orbital_angular_momentum(energy: np.ndarray, average: np.ndarray,
                             difference: np.ndarray, nholes: float) -> float:
    """
    Calculate the sum rule for the angular momentum of the spectra
    using the formula:
    L = -2 * nholes * int[spectra d energy] / sum(spectra)

    :param energy: Energy axis of the spectra
    :param average: average XAS spectra (left + right) for both polarisations
    :param difference: difference XAS spectra (right - left) for both polarisations
    :param nholes: Number of holes in the system
    :return: Angular momentum of the spectra
    """
    if len(energy) != len(average) or len(energy) != len(difference):
        raise ValueError(f"Energy and spectra must have the same length: {len(energy)} != {len(average)}")
    if nholes <= 0:
        raise ValueError(f"Number of holes must be greater than 0: {nholes}")

    # total intensity
    tot = trapz(average, energy)

    # Calculate the sum rule for the angular momentum
    L = -2 * nholes * trapz(difference, energy) / tot
    return L


def spin_angular_momentum(energy: np.ndarray, average: np.ndarray,
                          difference: np.ndarray, nholes: float,
                          split_energy: int | None = None, dipole_term: float = 0) -> float:
    """
    Calculate the sum rule for the spin angular momentum of the spectra
    using the formula:
    S = -2 * nholes * int[spectra d energy] / sum(spectra)

    :param energy: Energy axis of the spectra
    :param average: average XAS spectra (left + right) for both polarisations
    :param difference: difference XAS spectra (right - left) for both polarisations
    :param nholes: Number of holes in the system
    :param split_energy: energy to split the spectra between L3 and L2 (or None to use the middle of the spectra)
    :param dipole_term: magnetic dopole term (T_z), defaults to 0 for effective spin
    :return: Spin angular momentum of the spectra
    """
    if len(energy) != len(average) or len(energy) != len(difference):
        raise ValueError(f"Energy and spectra must have the same length: {len(energy)} != {len(average)}")
    if nholes <= 0:
        raise ValueError(f"Number of holes must be greater than 0: {nholes}")
    if split_energy is None:
        split_energy = (energy[0] + energy[-1]) / 2

    # total intensity
    tot = trapz(average, energy)

    # Calculate the sum rule for the spin angular momentum
    split_index = np.argmin(np.abs(energy - split_energy))
    l3_energy = energy[split_index:]  # L3 edge at lower energy
    l3_difference = difference[split_index:]
    l3_integral = trapz(l3_difference, l3_energy)
    l2_energy = energy[:split_index]
    l2_difference = difference[:split_index]
    l2_integral = trapz(l2_difference, l2_energy)
    S_eff = (3 / 2) * nholes * (l3_integral - 2 * l2_integral) / tot
    S = S_eff - dipole_term
    return S


def magnetic_moment(orbital: float, spin: float) -> float:
    """
    Calculate the magnetic moment of the system using the formula:
    M = -g * (L + 2 * S)  WHERE DOES THIS COME FROM?

    :param orbital: Orbital angular momentum of the system
    :param spin: Spin angular momentum of the system
    :return: Magnetic moment of the system
    """
    print('magnetic moment is probably wrong!')
    g = 2.0  # Landé g-factor for free electron
    return -g * (orbital + 2 * spin)
