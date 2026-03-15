from __future__ import annotations

from typing import Optional

from .vertex_text_builder import build_vertex_texts_for_platform


def build_key_phrase_summary(raw_text: str) -> str:
    text = " ".join(raw_text.upper().split())

    priority_phrases = [
        "UNLIT",
        "UNRELIABLE",
        "DRILLING OPERATIONS",
        "DRILLING",
        "MODU",
        "PLATFORM",
        "OFF STATION",
        "MISSING",
        "ESTABLISHED",
        "CANCEL",
        "EXERCISE",
        "FIRING",
        "SURVEY OPERATIONS",
        "PIPELAYING",
        "SUBSEA OPERATIONS",
    ]

    found = [p for p in priority_phrases if p in text]
    found = found[:3]

    return " / ".join(found)


def build_general_label_lines(*, warning_id: str, raw_text: str) -> list[str]:
    lines = [warning_id]

    key_phrase_summary = build_key_phrase_summary(raw_text)
    if key_phrase_summary:
        lines.append(key_phrase_summary)

    return lines


def build_profile_label_payload(
    *,
    profile_id: Optional[str],
    warning_id: str,
    raw_text: str,
    offshore_vertex=None,
    offshore_name: Optional[str] = None,
    offshore_match_status: Optional[str] = None,
):
    """
    Returns either:
    - list[TextObject]-style payload from build_vertex_texts_for_platform(...)
    - or list[dict] with {"lines": [...]} for general warnings
    """

    if profile_id == "offshore_platform_list" and offshore_vertex is not None:
        note_text = "MOVED" if offshore_match_status == "POSITION_UPDATED" else None
        return build_vertex_texts_for_platform(
            vertex=offshore_vertex,
            warning_id=warning_id,
            platform_name=offshore_name,
            note_text=note_text,
        )

    return [{
        "lines": build_general_label_lines(
            warning_id=warning_id,
            raw_text=raw_text,
        )
    }]
