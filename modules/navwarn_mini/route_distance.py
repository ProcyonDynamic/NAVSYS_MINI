from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import List, Tuple


EARTH_RADIUS_NM = 3440.065


def _dm_to_deg(deg: float, minutes: float, hemi: str, is_lat: bool) -> float:
    v = abs(deg) + (minutes / 60.0)
    hemi = hemi.upper()

    if is_lat:
        if hemi == "S":
            v = -v
    else:
        if hemi == "W":
            v = -v
    return v


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    lam1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lam2 = math.radians(lon2)

    dphi = phi2 - phi1
    dlam = lam2 - lam1

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.asin(min(1.0, math.sqrt(a)))

    return EARTH_RADIUS_NM * c


def load_jrc_route_csv(route_csv_path: str) -> List[Tuple[float, float]]:
    """
    Load route waypoints from JRC route sheet CSV.

    Expected waypoint rows look like:
    000,22,39.277,N,097,40.607,W,...

    Returns:
        [(lat, lon), ...]
    """
    p = Path(route_csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Route CSV not found: {route_csv_path}")

    waypoints: List[Tuple[float, float]] = []

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            # Skip comments / headers
            first = row[0].strip() if len(row) > 0 else ""
            if first.startswith("//"):
                continue
            if first in ("WPT No.", ""):
                continue

            # JRC waypoint rows usually start with numeric WPT No.
            if not first.isdigit():
                continue

            # Need at least:
            # 0=WPT No
            # 1=LAT deg
            # 2=LAT min
            # 3=N/S
            # 4=LON deg
            # 5=LON min
            # 6=E/W
            if len(row) < 7:
                continue

            try:
                lat_deg = float(row[1].strip())
                lat_min = float(row[2].strip())
                lat_hemi = row[3].strip().upper()

                lon_deg = float(row[4].strip())
                lon_min = float(row[5].strip())
                lon_hemi = row[6].strip().upper()

                lat = _dm_to_deg(lat_deg, lat_min, lat_hemi, is_lat=True)
                lon = _dm_to_deg(lon_deg, lon_min, lon_hemi, is_lat=False)

                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    waypoints.append((lat, lon))

            except (ValueError, IndexError):
                continue

    return waypoints


def min_distance_vertices_to_route_waypoints(
    vertices: List[Tuple[float, float]],
    route_waypoints: List[Tuple[float, float]],
) -> float:
    """
    v0.1:
    Minimum distance from any warning vertex to any route waypoint.
    """
    if not vertices:
        raise ValueError("No warning vertices provided.")
    if not route_waypoints:
        raise ValueError("No route waypoints provided.")

    best = None

    for vlat, vlon in vertices:
        for rlat, rlon in route_waypoints:
            d = haversine_nm(vlat, vlon, rlat, rlon)
            if best is None or d < best:
                best = d

    assert best is not None
    return float(best)