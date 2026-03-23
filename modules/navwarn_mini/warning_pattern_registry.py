from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WarningPattern:
    pattern_id: str
    human_display_name: str
    profile_ids: list[str] = field(default_factory=list)

    trigger_phrases: list[str] = field(default_factory=list)
    geometry_hints: list[str] = field(default_factory=list)
    expected_geometry_types: list[str] = field(default_factory=list)
    expected_block_types: list[str] = field(default_factory=list)
    list_style: str = ""
    self_cancel_allowed: bool = False
    preferred_geometry_source: str = "AUTO"

    label_hints: list[str] = field(default_factory=list)
    notes: str = ""


WARNING_PATTERNS: list[WarningPattern] = [
    WarningPattern(
        pattern_id="offshore_platform_list_basic",
        human_display_name="Offshore Platform List",
        profile_ids=["offshore_platform_list"],
        trigger_phrases=["MODU", "FPSO", "FSO", "JACK-UP", "SEMI-SUBMERSIBLE"],
        geometry_hints=["POINT_LIST"],
        expected_geometry_types=["POINT"],
        label_hints=["PLATFORM_NAME", "WARNING_ID"],
        notes="Basic offshore unit/platform list pattern.",
        expected_block_types=["GEOMETRY"],
        list_style="ALPHA_LABELLED",
        self_cancel_allowed=False,
        preferred_geometry_source="OFFSHORE_SECTION_SPLIT",
    ),
    WarningPattern(
        pattern_id="area_bounded_by",
        human_display_name="Area Bounded By",
        profile_ids=["general_operational_area"],
        trigger_phrases=["AREA BOUNDED BY", "IN AREA BOUNDED BY"],
        geometry_hints=["AREA_BOUNDARY"],
        expected_geometry_types=["AREA"],
        label_hints=["WARNING_ID", "KEY_PHRASE"],
        notes="Polygon-style area warning pattern.",
        expected_block_types=["GEOMETRY"],
        list_style="SUBAREA_ALPHA_OPTIONAL",
        self_cancel_allowed=True,
        preferred_geometry_source="STRUCTURE_FIRST",
    ),
    WarningPattern(
        pattern_id="line_along_between",
        human_display_name="Line Along / Between",
        profile_ids=["general_operational_area"],
        trigger_phrases=["ALONG", "BETWEEN"],
        geometry_hints=["LINEAR_FEATURE"],
        expected_geometry_types=["LINE"],
        label_hints=["WARNING_ID", "KEY_PHRASE"],
        notes="Line-style warning pattern.",
        expected_block_types=["TIME", "GEOMETRY"],
        list_style="SUBAREA_ALPHA_OPTIONAL",
        self_cancel_allowed=True,
        preferred_geometry_source="STRUCTURE_FIRST",
    ),
    WarningPattern(
        pattern_id="exercise_firing_ops",
        human_display_name="Exercise / Firing Operations",
        profile_ids=["general_operational_area"],
        trigger_phrases=["EXERCISE", "FIRING"],
        geometry_hints=["OPERATIONAL_AREA"],
        expected_geometry_types=["AREA", "LINE", "POINT"],
        label_hints=["WARNING_ID", "EXERCISE", "FIRING"],
        notes="Exercise or firing operational warning.",
    ),
    WarningPattern(
        pattern_id="survey_ops",
        human_display_name="Survey Operations",
        profile_ids=["general_operational_area"],
        trigger_phrases=["SURVEY OPERATIONS", "SEISMIC", "SUBSEA OPERATIONS", "PIPELAYING"],
        geometry_hints=["OPERATIONAL_AREA"],
        expected_geometry_types=["AREA", "LINE", "POINT"],
        label_hints=["WARNING_ID", "KEY_PHRASE"],
        notes="Survey / subsea / pipelaying style warning.",
        expected_block_types=["GEOMETRY"],
        list_style="LINEAR_OR_AREA",
        self_cancel_allowed=True,
        preferred_geometry_source="STRUCTURE_FIRST",
    ),
    WarningPattern(
        pattern_id="cancellation_basic",
        human_display_name="Cancellation Pattern",
        profile_ids=["cancellation_notice"],
        trigger_phrases=["CANCEL"],
        geometry_hints=["NO_GEOMETRY"],
        expected_geometry_types=[],
        label_hints=["STATE_CHANGE"],
        notes="Basic cancellation pattern.",
        expected_block_types=["CANCELLATION"],
        list_style="ID_LIST_OPTIONAL",
        self_cancel_allowed=False,
        preferred_geometry_source="NONE",
    ),
]

