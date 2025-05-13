"""
Set of functions for analysing x-ray absorption spectra
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import h5py
from lmfit.models import LinearModel, QuadraticModel, ExponentialModel, StepModel
from itertools import islice
from collections import defaultdict


def get_spectra(*file_list: str, energy_path: str, signal_path: str, pol_path: str, monitor_path: str = None):
    """get signals and energy from spectra scan files"""
    en_list = []
    signals = defaultdict(dict)
    for file in file_list:
        with h5py.File(file, 'r', swmr=True) as hdf:
            energy = hdf[energy_path][()]
            signal = hdf[signal_path][()]
            if monitor_path:
                monitor = hdf[monitor_path][()]
                signal = signal / monitor
            pol = hdf[pol_path].asstr()[()]

        en_list.append(energy)
        signals[pol][os.path.basename(file)] = (energy, signal)
    av_energy = average_energy_scans(*en_list)
    interp_signals = {p: average_energy_spectra(av_energy, *val.values()) for p, val in signals.items()}
    return av_energy, interp_signals, signals


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
    :param args: (mes_energy, mes_signal): pair of (m*1) arrays for energy and measurement signals
    :returns signal: (n*1) array of averaged signal values at points in energy
    """
    data = np.zeros([len(args), len(energy)])
    for n, (en, dat) in enumerate(args):
        data[n, :] = np.interp(energy, en, dat)
    return data.mean(axis=0)


def signal_jump(energy, signal, ev_from_start=5., ev_from_end=None) -> float:
    """Return signal jump from start to end"""
    ev_from_end = ev_from_end or ev_from_start
    ini_signal = np.mean(signal[energy < np.min(energy) + ev_from_start])
    fnl_signal = np.mean(signal[energy > np.max(energy) - ev_from_end])
    return fnl_signal - ini_signal


def subtract_flat_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, np.ndarray]:
    """Subtract flat background"""
    bkg = np.mean(signal[energy < np.min(energy) + ev_from_start])
    return np.subtract(signal, bkg), bkg * np.ones_like(signal)


def normalise_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, np.ndarray]:
    """Normalise background to one"""
    bkg = np.mean(signal[energy < np.min(energy) + ev_from_start])
    return np.divide(signal, bkg), bkg * np.ones_like(signal)


def fit_linear_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, np.ndarray]:
    """Use lmfit to determine sloping background"""
    model = LinearModel(prefix='bkg_')
    region = energy < np.min(energy) + ev_from_start
    en_region = energy[region]
    sig_region = signal[region]
    pars = model.guess(sig_region, x=en_region)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    return signal - bkg, bkg


def fit_curve_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, np.ndarray]:
    """Use lmfit to determine sloping background"""
    model = QuadraticModel(prefix='bkg_')
    # region = (energy < np.min(energy) + ev_from_start) + (energy > np.max(energy) - ev_from_start)
    region = energy < np.min(energy) + ev_from_start
    en_region = energy[region]
    sig_region = signal[region]
    pars = model.guess(sig_region, x=en_region)
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    return signal - bkg, bkg


def fit_exp_background(energy, signal, ev_from_start=5.) -> tuple[np.ndarray, np.ndarray]:
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
    return signal - bkg, bkg


def fit_exp_step(energy, signal, ev_from_start=5., ev_from_end=5.) -> tuple[np.ndarray, np.ndarray]:  # good?
    """Use lmfit to determine sloping background"""
    model = ExponentialModel(prefix='bkg_') + StepModel(form='arctan', prefix='jmp_')  # form='linear'
    region = (energy < np.min(energy) + ev_from_start) + (energy > np.max(energy) - ev_from_start)
    en_region = energy[region]
    sig_region = signal[region]
    # pars = model.guess(sig_region, x=en_region)
    guess_jump = signal_jump(energy, signal, ev_from_start, ev_from_end)
    pars = model.make_params(
        bkg_amplitude=np.max(sig_region),
        bkg_decay=100.0,
        jmp_amplitude=dict(value=guess_jump, min=0),
        jmp_center=energy[np.argmax(signal)],  # np.mean(energy),
        jmp_sigma=dict(value=1, min=0),
    )
    fit_output = model.fit(sig_region, pars, x=en_region)
    bkg = fit_output.eval(x=energy)
    jump = fit_output.params['jmp_amplitude']
    # print('fit_exp_step:\n', fit_output.fit_report())
    # print(jump)
    return (signal - bkg) / jump, bkg / jump


def i06_norm(energy, signal) -> tuple[np.ndarray, np.ndarray]:
    """I06 norm and post_edge_norm option"""
    sig = 1.0 * signal
    sig /= sig[energy < energy[0] + 5].mean()  # nomalise by the average of a range of energy
    jump = sig[energy > energy[-1] - 5].mean() - sig[energy < energy[0] + 5].mean()

    print(jump)
    print(sig[energy < energy[0] + 5].mean())
    sig -= sig[energy < energy[0] + 5].mean()  # - 1
    jump2 = sig[energy > energy[-1] - 5].mean()
    print(jump2)
    sig /= jump2
    return sig, jump2 * np.ones_like(sig)


def fit_bkg_then_norm_to_peak(energy, signal, ev_from_start=5., ev_from_end=5.) -> tuple[np.ndarray, np.ndarray]:  # good?
    """Fit the background then normalise the post-edge to 1"""
    fit_signal, bkg = fit_exp_background(energy, signal, ev_from_start)
    peak = np.max(abs(fit_signal))
    return fit_signal / peak, bkg / peak


def fit_bkg_then_norm_to_jump(energy, signal, ev_from_start=5., ev_from_end=5.) -> tuple[np.ndarray, np.ndarray]:  # good?
    """Fit the background then normalise the post-edge to 1"""
    fit_signal, bkg = fit_exp_background(energy, signal, ev_from_start)
    jump = signal_jump(energy, fit_signal, ev_from_start, ev_from_end)
    return fit_signal / abs(jump), bkg / abs(jump)


def calc_xmcd(signals: dict[str, np.ndarray]) -> np.ndarray:
    """Subtract pc from nc"""
    return signals['nc'] - signals['pc']


def calc_xmld(signals: dict[str, np.ndarray]) -> np.ndarray:
    """Subtract lh from lv"""
    return signals['lv'] - signals['lh']


def calc_subtraction(signals: dict[str, np.ndarray]) -> tuple[np.ndarray, str]:
    """Calculate subtraction, either xmcd or xmld"""
    if 'pc' in signals:
        result = calc_xmcd(signals)
        name = 'XMCD'
    elif 'lh' in signals:
        result = calc_xmld(signals)
        name = 'XMLD'
    else:
        print('Polarisation not recognised')
        result = np.mean(signals.values(), axis=0)
        name = ''
    return result, name


def analyse_signals(av_energy, signals) -> tuple[np.ndarray, dict]:
    """wrapper"""

    norm_signals = {
        label: fit_bkg_then_norm_to_jump(av_energy, signal, ev_from_start=6, ev_from_end=10)[0] for label, signal in signals.items()
    }

    result, label = calc_subtraction(norm_signals)
    print(f"Analysing {label}")
    norm_signals[label] = result
    return av_energy, norm_signals


def analyse_plot_scans(*filenames: str, signal_name=None, title=''):
    """wrapper"""

    energy_path, signal_path, monitor_path, pol_path = get_scan_paths(filenames[0], signal_name)
    signal_name = signal_name or signal_path
    av_energy, signals, raw = get_spectra(
        *filenames,
        energy_path=energy_path,
        signal_path=signal_path,
        pol_path=pol_path,
        monitor_path=monitor_path
    )
    _, results = analyse_signals(av_energy, signals)

    analysis_type = next(islice(reversed(results), 1, None), 'None')  # get 2nd last field name in results

    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle(f"{title} {signal_name} {analysis_type}")

    for pol, data in raw.items():
        for name, (energy, sig) in data.items():
            ax[0].plot(energy, sig, '-', label=f"{pol}-{name}")
    ax[0].set_xlabel('Energy [eV]')
    ax[0].set_ylabel('signal / monitor')
    ax[0].set_title('raw spectra')
    ax[0].legend()

    for label, sig in results.items():
        ax[1].plot(av_energy, sig, '-', label=label)
    ax[1].set_xlabel('Energy [eV]')
    ax[1].set_ylabel('normalised signal - bkg')
    ax[1].set_title('subtracted, normalised spectra')
    ax[1].legend()

    ax[2].plot(av_energy, results['result'], '-', label=analysis_type)
    ax[2].set_xlabel('Energy [eV]')
    ax[2].set_title('Results')
    ax[2].legend()


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
    tot = np.trapezoid(average, energy)

    # Calculate the sum rule for the angular momentum
    L = -2 * nholes * np.trapezoid(difference, energy) / tot
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
    tot = np.trapezoid(average, energy)

    # Calculate the sum rule for the spin angular momentum
    split_index = np.argmin(np.abs(energy - split_energy))
    l3_energy = energy[split_index:]  # L3 edge at lower energy
    l3_difference = difference[split_index:]
    l3_integral = np.trapezoid(l3_difference, l3_energy)
    l2_energy = energy[:split_index]
    l2_difference = difference[:split_index]
    l2_integral = np.trapezoid(l2_difference, l2_energy)
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
