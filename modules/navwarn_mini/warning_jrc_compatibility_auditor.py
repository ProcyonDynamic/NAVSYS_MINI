from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .warning_plot_builder_service import PlotObject


@dataclass(frozen=True)
class JRCCompatibilityIssue:
    code: str
    severity: str  # ERROR | WARN
    scope: str     # OBJECT | FILE
    message: str


@dataclass(frozen=True)
class JRCCompatibilityReport:
    ok: bool
    issue_count: int
    error_count: int
    warning_count: int
    issues: list[JRCCompatibilityIssue] = field(default_factory=list)


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except Exception:
        return False


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def _looks_like_vertex_row(line: str) -> bool:
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 9:
        return False

    if not parts[0].isdigit():
        return False
    if not _is_number(parts[1]):
        return False
    if parts[2] not in ("N", "S"):
        return False
    if not parts[3].isdigit():
        return False
    if not _is_number(parts[4]):
        return False
    if parts[5] not in ("E", "W"):
        return False
    if not parts[6].isdigit():
        return False
    if not parts[7].isdigit():
        return False
    if not parts[8].isdigit():
        return False

    return True


def _validate_plot_object(obj: PlotObject) -> list[JRCCompatibilityIssue]:
    issues: list[JRCCompatibilityIssue] = []

    warning_id = _norm(getattr(obj, "source_warning_id", ""))
    navarea = _norm(getattr(obj, "source_navarea", ""))

    if not warning_id:
        issues.append(JRCCompatibilityIssue(
            code="META_001",
            severity="ERROR",
            scope="OBJECT",
            message="PlotObject missing source_warning_id",
        ))

    if not navarea:
        issues.append(JRCCompatibilityIssue(
            code="META_002",
            severity="WARN",
            scope="OBJECT",
            message=f"PlotObject {warning_id or '<UNKNOWN>'} missing source_navarea",
        ))

    if not obj.vertices:
        issues.append(JRCCompatibilityIssue(
            code="GEOM_001",
            severity="ERROR",
            scope="OBJECT",
            message=f"PlotObject {warning_id or '<UNKNOWN>'} has no vertices",
        ))
        return issues

    if obj.object_kind == "POINT" and len(obj.vertices) < 2:
        issues.append(JRCCompatibilityIssue(
            code="GEOM_002",
            severity="ERROR",
            scope="OBJECT",
            message=f"POINT object {warning_id or '<UNKNOWN>'} has fewer than 2 vertices; JRC LINE_AGGREGATE cannot render a one-vertex point",
        ))

    if obj.object_kind == "LINE" and len(obj.vertices) < 2:
        issues.append(JRCCompatibilityIssue(
            code="GEOM_003",
            severity="ERROR",
            scope="OBJECT",
            message=f"LINE object {warning_id or '<UNKNOWN>'} has fewer than 2 vertices",
        ))

    if obj.object_kind == "AREA" and len(obj.vertices) < 3:
        issues.append(JRCCompatibilityIssue(
            code="GEOM_004",
            severity="ERROR",
            scope="OBJECT",
            message=f"AREA object {warning_id or '<UNKNOWN>'} has fewer than 3 vertices",
        ))

    for idx, vertex in enumerate(obj.vertices, start=1):
        lat = vertex[0]
        lon = vertex[1]

        if not (-90.0 <= lat <= 90.0):
            issues.append(JRCCompatibilityIssue(
                code="COORD_001",
                severity="ERROR",
                scope="OBJECT",
                message=f"{warning_id or '<UNKNOWN>'} vertex {idx} latitude out of range: {lat}",
            ))

        if not (-180.0 <= lon <= 180.0):
            issues.append(JRCCompatibilityIssue(
                code="COORD_002",
                severity="ERROR",
                scope="OBJECT",
                message=f"{warning_id or '<UNKNOWN>'} vertex {idx} longitude out of range: {lon}",
            ))

    if obj.object_kind == "TEXT":
        issues.append(JRCCompatibilityIssue(
            code="TEXT_001",
            severity="WARN",
            scope="OBJECT",
            message=f"TEXT object {warning_id or '<UNKNOWN>'} still exists as a separate object; final doctrine expects text to become constructed LINE_AGGREGATE geometry",
        ))

    return issues


def _validate_exported_csv_text(csv_text: str) -> list[JRCCompatibilityIssue]:
    issues: list[JRCCompatibilityIssue] = []

    lines = csv_text.splitlines()
    if not lines:
        issues.append(JRCCompatibilityIssue(
            code="FILE_001",
            severity="ERROR",
            scope="FILE",
            message="Exported CSV is empty",
        ))
        return issues

    found_line_aggregate = False
    found_end = False
    found_warning_id_comment = False
    found_terminator = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("// [WARNING_ID:"):
            found_warning_id_comment = True

        if stripped == "// NNNN":
            found_terminator = True

        if stripped == "LINE_AGGREGATE":
            found_line_aggregate = True

            if i + 1 >= len(lines):
                issues.append(JRCCompatibilityIssue(
                    code="STRUCT_001",
                    severity="ERROR",
                    scope="FILE",
                    message="LINE_AGGREGATE is last line; missing required blank row and block content",
                ))
            elif lines[i + 1].strip() != "":
                issues.append(JRCCompatibilityIssue(
                    code="STRUCT_002",
                    severity="ERROR",
                    scope="FILE",
                    message="Missing required blank row under LINE_AGGREGATE",
                ))

        if stripped == "END":
            found_end = True

        if "//" in line and "," in line and not stripped.startswith("//"):
            issues.append(JRCCompatibilityIssue(
                code="STRUCT_003",
                severity="ERROR",
                scope="FILE",
                message="Inline comment detected inside a CSV vertex row",
            ))

        if stripped and stripped not in ("LINE_AGGREGATE", "END") and not stripped.startswith("//"):
            if "," in line and not _looks_like_vertex_row(line):
                issues.append(JRCCompatibilityIssue(
                    code="STRUCT_004",
                    severity="WARN",
                    scope="FILE",
                    message=f"Suspicious non-comment non-control row: {line}",
                ))

        i += 1

    if not found_line_aggregate:
        issues.append(JRCCompatibilityIssue(
            code="STRUCT_005",
            severity="ERROR",
            scope="FILE",
            message="No LINE_AGGREGATE block found in exported CSV",
        ))

    if not found_end:
        issues.append(JRCCompatibilityIssue(
            code="STRUCT_006",
            severity="ERROR",
            scope="FILE",
            message="No END row found in exported CSV",
        ))

    if not found_warning_id_comment:
        issues.append(JRCCompatibilityIssue(
            code="META_003",
            severity="WARN",
            scope="FILE",
            message="No // [WARNING_ID: ...] block comment found before warning sections",
        ))

    if not found_terminator:
        issues.append(JRCCompatibilityIssue(
            code="META_004",
            severity="WARN",
            scope="FILE",
            message="No // NNNN warning-section terminator found",
        ))

    return issues


def audit_plot_objects_for_jrc(
    *,
    plot_objects: list[PlotObject],
) -> JRCCompatibilityReport:
    issues: list[JRCCompatibilityIssue] = []

    if not plot_objects:
        issues.append(JRCCompatibilityIssue(
            code="OBJ_001",
            severity="ERROR",
            scope="OBJECT",
            message="No plot objects supplied for export",
        ))
    else:
        for obj in plot_objects:
            issues.extend(_validate_plot_object(obj))

    error_count = sum(1 for x in issues if x.severity == "ERROR")
    warning_count = sum(1 for x in issues if x.severity == "WARN")

    return JRCCompatibilityReport(
        ok=error_count == 0,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )


def audit_exported_jrc_csv_file(
    *,
    plot_csv_path: str | Path,
) -> JRCCompatibilityReport:
    path = Path(plot_csv_path)

    if not path.exists():
        issues = [
            JRCCompatibilityIssue(
                code="FILE_002",
                severity="ERROR",
                scope="FILE",
                message=f"Exported CSV not found: {path}",
            )
        ]
        return JRCCompatibilityReport(
            ok=False,
            issue_count=1,
            error_count=1,
            warning_count=0,
            issues=issues,
        )

    text = path.read_text(encoding="utf-8-sig")
    issues = _validate_exported_csv_text(text)

    error_count = sum(1 for x in issues if x.severity == "ERROR")
    warning_count = sum(1 for x in issues if x.severity == "WARN")

    return JRCCompatibilityReport(
        ok=error_count == 0,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )