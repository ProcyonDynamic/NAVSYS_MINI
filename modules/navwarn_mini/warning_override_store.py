from __future__ import annotations

import json
from pathlib import Path


def _safe_name(value: str) -> str:
    value = (value or "").strip().upper()
    value = value.replace("NAVAREA ", "")
    value = value.replace("/", "_")
    value = value.replace(" ", "_")
    return value or "UNKNOWN"


def build_override_path(output_root: str, navarea: str, warning_id: str) -> Path:
    root = Path(output_root)
    return (
        root
        / "data"
        / "NAVWARN"
        / "editor_overrides"
        / _safe_name(navarea)
        / f"{_safe_name(warning_id)}.json"
    )


def has_warning_override(output_root: str, navarea: str, warning_id: str) -> bool:
    try:
        return build_override_path(output_root, navarea, warning_id).exists()
    except Exception:
        return False


def load_warning_override(output_root: str, navarea: str, warning_id: str) -> dict | None:
    try:
        path = build_override_path(output_root, navarea, warning_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_warning_override(output_root: str, navarea: str, warning_id: str, override_data: dict) -> str:
    if not isinstance(override_data, dict):
        raise ValueError("override_data must be a dict")

    path = build_override_path(output_root, navarea, warning_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(override_data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return str(path)
