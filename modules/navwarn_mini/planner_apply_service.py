from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .planner_archive_fallback_service import resolve_warning_section_with_fallback
from .planner_cumulative_service import build_planner_cumulative_snapshot
from .voyage_userchart_service import build_voyage_userchart_path


@dataclass
class PlannerApplyResult:
    ok: bool
    mode: str
    chart_csv_path: str
    route_id: str
    navarea: str
    applied_warning_ids: list[str] = field(default_factory=list)
    missing_warning_ids: list[str] = field(default_factory=list)
    fallback_sources: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _render_audit_header(
    *,
    route_id: str,
    navarea: str,
    warning_ids: list[str],
    mode: str,
    fallback_sources: dict[str, str],
) -> list[str]:
    lines = [
        f"// [USERCHART_ROUTE_ID: {route_id}]",
        f"// [USERCHART_NAVAREA: {navarea}]",
        f"// [PLANNER_APPLY_MODE: {mode}]",
        f"// [PLOTTED_WARNING_COUNT: {len(warning_ids)}]",
        "// [PLOTTED_WARNING_IDS_BEGIN]",
    ]

    for wid in warning_ids:
        src = fallback_sources.get(wid, "UNKNOWN")
        lines.append(f"// [PLOTTED_WARNING_ID: {wid}] [SOURCE: {src}]")

    lines.append("// [PLOTTED_WARNING_IDS_END]")
    lines.append("")

    return lines


def _write_chart_from_sections(
    *,
    chart_csv_path: Path,
    route_id: str,
    navarea: str,
    mode: str,
    ordered_warning_ids: list[str],
    sections: dict[str, str],
    fallback_sources: dict[str, str],
) -> None:
    out_lines: list[str] = []
    out_lines.extend(
        _render_audit_header(
            route_id=route_id,
            navarea=navarea,
            warning_ids=ordered_warning_ids,
            mode=mode,
            fallback_sources=fallback_sources,
        )
    )

    for wid in ordered_warning_ids:
        text = sections[wid].rstrip()
        if text:
            out_lines.extend(text.splitlines())
            out_lines.append("")

    chart_csv_path.parent.mkdir(parents=True, exist_ok=True)
    chart_csv_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")


def _resolve_wanted_ids(
    *,
    output_root: str,
    navarea: str,
    mode: str,
    selected_warning_ids: list[str] | None,
) -> list[str]:
    selected_warning_ids = [
        " ".join((wid or "").split())
        for wid in (selected_warning_ids or [])
        if " ".join((wid or "").split())
    ]

    if selected_warning_ids:
        return selected_warning_ids

    snapshot = build_planner_cumulative_snapshot(
        output_root=output_root,
        navarea=navarea,
    )

    normalized_mode = (mode or "").strip().upper()

    if normalized_mode == "APPLY_EFFECTIVE_ACTIVE":
        return list(snapshot.get("effective_active_ids", []))

    if normalized_mode == "APPLY_NEW_ONLY":
        return list(snapshot.get("newer_preserved_ids", []))

    if normalized_mode == "REBUILD_FROM_STATE":
        return list(snapshot.get("effective_active_ids", []))

    if normalized_mode in ("APPLY_SELECTED", "REBUILD_SELECTED"):
        return []

    return []


def apply_planner_mode(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    mode: str,
    selected_warning_ids: list[str] | None = None,
) -> PlannerApplyResult:
    normalized_mode = (mode or "").strip().upper()

    if normalized_mode not in (
        "APPLY_EFFECTIVE_ACTIVE",
        "APPLY_NEW_ONLY",
        "REBUILD_FROM_STATE",
        "APPLY_SELECTED",
        "REBUILD_SELECTED",
    ):
        return PlannerApplyResult(
            ok=False,
            mode=normalized_mode,
            chart_csv_path="",
            route_id=route_id,
            navarea=navarea,
            errors=[f"Unsupported planner apply mode: {mode}"],
        )

    wanted_ids = _resolve_wanted_ids(
        output_root=output_root,
        navarea=navarea,
        mode=normalized_mode,
        selected_warning_ids=selected_warning_ids,
    )

    sections: dict[str, str] = {}
    missing_ids: list[str] = []
    fallback_sources: dict[str, str] = {}
    errors: list[str] = []

    for wid in wanted_ids:
        lookup = resolve_warning_section_with_fallback(
            output_root=output_root,
            route_id=route_id,
            navarea=navarea,
            warning_id=wid,
        )

        errors.extend(lookup.errors)

        if lookup.found and lookup.section_text:
            sections[wid] = lookup.section_text
            fallback_sources[wid] = lookup.source
        else:
            missing_ids.append(wid)

    ordered_applied_ids = [wid for wid in wanted_ids if wid in sections]

    chart_csv_path = build_voyage_userchart_path(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
    )

    _write_chart_from_sections(
        chart_csv_path=chart_csv_path,
        route_id=route_id,
        navarea=navarea,
        mode=normalized_mode,
        ordered_warning_ids=ordered_applied_ids,
        sections=sections,
        fallback_sources=fallback_sources,
    )

    return PlannerApplyResult(
        ok=True,
        mode=normalized_mode,
        chart_csv_path=str(chart_csv_path),
        route_id=route_id,
        navarea=navarea,
        applied_warning_ids=ordered_applied_ids,
        missing_warning_ids=missing_ids,
        fallback_sources=fallback_sources,
        errors=errors,
    )