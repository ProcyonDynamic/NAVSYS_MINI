from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .warning_profile_registry import WARNING_PROFILES, WarningProfile


@dataclass
class WarningProfileMatch:
    profile: Optional[WarningProfile]
    score: int
    reasons: list[str]


def match_warning_profile(*, raw_text: str, interp_warning_type: str = "") -> WarningProfileMatch:
    text = " ".join((raw_text or "").upper().split())
    interp_type = (interp_warning_type or "").upper().strip()

    best_profile: Optional[WarningProfile] = None
    best_score = -1
    best_reasons: list[str] = []

    for profile in WARNING_PROFILES:
        if not profile.active_flag:
            continue

        score = 0
        reasons: list[str] = []

        for kw in profile.keywords:
            if kw.upper() in text:
                score += 10
                reasons.append(f"keyword:{kw}")

        for trig in profile.shared_triggers:
            if trig.upper() in text:
                score += 5
                reasons.append(f"shared_trigger:{trig}")

        for trig in profile.other_triggers:
            if trig.upper() in text:
                score += 3
                reasons.append(f"other_trigger:{trig}")

        for ex in profile.exclusion_conditions:
            if ex.upper() in text:
                score -= 100
                reasons.append(f"excluded:{ex}")

        if interp_type:
            if profile.category_type == "OFFSHORE" and interp_type in ("MODU", "PLATFORM"):
                score += 15
                reasons.append(f"interp_type:{interp_type}")
            elif profile.category_type == "CANCELLATION" and interp_type == "CANCELLATION":
                score += 15
                reasons.append(f"interp_type:{interp_type}")
            elif profile.category_type == "REFERENCE" and interp_type == "REFERENCE":
                score += 15
                reasons.append(f"interp_type:{interp_type}")

        score -= profile.match_priority

        if score > best_score:
            best_profile = profile
            best_score = score
            best_reasons = reasons

    if best_profile is None or best_score < 0:
        return WarningProfileMatch(profile=None, score=0, reasons=[])

    return WarningProfileMatch(
        profile=best_profile,
        score=best_score,
        reasons=best_reasons,
    )
