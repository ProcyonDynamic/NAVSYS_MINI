from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ReviewStatus = str


@dataclass(slots=True)
class VesselRecord:
    vessel_id: str = "default_vessel"
    name: str = ""
    imo_number: Optional[str] = None
    call_sign: Optional[str] = None
    flag_state: Optional[str] = None
    vessel_type: Optional[str] = None
    gross_tonnage: Optional[float] = None
    net_tonnage: Optional[float] = None
    deadweight: Optional[float] = None
    owner_name: Optional[str] = None
    operator_name: Optional[str] = None


@dataclass(slots=True)
class VoyageRecord:
    voyage_id: str = "default_voyage"
    voyage_number: str = ""
    departure_port: str = ""
    arrival_port: str = ""
    eta: str = ""
    etb: str = ""
    etc: str = ""
    cargo_summary: str = ""
    port_history: str = ""
    current_port: str = ""
    next_port: str = ""


@dataclass(slots=True)
class DocumentStatusRecord:
    doc_name: str
    required: bool = False
    filled: bool = False
    printed: bool = False
    signed: bool = False
    recorded: bool = False
    sent: bool = False
    status: str = "pending"
    notes: str = ""


@dataclass(slots=True)
class CrewRegistryState:
    selected_crew_id: Optional[str] = None
    total_crew: int = 0
    last_created_crew_id: Optional[str] = None


@dataclass(slots=True)
class CertificateVaultState:
    total_certificates: int = 0
    last_updated_certificate: Optional[str] = None


@dataclass(slots=True)
class PortRequirementsState:
    selected_port_name: Optional[str] = None
    total_ports: int = 0


@dataclass(slots=True)
class DocumentRegistryState:
    total_documents: int = 0
    last_import_document_id: Optional[str] = None
    last_import_manifest_path: Optional[str] = None


@dataclass(slots=True)
class ReviewQueueState:
    total_items: int = 0
    pending_items: int = 0
    last_document_id: Optional[str] = None


@dataclass(slots=True)
class GeneratedOutputRecord:
    category: str
    output_path: str
    generated_at: str


@dataclass(slots=True)
class TCELiteEnvelope:
    WHAT: Dict[str, Any] = field(default_factory=dict)
    WHO: Dict[str, Any] = field(default_factory=dict)
    WHEN: Dict[str, Any] = field(default_factory=dict)
    WHERE: Dict[str, Any] = field(default_factory=dict)
    HOW: Dict[str, Any] = field(default_factory=dict)
    WHY: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReviewQueueItem:
    document_id: str
    review_required: bool
    review_reasons: List[str] = field(default_factory=list)
    parsed_fields: Dict[str, Any] = field(default_factory=dict)
    final_fields: Dict[str, Any] = field(default_factory=dict)
    accepted_fields: Dict[str, Any] = field(default_factory=dict)
    field_evidence: Dict[str, Any] = field(default_factory=dict)
    field_validation: Dict[str, Any] = field(default_factory=dict)
    field_conflicts: Dict[str, Any] = field(default_factory=dict)
    field_confidence: Dict[str, Any] = field(default_factory=dict)
    candidate_bundles: Dict[str, Any] = field(default_factory=dict)
    compare_ledger: List[Dict[str, Any]] = field(default_factory=list)
    accepted_candidate_refs: Dict[str, Any] = field(default_factory=dict)
    operator_overrides: Dict[str, Any] = field(default_factory=dict)
    field_statuses: Dict[str, Any] = field(default_factory=dict)
    unresolved_fields: Dict[str, Any] = field(default_factory=dict)
    field_policy: Dict[str, Any] = field(default_factory=dict)
    prioritized_field_queue: List[Dict[str, Any]] = field(default_factory=list)
    escalation_policy: Dict[str, Any] = field(default_factory=dict)
    triage_actions: List[Dict[str, Any]] = field(default_factory=list)
    triage_state: Dict[str, Any] = field(default_factory=dict)
    routing_hints: Dict[str, Any] = field(default_factory=dict)
    assignment_actions: List[Dict[str, Any]] = field(default_factory=list)
    assignment_state: Dict[str, Any] = field(default_factory=dict)
    sla_policy: Dict[str, Any] = field(default_factory=dict)
    watch_actions: List[Dict[str, Any]] = field(default_factory=list)
    watch_state: Dict[str, Any] = field(default_factory=dict)
    reminder_stage: Dict[str, Any] = field(default_factory=dict)
    reminder_actions: List[Dict[str, Any]] = field(default_factory=list)
    notification_prep: Dict[str, Any] = field(default_factory=dict)
    notification_ledger: Dict[str, Any] = field(default_factory=dict)
    delivery_attempts: Dict[str, Any] = field(default_factory=dict)
    notification_actions: List[Dict[str, Any]] = field(default_factory=list)
    transport_requests: Dict[str, Any] = field(default_factory=dict)
    transport_results: Dict[str, Any] = field(default_factory=dict)
    transport_actions: List[Dict[str, Any]] = field(default_factory=list)
    local_alerts: Dict[str, Any] = field(default_factory=dict)
    alert_actions: List[Dict[str, Any]] = field(default_factory=list)
    incident_threads: Dict[str, Any] = field(default_factory=dict)
    incident_actions: List[Dict[str, Any]] = field(default_factory=list)
    external_bridge_exports: Dict[str, Any] = field(default_factory=dict)
    external_bridge_results: Dict[str, Any] = field(default_factory=dict)
    external_bridge_actions: List[Dict[str, Any]] = field(default_factory=list)
    intake_contracts: Dict[str, Any] = field(default_factory=dict)
    intake_acks: Dict[str, Any] = field(default_factory=dict)
    intake_actions: List[Dict[str, Any]] = field(default_factory=list)
    status: ReviewStatus = "PENDING"
    tce: TCELiteEnvelope = field(default_factory=TCELiteEnvelope)
    resolution_reason: str = ""
    resolved_by: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class PortalisState:
    vessel: VesselRecord = field(default_factory=VesselRecord)
    voyage: VoyageRecord = field(default_factory=VoyageRecord)
    documents: List[DocumentStatusRecord] = field(default_factory=list)
    crew_registry: CrewRegistryState = field(default_factory=CrewRegistryState)
    certificate_vault: CertificateVaultState = field(default_factory=CertificateVaultState)
    port_requirements: PortRequirementsState = field(default_factory=PortRequirementsState)
    document_registry: DocumentRegistryState = field(default_factory=DocumentRegistryState)
    review_queue: ReviewQueueState = field(default_factory=ReviewQueueState)
    generated_outputs: List[GeneratedOutputRecord] = field(default_factory=list)


def default_document_statuses() -> List[DocumentStatusRecord]:
    return [
        DocumentStatusRecord(doc_name="Crew List", required=True),
        DocumentStatusRecord(doc_name="Maritime Declaration of Health", required=True),
        DocumentStatusRecord(doc_name="Port Requirement Checklist", required=True),
        DocumentStatusRecord(doc_name="Certificate Pack", required=False),
    ]
