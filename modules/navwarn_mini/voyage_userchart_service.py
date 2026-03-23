from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .warning_plot_export_service import export_plot_objects_to_csv
from .warning_section_archive_service import archive_warning_section


@dataclass
class VoyageUserchartResult:
    ok: bool
    mode: str
    chart_csv_path: str
    route_id: str
    navarea: str
    warning_ids: list[str] = field(default_factory=list)
    archived_section_csv_path: str = ""
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


def derive_route_id(route_csv_path: str | None, fallback_run_id: str) -> str:
    if route_csv_path:
        stem = Path(route_csv_path).stem.strip()
        if stem:
            return stem.upper()
    return fallback_run_id.upper()


def build_voyage_userchart_path(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
) -> Path:
    root = Path(output_root)
    charts_dir = root / "NAVWARN" / "voyage_usercharts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    safe_route = _safe_token(route_id)
    safe_navarea = _safe_token(navarea)

    return charts_dir / f"{safe_route}_{safe_navarea}_userchart.csv"


def _extract_warning_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}

    current_warning_id = ""
    current_lines: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("// [WARNING_ID:"):
            if in_section and current_warning_id and current_lines:
                sections[current_warning_id] = current_lines[:]

            current_warning_id = (
                stripped.replace("// [WARNING_ID:", "")
                .replace("]", "")
                .strip()
            )
            current_lines = [line]
            in_section = True
            continue

        if in_section:
            current_lines.append(line)

            if stripped == "// NNNN":
                if current_warning_id:
                    sections[current_warning_id] = current_lines[:]
                current_warning_id = ""
                current_lines = []
                in_section = False

    if in_section and current_warning_id and current_lines:
        sections[current_warning_id] = current_lines[:]

    return sections


def _read_existing_sections(chart_csv_path: Path) -> dict[str, list[str]]:
    if not chart_csv_path.exists():
        return {}

    text = chart_csv_path.read_text(encoding="utf-8-sig")
    return _extract_warning_sections(text.splitlines())


def _render_audit_header(
    *,
    route_id: str,
    navarea: str,
    warning_ids: list[str],
) -> list[str]:
    lines = [
        f"// [USERCHART_ROUTE_ID: {route_id}]",
        f"// [USERCHART_NAVAREA: {navarea}]",
        f"// [PLOTTED_WARNING_COUNT: {len(warning_ids)}]",
        "// [PLOTTED_WARNING_IDS_BEGIN]",
    ]

    for wid in warning_ids:
        lines.append(f"// [PLOTTED_WARNING_ID: {wid}]")

    lines.append("// [PLOTTED_WARNING_IDS_END]")
    lines.append("")

    return lines


def _assemble_chart_text(
    *,
    route_id: str,
    navarea: str,
    sections: dict[str, list[str]],
) -> str:
    ordered_warning_ids = sorted(sections.keys())

    out_lines: list[str] = []
    out_lines.extend(
        _render_audit_header(
            route_id=route_id,
            navarea=navarea,
            warning_ids=ordered_warning_ids,
        )
    )

    for wid in ordered_warning_ids:
        out_lines.extend(sections[wid])
        if not out_lines or out_lines[-1] != "":
            out_lines.append("")

    return "\n".join(out_lines).rstrip() + "\n"


def create_or_update_voyage_userchart(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    warning_id: str,
    plot_objects: list,
    mode: str,
) -> VoyageUserchartResult:
    chart_csv_path = build_voyage_userchart_path(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
    )

    temp_dir = chart_csv_path.parent / "_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_warning_csv = temp_dir / f"{_safe_token(warning_id)}.csv"

    export_result = export_plot_objects_to_csv(
        plot_objects=plot_objects,
        plot_csv_path=temp_warning_csv,
    )

    if not export_result.ok or not temp_warning_csv.exists():
        return VoyageUserchartResult(
            ok=False,
            mode=mode,
            chart_csv_path=str(chart_csv_path),
            route_id=route_id,
            navarea=navarea,
            warning_ids=[],
            archived_section_csv_path="",
            errors=list(export_result.errors),
        )

    temp_text = temp_warning_csv.read_text(encoding="utf-8-sig")
    archive_result = archive_warning_section(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
        warning_id=warning_id,
        section_text=temp_text,
    )

    new_sections = _read_existing_sections(temp_warning_csv)
    existing_sections = _read_existing_sections(chart_csv_path)

    normalized_mode = (mode or "UPDATE_EXISTING").strip().upper()

    if normalized_mode == "CREATE_NEW":
        merged_sections = dict(new_sections)
    else:
        merged_sections = dict(existing_sections)
        for wid, lines in new_sections.items():
            merged_sections[wid] = lines

    chart_text = _assemble_chart_text(
        route_id=route_id,
        navarea=navarea,
        sections=merged_sections,
    )

    chart_csv_path.write_text(chart_text, encoding="utf-8")

    warning_ids = sorted(merged_sections.keys())

    combined_errors = list(export_result.errors)
    combined_errors.extend(archive_result.errors)

    return VoyageUserchartResult(
        ok=True,
        mode=normalized_mode,
        chart_csv_path=str(chart_csv_path),
        route_id=route_id,
        navarea=navarea,
        warning_ids=warning_ids,
        archived_section_csv_path=archive_result.archive_csv_path,
        errors=combined_errors,
    )