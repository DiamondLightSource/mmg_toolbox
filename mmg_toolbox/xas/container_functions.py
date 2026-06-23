from __future__ import annotations

from mmg_toolbox.utils.polarisation import opposite_polarisations, check_polarisation
from mmg_toolbox.xas.spectra_container import SpectraContainer


def average_scans(*scans: SpectraContainer) -> SpectraContainer:
    """
    Average spectra within a set of scans

        av_scan = average_scans(scan1, scan2, scan3)

    Equivalent to: av_scan = sum([scan2, scan3], scan1)

    :param scans: list of SpectraContainer objects
    :return: SpectraContainer object containing averaged spectra
    """
    av_scan = sum(scans[1:], scans[0].copy())
    av_scan.name = '+'.join(
        [scans[0].name, '..', scans[-1].name]
        if len(scans) > 3 else
        [s.name for s in scans]
    )
    av_scan.parents = list(scans)
    return av_scan


def average_polarised_scans(*scans: SpectraContainer) -> tuple[SpectraContainer, SpectraContainer | None]:
    """
    Find unique polarisations and average each scan at that polarisation
    Spectra are only separated by polarisation, all spectra with the same polarisation
    are averaged together.

        pol1, pol2 = average_polarised_scans(*scans)

    :param scans: list of SpectraContainer objects
    :return: pol1, (pol2|None) SpectraContainer objects for opposite polarisations
    """
    pols = opposite_polarisations(scans[0].metadata.pol, scans[0].metadata.pol_angle)
    pol_scans = [
        [scan for scan in scans if check_polarisation(scan.metadata.pol) == pol]
        for pol in pols
    ]

    # average spectra containers
    av_scans = [
        average_scans(*_scans)
        for _scans in pol_scans
    ]

    # rename containers
    for pol, scan, pol_scan_list in zip(pols, av_scans, pol_scans):
        scan.name = pol
        scan.parents = pol_scan_list
        for spectra in scan.spectra.values():
            spectra.process_label += f"_{pol}"
    if len(pol_scans) == 1:
        return av_scans[0], None
    return av_scans[0], av_scans[1]


def polarised_pairs(*scans: SpectraContainer) -> list[tuple[SpectraContainer, SpectraContainer]]:
    """
    Find the polarisation pair of each spectra from the list of spectra

        [(pol1, pol2), (pol3, pol4)] = polarised_pairs(*scans)

    :param scans: list of SpectraContainer objects
    :return: list((pol1, pol2)) SpectraContainer objects for opposite polarisations
    """
    pol1, pol2 = opposite_polarisations(scans[0].metadata.pol, scans[0].metadata.pol_angle)
    pol1_scans, pol2_scans = [
        [scan for scan in scans if check_polarisation(scan.metadata.pol) == pol]
        for pol in (pol1, pol2)
    ]
    return list((p1, p2) for p1, p2 in zip(pol1_scans, pol2_scans))


def pair_scans(*scans: SpectraContainer) -> list[tuple[SpectraContainer, SpectraContainer]]:
    """
    Find the polarisation pair of each spectra from the list of spectra

        [(pol1, pol2), (pol3, pol4)] = pair_scans(*scans)

    Scans are paired against their opposite polarisation or the opposite magnetic field,
    whichever comes first.

    :param scans: list of SpectraContainer objects
    :return: list((pol1, pol2)) SpectraContainer objects for opposite polarisations
    """
    pairs: list[tuple[SpectraContainer, SpectraContainer]] = []
    scans = list(scans)
    for n, scan in enumerate(scans):
        pol, op_pol = opposite_polarisations(scan.metadata.pol, scan.metadata.pol_angle)
        field = scan.metadata.mag_field
        for m, next_scan in enumerate(scans[n + 1:]):
            if next_scan.metadata.pol == op_pol or abs(next_scan.metadata.mag_field + field) < 0.01:
                pairs.append((scan, scans.pop(n + m + 1)))
                break
    return pairs
