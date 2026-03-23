from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .active_warning_table import (
    ActiveWarningRecord,
    upsert_warning_record,
    mark_cancelled_targets,
)
from .warning_cumulative_service import extract_cumulative_ids, reconcile_cumulative_snapshot


class WarningState:
    ACTIVE = "ACTIVE"
    CANCELLED_EXPLICIT = "CANCELLED_EXPLICIT"
    OMMITTED_BY_CUMULATIVE = "OMITTED_BY_CUMULATIVE"
    DUPLICATE = "DUPLICATE"
    REFERENCE_CUMULATIVE = "REFERENCE_CUMULATIVE"


@dataclass
class StateContext:
    warning_id: str
    navarea: str
    created_utc: str
    active_table_csv: Path


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


def handle_reference(
    *,
    ctx,
    raw_text: str,
):
    listed_ids = extract_cumulative_ids(raw_text)

    reconcile_result = reconcile_cumulative_snapshot(
        active_table_csv_path=str(ctx.active_table_csv),
        cumulative_warning_id=ctx.warning_id,
        cumulative_navarea=ctx.navarea,
        cumulative_issued_utc=ctx.created_utc,
        listed_ids=listed_ids,
    )

    return StateDecision(
        handled=True,
        response={
            "ok": reconcile_result.ok,
            "warning_id": ctx.warning_id,
            "state": "REFERENCE_CUMULATIVE",
            "listed_ids": reconcile_result.listed_ids,
            "kept_ids": reconcile_result.kept_ids,
            "omitted_ids": reconcile_result.omitted_ids,
            "newer_preserved_ids": reconcile_result.newer_preserved_ids,
            "errors": list(reconcile_result.errors),
        },
    )


def handle_cancellation(*, ctx: StateContext, cancellation_targets: list[str]) -> StateDecision:
    upsert_warning_record(
        ctx.active_table_csv,
        ActiveWarningRecord(
            warning_id=ctx.warning_id,
            navarea=ctx.navarea,
            state="CANCELLED_EXPLICIT",
            source_warning_id=ctx.warning_id,
            cancel_targets=";".join(cancellation_targets),
            last_updated_utc=ctx.created_utc,
            plotted="NO",
            plot_ref="",
            issued_utc=ctx.created_utc,
            state_reason="EXPLICIT_CANCELLATION_WARNING",
            last_seen_in_cumulative_id="",
            last_seen_in_cumulative_utc="",
            omitted_by_cumulative_id="",
            omitted_by_cumulative_utc="",
        ),
    )

    mark_cancelled_targets(
        ctx.active_table_csv,
        cancellation_targets,
        ctx.created_utc,
    )

    return StateDecision(
        handled=True,
        response={
            "ok": True,
            "state": WarningState.CANCELLED_EXPLICIT,
            "status": "CANCELLATION_WARNING",
            "warning_id": ctx.warning_id,
            "cancel_targets": cancellation_targets,
        },
    )