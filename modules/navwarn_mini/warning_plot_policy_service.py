from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .warning_plot_policy_registry import WARNING_PLOT_POLICIES, WarningPlotPolicy


@dataclass
class WarningPlotPolicyMatch:
    policy: Optional[WarningPlotPolicy]
    policy_id: Optional[str]


def resolve_plot_policy_for_profile(*, profile) -> WarningPlotPolicyMatch:
    if profile is None:
        return WarningPlotPolicyMatch(
            policy=WARNING_PLOT_POLICIES.get("plot_operational_default"),
            policy_id="plot_operational_default",
        )

    policy_id = profile.plotting_policy_ref or "plot_operational_default"
    policy = WARNING_PLOT_POLICIES.get(
        policy_id,
        WARNING_PLOT_POLICIES["plot_operational_default"],
    )

    return WarningPlotPolicyMatch(
        policy=policy,
        policy_id=policy.policy_id,
    )
