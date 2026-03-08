from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import SightInput, SkyfieldResult
from .deviation_card import load_deviation_card_csv, interpolate_deviation


@dataclass(frozen=True)
class CompassErrorResult:
    instrument_mode: str
    instrument_label: str

    true_azimuth_deg: float
    bearing_used_deg: float

    error_deg: float
    error_dir: str   # E / W

    variation_deg: float | None
    observed_deviation_deg: float | None
    card_deviation_deg: float | None
    deviation_diff_deg: float | None


def _normalize_signed_delta_deg(x: float) -> float:
    """
    Normalize angle difference to (-180, +180]
    """
    y = (x + 180.0) % 360.0 - 180.0
    if y <= -180.0:
        y += 360.0
    return y


def _signed_to_mag_dir(x: float) -> tuple[float, str]:
    if x >= 0:
        return abs(x), "E"
    return abs(x), "W"


def compute_error_from_bearing(
    *,
    true_azimuth_deg: float,
    bearing_deg: float,
) -> tuple[float, str, float]:
    """
    Error = True - Observed

    Returns:
        (abs_error_deg, dir, signed_error_deg)

    signed convention:
        East  = positive
        West  = negative
    """
    signed_delta = _normalize_signed_delta_deg(true_azimuth_deg - bearing_deg)
    err_deg, err_dir = _signed_to_mag_dir(signed_delta)
    return err_deg, err_dir, signed_delta


def compute_compass_or_gyro_error(
    s: SightInput,
    sky: SkyfieldResult,
    *,
    deviation_card_csv_path: Optional[str] = None,
) -> CompassErrorResult:
    """
    Modes:
    - GYRO_1 / GYRO_2:
        error = Zn - observed bearing
    - MAGNETIC:
        compass error = Zn - compass bearing
        if variation provided:
            observed deviation = compass error - variation
        if deviation card provided:
            interpolate expected deviation from card at observed bearing
            deviation_diff = observed deviation - card deviation
    """
    if s.observed_bearing_deg is None:
        raise ValueError("observed_bearing_deg is required.")

    err_deg, err_dir, signed_error = compute_error_from_bearing(
        true_azimuth_deg=sky.zn_deg,
        bearing_deg=s.observed_bearing_deg,
    )

    observed_deviation_deg = None
    card_deviation_deg = None
    deviation_diff_deg = None

    if s.instrument_mode == "MAGNETIC":
        if s.variation_deg is not None:
            # Deviation = Compass Error - Variation
            observed_deviation_deg = signed_error - s.variation_deg

        if deviation_card_csv_path:
            pts = load_deviation_card_csv(deviation_card_csv_path)
            card_deviation_deg = interpolate_deviation(pts, s.observed_bearing_deg)

        if observed_deviation_deg is not None and card_deviation_deg is not None:
            deviation_diff_deg = observed_deviation_deg - card_deviation_deg

    label = s.instrument_label.strip() if s.instrument_label.strip() else s.instrument_mode

    return CompassErrorResult(
        instrument_mode=s.instrument_mode,
        instrument_label=label,
        true_azimuth_deg=float(sky.zn_deg),
        bearing_used_deg=float(s.observed_bearing_deg),
        error_deg=float(err_deg),
        error_dir=err_dir,
        variation_deg=s.variation_deg,
        observed_deviation_deg=observed_deviation_deg,
        card_deviation_deg=card_deviation_deg,
        deviation_diff_deg=deviation_diff_deg,
    )