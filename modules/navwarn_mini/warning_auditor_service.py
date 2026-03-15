from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WarningAuditResult:
    audit_status: str
    audit_flags: list[str] = field(default_factory=list)
    audit_notes: list[str] = field(default_factory=list)


def audit_warning_result(
    *,
    profile_match=None,
    pattern_match=None,
    geometry_hint_result=None,
    actual_geom_type: Optional[str] = None,
    vertex_count: int = 0,
    is_reference_message: bool = False,
    is_cancellation: bool = False,
    offshore_object_count: int = 0,
) -> WarningAuditResult:
    flags: list[str] = []
    notes: list[str] = []

    profile_id = profile_match.profile.internal_id if getattr(profile_match, "profile", None) else None
    pattern_id = pattern_match.pattern.pattern_id if getattr(pattern_match, "pattern", None) else None
    geometry_consistency = (
        geometry_hint_result.geometry_consistency
        if geometry_hint_result is not None
        else "UNKNOWN"
    )
    expected_geometry_types = (
        geometry_hint_result.expected_geometry_types
        if geometry_hint_result is not None
        else []
    )

    # 1) Reference/cancellation should normally not carry operational geometry
    if is_reference_message and vertex_count > 0:
        flags.append("REFERENCE_HAS_GEOMETRY")
        notes.append("Reference-style bulletin produced geometry.")
    if is_cancellation and vertex_count > 0:
        flags.append("CANCELLATION_HAS_GEOMETRY")
        notes.append("Cancellation bulletin produced geometry.")

    # 2) Geometry mismatch against expectations
    if geometry_consistency == "MISMATCH":
        flags.append("GEOMETRY_EXPECTATION_MISMATCH")
        notes.append(
            f"Expected one of {expected_geometry_types}, got {actual_geom_type}."
        )

    # 3) No geometry expectation available
    if geometry_consistency == "NO_EXPECTATION":
        flags.append("NO_GEOMETRY_EXPECTATION")
        notes.append("No expected geometry was available from profile/pattern.")

    # 4) Pattern missing while profile exists
    if profile_id and not pattern_id:
        flags.append("PROFILE_WITHOUT_PATTERN")
        notes.append("Profile matched but no structural pattern matched.")

    # 5) Offshore-specific sanity
    if profile_id == "offshore_platform_list":
        if vertex_count == 0:
            flags.append("OFFSHORE_NO_GEOMETRY")
            notes.append("Offshore warning matched but no plotted points were produced.")
        if offshore_object_count == 0:
            flags.append("OFFSHORE_NO_OBJECTS")
            notes.append("Offshore profile matched but no offshore objects were resolved.")
        if offshore_object_count > 0 and vertex_count != offshore_object_count:
            flags.append("OFFSHORE_COUNT_MISMATCH")
            notes.append(
                f"Offshore objects={offshore_object_count}, plotted vertices={vertex_count}."
            )

    # Final status
    if any(f in flags for f in (
        "GEOMETRY_EXPECTATION_MISMATCH",
        "OFFSHORE_NO_GEOMETRY",
        "OFFSHORE_NO_OBJECTS",
        "OFFSHORE_COUNT_MISMATCH",
        "CANCELLATION_HAS_GEOMETRY",
        "REFERENCE_HAS_GEOMETRY",
    )):
        status = "REVIEW_REQUIRED"
    elif flags:
        status = "WARN"
    else:
        status = "PASS"

    return WarningAuditResult(
        audit_status=status,
        audit_flags=flags,
        audit_notes=notes,
    )
