from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .warning_pattern_registry import WARNING_PATTERNS, WarningPattern


@dataclass
class WarningPatternMatch:
    pattern: Optional[WarningPattern]
    score: int
    reasons: list[str]


def match_warning_pattern(
    *,
    raw_text: str,
    profile_id: Optional[str] = None,
) -> WarningPatternMatch:
    text = " ".join((raw_text or "").upper().split())
    best_pattern: Optional[WarningPattern] = None
    best_score = -1
    best_reasons: list[str] = []

    for pattern in WARNING_PATTERNS:
        score = 0
        reasons: list[str] = []

        if profile_id and pattern.profile_ids:
            if profile_id in pattern.profile_ids:
                score += 10
                reasons.append(f"profile:{profile_id}")
            else:
                continue

        for phrase in pattern.trigger_phrases:
            if phrase.upper() in text:
                score += 10
                reasons.append(f"phrase:{phrase}")

        if score > best_score:
            best_pattern = pattern
            best_score = score
            best_reasons = reasons

    if best_pattern is None or best_score < 0:
        return WarningPatternMatch(pattern=None, score=0, reasons=[])

    return WarningPatternMatch(
        pattern=best_pattern,
        score=best_score,
        reasons=best_reasons,
    )

