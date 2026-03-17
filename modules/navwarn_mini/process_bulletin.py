from __future__ import annotations

from typing import Optional

from .process_warning import process_warning_text
from .warning_splitter_service import split_bulletin_to_envelopes


def process_bulletin_text(
    *,
    raw_text: str,
    output_root: str,
    source_kind: str = "MANUAL",
    source_title: str = "",
    source_url: str = "",
    operator_name: str = "",
    vessel_name: str = "",
    ship_lat: Optional[float] = None,
    ship_lon: Optional[float] = None,
    plotted: str = "NO",
    validity_start_utc: Optional[str] = None,
    validity_end_utc: Optional[str] = None,
    validity_ufn: bool = True,
    route_csv_path: Optional[str] = None,
) -> dict:

    split_result = split_bulletin_to_envelopes(
        raw_text=raw_text,
        source=source_kind,
    )

    results: list[dict] = []
    errors: list[str] = list(split_result.errors)

    for env in split_result.envelopes:
        try:
            result = process_warning_text(
                raw_text=env.raw_text,
                navarea=env.navarea or "",
                ship_lat=ship_lat,
                ship_lon=ship_lon,
                output_root=output_root,
                warning_id=env.warning_id or "",
                title=env.warning_id or "",
                source_kind=source_kind,
                source_title=source_title,
                source_url=source_url,
                operator_name=operator_name,
                vessel_name=vessel_name,
                plotted=plotted,
                validity_start_utc=validity_start_utc,
                validity_end_utc=validity_end_utc,
                validity_ufn=validity_ufn,
                route_csv_path=route_csv_path,
            )

            results.append(result)

        except Exception as e:
            errors.append(f"warning_error[{env.warning_id or 'UNKNOWN'}]: {e}")

    return {
        "ok": len(results) > 0 and len(errors) == 0,
        "split_count": split_result.split_count,
        "processed_count": len(results),
        "results": results,
        "errors": errors,
    }