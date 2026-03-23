from __future__ import annotations

from dataclasses import dataclass, field

from .planner_archive_fallback_service import resolve_warning_section_with_fallback
from .planner_cumulative_service import build_planner_cumulative_snapshot


@dataclass
class SlotWarningAvailability:
    warning_id: str
    source: str  # ROUTE_ARCHIVE | GLOBAL_ARCHIVE | PLOT_REF | NONE
    available: bool


@dataclass
class SlotSummaryResult:
    ok: bool
    route_id: str
    navarea: str
    effective_active_ids: list[str] = field(default_factory=list)
    available_route_archive_count: int = 0
    available_fallback_count: int = 0
    missing_count: int = 0
    availability_rows: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def build_slot_summary(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
) -> SlotSummaryResult:
    snapshot = build_planner_cumulative_snapshot(
        output_root=output_root,
        navarea=navarea,
    )

    effective_active_ids = list(snapshot.get("effective_active_ids", []))

    route_count = 0
    fallback_count = 0
    missing_count = 0
    rows: list[dict] = []
    errors: list[str] = []

    for wid in effective_active_ids:
        lookup = resolve_warning_section_with_fallback(
            output_root=output_root,
            route_id=route_id,
            navarea=navarea,
            warning_id=wid,
        )

        errors.extend(lookup.errors)

        source = lookup.source if lookup.found else "NONE"
        available = bool(lookup.found)

        if source == "ROUTE_ARCHIVE":
            route_count += 1
        elif source in ("GLOBAL_ARCHIVE", "PLOT_REF"):
            fallback_count += 1
        else:
            missing_count += 1

        rows.append({
            "warning_id": wid,
            "source": source,
            "available": available,
        })

    return SlotSummaryResult(
        ok=True,
        route_id=route_id,
        navarea=navarea,
        effective_active_ids=effective_active_ids,
        available_route_archive_count=route_count,
        available_fallback_count=fallback_count,
        missing_count=missing_count,
        availability_rows=rows,
        errors=errors,
    )