from __future__ import annotations

from dataclasses import replace
from typing import List

from .models import Geometry, LatLon, WarningDraft


def _same_point(a: LatLon, b: LatLon, eps: float = 1e-9) -> bool:
    return abs(a.lat - b.lat) <= eps and abs(a.lon - b.lon) <= eps


def _unique_points(points: List[LatLon], eps: float = 1e-9) -> List[LatLon]:
    """Deduplicate while preserving order (eps-based)."""
    out: List[LatLon] = []
    for p in points:
        if not any(_same_point(p, q, eps=eps) for q in out):
            out.append(p)
    return out


def normalize_geometry(g: Geometry) -> Geometry:
    """
    Normalization rules:
    - POINT: require at least 1 vertex; keep order; closed=False.
    - LINE: require >=2 vertices; keep order; closed=False.
    - AREA: require >=3 unique vertices; ensure closed=True by appending first vertex
      if last != first.
    """
    if g.vertices is None:
        verts: List[LatLon] = []
    else:
        verts = list(g.vertices)

    geom_type = g.geom_type

    if geom_type == "POINT":
        # Keep as-is (validation will enforce >=1)
        return Geometry(geom_type="POINT", vertices=verts, closed=False)

    if geom_type == "LINE":
        # Keep as-is (validation will enforce >=2)
        return Geometry(geom_type="LINE", vertices=verts, closed=False)

    if geom_type == "AREA":
        # For AREA we normalize closure and uniqueness of the boundary vertices.
        # We allow repeated last==first closure vertex.
        unique = _unique_points(verts)
        # If the operator already included closure vertex, unique() removes it. We'll re-add closure below.
        if len(unique) >= 1:
            first = unique[0]
            # Rebuild base sequence in original order but without exact duplicates (except closure)
            base = unique
            # Close it
            if len(base) > 0 and not _same_point(base[-1], first):
                base = base + [first]
            return Geometry(geom_type="AREA", vertices=base, closed=True)
        return Geometry(geom_type="AREA", vertices=unique, closed=False)

    # Unknown geom_type: preserve but don't mutate (validation will fail it)
    return g


def _clean_text(s: str) -> str:
    # Trim + collapse internal whitespace lines minimally
    s = (s or "").strip()
    # normalize Windows newlines and strip trailing spaces per line
    lines = [ln.rstrip() for ln in s.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    # remove excessive blank lines (keep single blank lines)
    out_lines = []
    blank = False
    for ln in lines:
        if ln.strip() == "":
            if not blank:
                out_lines.append("")
            blank = True
        else:
            out_lines.append(ln)
            blank = False
    return "\n".join(out_lines).strip()


def normalize_warning(draft: WarningDraft) -> WarningDraft:
    """
    Returns a new WarningDraft with:
    - normalized geometry
    - trimmed/cleaned strings (warning_id, title, body)
    """
    ng = normalize_geometry(draft.geometry)

    # Use dataclasses.replace to keep the object frozen-friendly.
    return replace(
        draft,
        warning_id=_clean_text(draft.warning_id),
        title=_clean_text(draft.title),
        body=_clean_text(draft.body),
        operator_name=_clean_text(draft.operator_name),
        operator_watch=_clean_text(draft.operator_watch),
        operator_notes=_clean_text(draft.operator_notes),
        geometry=ng,
    )