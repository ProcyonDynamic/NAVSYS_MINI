from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WarningProfile:
    internal_id: str
    human_display_name: str
    category_type: str
    active_flag: bool = True
    version: str = "v0.1"

    keywords: list[str] = field(default_factory=list)
    shared_triggers: list[str] = field(default_factory=list)
    other_triggers: list[str] = field(default_factory=list)
    exclusion_conditions: list[str] = field(default_factory=list)
    formatting_variants: list[str] = field(default_factory=list)

    expected_geometry_types: list[str] = field(default_factory=list)
    typical_object_types: list[str] = field(default_factory=list)
    typical_data_blocks: list[str] = field(default_factory=list)
    required_data_blocks: list[str] = field(default_factory=list)
    optional_data_blocks: list[str] = field(default_factory=list)

    typical_time_expression_patterns: list[str] = field(default_factory=list)
    typical_cancellation_patterns: list[str] = field(default_factory=list)
    typical_reference_patterns: list[str] = field(default_factory=list)

    plotting_policy_ref: Optional[str] = None
    extraction_policy_ref: Optional[str] = None
    label_policy_ref: Optional[str] = None
    export_policy_ref: Optional[str] = None

    match_priority: int = 100
    confidence_hints: list[str] = field(default_factory=list)

    notes: str = ""
    examples: list[str] = field(default_factory=list)


WARNING_PROFILES: list[WarningProfile] = [
    WarningProfile(
        internal_id="offshore_platform_list",
        human_display_name="Offshore Platform / MODU Warning",
        category_type="OFFSHORE",
        keywords=[
            "MODU",
            "PLATFORM",
            "FPSO",
            "FSO",
            "DRILLING RIG",
            "SEMI-SUBMERSIBLE",
            "JACK-UP",
            "JACK UP",
        ],
        expected_geometry_types=["POINT"],
        typical_object_types=["OFFSHORE_OBJECT"],
        typical_data_blocks=["platform_name", "coordinate"],
        required_data_blocks=["coordinate"],
        optional_data_blocks=["platform_name", "movement_note"],
        plotting_policy_ref="plot_offshore_default",
        extraction_policy_ref="extract_offshore_default",
        label_policy_ref="label_offshore_default",
        export_policy_ref="export_jrc_default",
        match_priority=10,
        notes="Profile for MODU/platform lists and offshore unit bulletins.",
    ),
    WarningProfile(
        internal_id="cancellation_notice",
        human_display_name="Cancellation Notice",
        category_type="CANCELLATION",
        keywords=["CANCEL"],
        expected_geometry_types=[],
        typical_object_types=["STATE_CHANGE"],
        typical_data_blocks=["cancel_target"],
        required_data_blocks=["cancel_target"],
        plotting_policy_ref="plot_none",
        extraction_policy_ref="extract_cancellation_default",
        label_policy_ref="label_cancellation_default",
        export_policy_ref="export_state_only",
        match_priority=5,
        notes="Used for warning cancellations and lifecycle transitions.",
    ),
    WarningProfile(
        internal_id="reference_bulletin",
        human_display_name="Reference Bulletin",
        category_type="REFERENCE",
        keywords=["IN FORCE", "REFERENCE", "REFER TO"],
        expected_geometry_types=[],
        typical_object_types=["REFERENCE_NOTICE"],
        typical_data_blocks=["reference_ids"],
        plotting_policy_ref="plot_none",
        extraction_policy_ref="extract_reference_default",
        label_policy_ref="label_reference_default",
        export_policy_ref="export_state_only",
        match_priority=20,
        notes="Non-operational reference-style bulletins.",
    ),
    WarningProfile(
        internal_id="general_operational_area",
        human_display_name="General Operational Area Warning",
        category_type="OPERATIONAL_AREA",
        keywords=[
            "DRILLING OPERATIONS",
            "EXERCISE",
            "FIRING",
            "SURVEY OPERATIONS",
            "PIPELAYING",
            "SUBSEA OPERATIONS",
        ],
        expected_geometry_types=["AREA", "LINE", "POINT"],
        typical_object_types=["WARNING_GEOMETRY"],
        typical_data_blocks=["geometry"],
        required_data_blocks=["geometry"],
        optional_data_blocks=["time_window", "notes"],
        plotting_policy_ref="plot_operational_default",
        extraction_policy_ref="extract_operational_default",
        label_policy_ref="label_operational_default",
        export_policy_ref="export_jrc_default",
        match_priority=50,
        notes="Fallback operational warning profile for area/line/point activity.",
    ),
]
