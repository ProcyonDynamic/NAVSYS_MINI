from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    CertificateVaultState,
    CrewRegistryState,
    DocumentRegistryState,
    DocumentStatusRecord,
    GeneratedOutputRecord,
    PortRequirementsState,
    PortalisState,
    ReviewQueueItem,
    ReviewQueueState,
    TCELiteEnvelope,
    VesselRecord,
    VoyageRecord,
    default_document_statuses,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_portalis_state(json_path: str) -> PortalisState:
    path = Path(json_path)
    if not path.exists():
        return PortalisState(documents=default_document_statuses())

    data = json.loads(path.read_text(encoding="utf-8"))
    return _state_from_payload(data)


def save_portalis_state(state: PortalisState, json_path: str) -> None:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_review_queue(portalis_root: str | Path) -> List[ReviewQueueItem]:
    path = _review_queue_path(portalis_root)
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    items: List[ReviewQueueItem] = []

    for item in payload.get("items", []):
        tce_payload = item.get("tce") or {}
        items.append(
            ReviewQueueItem(
                document_id=item.get("document_id", ""),
                review_required=bool(item.get("review_required", False)),
                review_reasons=list(item.get("review_reasons", [])),
                parsed_fields=dict(item.get("parsed_fields", {})),
                final_fields=dict(item.get("final_fields", {})),
                accepted_fields=dict(item.get("accepted_fields", {})),
                field_evidence=dict(item.get("field_evidence", {})),
                field_validation=dict(item.get("field_validation", {})),
                field_conflicts=dict(item.get("field_conflicts", {})),
                field_confidence=dict(item.get("field_confidence", {})),
                candidate_bundles=dict(item.get("candidate_bundles", {})),
                compare_ledger=list(item.get("compare_ledger", [])),
                accepted_candidate_refs=dict(item.get("accepted_candidate_refs", {})),
                operator_overrides=dict(item.get("operator_overrides", {})),
                field_statuses=dict(item.get("field_statuses", {})),
                unresolved_fields=dict(item.get("unresolved_fields", {})),
                field_policy=dict(item.get("field_policy", {})),
                prioritized_field_queue=list(item.get("prioritized_field_queue", [])),
                escalation_policy=dict(item.get("escalation_policy", {})),
                triage_actions=list(item.get("triage_actions", [])),
                triage_state=dict(item.get("triage_state", {})),
                routing_hints=dict(item.get("routing_hints", {})),
                assignment_actions=list(item.get("assignment_actions", [])),
                assignment_state=dict(item.get("assignment_state", {})),
                sla_policy=dict(item.get("sla_policy", {})),
                watch_actions=list(item.get("watch_actions", [])),
                watch_state=dict(item.get("watch_state", {})),
                reminder_stage=dict(item.get("reminder_stage", {})),
                reminder_actions=list(item.get("reminder_actions", [])),
                notification_prep=dict(item.get("notification_prep", {})),
                notification_ledger=dict(item.get("notification_ledger", {})),
                delivery_attempts=dict(item.get("delivery_attempts", {})),
                notification_actions=list(item.get("notification_actions", [])),
                transport_requests=dict(item.get("transport_requests", {})),
                transport_results=dict(item.get("transport_results", {})),
                transport_actions=list(item.get("transport_actions", [])),
                local_alerts=dict(item.get("local_alerts", {})),
                alert_actions=list(item.get("alert_actions", [])),
                incident_threads=dict(item.get("incident_threads", {})),
                incident_actions=list(item.get("incident_actions", [])),
                external_bridge_exports=dict(item.get("external_bridge_exports", {})),
                external_bridge_results=dict(item.get("external_bridge_results", {})),
                external_bridge_actions=list(item.get("external_bridge_actions", [])),
                status=item.get("status", "PENDING"),
                tce=TCELiteEnvelope(
                    WHAT=dict(tce_payload.get("WHAT", {})),
                    WHO=dict(tce_payload.get("WHO", {})),
                    WHEN=dict(tce_payload.get("WHEN", {})),
                    WHERE=dict(tce_payload.get("WHERE", {})),
                    HOW=dict(tce_payload.get("HOW", {})),
                    WHY=dict(tce_payload.get("WHY", {})),
                ),
                resolution_reason=item.get("resolution_reason", ""),
                resolved_by=item.get("resolved_by", ""),
                created_at=item.get("created_at", ""),
                updated_at=item.get("updated_at", ""),
            )
        )

    return items


def save_review_queue(portalis_root: str | Path, items: List[ReviewQueueItem]) -> None:
    path = _review_queue_path(portalis_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"items": [asdict(item) for item in items]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def enqueue_review_item(portalis_root: str | Path, item: ReviewQueueItem) -> None:
    items = load_review_queue(portalis_root)
    replaced = False

    for idx, existing in enumerate(items):
        if existing.document_id == item.document_id:
            items[idx] = item
            replaced = True
            break

    if not replaced:
        items.append(item)

    save_review_queue(portalis_root, items)


def build_portalis_state_snapshot(
    state: PortalisState,
    *,
    crew_count: int,
    certificate_count: int,
    port_count: int,
    document_count: int,
    review_items: List[ReviewQueueItem],
) -> PortalisState:
    state.crew_registry.total_crew = crew_count
    state.certificate_vault.total_certificates = certificate_count
    state.port_requirements.total_ports = port_count
    state.document_registry.total_documents = document_count
    state.review_queue.total_items = len(review_items)
    state.review_queue.pending_items = len([item for item in review_items if item.status == "PENDING"])
    return state


def append_generated_output(
    state: PortalisState,
    *,
    category: str,
    output_path: str,
    generated_at: str | None = None,
) -> PortalisState:
    state.generated_outputs.append(
        GeneratedOutputRecord(
            category=category,
            output_path=output_path,
            generated_at=generated_at or utc_now_iso(),
        )
    )
    return state


def _review_queue_path(portalis_root: str | Path) -> Path:
    return Path(portalis_root) / "review_queue.json"


def _state_from_payload(data: Dict[str, Any]) -> PortalisState:
    vessel_payload = _normalize_vessel_payload(data.get("vessel") or {})
    voyage_payload = _normalize_voyage_payload(data.get("voyage") or {})

    documents_payload = data.get("documents") or []
    documents = [_document_status_from_payload(item) for item in documents_payload] or default_document_statuses()

    generated_outputs = [
        GeneratedOutputRecord(
            category=str(item.get("category", "")),
            output_path=str(item.get("output_path", "")),
            generated_at=str(item.get("generated_at", "")),
        )
        for item in (data.get("generated_outputs") or [])
    ]

    return PortalisState(
        vessel=VesselRecord(**vessel_payload),
        voyage=VoyageRecord(**voyage_payload),
        documents=documents,
        crew_registry=_dataclass_from_payload(CrewRegistryState, data.get("crew_registry")),
        certificate_vault=_dataclass_from_payload(CertificateVaultState, data.get("certificate_vault")),
        port_requirements=_dataclass_from_payload(PortRequirementsState, data.get("port_requirements")),
        document_registry=_dataclass_from_payload(DocumentRegistryState, data.get("document_registry")),
        review_queue=_dataclass_from_payload(ReviewQueueState, data.get("review_queue")),
        generated_outputs=generated_outputs,
    )


def _normalize_vessel_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    vessel = dict(payload)

    aliases = {
        "ship_name": "name",
        "imo": "imo_number",
        "flag": "flag_state",
        "operator": "operator_name",
        "manager": "owner_name",
    }
    for old_key, new_key in aliases.items():
        if old_key in vessel and new_key not in vessel:
            vessel[new_key] = vessel.pop(old_key)

    allowed_keys = set(VesselRecord.__dataclass_fields__.keys())
    normalized = {key: vessel.get(key) for key in allowed_keys if key in vessel}
    normalized.setdefault("vessel_id", "default_vessel")
    normalized.setdefault("name", "")
    return normalized


def _normalize_voyage_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    voyage = dict(payload)

    aliases = {
        "voyage_no": "voyage_number",
        "port_from": "departure_port",
        "port_to": "arrival_port",
    }
    for old_key, new_key in aliases.items():
        if old_key in voyage and new_key not in voyage:
            voyage[new_key] = voyage.pop(old_key)

    allowed_keys = set(VoyageRecord.__dataclass_fields__.keys())
    normalized = {key: voyage.get(key) for key in allowed_keys if key in voyage}
    normalized.setdefault("voyage_id", "default_voyage")
    normalized.setdefault("voyage_number", "")
    normalized.setdefault("departure_port", "")
    normalized.setdefault("arrival_port", "")
    normalized.setdefault("eta", "")
    normalized.setdefault("etb", "")
    normalized.setdefault("etc", "")
    normalized.setdefault("cargo_summary", "")
    normalized.setdefault("port_history", "")
    normalized.setdefault("current_port", normalized.get("arrival_port", ""))
    normalized.setdefault("next_port", "")
    return normalized


def _document_status_from_payload(payload: Dict[str, Any]) -> DocumentStatusRecord:
    item = dict(payload or {})
    if "status" not in item:
        item["status"] = "complete" if item.get("sent") else "pending"

    allowed_keys = set(DocumentStatusRecord.__dataclass_fields__.keys())
    normalized = {key: item.get(key) for key in allowed_keys if key in item}
    normalized.setdefault("doc_name", "")
    normalized.setdefault("required", False)
    normalized.setdefault("filled", False)
    normalized.setdefault("printed", False)
    normalized.setdefault("signed", False)
    normalized.setdefault("recorded", False)
    normalized.setdefault("sent", False)
    normalized.setdefault("status", "pending")
    normalized.setdefault("notes", "")
    return DocumentStatusRecord(**normalized)


def _dataclass_from_payload(cls, payload: Dict[str, Any] | None):
    payload = payload or {}
    allowed_keys = set(cls.__dataclass_fields__.keys())
    normalized = {key: payload.get(key) for key in allowed_keys if key in payload}
    return cls(**normalized)
