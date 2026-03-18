from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .active_warning_table import ActiveWarningRecord, upsert_warning_record
from .chart_session_builder import update_active_session_for_warning

from .ns01_daily import regenerate_daily_ns01_txt
from .register_ns01 import next_seq_for_register, make_ns01_row, append_ns01_row
from .warning_plot_export_service import export_plot_objects_to_csv

@dataclass
class OutputResult:
    plot_csv_path: str
    daily_ns01_csv_path: str
    daily_ns01_txt_path: str
    active_session_csv_path: str
    active_session_ok: bool


def persist_operational_warning_output(
    *,
    classified,
    plot_objects,
    plot_csv: Path,
    daily_ns01_csv: Path,
    daily_ns01_txt: Path,
    active_table_csv: Path,
    active_session_csv: Path,
    warning_id: str,
    navarea: str,
    created_utc: str,
    run_id: str,
    operator_name: str,
    vessel_name: str,
    plotted: str,
) -> OutputResult:
    # 1) Export JRC CSV
    plot_export_result = export_plot_objects_to_csv(
        plot_objects=plot_objects,
        plot_csv_path=plot_csv,
    )

    plot_was_written = (
        plot_export_result.ok and plot_export_result.exported_object_count > 0
    )

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
            plot_ref=str(plot_csv) if plot_was_written else "",
        ),
    )    

    
    # 5) Update active chart session
    merged_result = update_active_session_for_warning(
        active_table_csv_path=str(active_table_csv),
        output_csv_path=str(active_session_csv),
        warning_plot_csv_path=str(plot_csv),
        warning_state="ACTIVE",
        is_replacement=False,
    )

    return OutputResult(
        plot_csv_path=str(plot_csv),
        daily_ns01_csv_path=str(daily_ns01_csv),
        daily_ns01_txt_path=str(daily_ns01_txt),
        active_session_csv_path=str(active_session_csv),
        active_session_ok=merged_result["ok"],
    )
