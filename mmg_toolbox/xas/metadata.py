from __future__ import annotations

import numpy as np


class Metadata:
    filename: str = ''
    beamline: str = ''
    scan_no: int = 0
    start_date_iso: str = ''
    end_date_iso: str = ''
    cmd: str = ''
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
