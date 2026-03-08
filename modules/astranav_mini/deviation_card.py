from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple


def load_deviation_card_csv(csv_path: str) -> List[Tuple[float, float]]:
    """
    CSV format:
        Heading,Deviation

    Convention:
        East  = positive
        West  = negative

    Example:
        0,1.0
        30,1.5
        ...
        360,1.0
    """
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Deviation card CSV not found: {csv_path}")

    points: List[Tuple[float, float]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                hdg = float((row.get("Heading") or "").strip())
                dev = float((row.get("Deviation") or "").strip())
            except ValueError:
                continue
            points.append((hdg, dev))

    if not points:
        raise ValueError("Deviation card CSV contains no valid rows.")

    points.sort(key=lambda x: x[0])

    # Ensure 0/360 wrap support
    headings = [h for h, _ in points]
    if 0.0 not in headings and 360.0 in headings:
        # ok
        pass
    elif 360.0 not in headings and 0.0 in headings:
        # duplicate 0 as 360
        dev0 = [d for h, d in points if h == 0.0][0]
        points.append((360.0, dev0))
        points.sort(key=lambda x: x[0])

    return points


def _normalize_heading_360(hdg: float) -> float:
    x = hdg % 360.0
    if x < 0:
        x += 360.0
    return x


def interpolate_deviation(points: List[Tuple[float, float]], heading_deg: float) -> float:
    """
    Linear interpolation on a heading circle.
    Requires points sorted by heading and ideally 0/360 continuity.
    """
    if not points:
        raise ValueError("No deviation card points provided.")

    h = _normalize_heading_360(heading_deg)

    # exact match
    for hp, dp in points:
        if abs(h - hp) < 1e-9:
            return float(dp)

    # if heading is beyond last defined point, wrap toward 360/0
    pts = list(points)
    if pts[-1][0] < 360.0 and pts[0][0] == 0.0:
        pts.append((360.0, pts[0][1]))

    for i in range(len(pts) - 1):
        h1, d1 = pts[i]
        h2, d2 = pts[i + 1]
        if h1 <= h <= h2:
            if abs(h2 - h1) < 1e-9:
                return float(d1)
            t = (h - h1) / (h2 - h1)
            return float(d1 + t * (d2 - d1))

    # wrap fallback
    return float(pts[-1][1])