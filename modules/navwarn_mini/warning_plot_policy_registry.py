from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WarningPlotPolicy:
    policy_id: str
    human_display_name: str

    enable_text: bool = True

    title_text_size: Optional[int] = None
    body_text_size: Optional[int] = None

    red_color_no: Optional[int] = None
    amber_color_no: Optional[int] = None

    main_width: Optional[int] = None
    main_line_type: Optional[int] = None

    point_symbol_kind: str = "x"
    notes: str = ""


WARNING_PLOT_POLICIES: dict[str, WarningPlotPolicy] = {
    "plot_offshore_default": WarningPlotPolicy(
        policy_id="plot_offshore_default",
        human_display_name="Offshore Default",
        enable_text=True,
        title_text_size=16,
        body_text_size=14,
        red_color_no=9,
        amber_color_no=2,
        main_width=3,
        main_line_type=1,
        point_symbol_kind="x",
        notes="Default offshore/MODU plotting policy.",
    ),
    "plot_operational_default": WarningPlotPolicy(
        policy_id="plot_operational_default",
        human_display_name="Operational Default",
        enable_text=True,
        title_text_size=16,
        body_text_size=14,
        red_color_no=9,
        amber_color_no=2,
        main_width=3,
        main_line_type=1,
        point_symbol_kind="x",
        notes="Default operational area/line/point plotting policy.",
    ),
    "plot_none": WarningPlotPolicy(
        policy_id="plot_none",
        human_display_name="No Plot",
        enable_text=False,
        title_text_size=16,
        body_text_size=14,
        red_color_no=9,
        amber_color_no=2,
        main_width=3,
        main_line_type=1,
        point_symbol_kind="x",
        notes="Used for state-only/reference/cancellation style flows.",
    ),
}
