from __future__ import annotations
from typing import List

from .semantic_models import SemanticEntity, SemanticPacket
from .semantic_registry_loader import load_semantic_registry


def build_semantic_packet(raw_text: str, normalized_text: str) -> SemanticPacket:
    entities: List[SemanticEntity] = []
    key_phrases: List[str] = []
    matched_registries: List[str] = []
    warnings: List[str] = []

    haystack = normalized_text.upper()
    registry = load_semantic_registry()

    for item in registry:
        canonical_name = str(item.get("canonical_name", "")).strip()
        entity_type = str(item.get("entity_type", "UNKNOWN")).strip()
        aliases = item.get("aliases", [])
        tags = item.get("tags", [])
        registry_id = item.get("registry_id")

        candidates = [canonical_name] + [str(x) for x in aliases]

        for phrase in candidates:
            phrase = phrase.strip()
            if not phrase:
                continue

            if phrase.upper() in haystack:
                entity = SemanticEntity(
                    entity_type=entity_type,
                    raw_text=phrase,
                    canonical_name=canonical_name or phrase,
                    confidence=0.90,
                    source_method="registry_match",
                    registry_id=registry_id,
                    tags=list(tags) if isinstance(tags, list) else [],
                )
                entities.append(entity)
                matched_registries.append(entity_type)

                kp = entity.canonical_name.upper()
                if kp not in key_phrases:
                    key_phrases.append(kp)
                break

    return SemanticPacket(
        entities=entities,
        key_phrases=key_phrases,
        matched_registries=sorted(set(matched_registries)),
        warnings=warnings,
    )