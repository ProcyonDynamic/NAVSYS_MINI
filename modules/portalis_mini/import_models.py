from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImportRequest:
    source_path: str
    document_type: str
    declared_entity_kind: Optional[str] = None
    declared_entity_id: Optional[str] = None
    notes: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ImportStoredFile:
    original_path: str
    stored_path: str
    file_name: str
    extension: str
    file_size_bytes: int
    sha256: str


@dataclass
class ImportExtractionResult:
    ok: bool
    parser_key: Optional[str] = None
    confidence: float = 0.0
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    raw_text_path: Optional[str] = None
    structured_output_path: Optional[str] = None


@dataclass
class ImportResult:
    ok: bool
    import_id: str
    manifest_path: Optional[str] = None
    stored_file: Optional[ImportStoredFile] = None
    extraction: Optional[ImportExtractionResult] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)