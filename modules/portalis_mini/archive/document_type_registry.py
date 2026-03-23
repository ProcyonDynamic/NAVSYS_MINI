from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DocumentTypeDefinition:
    code: str
    label: str
    category: str
    allowed_extensions: List[str] = field(default_factory=list)
    requires_owner: bool = False
    allowed_owner_entities: List[str] = field(default_factory=list)
    parser_key: Optional[str] = None
    default_confidence: float = 0.0


DOCUMENT_TYPE_REGISTRY: Dict[str, DocumentTypeDefinition] = {
    "CREW_PASSPORT": DocumentTypeDefinition(
        code="CREW_PASSPORT",
        label="Crew Passport",
        category="crew_document",
        allowed_extensions=[".pdf", ".jpg", ".jpeg", ".png", ".webp"],
        requires_owner=True,
        allowed_owner_entities=["crew"],
        parser_key="passport",
        default_confidence=0.0,
    ),
    "SEAMAN_BOOK": DocumentTypeDefinition(
        code="SEAMAN_BOOK",
        label="Seaman Book",
        category="crew_document",
        allowed_extensions=[".pdf", ".jpg", ".jpeg", ".png", ".webp"],
        requires_owner=True,
        allowed_owner_entities=["crew"],
        parser_key="seaman_book",
        default_confidence=0.0,
    ),
    "VISA": DocumentTypeDefinition(
        code="VISA",
        label="Visa",
        category="crew_document",
        allowed_extensions=[".pdf", ".jpg", ".jpeg", ".png", ".webp"],
        requires_owner=True,
        allowed_owner_entities=["crew"],
        parser_key="visa",
        default_confidence=0.0,
    ),
    "SHIP_CERTIFICATE": DocumentTypeDefinition(
        code="SHIP_CERTIFICATE",
        label="Ship Certificate",
        category="ship_document",
        allowed_extensions=[".pdf", ".jpg", ".jpeg", ".png"],
        requires_owner=True,
        allowed_owner_entities=["ship"],
        parser_key="certificate",
        default_confidence=0.0,
    ),
    "ARRIVAL_FORM": DocumentTypeDefinition(
        code="ARRIVAL_FORM",
        label="Arrival Form",
        category="port_form",
        allowed_extensions=[".pdf", ".docx", ".xlsx", ".xls"],
        requires_owner=False,
        allowed_owner_entities=[],
        parser_key="arrival_form",
        default_confidence=0.0,
    ),
    "ANKO_REPORT": DocumentTypeDefinition(
        code="ANKO_REPORT",
        label="ANKO Report",
        category="port_form",
        allowed_extensions=[".pdf", ".docx", ".xlsx", ".xls"],
        requires_owner=False,
        allowed_owner_entities=[],
        parser_key="anko_report",
        default_confidence=0.0,
    ),
}


def get_document_type(doc_type: str) -> Optional[DocumentTypeDefinition]:
    return DOCUMENT_TYPE_REGISTRY.get((doc_type or "").strip().upper())


def list_document_type_choices() -> List[dict]:
    return [
        {
            "code": item.code,
            "label": item.label,
            "category": item.category,
            "allowed_extensions": item.allowed_extensions,
            "requires_owner": item.requires_owner,
            "allowed_owner_entities": item.allowed_owner_entities,
            "parser_key": item.parser_key,
        }
        for item in DOCUMENT_TYPE_REGISTRY.values()
    ]