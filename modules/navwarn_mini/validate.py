from __future__ import annotations

from typing import List

from .models import WarningDraft, LatLon


def _in_lat_range(lat: float) -> bool:
    return -90.0 <= lat <= 90.0


def _in_lon_range(lon: float) -> bool:
    return -180.0 <= lon <= 180.0


def _count_unique_vertices(vertices: List[LatLon], eps: float = 1e-9) -> int:
    uniq: List[LatLon] = []
    for p in vertices:
        if not any(abs(p.lat - q.lat) <= eps and abs(p.lon - q.lon) <= eps for q in uniq):
            uniq.append(p)
    return len(uniq)


def validate_warning(draft: WarningDraft, *, max_vertices: int = 2000) -> List[str]:
    """
    Returns list of error strings (empty list means OK).

    Must check:
    - geom_type in {POINT, LINE, AREA}
    - lat/lon ranges for every vertex
    - vertex counts per geom_type
    - guardrails: max vertices
    """
    errs: List[str] = []

    g = draft.geometry
    geom_type = g.geom_type
    vertices = list(g.vertices or [])

    if geom_type not in ("POINT", "LINE", "AREA"):
        errs.append(f"Invalid geom_type: {geom_type!r} (expected POINT|LINE|AREA)")

    if len(vertices) == 0:
        errs.append("No vertices provided.")

    if len(vertices) > max_vertices:
        errs.append(f"Too many vertices: {len(vertices)} (max {max_vertices}).")

    # Lat/lon sanity
    for i, v in enumerate(vertices):
        if not _in_lat_range(v.lat):
            errs.append(f"Vertex[{i}] latitude out of range: {v.lat}")
        if not _in_lon_range(v.lon):
            errs.append(f"Vertex[{i}] longitude out of range: {v.lon}")

    # Minimum vertex counts
    # NOTE: AREA may be normalized to include closure vertex (first repeated at end).
    unique_count = _count_unique_vertices(vertices)

    if geom_type == "POINT":
        if unique_count < 1:
            errs.append("POINT requires at least 1 coordinate.")

    elif geom_type == "LINE":
        if unique_count < 2:
            errs.append("LINE requires at least 2 unique coordinates.")

    elif geom_type == "AREA":
        if unique_count < 3:
            errs.append("AREA requires at least 3 unique coordinates.")
        # If closed flag is True, ensure last==first (after normalization it should be)
        if g.closed:
            if len(vertices) < 4:
                # With closure, a minimal triangle is 4 points (3 + repeated first)
                errs.append("AREA marked closed but has too few vertices to be a closed polygon.")
            else:
                first = vertices[0]
                last = vertices[-1]
                if abs(first.lat - last.lat) > 1e-9 or abs(first.lon - last.lon) > 1e-9:
                    errs.append("AREA marked closed but last vertex != first vertex (polygon not closed).")

    # Basic required text fields (keep it minimal but useful)
    if not (draft.warning_id or "").strip():
        errs.append("warning_id is empty.")
    if not (draft.title or "").strip():
        errs.append("title is empty.")
    if not (draft.body or "").strip():
        errs.append("body is empty.")
    if not (draft.navarea or "").strip():
        errs.append("navarea is empty.")

    return errs