from __future__ import annotations

import numpy as np


class Metadata:
    filename: str = ''
    beamline: str = ''
    scan_no: int = 0
    start_date_iso: str = ''
    end_date_iso: str = ''
    cmd: str = ''
    count_time: float = 1.
    pol: str = 'pc'
    pol_angle: float = 0.0
    sample_name: str = ''
    temp: float = 300
    mag_field: float = 0
    pitch: float = 0  # 0 == sample surface normal to beam

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if hasattr(self, name):
                setattr(self, name, value)
            else:
                raise ValueError(f'Unknown metadata attribute: {name}')

    def __str__(self):
        return str(self.__dict__)


class XasMetadata(Metadata):
    default_mode: str = 'tey'
    element: str = ''
    edge: str = ''
    energy: np.ndarray[tuple[int], np.dtype[np.float64]] = np.arange(10)
    monitor: np.ndarray[tuple[int], np.dtype[np.float64]] = np.ones(10)
    raw_signals: dict[str, np.ndarray[tuple[int], np.dtype[np.float64]]] = {'tey': np.zeros(10)}


def merge_metadata(*metadata: Metadata) -> Metadata:
    """
    Merge Metadata for a series of SpectraContainers
    """
    if len(metadata) == 0:
        return Metadata()

    first = metadata[0]
    return Metadata(
        filename = '',
        beamline = first.beamline,
        scan_no = 0,
        start_date_iso = min(m.start_date_iso for m in metadata),
        end_date_iso = max(m.end_date_iso for m in metadata),
        cmd = first.cmd,
        count_time = first.count_time,
        pol = first.pol,
        pol_angle = first.pol_angle,
        sample_name = first.sample_name,
        temp = sum(m.temp for m in metadata) / len(metadata),
        mag_field = sum(m.mag_field for m in metadata) / len(metadata),
        pitch = sum(m.pitch for m in metadata) / len(metadata),
    )


def merge_xas_metadata(*metadata: XasMetadata) -> XasMetadata:
    """
    Merge Metadata for a series of SpectraContainers
    """
    if len(metadata) == 0:
        return XasMetadata()

    first = metadata[0]
    return XasMetadata(
        filename='',
        beamline=first.beamline,
        scan_no=0,
        start_date_iso=min(m.start_date_iso for m in metadata),
        end_date_iso=max(m.end_date_iso for m in metadata),
        cmd=first.cmd,
        count_time=first.count_time,
        pol=first.pol,
        pol_angle=first.pol_angle,
        sample_name=first.sample_name,
        temp=sum(m.temp for m in metadata) / len(metadata),
        mag_field=sum(m.mag_field for m in metadata) / len(metadata),
        pitch=sum(m.pitch for m in metadata) / len(metadata),
        default_mode=first.default_mode,
        element=first.element,
        edge=first.edge,
        energy=first.energy,
        monitor=first.monitor,
        raw_signals=first.raw_signals
    )