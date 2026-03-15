from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GeometryHintResult:
    expected_geometry_types: list[str]
    geometry_hints: list[str]
    geometry_consistency: str


def build_geometry_hints(
    *,
    profile_match=None,
    pattern_match=None,
    actual_geom_type: Optional[str] = None,
) -> GeometryHintResult:
    expected_geometry_types: list[str] = []
    geometry_hints: list[str] = []

    if profile_match and getattr(profile_match, "profile", None):
        expected_geometry_types.extend(
            profile_match.profile.expected_geometry_types or []
        )

    if pattern_match and getattr(pattern_match, "pattern", None):
        expected_geometry_types.extend(
            pattern_match.pattern.expected_geometry_types or []
        )
        geometry_hints.extend(
            pattern_match.pattern.geometry_hints or []
        )

    # deduplicate while preserving order
    expected_geometry_types = list(dict.fromkeys(expected_geometry_types))
    geometry_hints = list(dict.fromkeys(geometry_hints))

    geometry_consistency = "UNKNOWN"

    if actual_geom_type and expected_geometry_types:
        if actual_geom_type in expected_geometry_types:
            geometry_consistency = "MATCH"
        else:
            geometry_consistency = "MISMATCH"
    elif actual_geom_type:
        geometry_consistency = "NO_EXPECTATION"

    return GeometryHintResult(
        expected_geometry_types=expected_geometry_types,
        geometry_hints=geometry_hints,
        geometry_consistency=geometry_consistency,
    )
