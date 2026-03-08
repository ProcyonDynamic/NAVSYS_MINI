from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .models import LineAggregateObject, StyledVertex


def _deg_to_dm(x_deg: float, is_lat: bool) -> Tuple[int, float, str]:
    """
    Convert decimal degrees to degrees + minutes + hemisphere.

    Lat:  DD,MM.mmm,N/S
    Lon: DDD,MM.mmm,E/W
    """
    x_abs = abs(x_deg)

    deg = int(x_abs)
    minutes = (x_abs - deg) * 60.0

    if is_lat:
        hemi = "N" if x_deg >= 0 else "S"
    else:
        hemi = "E" if x_deg >= 0 else "W"

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

    # Ensure the comment field exists (keep trailing comma when blank)
    return f"{lat_d},{lat_m},{lat_h},{lon_d},{lon_m},{lon_h},{line_type},{width},{color_no},{comment}"


def export_jrc_userchart_csv(
    *,
    objects: List[LineAggregateObject],
    output_csv_path: str
) -> None:
    """
    JRC dialect (as per your sample):

      LINE_AGGREGATE
      <ONE BLANK LINE>
      DD,MM.mmm,N,DDD,MM.mmm,E/W,Type,Width,ColorNo,Comment
      ...
      END

    No extra headers, no extra blank lines elsewhere.
    """
    out_path = Path(output_csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []

    for obj in objects:
        lines.append("LINE_AGGREGATE")
        lines.append("")  # exactly ONE blank line after LINE_AGGREGATE

        for v in obj.vertices:
            lines.append(_vertex_row(v))

        lines.append("END")

        # IMPORTANT: do NOT add extra blank line after END unless you confirm JRC accepts it.
        # If you later want separation between objects, we can add exactly one blank line here.
        # For now: strict.

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")