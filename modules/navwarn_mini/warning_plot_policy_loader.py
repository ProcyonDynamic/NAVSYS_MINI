from __future__ import annotations

import json
from pathlib import Path

from .warning_plot_decision_models import WarningPlotPolicy


def _load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Policy file must contain a JSON object: {path}")

    return data


def _merge_policy_dicts(base: dict, override: dict) -> dict:
    merged = dict(base)
    for policy_id, override_fields in override.items():
        if not isinstance(override_fields, dict):
            raise ValueError(f"Override entry for {policy_id} must be an object")

        base_fields = merged.get(policy_id, {})
        if not isinstance(base_fields, dict):
            base_fields = {}

        merged[policy_id] = {**base_fields, **override_fields, "policy_id": policy_id}

    return merged


def load_plot_policies(
    defaults_path: str | Path,
    overrides_path: str | Path,
) -> dict[str, WarningPlotPolicy]:
    defaults_path = Path(defaults_path)
    overrides_path = Path(overrides_path)

    raw_defaults = _load_json_file(defaults_path)
    raw_overrides = _load_json_file(overrides_path)

    merged = _merge_policy_dicts(raw_defaults, raw_overrides)

    policies: dict[str, WarningPlotPolicy] = {}
    for policy_id, raw in merged.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Policy entry for {policy_id} must be an object")

        raw = dict(raw)
        raw["policy_id"] = policy_id
        policy = WarningPlotPolicy.from_dict(raw)
        policies[policy_id] = policy

    return policies


def save_plot_policy_overrides(
    overrides_path: str | Path,
    override_data: dict,
) -> None:
    overrides_path = Path(overrides_path)
    overrides_path.parent.mkdir(parents=True, exist_ok=True)

    with overrides_path.open("w", encoding="utf-8") as f:
        json.dump(override_data, f, indent=2, ensure_ascii=False, sort_keys=True)