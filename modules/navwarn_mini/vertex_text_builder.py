from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VertexTextPolicy:
    char_width_nm: float = 1.20
    char_height_nm: float = 1.80
    char_spacing_nm: float = 0.45

    text_line_type: int = 1
    text_width: int = 1
    text_color_no: int = 5

    connector_line_type: int = 3
    connector_width: int = 1
    connector_color_no: int = 2

    anchor_dx_nm: float = 0.80
    anchor_dy_nm: float = 0.80


@dataclass(frozen=True)
class StyledTextVertex:
    lat: float
    lon: float
    line_type: int
    width: int
    color_no: int


@dataclass(frozen=True)
class Glyph:
    paths: list[list[tuple[float, float]]]
    advance: float


def short_warning_id(warning_id: str) -> str:
    parts = " ".join(warning_id.upper().split()).split()
    if len(parts) >= 3 and parts[0] == "NAVAREA":
        return f"{parts[1]} {parts[2]}"
    return warning_id.strip().upper()


def policy_for_phrase(
    *,
    text: str,
    object_kind: str,
) -> VertexTextPolicy:
    cleaned = " ".join((text or "").upper().split())
    n = len(cleaned)

    if object_kind == "POINT":
        base = VertexTextPolicy(
            char_width_nm=0.85,
            char_height_nm=1.30,
            char_spacing_nm=0.28,
            text_line_type=1,
            text_width=1,
            text_color_no=5,
            connector_line_type=3,
            connector_width=1,
            connector_color_no=2,
            anchor_dx_nm=0.70,
            anchor_dy_nm=0.70,
        )
    elif object_kind == "LINE":
        base = VertexTextPolicy(
            char_width_nm=1.00,
            char_height_nm=1.55,
            char_spacing_nm=0.32,
            text_line_type=1,
            text_width=1,
            text_color_no=5,
            connector_line_type=3,
            connector_width=1,
            connector_color_no=2,
            anchor_dx_nm=0.50,
            anchor_dy_nm=0.60,
        )
    else:
        base = VertexTextPolicy(
            char_width_nm=1.20,
            char_height_nm=1.80,
            char_spacing_nm=0.38,
            text_line_type=1,
            text_width=1,
            text_color_no=5,
            connector_line_type=3,
            connector_width=1,
            connector_color_no=2,
            anchor_dx_nm=0.80,
            anchor_dy_nm=0.80,
        )

    if n >= 26:
        return VertexTextPolicy(
            char_width_nm=base.char_width_nm * 0.70,
            char_height_nm=base.char_height_nm * 0.70,
            char_spacing_nm=base.char_spacing_nm * 0.75,
            text_line_type=base.text_line_type,
            text_width=base.text_width,
            text_color_no=base.text_color_no,
            connector_line_type=base.connector_line_type,
            connector_width=base.connector_width,
            connector_color_no=base.connector_color_no,
            anchor_dx_nm=base.anchor_dx_nm,
            anchor_dy_nm=base.anchor_dy_nm,
        )

    if n >= 18:
        return VertexTextPolicy(
            char_width_nm=base.char_width_nm * 0.82,
            char_height_nm=base.char_height_nm * 0.82,
            char_spacing_nm=base.char_spacing_nm * 0.82,
            text_line_type=base.text_line_type,
            text_width=base.text_width,
            text_color_no=base.text_color_no,
            connector_line_type=base.connector_line_type,
            connector_width=base.connector_width,
            connector_color_no=base.connector_color_no,
            anchor_dx_nm=base.anchor_dx_nm,
            anchor_dy_nm=base.anchor_dy_nm,
        )

    return base


def _nm_to_deg_lat(nm: float) -> float:
    return nm / 60.0


def _nm_to_deg_lon(nm: float, lat: float) -> float:
    coslat = max(1e-6, abs(math.cos(math.radians(lat))))
    return nm / (60.0 * coslat)


def _xy_to_latlon(
    *,
    anchor_lat: float,
    anchor_lon: float,
    x_nm: float,
    y_nm: float,
) -> tuple[float, float]:
    lat = anchor_lat + _nm_to_deg_lat(y_nm)
    lon = anchor_lon + _nm_to_deg_lon(x_nm, anchor_lat)
    return lat, lon


def _same_point(
    a: tuple[float, float],
    b: tuple[float, float],
    eps: float = 1e-9,
) -> bool:
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps


def _append_if_new(
    out: list[tuple[float, float]],
    point: tuple[float, float],
) -> None:
    if not out or not _same_point(out[-1], point):
        out.append(point)


def _transform_path(
    *,
    path: list[tuple[float, float]],
    cursor_x_units: float,
    policy: VertexTextPolicy,
) -> list[tuple[float, float]]:
    transformed: list[tuple[float, float]] = []

    for local_x, local_y in path:
        x_nm = (
            policy.anchor_dx_nm
            + ((cursor_x_units + local_x) * policy.char_width_nm)
            + (cursor_x_units * policy.char_spacing_nm)
        )
        y_nm = policy.anchor_dy_nm + (local_y * policy.char_height_nm)
        _append_if_new(transformed, (x_nm, y_nm))

    return transformed


def _make_glyphs() -> dict[str, Glyph]:
    return {
        "A": Glyph(
            paths=[
                [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)],
                [(0.25, 0.50), (0.75, 0.50)],
            ],
            advance=1.20,
        ),
        "B": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0)],
                [(0.0, 1.0), (0.75, 0.85), (0.0, 0.55)],
                [(0.0, 0.55), (0.80, 0.35), (0.0, 0.0)],
            ],
            advance=1.20,
        ),
        "C": Glyph(
            paths=[
                [(1.0, 0.95), (0.55, 1.0), (0.10, 0.75), (0.0, 0.50), (0.10, 0.25), (0.55, 0.0), (1.0, 0.05)],
            ],
            advance=1.15,
        ),
        "D": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0)],
                [(0.0, 1.0), (0.70, 0.85), (0.95, 0.50), (0.70, 0.15), (0.0, 0.0)],
            ],
            advance=1.20,
        ),
        "E": Glyph(
            paths=[
                [(1.0, 1.0), (0.0, 1.0), (0.0, 0.0), (1.0, 0.0)],
                [(0.0, 0.50), (0.70, 0.50)],
            ],
            advance=1.10,
        ),
        "F": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
                [(0.0, 0.50), (0.70, 0.50)],
            ],
            advance=1.10,
        ),
        "G": Glyph(
            paths=[
                [(1.0, 0.95), (0.55, 1.0), (0.10, 0.75), (0.0, 0.50), (0.10, 0.25), (0.55, 0.0), (1.0, 0.05), (1.0, 0.45), (0.65, 0.45)],
            ],
            advance=1.20,
        ),
        "H": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0)],
                [(1.0, 0.0), (1.0, 1.0)],
                [(0.0, 0.50), (1.0, 0.50)],
            ],
            advance=1.20,
        ),
        "I": Glyph(
            paths=[
                [(0.0, 1.0), (1.0, 1.0)],
                [(0.5, 1.0), (0.5, 0.0)],
                [(0.0, 0.0), (1.0, 0.0)],
            ],
            advance=1.00,
        ),
        "J": Glyph(
            paths=[
                [(1.0, 1.0), (1.0, 0.20), (0.75, 0.0), (0.25, 0.0), (0.0, 0.20)],
            ],
            advance=1.10,
        ),
        "K": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0)],
                [(1.0, 1.0), (0.0, 0.50), (1.0, 0.0)],
            ],
            advance=1.15,
        ),
        "L": Glyph(
            paths=[
                [(0.0, 1.0), (0.0, 0.0), (1.0, 0.0)],
            ],
            advance=1.05,
        ),
        "M": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0), (0.5, 0.55), (1.0, 1.0), (1.0, 0.0)],
            ],
            advance=1.35,
        ),
        "N": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)],
            ],
            advance=1.25,
        ),
        "O": Glyph(
            paths=[
                [(0.15, 0.0), (0.85, 0.0), (1.0, 0.50), (0.85, 1.0), (0.15, 1.0), (0.0, 0.50), (0.15, 0.0)],
            ],
            advance=1.20,
        ),
        "P": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0), (0.75, 1.0), (0.95, 0.75), (0.75, 0.50), (0.0, 0.50)],
            ],
            advance=1.15,
        ),
        "Q": Glyph(
            paths=[
                [(0.15, 0.0), (0.85, 0.0), (1.0, 0.50), (0.85, 1.0), (0.15, 1.0), (0.0, 0.50), (0.15, 0.0)],
                [(0.60, 0.25), (1.0, -0.10)],
            ],
            advance=1.20,
        ),
        "R": Glyph(
            paths=[
                [(0.0, 0.0), (0.0, 1.0), (0.75, 1.0), (0.95, 0.75), (0.75, 0.50), (0.0, 0.50)],
                [(0.0, 0.50), (1.0, 0.0)],
            ],
            advance=1.20,
        ),
        "S": Glyph(
            paths=[
                [(1.0, 0.90), (0.65, 1.0), (0.20, 0.80), (0.75, 0.50), (0.95, 0.25), (0.60, 0.0), (0.0, 0.10)],
            ],
            advance=1.10,
        ),
        "T": Glyph(
            paths=[
                [(0.0, 1.0), (1.0, 1.0)],
                [(0.5, 1.0), (0.5, 0.0)],
            ],
            advance=1.05,
        ),
        "U": Glyph(
            paths=[
                [(0.0, 1.0), (0.0, 0.20), (0.20, 0.0), (0.80, 0.0), (1.0, 0.20), (1.0, 1.0)],
            ],
            advance=1.20,
        ),
        "V": Glyph(
            paths=[
                [(0.0, 1.0), (0.50, 0.0), (1.0, 1.0)],
            ],
            advance=1.15,
        ),
        "W": Glyph(
            paths=[
                [(0.0, 1.0), (0.20, 0.0), (0.50, 0.55), (0.80, 0.0), (1.0, 1.0)],
            ],
            advance=1.40,
        ),
        "X": Glyph(
            paths=[
                [(0.0, 1.0), (1.0, 0.0)],
                [(0.0, 0.0), (1.0, 1.0)],
            ],
            advance=1.15,
        ),
        "Y": Glyph(
            paths=[
                [(0.0, 1.0), (0.50, 0.50), (1.0, 1.0)],
                [(0.50, 0.50), (0.50, 0.0)],
            ],
            advance=1.15,
        ),
        "Z": Glyph(
            paths=[
                [(0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0)],
            ],
            advance=1.10,
        ),
        "0": Glyph(
            paths=[
                [(0.15, 0.0), (0.85, 0.0), (1.0, 0.50), (0.85, 1.0), (0.15, 1.0), (0.0, 0.50), (0.15, 0.0)],
            ],
            advance=1.15,
        ),
        "1": Glyph(
            paths=[
                [(0.35, 0.75), (0.50, 1.0), (0.50, 0.0)],
                [(0.25, 0.0), (0.75, 0.0)],
            ],
            advance=0.95,
        ),
        "2": Glyph(
            paths=[
                [(0.0, 0.80), (0.25, 1.0), (0.80, 1.0), (1.0, 0.75), (0.0, 0.0), (1.0, 0.0)],
            ],
            advance=1.10,
        ),
        "3": Glyph(
            paths=[
                [(0.0, 0.90), (0.25, 1.0), (0.80, 1.0), (0.55, 0.50), (0.80, 0.0), (0.20, 0.0), (0.0, 0.10)],
            ],
            advance=1.10,
        ),
        "4": Glyph(
            paths=[
                [(0.80, 0.0), (0.80, 1.0)],
                [(0.0, 0.35), (1.0, 0.35)],
                [(0.0, 0.35), (0.65, 1.0)],
            ],
            advance=1.15,
        ),
        "5": Glyph(
            paths=[
                [(1.0, 1.0), (0.15, 1.0), (0.0, 0.55), (0.70, 0.55), (0.95, 0.30), (0.75, 0.0), (0.15, 0.0)],
            ],
            advance=1.10,
        ),
        "6": Glyph(
            paths=[
                [(0.95, 0.85), (0.75, 1.0), (0.20, 0.80), (0.0, 0.40), (0.20, 0.0), (0.75, 0.0), (0.95, 0.30), (0.75, 0.55), (0.15, 0.55)],
            ],
            advance=1.10,
        ),
        "7": Glyph(
            paths=[
                [(0.0, 1.0), (1.0, 1.0), (0.35, 0.0)],
            ],
            advance=1.05,
        ),
        "8": Glyph(
            paths=[
                [(0.20, 0.50), (0.0, 0.75), (0.20, 1.0), (0.80, 1.0), (1.0, 0.75), (0.80, 0.50), (0.20, 0.50), (0.0, 0.25), (0.20, 0.0), (0.80, 0.0), (1.0, 0.25), (0.80, 0.50)],
            ],
            advance=1.10,
        ),
        "9": Glyph(
            paths=[
                [(0.85, 0.45), (0.20, 0.45), (0.0, 0.70), (0.20, 1.0), (0.80, 1.0), (1.0, 0.70), (0.80, 0.20), (0.55, 0.0), (0.10, 0.10)],
            ],
            advance=1.10,
        ),
        "/": Glyph(
            paths=[
                [(0.10, 0.0), (0.90, 1.0)],
            ],
            advance=0.95,
        ),
        "-": Glyph(
            paths=[
                [(0.15, 0.50), (0.85, 0.50)],
            ],
            advance=0.90,
        ),
        ".": Glyph(
            paths=[
                [(0.45, 0.0), (0.55, 0.0)],
            ],
            advance=0.55,
        ),
        "|": Glyph(
            paths=[
                [(0.50, 0.0), (0.50, 1.0)],
            ],
            advance=0.70,
        ),
        " ": Glyph(
            paths=[],
            advance=0.80,
        ),
    }


def _fallback_glyph() -> Glyph:
    return Glyph(
        paths=[
            [(0.0, 0.0), (1.0, 1.0)],
            [(0.0, 1.0), (1.0, 0.0)],
        ],
        advance=1.10,
    )


def build_phrase_line_aggregate(
    *,
    anchor_lat: float,
    anchor_lon: float,
    text: str,
    policy: Optional[VertexTextPolicy] = None,
) -> list[StyledTextVertex]:
    p = policy or VertexTextPolicy()
    raw_text = " ".join((text or "").upper().split())

    if not raw_text:
        return []

    glyphs = _make_glyphs()

    phrase_vertices_local: list[tuple[float, float, int, int, int]] = []
    cursor_x_units = 0.0
    prev_char_end: Optional[tuple[float, float]] = None

    for ch in raw_text:
        glyph = glyphs.get(ch, _fallback_glyph())

        glyph_paths_transformed: list[list[tuple[float, float]]] = []
        for path in glyph.paths:
            transformed = _transform_path(
                path=path,
                cursor_x_units=cursor_x_units,
                policy=p,
            )
            if len(transformed) >= 2:
                glyph_paths_transformed.append(transformed)

        if glyph_paths_transformed:
            glyph_start = glyph_paths_transformed[0][0]

            if prev_char_end is not None and not _same_point(prev_char_end, glyph_start):
                phrase_vertices_local.append(
                    (
                        prev_char_end[0],
                        prev_char_end[1],
                        p.connector_line_type,
                        p.connector_width,
                        p.connector_color_no,
                    )
                )
                phrase_vertices_local.append(
                    (
                        glyph_start[0],
                        glyph_start[1],
                        p.text_line_type,
                        p.text_width,
                        p.text_color_no,
                    )
                )

            first_path = True
            for path in glyph_paths_transformed:
                if first_path and prev_char_end is None:
                    phrase_vertices_local.append(
                        (
                            path[0][0],
                            path[0][1],
                            p.text_line_type,
                            p.text_width,
                            p.text_color_no,
                        )
                    )
                elif first_path is False:
                    bridge_start = prev_char_end
                    bridge_end = path[0]

                    if bridge_start is not None and not _same_point(bridge_start, bridge_end):
                        phrase_vertices_local.append(
                            (
                                bridge_start[0],
                                bridge_start[1],
                                p.text_line_type,
                                p.text_width,
                                p.text_color_no,
                            )
                        )
                        phrase_vertices_local.append(
                            (
                                bridge_end[0],
                                bridge_end[1],
                                p.text_line_type,
                                p.text_width,
                                p.text_color_no,
                            )
                        )

                start_index = 1 if first_path or prev_char_end is not None else 0

                for x_nm, y_nm in path[start_index:]:
                    last = phrase_vertices_local[-1] if phrase_vertices_local else None
                    if last is not None and _same_point((last[0], last[1]), (x_nm, y_nm)):
                        continue

                    phrase_vertices_local.append(
                        (
                            x_nm,
                            y_nm,
                            p.text_line_type,
                            p.text_width,
                            p.text_color_no,
                        )
                    )

                prev_char_end = path[-1]
                first_path = False

        else:
            prev_char_end = None

        cursor_x_units += glyph.advance

    styled: list[StyledTextVertex] = []
    for x_nm, y_nm, line_type, width, color_no in phrase_vertices_local:
        lat, lon = _xy_to_latlon(
            anchor_lat=anchor_lat,
            anchor_lon=anchor_lon,
            x_nm=x_nm,
            y_nm=y_nm,
        )
        styled.append(
            StyledTextVertex(
                lat=lat,
                lon=lon,
                line_type=line_type,
                width=width,
                color_no=color_no,
            )
        )

    return styled