from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .plot_editor_models import (
    PlotOverride,
    plot_override_from_dict,
    dataclass_to_dict,
)


# Default override root
DEFAULT_OVERRIDE_ROOT = Path("data/NAVWARN/overrides")


def override_path(
    *,
    warning_id: str,
    root: Path = DEFAULT_OVERRIDE_ROOT
) -> Path:
    """
    Returns path for override JSON.
    """
    return root / f"{warning_id}.json"


def override_exists(
    *,
    warning_id: str,
    root: Path = DEFAULT_OVERRIDE_ROOT
) -> bool:
    return override_path(warning_id=warning_id, root=root).exists()


def load_override(
    *,
    warning_id: str,
    root: Path = DEFAULT_OVERRIDE_ROOT
) -> Optional[PlotOverride]:
    """
    Loads override if present.
    """
    p = override_path(warning_id=warning_id, root=root)

    if not p.exists():
        return None

    data = json.loads(p.read_text(encoding="utf-8"))

    return plot_override_from_dict(data)


def save_override(
    override: PlotOverride,
    *,
    root: Path = DEFAULT_OVERRIDE_ROOT
) -> Path:
    """
    Saves override JSON.
    """
    p = override_path(warning_id=override.warning_id, root=root)

    p.parent.mkdir(parents=True, exist_ok=True)

    payload = dataclass_to_dict(override)

    p.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8"
    )

    return p


def clear_override(
    *,
    warning_id: str,
    root: Path = DEFAULT_OVERRIDE_ROOT
) -> bool:
    """
    Deletes override file.
    """
    p = override_path(warning_id=warning_id, root=root)

    if not p.exists():
        return False

    p.unlink()

    return True