from __future__ import annotations

from pathlib import Path

from .warning_plot_decision_models import WarningPlotPolicy
from .warning_plot_policy_loader import load_plot_policies


def load_plot_policy_registry(output_root: str) -> dict[str, WarningPlotPolicy]:
    root = Path(output_root)
    config_dir = root / "NAVWARN" / "config"

    defaults_path = config_dir / "plot_policy_defaults.json"
    overrides_path = config_dir / "plot_policy_overrides.json"

    module_root = Path(__file__).resolve().parents[2]
    bundled_defaults = module_root / "data" / "NAVWARN" / "config" / "plot_policy_defaults.json"
    bundled_overrides = module_root / "data" / "NAVWARN" / "config" / "plot_policy_overrides.json"

    if not defaults_path.exists():
        defaults_path = bundled_defaults

    if not overrides_path.exists():
        overrides_path = bundled_overrides

    return load_plot_policies(
        defaults_path=defaults_path,
        overrides_path=overrides_path,
    )


def get_plot_policy(
    *,
    output_root: str,
    policy_id: str,
) -> WarningPlotPolicy | None:
    registry = load_plot_policy_registry(output_root)
    return registry.get(policy_id)