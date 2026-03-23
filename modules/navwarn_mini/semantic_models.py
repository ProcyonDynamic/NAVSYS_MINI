from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class SemanticEntity:
    entity_type: str
    raw_text: str
    canonical_name: str
    confidence: float
    source_method: str
    registry_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SemanticPacket:
    entities: List[SemanticEntity]
    key_phrases: List[str]
    matched_registries: List[str]
    warnings: List[str]