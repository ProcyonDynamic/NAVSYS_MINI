from __future__ import annotations

from typing import List, Tuple

from .models import (
    WarningClassified,
    LineAggregateObject,
    StyledVertex,
    TextObject,
)


def _color_for_band(band: str, *, red_color_no: int, amber_color_no: int) -> int:
    if band == "RED":
        return red_color_no
    return amber_color_no


def _compute_anchor_point(w: WarningClassified) -> Tuple[float, float]:
    """
    Choose a sensible anchor for text placement.
    v0.1: first vertex.
    """
    v = w.geometry.vertices[0]
    return (v.lat, v.lon)


def _point_symbol_x(
    lat: float,
    lon: float,
    *,
    size_nm: float = 0.6,
) -> List[Tuple[float, float]]:
    """
    Build a single-stroke 'X' around (lat, lon) as a polyline path:
      (-1,-1) -> (1,1) -> (1,-1) -> (-1,1)

    We approximate NM offsets to degrees:
      1 minute latitude = 1 NM
      delta_lat_deg = nm / 60
      delta_lon_deg = nm / (60*cos(lat))
    """
    # Convert size to degree offsets
    dlat = size_nm / 60.0
    coslat = max(1e-6, abs(__import__("math").cos(__import__("math").radians(lat))))
    dlon = size_nm / (60.0 * coslat)

    pts = [
        (lat - dlat, lon - dlon),
        (lat + dlat, lon + dlon),
        (lat + dlat, lon - dlon),
        (lat - dlat, lon + dlon),
    ]
    return pts


def _ensure_area_closed(vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if not vertices:
        return vertices
    if vertices[0] != vertices[-1]:
        return vertices + [vertices[0]]
    return vertices


def build_line_aggregate(
    w: WarningClassified,
    *,
    enable_text: bool = True,
    title_text_size: int = 16,
    body_text_size: int = 14,
    red_color_no: int = 9,
    amber_color_no: int = 2,
    gap_color_no: int = 5,
    main_width: int = 3,
    gap_width: int = 1,
    main_line_type: int = 1,
    gap_line_type: int = 3,
) -> LineAggregateObject:
    """
    Builds one atomic LINE_AGGREGATE for a warning.

    Geometry rules:
    - POINT -> render as an X symbol (single continuous stroke).
    - LINE  -> render as polyline.
    - AREA  -> render as closed boundary polyline (should already be normalized, but we guard).

    Styling rules:
    - Main geometry: width=3, line_type=solid, color=RED(9) or AMBER(2).
    - Optional GAP vertices are supported (comment='GAP', thin cyan), but v0.1 X symbol doesn't need them.

    Text rules:
    - Title text size 16
    - Body text size 14
    (Color is handled by ECDIS; we still emit text. Printed NS-01/appendix is authoritative for body.)
    """
    if w.status != "OK":
        # Fail closed: do not build plot objects if invalid.
        raise ValueError(f"Cannot build plot object for status={w.status}: {w.errors}")

    band = w.band
    main_color = _color_for_band(band, red_color_no=red_color_no, amber_color_no=amber_color_no)

    geom_type = w.geometry.geom_type
    verts_ll = [(v.lat, v.lon) for v in w.geometry.vertices]

    if geom_type == "POINT":
        # Use first vertex as center
        center_lat, center_lon = verts_ll[0]
        draw_path = _point_symbol_x(center_lat, center_lon, size_nm=0.6)
    elif geom_type == "LINE":
        draw_path = verts_ll
    elif geom_type == "AREA":
        draw_path = _ensure_area_closed(verts_ll)
    else:
        raise ValueError(f"Unknown geom_type: {geom_type}")

    styled_vertices: List[StyledVertex] = [
        StyledVertex(
            lat=lat,
            lon=lon,
            line_type=main_line_type,
            width=main_width,
            color_no=main_color,
            comment="",
        )
        for (lat, lon) in draw_path
    ]

    # Text objects (optional)
    text_objects: List[TextObject] = []
    if enable_text:
        anchor_lat, anchor_lon = _compute_anchor_point(w)

        # Title near anchor
        text_objects.append(
            TextObject(
                lat=anchor_lat,
                lon=anchor_lon,
                rotation_deg=0.0,
                size=title_text_size,
                text=w.warning_id.strip() if w.warning_id.strip() else w.title.strip(),
            )
        )

        # Body slightly offset in latitude (about 0.3 NM ~ 0.005 deg)
        body_lat = anchor_lat - (0.3 / 60.0)
        body_text = w.body.strip()
        if body_text:
            # Keep body reasonable for ECDIS text; full text always in printed report
            if len(body_text) > 240:
                body_text = body_text[:237] + "..."
            text_objects.append(
                TextObject(
                    lat=body_lat,
                    lon=anchor_lon,
                    rotation_deg=0.0,
                    size=body_text_size,
                    text=body_text,
                )
            )

    return LineAggregateObject(
        run_id=w.run_id,
        warning_id=w.warning_id,
        band=w.band,
        default_line_type=main_line_type,
        default_width=main_width,
        default_color_no=main_color,
        vertices=styled_vertices,
        text_objects=text_objects,
    )