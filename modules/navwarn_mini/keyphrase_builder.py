from __future__ import annotations
from typing import List

from .semantic_models import SemanticPacket

MAX_LABEL_WORDS = 6

ENTITY_PRIORITY = {
    "OFFSHORE_UNIT": 1,
    "VESSEL": 2,
    "MRCC": 3,
    "RADIO_STATION": 4,
    "NAVTEX_SYSTEM": 5,
    "NAVAREA": 6,
    "DISTRESS_TERM": 7,
    "URGENCY_TERM": 8,
    "SAFETY_TERM": 9,
    "AID_TO_NAVIGATION": 10,
    "ICE_TERM": 11,
    "STATE_TERM": 12,
}


def build_key_phrases(
    warning_id: str,
    semantic_packet: SemanticPacket,
) -> List[str]:
    phrases: List[str] = []

    if warning_id:
        phrases.append(warning_id.upper())

    sorted_entities = sorted(
        semantic_packet.entities,
        key=lambda ent: ENTITY_PRIORITY.get(ent.entity_type, 999),
    )

    for ent in sorted_entities:
        label = ent.canonical_name.upper().strip()
        words = label.split()
        if len(words) > MAX_LABEL_WORDS:
            label = " ".join(words[:MAX_LABEL_WORDS])

        if label and label not in phrases:
            phrases.append(label)

    return phrases