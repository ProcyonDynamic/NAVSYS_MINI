from __future__ import annotations

import re
from typing import Literal

GeomType = Literal["POINT", "LINE", "AREA"]


_AREA_HINTS = [
    "AREA BOUND BY",
    "AREAS BOUND BY",
    "BOUNDED BY",
    "BOUND BY",
    "WITHIN",
    "RADIUS",
    "CIRCLE",
    "SAFETY ZONE",
]

_LINE_HINTS = [
    "LINE",
    "TRACKLINE",
    "CABLE ROUTE",
    "PIPELINE ROUTE",
    "FROM",
    "TO",
    "BETWEEN",
]


def infer_geom_type_from_text(raw_text: str, vertex_count: int) -> GeomType:
    """
    v0.1 heuristic (safe defaults):
    - 0 verts: POINT (validation will fail anyway)
    - 1 vert: POINT
    - 2+ verts:
        - if strong AREA hints -> AREA
        - else if strong LINE hints -> LINE
        - else -> AREA if >=3, else LINE
    """
    if vertex_count <= 1:
        return "POINT"

    u = (raw_text or "").upper()

    if any(h in u for h in _AREA_HINTS):
        return "AREA"
    if any(h in u for h in _LINE_HINTS):
        # if you explicitly say LINE/ROUTE/FROM-TO, treat as LINE
        return "LINE"

    # fallback: 3+ points usually describe a boundary -> AREA
    if vertex_count >= 3:
        return "AREA"
    return "LINE"