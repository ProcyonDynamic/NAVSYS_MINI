from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .active_warning_table import load_active_warning_table


@dataclass
class ArchiveLookupResult:
    found: bool
    source: str  # ROUTE_ARCHIVE | GLOBAL_ARCHIVE | PLOT_REF | NONE
    warning_id: str
    navarea: str
    route_id: str
    section_text: str = ""
    source_path: str = ""
    errors: list[str] = field(default_factory=list)


def _safe_token(text: str) -> str:
    return (
        (text or "")
        .strip()
        .upper()
        .replace("NAVAREA ", "")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def _route_archive_path(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    warning_id: str,
) -> Path:
    return (
        Path(output_root)
        / "NAVWARN"
        / "warning_archive"
        / _safe_token(route_id)
        / _safe_token(navarea)
        / f"{_safe_token(warning_id)}.csv"
    )


def _global_archive_path(
    *,
    output_root: str,
    navarea: str,
    warning_id: str,
) -> Path:
    return (
        Path(output_root)
        / "NAVWARN"
        / "warning_archive_global"
        / _safe_token(navarea)
        / f"{_safe_token(warning_id)}.csv"
    )


def _extract_warning_section_from_chart(
    *,
    chart_path: Path,
    warning_id: str,
) -> str:
    if not chart_path.exists():
        return ""

    target = " ".join((warning_id or "").split()).upper()
    lines = chart_path.read_text(encoding="utf-8-sig").splitlines()

    current_id = ""
    current_lines: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("// [WARNING_ID:"):
            current_id = (
                stripped.replace("// [WARNING_ID:", "")
                .replace("]", "")
                .strip()
                .upper()
            )
            current_lines = [line]
            in_section = True
            continue

        if in_section:
            current_lines.append(line)

            if stripped == "// NNNN":
                if current_id == target:
                    return "\n".join(current_lines).rstrip() + "\n"
                current_id = ""
                current_lines = []
                in_section = False

    return ""


def _lookup_from_plot_ref(
    *,
    output_root: str,
    navarea: str,
    warning_id: str,
) -> ArchiveLookupResult:
    active_table_csv = Path(output_root) / "NAVWARN" / "active_warning_table.csv"

    if not active_table_csv.exists():
        return ArchiveLookupResult(
            found=False,
            source="NONE",
            warning_id=warning_id,
            navarea=navarea,
            route_id="",
            errors=[],
        )

    try:
        rows = load_active_warning_table(active_table_csv)
    except Exception as exc:
        return ArchiveLookupResult(
            found=False,
            source="NONE",
            warning_id=warning_id,
            navarea=navarea,
            route_id="",
            errors=[f"Failed to load active warning table: {exc}"],
        )

    target_wid = " ".join((warning_id or "").split()).upper()
    target_nav = " ".join((navarea or "").split()).upper()

    for row in rows:
        row_wid = " ".join((getattr(row, "warning_id", "") or "").split()).upper()
        row_nav = " ".join((getattr(row, "navarea", "") or "").split()).upper()
        plot_ref = (getattr(row, "plot_ref", "") or "").strip()

        if row_wid != target_wid or row_nav != target_nav:
            continue
        if not plot_ref:
            continue

        chart_path = Path(plot_ref)
        section_text = _extract_warning_section_from_chart(
            chart_path=chart_path,
            warning_id=warning_id,
        )

        if section_text:
            return ArchiveLookupResult(
                found=True,
                source="PLOT_REF",
                warning_id=warning_id,
                navarea=navarea,
                route_id="",
                section_text=section_text,
                source_path=str(chart_path),
                errors=[],
            )

    return ArchiveLookupResult(
        found=False,
        source="NONE",
        warning_id=warning_id,
        navarea=navarea,
        route_id="",
        errors=[],
    )


def resolve_warning_section_with_fallback(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    warning_id: str,
) -> ArchiveLookupResult:
    route_path = _route_archive_path(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
        warning_id=warning_id,
    )

    if route_path.exists():
        return ArchiveLookupResult(
            found=True,
            source="ROUTE_ARCHIVE",
            warning_id=warning_id,
            navarea=navarea,
            route_id=route_id,
            section_text=route_path.read_text(encoding="utf-8-sig").rstrip() + "\n",
            source_path=str(route_path),
            errors=[],
        )

    global_path = _global_archive_path(
        output_root=output_root,
        navarea=navarea,
        warning_id=warning_id,
    )

    if global_path.exists():
        return ArchiveLookupResult(
            found=True,
            source="GLOBAL_ARCHIVE",
            warning_id=warning_id,
            navarea=navarea,
            route_id=route_id,
            section_text=global_path.read_text(encoding="utf-8-sig").rstrip() + "\n",
            source_path=str(global_path),
            errors=[],
        )

    plot_ref_result = _lookup_from_plot_ref(
        output_root=output_root,
        navarea=navarea,
        warning_id=warning_id,
    )

    if plot_ref_result.found:
        return plot_ref_result

    return ArchiveLookupResult(
        found=False,
        source="NONE",
        warning_id=warning_id,
        navarea=navarea,
        route_id=route_id,
        errors=list(plot_ref_result.errors),
    )