from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal, Optional

Band = Literal["RED", "AMBER"]


@dataclass(frozen=True)
class PlotPolicyDefaults:
    red_color_no: int = 9
    amber_color_no: int = 2
    main_width: int = 3
    main_line_type: int = 1
    title_text_size: int = 16
    body_text_size: int = 14
    enable_text: bool = True
    point_symbol_size_nm: float = 0.6


DEFAULT_PLOT_POLICY = PlotPolicyDefaults()


def get_default_plot_policy_dict() -> dict:
    return asdict(DEFAULT_PLOT_POLICY)


def resolve_plot_policy(*, band: Band, override: Optional[dict] = None) -> dict:
    policy = get_default_plot_policy_dict()

    if override:
        for key, value in override.items():
            if key in policy and value is not None:
                policy[key] = value

    policy["effective_color_no"] = (
        policy["red_color_no"] if band == "RED" else policy["amber_color_no"]
    )

    return policy