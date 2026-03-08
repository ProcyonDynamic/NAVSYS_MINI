from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

BodyKind = Literal["SUN", "STAR", "PLANET"]
InstrumentMode = Literal["MAGNETIC", "GYRO_1", "GYRO_2"]


@dataclass(frozen=True)
class SightInput:
    run_id: str
    time_utc: str              # ISO8601 Z
    lat: float
    lon: float
    body_kind: BodyKind
    body_name: str
    instrument_mode: InstrumentMode

    observed_bearing_deg: Optional[float] = None
    observed_ho_deg: Optional[float] = None

    height_of_eye_m: Optional[float] = None

    # signed convention:
    # East  = positive
    # West  = negative
    variation_deg: Optional[float] = None
    deviation_deg: Optional[float] = None

    instrument_label: str = ""


@dataclass(frozen=True)
class SkyfieldResult:
    zn_deg: float
    hc_deg: Optional[float]