from __future__ import annotations

from pathlib import Path

from .route_distance import load_jrc_route_csv


NAVAREA_BOUNDS = {
    "IV": {
        "lat_min": 0.0,
        "lat_max": 90.0,
        "lon_min": -100.0,
        "lon_max": -5.0,
    },
    "V": {
        "lat_min": -60.0,
        "lat_max": 15.0,
        "lon_min": -70.0,
        "lon_max": 20.0,
    },
    "VI": {
        "lat_min": -60.0,
        "lat_max": 12.0,
        "lon_min": 20.0,
        "lon_max": 120.0,
    },
    "XII": {
        "lat_min": 0.0,
        "lat_max": 66.0,
        "lon_min": 100.0,
        "lon_max": 180.0,
    },
}


def _inside_bounds(lat: float, lon: float, bounds: dict) -> bool:
    return (
        bounds["lat_min"] <= lat <= bounds["lat_max"]
        and bounds["lon_min"] <= lon <= bounds["lon_max"]
    )


def detect_navareas_from_route_csv(
    route_csv_path: str,
) -> dict:
    path = Path(route_csv_path)
    if not path.exists():
        return {
            "ok": False,
            "route_id": "",
            "navareas": [],
            "errors": [f"Route CSV not found: {route_csv_path}"],
        }

    try:
        waypoints = load_jrc_route_csv(str(path))
    except Exception as exc:
        return {
            "ok": False,
            "route_id": "",
            "navareas": [],
            "errors": [f"Failed to load route CSV: {exc}"],
        }

    detected: list[str] = []

    for lat, lon in waypoints:
        for navarea, bounds in NAVAREA_BOUNDS.items():
            if _inside_bounds(lat, lon, bounds):
                if navarea not in detected:
                    detected.append(navarea)

    return {
        "ok": True,
        "route_id": path.stem.upper(),
        "navareas": detected,
        "waypoint_count": len(waypoints),
        "errors": [],
    }


def build_chart_slots(
    *,
    output_root: str,
    route_id: str,
    navareas: list[str],
) -> list[dict]:
    root = Path(output_root)
    charts_dir = root / "NAVWARN" / "voyage_usercharts"

    slots: list[dict] = []

    for navarea in navareas:
        chart_name = f"{route_id}_{navarea}_userchart.csv"
        chart_path = charts_dir / chart_name

        slots.append(
            {
                "route_id": route_id,
                "navarea": navarea,
                "chart_name": chart_name,
                "chart_path": str(chart_path),
                "exists": chart_path.exists(),
            }
        )

    return slots