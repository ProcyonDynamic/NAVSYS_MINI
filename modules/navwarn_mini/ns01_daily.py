from __future__ import annotations

from typing import List, Optional

from .register_ns01 import read_ns01_csv, NS01Row
from .report_ns01 import render_ns01_txt, write_text_file


def _row_from_dict(d: dict) -> NS01Row:
    def ffloat(x: str, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def foptfloat(x: str) -> Optional[float]:
        x = (x or "").strip()
        if x == "":
            return None
        try:
            return float(x)
        except Exception:
            return None

    return NS01Row(
        seq=int((d.get("Seq") or "0").strip() or "0"),
        form=(d.get("Form") or "").strip(),
        time_utc=(d.get("Time_UTC") or "").strip(),
        run_id=(d.get("Run_ID") or "").strip(),
        navarea=(d.get("NAVAREA") or "").strip(),
        warning_id=(d.get("Warning_ID") or "").strip(),
        type=(d.get("Type") or "").strip(),
        psn_lat=ffloat(d.get("PSN_Lat") or "0"),
        psn_lon=ffloat(d.get("PSN_Lon") or "0"),
        dist_nm=foptfloat(d.get("Dist_NM") or ""),
        band=(d.get("Band") or "").strip(),
        plotted=(d.get("Plotted") or "").strip().upper(),
        source_kind=(d.get("Source_Kind") or "").strip(),
        source_url=(d.get("Source_URL") or "").strip(),
        status=(d.get("Status") or "").strip(),
        notes=(d.get("Notes") or "").strip(),
    )


def regenerate_daily_ns01_txt(
    *,
    daily_ns01_csv_path: str,
    out_txt_path: str,
    run_id: str,
    generated_utc: str,
    operator_name: str = "",
    vessel_name: str = "",
) -> None:
    rows_dicts = read_ns01_csv(daily_ns01_csv_path)
    rows: List[NS01Row] = [_row_from_dict(d) for d in rows_dicts]

    text = render_ns01_txt(
        rows=rows,
        run_id=run_id,
        generated_utc=generated_utc,
        operator_name=operator_name,
        vessel_name=vessel_name,
    )
    write_text_file(text, out_txt_path)