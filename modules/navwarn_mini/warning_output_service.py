from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .active_warning_table import ActiveWarningRecord, upsert_warning_record
from .chart_session_builder import update_active_session_for_warning
from .export_jrc_csv import export_jrc_userchart_csv
from .ns01_daily import regenerate_daily_ns01_txt
from .register_ns01 import next_seq_for_register, make_ns01_row, append_ns01_row


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
    export_jrc_userchart_csv(
        objects=plot_objects,
        output_csv_path=str(plot_csv),
    )

    # 2) Append NS-01
    seq = next_seq_for_register(str(daily_ns01_csv))
    row = make_ns01_row(seq, classified, plotted=plotted)
    append_ns01_row(str(daily_ns01_csv), row)

    # 3) Regenerate daily printable NS-01
    regenerate_daily_ns01_txt(
        daily_ns01_csv_path=str(daily_ns01_csv),
        out_txt_path=str(daily_ns01_txt),
        run_id=run_id,
        generated_utc=created_utc,
        operator_name=operator_name,
        vessel_name=vessel_name,
    )

    # 4) Mark warning active
    upsert_warning_record(
        active_table_csv,
        ActiveWarningRecord(
            warning_id=warning_id,
            navarea=navarea,
            state="ACTIVE",
            source_warning_id=warning_id,
            cancel_targets="",
            last_updated_utc=created_utc,
            plotted="YES",
            plot_ref=str(plot_csv),
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
