from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .line_aggregate_symbol_constructor import build_symbol_vertices
from .warning_plot_builder_service import PlotObject


@dataclass
class PlotExportResult:
    ok: bool
    plot_csv_path: Optional[str]
    exported_row_count: int
    exported_object_count: int
    errors: list[str] = field(default_factory=list)


def _to_ddm(value: float, is_lat: bool) -> tuple[str, str, str]:
    abs_val = abs(value)
    deg = int(abs_val)
    minutes = (abs_val - deg) * 60.0

    if is_lat:
        hemi = "N" if value >= 0 else "S"
        return f"{deg:02d}", f"{minutes:06.3f}", hemi

    hemi = "E" if value >= 0 else "W"
    return f"{deg:03d}", f"{minutes:06.3f}", hemi


def _close_vertices(vertices: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not vertices:
        return vertices
    if vertices[0] == vertices[-1]:
        return vertices
    return vertices + [vertices[0]]


def _materialize_vertices(obj: PlotObject) -> list[tuple[float, float]]:
    vertices = list(obj.vertices)

    if obj.object_kind == "AREA":
        return _close_vertices(vertices)

    if obj.object_kind == "POINT":
        if len(vertices) == 1:
            lat, lon = vertices[0]
            symbol_kind = (obj.point_symbol_kind or "X").strip()
            return build_symbol_vertices(
                symbol_kind=symbol_kind,
                lat=lat,
                lon=lon,
                size_nm=0.6,
            )
        return vertices

    return vertices


def _vertex_row_text(
    lat: float,
    lon: float,
    line_type: int,
    width: int,
    color_no: int,
) -> str:
    lat_deg, lat_min, lat_hemi = _to_ddm(lat, is_lat=True)
    lon_deg, lon_min, lon_hemi = _to_ddm(lon, is_lat=False)

    return (
        f"{lat_deg},{lat_min},{lat_hemi},"
        f"{lon_deg},{lon_min},{lon_hemi},"
        f"{line_type},{width},{color_no},"
    )


def _warning_comment_lines(obj: PlotObject) -> list[str]:
    warning_id = (obj.source_warning_id or "").strip() or "UNKNOWN"
    navarea = (obj.source_navarea or "").strip()
    render_family = str(obj.metadata.get("render_family", "")).strip()
    label_mode = str(obj.metadata.get("label_mode", "")).strip()
    point_symbol_kind = (obj.point_symbol_kind or "").strip()

    lines = [
        f"// [WARNING_ID: {warning_id}]",
    ]

    if navarea:
        lines.append(f"// [NAVAREA: {navarea}]")

    lines.append("// [BLOCK_ROLE: GEOMETRY]")
    lines.append(f"// [OBJECT_KIND: {obj.object_kind}]")
    lines.append(f"// [GEOM_TYPE: {obj.geom_type}]")

    if render_family:
        lines.append(f"// [RENDER_FAMILY: {render_family}]")

    if label_mode:
        lines.append(f"// [LABEL_MODE: {label_mode}]")

    if point_symbol_kind:
        lines.append(f"// [POINT_SYMBOL: {point_symbol_kind}]")

    return lines


def _text_comment_lines(obj: PlotObject) -> list[str]:
    warning_id = (obj.source_warning_id or "").strip() or "UNKNOWN"
    text = " ".join((obj.text or "").split())

    lines = [
        f"// [WARNING_ID: {warning_id}]",
        "// [BLOCK_ROLE: TEXT]",
        "// [TEXT_RENDER: VERTEX_STROKE]",
    ]

    if text:
        lines.append(f"// [TEXT: {text}]")

    if obj.metadata.get("text_object_kind"):
        lines.append(f"// [TEXT_OBJECT_KIND: {obj.metadata['text_object_kind']}]")
    if obj.metadata.get("text_char_width_nm") is not None:
        lines.append(f"// [TEXT_CHAR_WIDTH_NM: {obj.metadata['text_char_width_nm']}]")
    if obj.metadata.get("text_char_height_nm") is not None:
        lines.append(f"// [TEXT_CHAR_HEIGHT_NM: {obj.metadata['text_char_height_nm']}]")
    if obj.metadata.get("text_char_spacing_nm") is not None:
        lines.append(f"// [TEXT_CHAR_SPACING_NM: {obj.metadata['text_char_spacing_nm']}]")
    if obj.metadata.get("text_line_type") is not None:
        lines.append(f"// [TEXT_LINE_TYPE: {obj.metadata['text_line_type']}]")
    if obj.metadata.get("text_width") is not None:
        lines.append(f"// [TEXT_WIDTH: {obj.metadata['text_width']}]")
    if obj.metadata.get("text_color_no") is not None:
        lines.append(f"// [TEXT_COLOR_NO: {obj.metadata['text_color_no']}]")
    if obj.metadata.get("connector_line_type") is not None:
        lines.append(f"// [CONNECTOR_LINE_TYPE: {obj.metadata['connector_line_type']}]")
    if obj.metadata.get("connector_width") is not None:
        lines.append(f"// [CONNECTOR_WIDTH: {obj.metadata['connector_width']}]")
    if obj.metadata.get("connector_color_no") is not None:
        lines.append(f"// [CONNECTOR_COLOR_NO: {obj.metadata['connector_color_no']}]")

    return lines


def _line_aggregate_block_lines(
    *,
    comment_lines: list[str],
    vertices: list[tuple[float, float]],
    styled_vertices: list[tuple[float, float, int, int, int]],
    line_type: int,
    width: int,
    color_no: int,
) -> list[str]:
    lines: list[str] = []

    lines.extend(comment_lines)
    lines.append("LINE_AGGREGATE")
    lines.append("")

    if styled_vertices:
        for lat, lon, v_line_type, v_width, v_color_no in styled_vertices:
            lines.append(
                _vertex_row_text(
                    lat=lat,
                    lon=lon,
                    line_type=v_line_type,
                    width=v_width,
                    color_no=v_color_no,
                )
            )
    else:
        for lat, lon in vertices:
            lines.append(
                _vertex_row_text(
                    lat=lat,
                    lon=lon,
                    line_type=line_type,
                    width=width,
                    color_no=color_no,
                )
            )

    lines.append("END")
    return lines


def export_plot_objects_to_csv(
    *,
    plot_objects: list[PlotObject],
    plot_csv_path: str | Path,
) -> PlotExportResult:
    plot_csv_path = Path(plot_csv_path)
    plot_csv_path.parent.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    rows_written = 0
    exported_object_count = 0

    if not plot_objects:
        return PlotExportResult(
            ok=False,
            plot_csv_path=None,
            exported_row_count=0,
            exported_object_count=0,
            errors=["No plot objects to export"],
        )

    try:
        lines: list[str] = []

        vertices: list[tuple[float, float]] = []

        for obj in plot_objects:
            if not obj.vertices and not obj.styled_vertices:
                errors.append(
                    f"Skipped object with no vertices for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            if obj.object_kind not in ("POINT", "LINE", "AREA", "TEXT"):
                errors.append(
                    f"Skipped unsupported object_kind={obj.object_kind} for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            vertices = _materialize_vertices(obj)

            errors.append(
                f"[EXPORT DEBUG] warning_id={obj.source_warning_id or 'UNKNOWN'} "
                f"object_kind={obj.object_kind} geom_type={obj.geom_type} "
                f"vertex_count={len(vertices)} line_type={obj.line_type} "
                f"line_width={obj.line_width} color_no={obj.color_no}"
            )
            
            
            if len(vertices) < 2:
                errors.append(
                    f"INVALID GEOMETRY: <2 vertices for "
                    f"warning_id={obj.source_warning_id or 'UNKNOWN'} "
                    f"(object_kind={obj.object_kind}, geom_type={obj.geom_type})"
                )

            if obj.object_kind == "POINT" and len(vertices) < 2:
                errors.append(
                    f"POINT object could not be expanded to valid LINE_AGGREGATE for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            if obj.object_kind == "LINE" and len(vertices) < 2:
                errors.append(
                    f"Skipped invalid LINE with <2 vertices for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            if obj.object_kind == "AREA" and len(vertices) < 3:
                errors.append(
                    f"Skipped invalid AREA with <3 vertices for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            if obj.object_kind == "TEXT" and len(obj.styled_vertices) < 2:
                errors.append(
                    f"Skipped invalid TEXT with <2 styled vertices for warning_id={obj.source_warning_id or 'UNKNOWN'}"
                )
                continue

            if obj.line_type is None or obj.line_width is None or obj.color_no is None:
                errors.append(
                    f"Missing style for object warning_id={obj.source_warning_id or 'UNKNOWN'} "
                    f"(object_kind={obj.object_kind}, geom_type={obj.geom_type})"
                )
                continue

            line_type = obj.line_type
            width = obj.line_width
            color_no = obj.color_no
            comment_lines = _text_comment_lines(obj) if obj.object_kind == "TEXT" else _warning_comment_lines(obj)

            block_lines = _line_aggregate_block_lines(
                comment_lines=comment_lines,
                vertices=vertices,
                styled_vertices=obj.styled_vertices,
                line_type=line_type,
                width=width,
                color_no=color_no,
            )

            lines.extend(block_lines)
            lines.append("// NNNN")
            lines.append("")

            rows_written += len(block_lines) + 2
            exported_object_count += 1

        plot_csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return PlotExportResult(
            ok=exported_object_count > 0,
            plot_csv_path=str(plot_csv_path),
            exported_row_count=rows_written,
            exported_object_count=exported_object_count,
            errors=errors,
        )

    except Exception as exc:
        errors.append(f"Plot CSV export failed: {exc}")
        return PlotExportResult(
            ok=False,
            plot_csv_path=None,
            exported_row_count=0,
            exported_object_count=0,
            errors=errors,
        )