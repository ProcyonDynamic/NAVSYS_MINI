from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .active_warning_table import ActiveWarningRecord, upsert_warning_record
from .ns01_daily import regenerate_daily_ns01_txt
from .register_ns01 import next_seq_for_register, make_ns01_row, append_ns01_row
from .voyage_userchart_service import create_or_update_voyage_userchart


@dataclass
class OutputResult:
    plot_csv_path: str
    daily_ns01_csv_path: str
    daily_ns01_txt_path: str
    route_id: str
    chart_mode: str
    plotted_warning_ids: list[str]
    archived_section_csv_path: str


def persist_operational_warning_output(
    *,
    classified,
    plot_objects,
    output_root: str,
    daily_ns01_csv: Path,
    daily_ns01_txt: Path,
    active_table_csv: Path,
    warning_id: str,
    navarea: str,
    created_utc: str,
    run_id: str,
    operator_name: str,
    vessel_name: str,
    plotted: str,
    route_id: str,
    chart_mode: str,
) -> OutputResult:
    print("[OUTPUT DEBUG]", {
        "plot_object_count": len(plot_objects),
        "route_id": route_id,
        "chart_mode": chart_mode,
        "navarea": navarea,
    })

    chart_result = create_or_update_voyage_userchart(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
        warning_id=warning_id,
        plot_objects=plot_objects,
        mode=chart_mode,
    )

    plot_was_written = chart_result.ok
    plotted_flag = "YES" if plot_was_written else "NO"

    seq = next_seq_for_register(str(daily_ns01_csv))
    row = make_ns01_row(seq, classified, plotted=plotted_flag)
    append_ns01_row(str(daily_ns01_csv), row)

    regenerate_daily_ns01_txt(
        daily_ns01_csv_path=str(daily_ns01_csv),
        out_txt_path=str(daily_ns01_txt),
        run_id=run_id,
        generated_utc=created_utc,
        operator_name=operator_name,
        vessel_name=vessel_name,
    )

    upsert_warning_record(
        active_table_csv,
        ActiveWarningRecord(
            warning_id=warning_id,
            navarea=navarea,
            state="ACTIVE",
            source_warning_id=warning_id,
            cancel_targets="",
            last_updated_utc=created_utc,
            plotted=plotted_flag,
            plot_ref=chart_result.chart_csv_path if plot_was_written else "",
            issued_utc=created_utc,
            state_reason="NEW_OPERATIONAL_WARNING",
            last_seen_in_cumulative_id="",
            last_seen_in_cumulative_utc="",
            omitted_by_cumulative_id="",
            omitted_by_cumulative_utc="",
        ),
    )

    print("[OUTPUT DEBUG CHART RESULT]", {
        "ok": chart_result.ok,
        "chart_csv_path": chart_result.chart_csv_path,
        "route_id": chart_result.route_id,
        "navarea": chart_result.navarea,
        "warning_ids": chart_result.warning_ids,
        "archived_section_csv_path": chart_result.archived_section_csv_path,
        "errors": chart_result.errors,
    })

    print("[OUTPUT DEBUG FILE EXISTS]", {
        "chart_csv_exists": Path(chart_result.chart_csv_path).exists(),
        "chart_csv_path": chart_result.chart_csv_path,
        "archive_csv_exists": Path(chart_result.archived_section_csv_path).exists() if chart_result.archived_section_csv_path else False,
        "archive_csv_path": chart_result.archived_section_csv_path,
        "daily_ns01_csv_exists": daily_ns01_csv.exists(),
        "daily_ns01_csv_path": str(daily_ns01_csv),
        "daily_ns01_txt_exists": daily_ns01_txt.exists(),
        "daily_ns01_txt_path": str(daily_ns01_txt),
    })

    return OutputResult(
        plot_csv_path=chart_result.chart_csv_path,
        daily_ns01_csv_path=str(daily_ns01_csv),
        daily_ns01_txt_path=str(daily_ns01_txt),
        route_id=chart_result.route_id,
        chart_mode=chart_result.mode,
        plotted_warning_ids=chart_result.warning_ids,
        archived_section_csv_path=chart_result.archived_section_csv_path,
    )