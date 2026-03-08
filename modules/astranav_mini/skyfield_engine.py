from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from skyfield.api import load, wgs84, Star
from skyfield.data import hipparcos

from .models import SightInput, SkyfieldResult


class AstraNavError(Exception):
    pass


# Cache timescale / ephemeris in module memory
_TS = None
_EPH = None
_STARS_DF = None


def _get_timescale():
    global _TS
    if _TS is None:
        _TS = load.timescale()
    return _TS


def _get_ephemeris():
    global _EPH
    if _EPH is None:
        _EPH = load("de421.bsp")
    return _EPH


def _get_stars_dataframe():
    global _STARS_DF
    if _STARS_DF is None:
        with load.open(hipparcos.URL) as f:
            _STARS_DF = hipparcos.load_dataframe(f)
    return _STARS_DF


def _parse_time_utc(time_utc: str):
    """
    Parse ISO8601 Z string into Skyfield time.
    """
    ts = _get_timescale()

    s = time_utc.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return ts.from_datetime(dt)


def _normalize_body_name(body_name: str) -> str:
    return (body_name or "").strip().lower()


def _resolve_body(s: SightInput):
    """
    Resolve the requested celestial body for Skyfield.

    Supported:
    - SUN
    - PLANET (Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune)
    - STAR   (by Hipparcos common name match where possible)
    """
    eph = _get_ephemeris()
    kind = s.body_kind.upper()
    name = _normalize_body_name(s.body_name)

    if kind == "SUN":
        return eph["sun"]

    if kind == "PLANET":
        planet_map = {
            "mercury": "mercury barycenter",
            "venus": "venus barycenter",
            "mars": "mars barycenter",
            "jupiter": "jupiter barycenter",
            "saturn": "saturn barycenter",
            "uranus": "uranus barycenter",
            "neptune": "neptune barycenter",
            # optional aliases
            "mercury barycenter": "mercury barycenter",
            "venus barycenter": "venus barycenter",
            "mars barycenter": "mars barycenter",
            "jupiter barycenter": "jupiter barycenter",
            "saturn barycenter": "saturn barycenter",
            "uranus barycenter": "uranus barycenter",
            "neptune barycenter": "neptune barycenter",
        }
        key = planet_map.get(name)
        if not key:
            raise AstraNavError(f"Unsupported planet name: {s.body_name!r}")
        return eph[key]

    if kind == "STAR":
        df = _get_stars_dataframe()

        # Match common navigational star names against dataframe "name" column if present.
        # If no direct match exists, user can later provide HIP id in an upgraded version.
        if "name" not in df.columns:
            raise AstraNavError("Hipparcos dataframe does not contain star names.")

        matches = df[df["name"].fillna("").str.lower() == name]
        if len(matches) == 0:
            raise AstraNavError(f"Star not found by name: {s.body_name!r}")

        row = matches.iloc[0]
        return Star.from_dataframe(row)

    raise AstraNavError(f"Unsupported body kind: {s.body_kind!r}")


def _normalize_zn(az_deg: float) -> float:
    """
    Normalize azimuth to 0 <= Zn < 360
    """
    z = az_deg % 360.0
    if z < 0:
        z += 360.0
    return z


def compute_zn_hc_skyfield(s: SightInput) -> SkyfieldResult:
    """
    Compute:
    - Zn: true azimuth from observer to celestial body
    - Hc: computed altitude (same apparent altitude Skyfield returns)

    Notes:
    - Uses geodetic position via wgs84.latlon
    - Returns apparent topocentric alt/az
    """
    if not (-90.0 <= s.lat <= 90.0):
        raise AstraNavError(f"Latitude out of range: {s.lat}")
    if not (-180.0 <= s.lon <= 180.0):
        raise AstraNavError(f"Longitude out of range: {s.lon}")

    t = _parse_time_utc(s.time_utc)
    eph = _get_ephemeris()
    earth = eph["earth"]

    body = _resolve_body(s)
    observer = earth + wgs84.latlon(s.lat, s.lon)

    astrometric = observer.at(t).observe(body)
    apparent = astrometric.apparent()
    alt, az, _distance = apparent.altaz()

    zn = _normalize_zn(az.degrees)
    hc = float(alt.degrees)

    return SkyfieldResult(
        zn_deg=zn,
        hc_deg=hc,
    )