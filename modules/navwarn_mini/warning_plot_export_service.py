from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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


def _vertex_row(
    lat: float,
    lon: float,
    line_type: int,
    width: int,
    color_no: int,
) -> list[str]:
    lat_deg, lat_min, lat_hemi = _to_ddm(lat, is_lat=True)
    lon_deg, lon_min, lon_hemi = _to_ddm(lon, is_lat=False)

    return [
        lat_deg,
        lat_min,
        lat_hemi,
        lon_deg,
        lon_min,
        lon_hemi,
        str(line_type),
        str(width),
        str(color_no),
        "",
    ]


def _write_line_aggregate_block(writer: csv.writer, obj: PlotObject) -> int:
    rows_written = 0

    vertices = obj.vertices
    if obj.object_kind == "AREA":
        vertices = _close_vertices(vertices)

    line_type = obj.line_type if obj.line_type is not None else 1
    width = obj.line_width if obj.line_width is not None else 3
    color_no = obj.color_no if obj.color_no is not None else 4

    writer.writerow(["LINE_AGGREGATE"])
    rows_written += 1

    for lat, lon in vertices:
        writer.writerow(_vertex_row(lat, lon, line_type, width, color_no))
        rows_written += 1

    writer.writerow(["END"])
    rows_written += 1

    return rows_written


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

    try:
        with plot_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            for obj in plot_objects:
                if not obj.vertices:
                    continue

                # JRC constraint: export geometry only as LINE_AGGREGATE.
                # Ignore TEXT objects for now.
                if obj.object_kind in ("POINT", "LINE", "AREA"):
                    rows_written += _write_line_aggregate_block(writer, obj)
                    exported_object_count += 1

        return PlotExportResult(
            ok=True,
            plot_csv_path=str(plot_csv_path),
            exported_row_count=rows_written,
            exported_object_count=exported_object_count,
            errors=[],
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