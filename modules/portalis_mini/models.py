from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional


EntityType = Literal["crew", "vessel", "voyage", "port", "document", "certificate", "system"]
DocumentStatus = Literal[
    "active",
    "expired",
    "superseded",
    "draft",
    "incomplete",
    "awaiting_review",
    "rejected",
    "archived",
]
RendererType = Literal["word", "excel", "pdf", "text", "email"]
ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(slots=True)
class AuditMeta:
    source_file: Optional[str] = None
    source_type: Optional[str] = None
    ingested_at: Optional[datetime] = None
    ingested_by: Optional[str] = None
    ingest_method: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[ConfidenceLevel] = None
    review_required: bool = False
    review_notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class VesselRecord:
    vessel_id: str
    name: str
    imo_number: Optional[str] = None
    call_sign: Optional[str] = None
    flag_state: Optional[str] = None
    vessel_type: Optional[str] = None
    gross_tonnage: Optional[float] = None
    net_tonnage: Optional[float] = None
    deadweight: Optional[float] = None
    owner_name: Optional[str] = None
    operator_name: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class IdentityDocument:
    document_type: str
    number: Optional[str] = None
    issuing_state: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    nationality: Optional[str] = None
    original_or_copy: Optional[str] = None
    notes: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class VaccinationRecord:
    vaccine_name: Optional[str] = None
    dose_count: Optional[int] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    certificate_number: Optional[str] = None
    issuer: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class ContractRecord:
    contract_id: str
    employer: Optional[str] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    duration_days: Optional[int] = None
    position: Optional[str] = None
    status: Optional[str] = None
    source_document_id: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class CrewRecord:
    crew_id: str
    rank: Optional[str]
    family_name: str
    given_name: str
    middle_initial: Optional[str] = None
    full_middle_name: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    nationality_code: Optional[str] = None
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    country_of_birth: Optional[str] = None
    age: Optional[int] = None
    active_status: str = "active"
    date_sea_signed: Optional[date] = None
    sign_on_date: Optional[date] = None
    sign_off_date: Optional[date] = None
    passports: List[IdentityDocument] = field(default_factory=list)
    seaman_books: List[IdentityDocument] = field(default_factory=list)
    visas: List[IdentityDocument] = field(default_factory=list)
    vaccinations: List[VaccinationRecord] = field(default_factory=list)
    contracts: List[ContractRecord] = field(default_factory=list)
    notes: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)

    @property
    def display_name(self) -> str:
        parts = [self.family_name, self.given_name]
        if self.middle_initial:
            parts.append(self.middle_initial)
        return " ".join(part for part in parts if part)


@dataclass(slots=True)
class VoyageContext:
    voyage_id: str
    vessel_id: str
    voyage_number: Optional[str] = None
    current_port: Optional[str] = None
    last_port: Optional[str] = None
    next_port: Optional[str] = None
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    eta: Optional[datetime] = None
    etd: Optional[datetime] = None
    reason_of_call: Optional[str] = None
    period_of_stay: Optional[str] = None
    unlocode: Optional[str] = None
    ship_security_level: Optional[str] = None
    port_security_level: Optional[str] = None
    special_security_measures: Optional[str] = None
    persons_on_board: Optional[int] = None
    cargo_summary: Optional[str] = None
    draft_forward: Optional[float] = None
    draft_aft: Optional[float] = None
    draft_mean: Optional[float] = None
    last_10_ports: List[str] = field(default_factory=list)
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    display_name: str
    category_code: Optional[str] = None
    type_code: Optional[str] = None
    owner_entity_type: Optional[EntityType] = None
    owner_entity_id: Optional[str] = None
    file_path: Optional[str] = None
    file_hash_sha256: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: DocumentStatus = "active"
    source_document_id: Optional[str] = None
    duplicate_of_document_id: Optional[str] = None
    supersedes_document_id: Optional[str] = None
    superseded_by_document_id: Optional[str] = None
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class CertificateRecord:
    certificate_id: str
    canonical_name: str
    aliases: List[str] = field(default_factory=list)
    trigger_phrases: List[str] = field(default_factory=list)
    number: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    issuer: Optional[str] = None
    owner_entity_type: Optional[EntityType] = None
    owner_entity_id: Optional[str] = None
    source_document_id: Optional[str] = None
    status: DocumentStatus = "active"
    country_variant: Optional[str] = None
    notes: Optional[str] = None
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class FieldMappingRule:
    canonical_field: str
    target_field: str
    transform: Optional[str] = None
    required: bool = False
    default_value: Optional[str] = None
    notes: Optional[str] = None


@dataclass(slots=True)
class RendererDefinition:
    renderer_id: str
    display_name: str
    renderer_type: RendererType
    template_path: str
    output_extension: str
    description: Optional[str] = None
    required_fields: List[str] = field(default_factory=list)
    mapping_rules: List[FieldMappingRule] = field(default_factory=list)
    port_dependent: bool = False
    voyage_dependent: bool = False
    crew_dependent: bool = False
    certificate_trigger_enabled: bool = False
    active: bool = True
    audit: AuditMeta = field(default_factory=AuditMeta)


@dataclass(slots=True)
class ReviewItem:
    review_id: str
    entity_type: EntityType
    entity_id: str
    issue_type: str
    field_name: Optional[str] = None
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    confidence_score: Optional[float] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass(slots=True)
class GenerationResult:
    output_id: str
    renderer_id: str
    output_path: str
    generated_at: datetime
    source_entity_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    review_items: List[ReviewItem] = field(default_factory=list)


__all__ = [
    "AuditMeta",
    "CertificateRecord",
    "ConfidenceLevel",
    "ContractRecord",
    "CrewRecord",
    "DocumentRecord",
    "DocumentStatus",
    "EntityType",
    "FieldMappingRule",
    "GenerationResult",
    "IdentityDocument",
    "RendererDefinition",
    "RendererType",
    "ReviewItem",
    "VaccinationRecord",
    "VesselRecord",
    "VoyageContext",
]
