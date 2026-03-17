from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .warning_plot_decision_models import EffectivePlotDecision, WarningPlotPolicy
from .warning_plot_policy_registry import get_plot_policy


@dataclass
class PlotPolicyMatch:
    matched: bool
    policy_id: Optional[str]
    policy: Optional[WarningPlotPolicy]
    reasons: list[str]


def resolve_plot_policy_for_profile(
    *,
    output_root: str,
    profile,
) -> PlotPolicyMatch:
    policy_id = getattr(profile, "plotting_policy_ref", None)

    if not policy_id:
        return PlotPolicyMatch(
            matched=False,
            policy_id=None,
            policy=None,
            reasons=["Profile has no plotting_policy_ref"],
        )

    policy = get_plot_policy(output_root=output_root, policy_id=policy_id)
    if policy is None:
        return PlotPolicyMatch(
            matched=False,
            policy_id=policy_id,
            policy=None,
            reasons=[f"Policy not found: {policy_id}"],
        )

    return PlotPolicyMatch(
        matched=True,
        policy_id=policy_id,
        policy=policy,
        reasons=[f"Loaded policy from config: {policy_id}"],
    )
    
def build_effective_plot_decision(
    *,
    policy: WarningPlotPolicy,
    geom_type: str,
    band: str | None,
    offshore_object_count: int,
) -> EffectivePlotDecision:

    reasons: list[str] = []

    # 1. enable flags
    enable_plot = policy.enable_plot
    enable_text = policy.enable_text

    # 2. object mode resolution
    if policy.object_mode == "AUTO":
        if offshore_object_count > 0:
            object_mode = "MULTI_POINT"
            reasons.append("AUTO → MULTI_POINT (offshore objects present)")
        elif geom_type == "POINT":
            object_mode = "POINT"
            reasons.append("AUTO → POINT")
        elif geom_type == "LINE":
            object_mode = "LINE"
            reasons.append("AUTO → LINE")
        elif geom_type == "AREA":
            object_mode = "AREA"
            reasons.append("AUTO → AREA")
        else:
            object_mode = "POINT"
            reasons.append("AUTO → fallback POINT")
    else:
        object_mode = policy.object_mode
        reasons.append(f"Policy forced object_mode={object_mode}")

    # 3. color resolution
    effective_color_no = None

    if policy.severity_color_mode == "BY_BAND":
        if band == "RED":
            effective_color_no = policy.red_color_no
            reasons.append("Color from RED band")
        elif band == "AMBER":
            effective_color_no = policy.amber_color_no
            reasons.append("Color from AMBER band")
        elif band == "GREEN":
            effective_color_no = policy.green_color_no
            reasons.append("Color from GREEN band")
        else:
            reasons.append("No band → no color")
    elif policy.severity_color_mode == "FIXED":
        effective_color_no = policy.fixed_color_no
        reasons.append("Fixed color mode")
    else:
        reasons.append("Color disabled")

    return EffectivePlotDecision(
        policy_id=policy.policy_id,
        enable_plot=enable_plot,
        enable_text=enable_text,
        render_family=policy.render_family,
        object_mode=object_mode,
        effective_color_no=effective_color_no,
        hatch_enabled=policy.hatch_enabled,
        hatch_spacing_nm=policy.hatch_spacing_nm,
        label_mode=policy.label_mode,
        label_offset_mode=policy.label_offset_mode,
        point_symbol_kind=policy.point_symbol_kind,
        main_line_type=policy.main_line_type,
        main_width=policy.main_width,
        suppress_body_text_for_points=policy.suppress_body_text_for_points,
        collapse_to_boundary_only=policy.collapse_to_boundary_only,
        split_multi_object_output=policy.split_multi_object_output,
        reasons=reasons,
    )