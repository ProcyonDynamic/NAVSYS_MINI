from __future__ import annotations

from dataclasses import dataclass

from .models import SightInput, SkyfieldResult


@dataclass(frozen=True)
class LOPResult:
    zn_deg: float
    hc_deg: float
    ho_deg: float
    intercept_nm: float
    towards_away: str   # "TOWARDS" | "AWAY"
    lop_course_1_deg: float
    lop_course_2_deg: float


def _normalize_360(x: float) -> float:
    y = x % 360.0
    if y < 0:
        y += 360.0
    return y


def compute_intercept_nm(ho_deg: float, hc_deg: float) -> float:
    """
    Intercept in NM = (Ho - Hc) * 60
    """
    return (ho_deg - hc_deg) * 60.0


def compute_lop(
    s: SightInput,
    sky: SkyfieldResult,
) -> LOPResult:
    """
    Computes LOP by intercept method.

    Requires:
    - observed_ho_deg
    - computed hc_deg from Skyfield

    Result:
    - intercept_nm (absolute)
    - towards/away
    - two equivalent LOP courses (Zn+90 and Zn-90)
    """
    if s.observed_ho_deg is None:
        raise ValueError("observed_ho_deg is required for LOP computation.")
    if sky.hc_deg is None:
        raise ValueError("sky.hc_deg is required for LOP computation.")

    ho = float(s.observed_ho_deg)
    hc = float(sky.hc_deg)
    zn = float(sky.zn_deg)

    signed_intercept = compute_intercept_nm(ho, hc)
    towards_away = "TOWARDS" if signed_intercept >= 0 else "AWAY"

    intercept_nm = abs(signed_intercept)

    lop_course_1 = _normalize_360(zn + 90.0)
    lop_course_2 = _normalize_360(zn - 90.0)

    return LOPResult(
        zn_deg=zn,
        hc_deg=hc,
        ho_deg=ho,
        intercept_nm=intercept_nm,
        towards_away=towards_away,
        lop_course_1_deg=lop_course_1,
        lop_course_2_deg=lop_course_2,
    )