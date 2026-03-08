from __future__ import annotations

from typing import List, Tuple

from .coords import extract_vertices_from_text
from .geom_infer import infer_geom_type_from_text


def extract_vertices_and_geom(raw_text: str) -> tuple[list[tuple[float, float]], str]:
    """
    Returns (vertices, geom_type).
    - vertices: list[(lat, lon)] decimal degrees
    - geom_type: "POINT"|"LINE"|"AREA"
    """
    verts = extract_vertices_from_text(raw_text)
    geom = infer_geom_type_from_text(raw_text, len(verts))
    return verts, geom