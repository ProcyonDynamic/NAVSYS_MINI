from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .models import LineAggregateObject, StyledVertex


def _deg_to_dm(x_deg: float, is_lat: bool) -> Tuple[int, float, str]:
    x_abs = abs(x_deg)
    deg = int(x_abs)
    minutes = (x_abs - deg) * 60.0
    hemi = ("N" if x_deg >= 0 else "S") if is_lat else ("E" if x_deg >= 0 else "W")
    return deg, minutes, hemi


def _fmt_lat(lat: float) -> Tuple[str, str, str]:
    d, m, h = _deg_to_dm(lat, is_lat=True)
    return f"{d:02d}", f"{m:06.3f}", h


def _fmt_lon(lon: float) -> Tuple[str, str, str]:
    d, m, h = _deg_to_dm(lon, is_lat=False)
    return f"{d:03d}", f"{m:06.3f}", h


def _vertex_row(v: StyledVertex) -> str:
    lat_d, lat_m, lat_h = _fmt_lat(v.lat)
    lon_d, lon_m, lon_h = _fmt_lon(v.lon)
    line_type = int(v.line_type)
    width = int(v.width)
    color_no = int(v.color_no)
    comment = v.comment or ""
    return f"{lat_d},{lat_m},{lat_h},{lon_d},{lon_m},{lon_h},{line_type},{width},{color_no},{comment}"


def _text_row(lat: float, lon: float, text: str) -> str:
    lat_d, lat_m, lat_h = _fmt_lat(lat)
    lon_d, lon_m, lon_h = _fmt_lon(lon)
    safe_text = (text or "").replace("\n", " ").strip()
    return f"{lat_d},{lat_m},{lat_h},{lon_d},{lon_m},{lon_h},0,1,9,{safe_text}"


def export_jrc_userchart_csv(
    *,
    objects: List[LineAggregateObject],
    output_csv_path: str
) -> None:
    out_path = Path(output_csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []

    for obj in objects:
        # geometry aggregate
        lines.append("LINE_AGGREGATE")
        lines.append("")

        for v in obj.vertices:
            lines.append(_vertex_row(v))

        lines.append("END")

        # text aggregates
        for t in getattr(obj, "text_objects", []):
            lines.append("LINE_AGGREGATE")
            lines.append("")
            lines.append(_text_row(t.lat, t.lon, t.text))
            lines.append("END")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")