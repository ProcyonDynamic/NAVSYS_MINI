from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


VALID_RENDER_FAMILIES = {
    "GENERIC",
    "OFFSHORE",
    "OPERATIONAL",
    "NONE",
}

VALID_OBJECT_MODES = {
    "AUTO",
    "POINT",
    "LINE",
    "AREA",
    "MULTI_POINT",
}

VALID_LABEL_MODES = {
    "GENERAL",
    "OFFSHORE_PER_OBJECT",
    "NONE",
}

VALID_LABEL_OFFSET_MODES = {
    "AUTO",
    "FIXED",
    "NONE",
}

VALID_SEVERITY_COLOR_MODES = {
    "BY_BAND",
    "FIXED",
    "NONE",
}


@dataclass
class WarningPlotPolicy:
    policy_id: str
    human_display_name: str

    enable_plot: bool = True
    enable_text: bool = True

    render_family: str = "GENERIC"
    object_mode: str = "AUTO"

    point_symbol_kind: str = "default"

    main_line_type: Optional[int] = None
    main_width: Optional[int] = None

    hatch_enabled: bool = False
    hatch_spacing_nm: Optional[float] = None
    hatch_line_type: Optional[int] = None
    hatch_width: Optional[int] = None

    label_mode: str = "GENERAL"
    label_offset_mode: str = "AUTO"

    severity_color_mode: str = "BY_BAND"
    fixed_color_no: Optional[int] = None
    red_color_no: Optional[int] = None
    amber_color_no: Optional[int] = None
    green_color_no: Optional[int] = None

    suppress_body_text_for_points: bool = False
    collapse_to_boundary_only: bool = False
    split_multi_object_output: bool = False

    notes: str = ""

    def validate(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")

        if not self.human_display_name.strip():
            raise ValueError("human_display_name must not be empty")

        if self.render_family not in VALID_RENDER_FAMILIES:
            raise ValueError(f"Invalid render_family: {self.render_family}")

        if self.object_mode not in VALID_OBJECT_MODES:
            raise ValueError(f"Invalid object_mode: {self.object_mode}")

        if self.label_mode not in VALID_LABEL_MODES:
            raise ValueError(f"Invalid label_mode: {self.label_mode}")

        if self.label_offset_mode not in VALID_LABEL_OFFSET_MODES:
            raise ValueError(f"Invalid label_offset_mode: {self.label_offset_mode}")

        if self.severity_color_mode not in VALID_SEVERITY_COLOR_MODES:
            raise ValueError(f"Invalid severity_color_mode: {self.severity_color_mode}")

        if self.hatch_spacing_nm is not None and self.hatch_spacing_nm <= 0:
            raise ValueError("hatch_spacing_nm must be > 0 when provided")

        for field_name in (
            "main_line_type",
            "main_width",
            "hatch_line_type",
            "hatch_width",
            "fixed_color_no",
            "red_color_no",
            "amber_color_no",
            "green_color_no",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be >= 0 when provided")

    @classmethod
    def from_dict(cls, data: dict) -> "WarningPlotPolicy":
        obj = cls(
            policy_id=str(data["policy_id"]),
            human_display_name=str(data["human_display_name"]),
            enable_plot=bool(data.get("enable_plot", True)),
            enable_text=bool(data.get("enable_text", True)),
            render_family=str(data.get("render_family", "GENERIC")),
            object_mode=str(data.get("object_mode", "AUTO")),
            point_symbol_kind=str(data.get("point_symbol_kind", "default")),
            main_line_type=data.get("main_line_type"),
            main_width=data.get("main_width"),
            hatch_enabled=bool(data.get("hatch_enabled", False)),
            hatch_spacing_nm=data.get("hatch_spacing_nm"),
            hatch_line_type=data.get("hatch_line_type"),
            hatch_width=data.get("hatch_width"),
            label_mode=str(data.get("label_mode", "GENERAL")),
            label_offset_mode=str(data.get("label_offset_mode", "AUTO")),
            severity_color_mode=str(data.get("severity_color_mode", "BY_BAND")),
            fixed_color_no=data.get("fixed_color_no"),
            red_color_no=data.get("red_color_no"),
            amber_color_no=data.get("amber_color_no"),
            green_color_no=data.get("green_color_no"),
            suppress_body_text_for_points=bool(data.get("suppress_body_text_for_points", False)),
            collapse_to_boundary_only=bool(data.get("collapse_to_boundary_only", False)),
            split_multi_object_output=bool(data.get("split_multi_object_output", False)),
            notes=str(data.get("notes", "")),
        )
        obj.validate()
        return obj

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "human_display_name": self.human_display_name,
            "enable_plot": self.enable_plot,
            "enable_text": self.enable_text,
            "render_family": self.render_family,
            "object_mode": self.object_mode,
            "point_symbol_kind": self.point_symbol_kind,
            "main_line_type": self.main_line_type,
            "main_width": self.main_width,
            "hatch_enabled": self.hatch_enabled,
            "hatch_spacing_nm": self.hatch_spacing_nm,
            "hatch_line_type": self.hatch_line_type,
            "hatch_width": self.hatch_width,
            "label_mode": self.label_mode,
            "label_offset_mode": self.label_offset_mode,
            "severity_color_mode": self.severity_color_mode,
            "fixed_color_no": self.fixed_color_no,
            "red_color_no": self.red_color_no,
            "amber_color_no": self.amber_color_no,
            "green_color_no": self.green_color_no,
            "suppress_body_text_for_points": self.suppress_body_text_for_points,
            "collapse_to_boundary_only": self.collapse_to_boundary_only,
            "split_multi_object_output": self.split_multi_object_output,
            "notes": self.notes,
        }


@dataclass
class EffectivePlotDecision:
    policy_id: str
    enable_plot: bool
    enable_text: bool

    render_family: str
    object_mode: str

    effective_color_no: Optional[int]
    hatch_enabled: bool
    hatch_spacing_nm: Optional[float]

    label_mode: str
    label_offset_mode: str

    point_symbol_kind: str
    main_line_type: Optional[int]
    main_width: Optional[int]

    suppress_body_text_for_points: bool = False
    collapse_to_boundary_only: bool = False
    split_multi_object_output: bool = False

    reasons: list[str] = field(default_factory=list)