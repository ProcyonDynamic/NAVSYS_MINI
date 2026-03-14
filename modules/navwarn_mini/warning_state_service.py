from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


from .active_warning_table import (
    ActiveWarningRecord,
    upsert_warning_record,
    mark_cancelled_targets,
)
from .chart_session_builder import rebuild_active_session_csv


class WarningState:
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    DUPLICATE = "DUPLICATE"
    REFERENCE = "REFERENCE"


@dataclass
class StateContext:
    warning_id: str
    navarea: str
    created_utc: str
    active_table_csv: Path
    active_session_csv: Path


@dataclass
class StateDecision:
    handled: bool
    response: Optional[dict] = None


def handle_duplicate(*, is_duplicate: bool, warning_id: str) -> StateDecision:
    if not is_duplicate:
        return StateDecision(handled=False)

    return StateDecision(
        handled=True,
        response={
            "ok": True,
            "state": WarningState.DUPLICATE,
            "status": "DUPLICATE_WARNING",
            "warning_id": warning_id,
        },
    )


def handle_reference(*, ctx: StateContext, cancellation_targets: list[str]) -> StateDecision:
    upsert_warning_record(
        ctx.active_table_csv,
        ActiveWarningRecord(
            warning_id=ctx.warning_id,
            navarea=ctx.navarea,
            state="REFERENCE",
            source_warning_id=ctx.warning_id,
            cancel_targets=";".join(cancellation_targets),
            last_updated_utc=ctx.created_utc,
            plotted="NO",
            plot_ref="",
        ),
    )

    rebuild_active_session_csv(
        active_table_csv_path=str(ctx.active_table_csv),
        output_csv_path=str(ctx.active_session_csv),
    )

    return StateDecision(
        handled=True,
        response={
            "ok": True,
            "state": WarningState.REFERENCE,
            "status": "REFERENCE_BULLETIN",
            "warning_id": ctx.warning_id,
            "cancel_targets": cancellation_targets,
        },
    )


def handle_cancellation(*, ctx: StateContext, cancellation_targets: list[str]) -> StateDecision:
    upsert_warning_record(
        ctx.active_table_csv,
        ActiveWarningRecord(
            warning_id=ctx.warning_id,
            navarea=ctx.navarea,
            state="CANCELLED",
            source_warning_id=ctx.warning_id,
            cancel_targets=";".join(cancellation_targets),
            last_updated_utc=ctx.created_utc,
            plotted="NO",
            plot_ref="",
        ),
    )

    mark_cancelled_targets(
        ctx.active_table_csv,
        cancellation_targets,
        ctx.created_utc,
    )

    rebuild_active_session_csv(
        active_table_csv_path=str(ctx.active_table_csv),
        output_csv_path=str(ctx.active_session_csv),
    )

    return StateDecision(
        handled=True,
        response={
            "ok": True,
            "state": WarningState.CANCELLED,
            "status": "CANCELLATION_WARNING",
            "warning_id": ctx.warning_id,
            "cancel_targets": cancellation_targets,
        },
    )
