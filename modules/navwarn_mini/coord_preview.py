from __future__ import annotations

import math
from typing import List, Tuple


def _deg_to_dm(x_deg: float, is_lat: bool) -> tuple[int, float, str]:
    x_abs = abs(x_deg)
    deg = int(x_abs)
    minutes = (x_abs - deg) * 60.0

    if is_lat:
        hemi = "N" if x_deg >= 0 else "S"
    else:
        hemi = "E" if x_deg >= 0 else "W"
    return deg, minutes, hemi


def format_lat_dm(lat: float) -> str:
    d, m, h = _deg_to_dm(lat, is_lat=True)
    return f"{d:02d}-{m:06.3f}{h}"


def format_lon_dm(lon: float) -> str:
    d, m, h = _deg_to_dm(lon, is_lat=False)
    return f"{d:03d}-{m:06.3f}{h}"


def format_pair_dm(lat: float, lon: float) -> str:
    return f"{format_lat_dm(lat)} {format_lon_dm(lon)}"


def preview_vertices_dm(vertices: List[Tuple[float, float]]) -> str:
    """
    Human-check preview in the same style navigators are used to:
      24-21.874N 094-57.956W
    """
    if not vertices:
        return "NO COORDINATES EXTRACTED\n"

    lines = []
    for i, (lat, lon) in enumerate(vertices, start=1):
        lines.append(f"{i:02d}. {format_pair_dm(lat, lon)}")
    return "\n".join(lines) + "\n"


def preview_vertices_decimal(vertices: List[Tuple[float, float]]) -> str:
    if not vertices:
        return "NO COORDINATES EXTRACTED\n"

    lines = []
    for i, (lat, lon) in enumerate(vertices, start=1):
        lines.append(f"{i:02d}. {lat:.6f}, {lon:.6f}")
    return "\n".join(lines) + "\n"