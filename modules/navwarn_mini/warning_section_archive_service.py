from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WarningSectionArchiveResult:
    ok: bool
    archive_csv_path: str
    global_archive_csv_path: str
    warning_id: str
    route_id: str
    navarea: str
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


def build_warning_archive_path(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    warning_id: str,
) -> Path:
    root = Path(output_root)
    archive_dir = root / "NAVWARN" / "warning_archive" / _safe_token(route_id) / _safe_token(navarea)
    archive_dir.mkdir(parents=True, exist_ok=True)

    safe_warning_id = _safe_token(warning_id)

    return archive_dir / f"{safe_warning_id}.csv"


def build_global_warning_archive_path(
    *,
    output_root: str,
    navarea: str,
    warning_id: str,
) -> Path:
    root = Path(output_root)
    archive_dir = root / "NAVWARN" / "warning_archive_global" / _safe_token(navarea)
    archive_dir.mkdir(parents=True, exist_ok=True)

    safe_warning_id = _safe_token(warning_id)

    return archive_dir / f"{safe_warning_id}.csv"


def archive_warning_section(
    *,
    output_root: str,
    route_id: str,
    navarea: str,
    warning_id: str,
    section_text: str,
) -> WarningSectionArchiveResult:
    archive_path = build_warning_archive_path(
        output_root=output_root,
        route_id=route_id,
        navarea=navarea,
        warning_id=warning_id,
    )

    global_archive_path = build_global_warning_archive_path(
        output_root=output_root,
        navarea=navarea,
        warning_id=warning_id,
    )

    errors: list[str] = []

    try:
        payload = section_text.rstrip() + "\n"

        archive_path.write_text(payload, encoding="utf-8")
        global_archive_path.write_text(payload, encoding="utf-8")

        return WarningSectionArchiveResult(
            ok=True,
            archive_csv_path=str(archive_path),
            global_archive_csv_path=str(global_archive_path),
            warning_id=warning_id,
            route_id=route_id,
            navarea=navarea,
            errors=[],
        )

    except Exception as exc:
        errors.append(f"Failed to archive warning section: {exc}")

        return WarningSectionArchiveResult(
            ok=False,
            archive_csv_path=str(archive_path),
            global_archive_csv_path=str(global_archive_path),
            warning_id=warning_id,
            route_id=route_id,
            navarea=navarea,
            errors=errors,
        )