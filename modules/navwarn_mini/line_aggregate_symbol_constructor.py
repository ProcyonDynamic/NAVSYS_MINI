from __future__ import annotations

import math


def _nm_offsets(lat: float, size_nm: float) -> tuple[float, float]:
    dlat = size_nm / 60.0
    coslat = max(1e-6, abs(math.cos(math.radians(lat))))
    dlon = size_nm / (60.0 * coslat)
    return dlat, dlon


def build_symbol_vertices(
    *,
    symbol_kind: str,
    lat: float,
    lon: float,
    size_nm: float = 0.6,
) -> list[tuple[float, float]]:
    kind = " ".join((symbol_kind or "").upper().split()) or "X"
    dlat, dlon = _nm_offsets(lat, size_nm=size_nm)

    if kind in ("X", "DEFAULT", "UNKNOWN"):
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat + dlat, lon - dlon),
            (lat - dlat, lon + dlon),
        ]

    if kind == "SQUARE":
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat - dlat, lon + dlon),
            (lat - dlat, lon - dlon),
        ]

    if kind == "DIAMOND":
        return [
            (lat, lon - dlon),
            (lat + dlat, lon),
            (lat, lon + dlon),
            (lat - dlat, lon),
            (lat, lon - dlon),
        ]

    if kind == "SQUARE_X":
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat - dlat, lon + dlon),
            (lat - dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat + dlat, lon - dlon),
            (lat - dlat, lon + dlon),
        ]

    if kind == "WRECK":
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat + dlat, lon - dlon),
            (lat - dlat, lon + dlon),
            (lat, lon - dlon * 1.3),
            (lat, lon + dlon * 1.3),
        ]

    if kind == "BEACON":
        return [
            (lat - dlat, lon),
            (lat + dlat, lon),
            (lat + dlat * 0.35, lon - dlon * 0.55),
            (lat + dlat, lon),
            (lat + dlat * 0.35, lon + dlon * 0.55),
        ]

    if kind == "BUOY":
        return [
            (lat + dlat, lon),
            (lat + dlat * 0.25, lon + dlon),
            (lat - dlat * 0.55, lon + dlon * 0.70),
            (lat - dlat, lon),
            (lat - dlat * 0.55, lon - dlon * 0.70),
            (lat + dlat * 0.25, lon - dlon),
            (lat + dlat, lon),
        ]

    if kind == "PLATFORM":
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat - dlat, lon + dlon),
            (lat - dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat + dlat, lon - dlon),
            (lat - dlat, lon + dlon),
        ]

    if kind == "MODU":
        return [
            (lat - dlat, lon - dlon),
            (lat + dlat, lon - dlon),
            (lat + dlat, lon + dlon),
            (lat - dlat, lon + dlon),
            (lat - dlat, lon - dlon),
            (lat + dlat * 1.2, lon),
            (lat - dlat * 1.2, lon),
            (lat, lon - dlon * 1.2),
            (lat, lon + dlon * 1.2),
        ]

    return [
        (lat - dlat, lon - dlon),
        (lat + dlat, lon + dlon),
        (lat + dlat, lon - dlon),
        (lat - dlat, lon + dlon),
    ]