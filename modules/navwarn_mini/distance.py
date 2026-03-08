from __future__ import annotations

import math
from dataclasses import replace
from typing import List, Tuple, Optional

from .models import WarningDraft, WarningClassified, ShipPosition
from .normalize import normalize_warning
from .validate import validate_warning


# Mean Earth radius in nautical miles (1 NM = 1852 m)
EARTH_RADIUS_NM = 3440.065


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance using Haversine formula.
    Inputs/outputs in degrees / nautical miles.
    """
    # Convert degrees -> radians
    φ1 = math.radians(lat1)
    λ1 = math.radians(lon1)
    φ2 = math.radians(lat2)
    λ2 = math.radians(lon2)

    dφ = φ2 - φ1
    dλ = λ2 - λ1

    a = math.sin(dφ / 2.0) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2.0) ** 2
    c = 2.0 * math.asin(min(1.0, math.sqrt(a)))

    return EARTH_RADIUS_NM * c


def compute_distance_nm_simple(
    ship: ShipPosition,
    vertices: List[Tuple[float, float]],
) -> float:
    """
    v0.1 simple distance:
    - Compute great-circle distance from ship position to each vertex.
    - Return the minimum.
    """
    if not vertices:
        raise ValueError("No vertices provided for distance calculation.")

    best = None
    for (lat, lon) in vertices:
        d = _haversine_nm(ship.lat, ship.lon, lat, lon)
        if best is None or d < best:
            best = d

    assert best is not None
    return float(best)


def _band_from_distance(distance_nm: Optional[float], threshold_nm: float) -> str:
    """
    Band rule (failsafe):
      - distance None -> RED
      - <= threshold -> RED
      - > threshold -> AMBER
    """
    if distance_nm is None:
        return "RED"
    return "RED" if distance_nm <= threshold_nm else "AMBER"


def classify_warning(
    *,
    draft: WarningDraft,
    processed_utc: str,
    ship_position: Optional[ShipPosition],
    threshold_nm: float = 50.0,
) -> WarningClassified:
    """
    Produces WarningClassified.

    Rules:
    - Always normalize first.
    - Validate draft; if errors -> status FAILED, distance may still compute if possible,
      but safest is to mark FAILED and set distance None.
    - If ship_position is None => distance_nm=None and band=RED (failsafe)
    - Else distance_nm = min distance ship->vertex
    - band = RED if distance<=threshold else AMBER
    """
    nd = normalize_warning(draft)
    errs = validate_warning(nd)

    # If validation failed, we do not compute distance (keeps behavior predictable/safe).
    if errs:
        return WarningClassified(
            run_id=nd.run_id,
            processed_utc=processed_utc,
            navarea=nd.navarea,
            source_kind=nd.source_kind,
            source_ref=nd.source_ref,
            warning_id=nd.warning_id,
            title=nd.title,
            body=nd.body,
            validity=nd.validity,
            geometry=nd.geometry,
            ship_position=ship_position,
            distance_nm=None,
            band="RED",
            status="FAILED",
            errors=errs,
        )

    # OK draft. Compute distance if we have ship position.
    dist_nm: Optional[float] = None
    if ship_position is not None:
        verts = [(v.lat, v.lon) for v in nd.geometry.vertices]
        dist_nm = compute_distance_nm_simple(ship_position, verts)

    band = _band_from_distance(dist_nm, threshold_nm)

    return WarningClassified(
        run_id=nd.run_id,
        processed_utc=processed_utc,
        navarea=nd.navarea,
        source_kind=nd.source_kind,
        source_ref=nd.source_ref,
        warning_id=nd.warning_id,
        title=nd.title,
        body=nd.body,
        validity=nd.validity,
        geometry=nd.geometry,
        ship_position=ship_position,
        distance_nm=dist_nm,
        band=band,
        status="OK",
        errors=[],
    )