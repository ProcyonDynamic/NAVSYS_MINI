from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .archive.document_registry import DocumentRegistry
from .archive.import_service import DocumentImportService
from .import_models import ImportRequest, ImportResult, ImportStoredFile
from .import_utils import file_sha256, make_import_id
from .models import ReviewQueueItem, TCELiteEnvelope
from .storage import enqueue_review_item, utc_now_iso


def import_declared_document(req: ImportRequest, *, portalis_root: str | Path) -> ImportResult:
    root = Path(portalis_root)
    root.mkdir(parents=True, exist_ok=True)

    import_id = make_import_id()
    source_path = Path(req.source_path)

    if not source_path.exists():
        return ImportResult(
            ok=False,
            import_id=import_id,
            errors=[f"Source file not found: {source_path}"],
        )

    service = DocumentImportService(root)
    result = service.import_document(
        doc_type=req.document_type,
        source_file=source_path,
        owner_entity=req.declared_entity_kind or "",
        owner_id=req.declared_entity_id or "",
    )

    if not result.get("ok"):
        return ImportResult(
            ok=False,
            import_id=import_id,
            errors=list(result.get("errors", [])),
            warnings=list(result.get("warnings", [])),
        )

    document_id = result["document_id"]
    registry = DocumentRegistry(root)
    document_entry = registry.get_document(document_id) or {}
    tce_payload = document_entry.get("tce_lite") or {}

    manifest_path = _write_manifest(
        root=root,
        import_id=import_id,
        req=req,
        result=result,
        document_entry=document_entry,
    )

    review_required = bool(document_entry.get("review_required", False))
    if review_required:
        enqueue_review_item(
            root,
            ReviewQueueItem(
                document_id=document_id,
                review_required=True,
                review_reasons=list(document_entry.get("review_reasons", [])),
                parsed_fields=dict(document_entry.get("parsed_fields", {})),
                final_fields=dict(document_entry.get("final_fields", {})),
                accepted_fields=dict(document_entry.get("accepted_fields", {})),
                field_evidence=dict(document_entry.get("field_evidence", {})),
                field_validation=dict(document_entry.get("field_validation", {})),
                field_conflicts=dict(document_entry.get("field_conflicts", {})),
                field_confidence=dict(document_entry.get("field_confidence", {})),
                candidate_bundles=dict(document_entry.get("candidate_bundles", {})),
                compare_ledger=list(document_entry.get("compare_ledger", [])),
                accepted_candidate_refs=dict(document_entry.get("accepted_candidate_refs", {})),
                operator_overrides=dict(document_entry.get("operator_overrides", {})),
                field_statuses=dict(document_entry.get("field_statuses", {})),
                unresolved_fields=dict(document_entry.get("unresolved_fields", {})),
                field_policy=dict(document_entry.get("field_policy", {})),
                prioritized_field_queue=list(document_entry.get("prioritized_field_queue", [])),
                escalation_policy=dict(document_entry.get("escalation_policy", {})),
                triage_actions=list(document_entry.get("triage_actions", [])),
                triage_state=dict(document_entry.get("triage_state", {})),
                routing_hints=dict(document_entry.get("routing_hints", {})),
                assignment_actions=list(document_entry.get("assignment_actions", [])),
                assignment_state=dict(document_entry.get("assignment_state", {})),
                sla_policy=dict(document_entry.get("sla_policy", {})),
                watch_actions=list(document_entry.get("watch_actions", [])),
                watch_state=dict(document_entry.get("watch_state", {})),
                reminder_stage=dict(document_entry.get("reminder_stage", {})),
                reminder_actions=list(document_entry.get("reminder_actions", [])),
                notification_prep=dict(document_entry.get("notification_prep", {})),
                notification_ledger=dict(document_entry.get("notification_ledger", {})),
                delivery_attempts=dict(document_entry.get("delivery_attempts", {})),
                notification_actions=list(document_entry.get("notification_actions", [])),
                transport_requests=dict(document_entry.get("transport_requests", {})),
                transport_results=dict(document_entry.get("transport_results", {})),
                transport_actions=list(document_entry.get("transport_actions", [])),
                local_alerts=dict(document_entry.get("local_alerts", {})),
                alert_actions=list(document_entry.get("alert_actions", [])),
                incident_threads=dict(document_entry.get("incident_threads", {})),
                incident_actions=list(document_entry.get("incident_actions", [])),
                external_bridge_exports=dict(document_entry.get("external_bridge_exports", {})),
                external_bridge_results=dict(document_entry.get("external_bridge_results", {})),
                external_bridge_actions=list(document_entry.get("external_bridge_actions", [])),
                intake_contracts=dict(document_entry.get("intake_contracts", {})),
                intake_acks=dict(document_entry.get("intake_acks", {})),
                intake_actions=list(document_entry.get("intake_actions", [])),
                dropzone_handshakes=dict(document_entry.get("dropzone_handshakes", {})),
                dropzone_receipts=dict(document_entry.get("dropzone_receipts", {})),
                dropzone_receipt_history=dict(document_entry.get("dropzone_receipt_history", {})),
                dropzone_reconciliation=dict(document_entry.get("dropzone_reconciliation", {})),
                dropzone_recovery=dict(document_entry.get("dropzone_recovery", {})),
                dropzone_actions=list(document_entry.get("dropzone_actions", [])),
                status="PENDING",
                tce=TCELiteEnvelope(
                    WHAT=dict(tce_payload.get("WHAT", {})),
                    WHO=dict(tce_payload.get("WHO", {})),
                    WHEN=dict(tce_payload.get("WHEN", {})),
                    WHERE=dict(tce_payload.get("WHERE", {})),
                    HOW=dict(tce_payload.get("HOW", {})),
                    WHY=dict(tce_payload.get("WHY", {})),
                ),
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
            ),
        )

    stored_file_path = Path(result["stored_file"])
    stored_file = ImportStoredFile(
        original_path=str(source_path),
        stored_path=str(stored_file_path),
        file_name=stored_file_path.name,
        extension=stored_file_path.suffix.lower(),
        file_size_bytes=stored_file_path.stat().st_size,
        sha256=file_sha256(str(stored_file_path)),
    )

    return ImportResult(
        ok=True,
        import_id=import_id,
        manifest_path=str(manifest_path),
        stored_file=stored_file,
        extraction=None,
        errors=[],
        warnings=list(result.get("warnings", [])),
    )


def _write_manifest(
    *,
    root: Path,
    import_id: str,
    req: ImportRequest,
    result: dict,
    document_entry: dict,
) -> Path:
    manifest_dir = root / "import_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{import_id}.json"

    payload = {
        "import_id": import_id,
        "requested_at": utc_now_iso(),
        "request": asdict(req),
        "result": {
            "document_id": result.get("document_id"),
            "doc_type": result.get("doc_type"),
            "stored_file": result.get("stored_file"),
            "owner_entity": result.get("owner_entity"),
            "owner_id": result.get("owner_id"),
            "confidence": result.get("confidence"),
            "parsed_fields": result.get("parsed_fields") or {},
            "field_evidence": result.get("field_evidence") or {},
            "field_validation": result.get("field_validation") or {},
            "field_conflicts": result.get("field_conflicts") or {},
            "field_confidence": result.get("field_confidence") or {},
            "candidate_bundles": result.get("candidate_bundles") or {},
            "compare_ledger": result.get("compare_ledger") or [],
            "accepted_candidate_refs": result.get("accepted_candidate_refs") or {},
            "operator_overrides": result.get("operator_overrides") or {},
            "field_statuses": result.get("field_statuses") or {},
            "unresolved_fields": result.get("unresolved_fields") or {},
            "field_policy": result.get("field_policy") or {},
            "prioritized_field_queue": result.get("prioritized_field_queue") or [],
            "escalation_policy": result.get("escalation_policy") or {},
            "triage_actions": result.get("triage_actions") or [],
            "triage_state": result.get("triage_state") or {},
            "routing_hints": result.get("routing_hints") or {},
            "assignment_actions": result.get("assignment_actions") or [],
            "assignment_state": result.get("assignment_state") or {},
            "sla_policy": result.get("sla_policy") or {},
            "watch_actions": result.get("watch_actions") or [],
            "watch_state": result.get("watch_state") or {},
            "reminder_stage": result.get("reminder_stage") or {},
            "reminder_actions": result.get("reminder_actions") or [],
            "notification_prep": result.get("notification_prep") or {},
            "notification_ledger": result.get("notification_ledger") or {},
            "delivery_attempts": result.get("delivery_attempts") or {},
            "notification_actions": result.get("notification_actions") or [],
            "transport_requests": result.get("transport_requests") or {},
            "transport_results": result.get("transport_results") or {},
            "transport_actions": result.get("transport_actions") or [],
            "local_alerts": result.get("local_alerts") or {},
            "alert_actions": result.get("alert_actions") or [],
            "incident_threads": result.get("incident_threads") or {},
            "incident_actions": result.get("incident_actions") or [],
            "external_bridge_exports": result.get("external_bridge_exports") or {},
            "external_bridge_results": result.get("external_bridge_results") or {},
            "external_bridge_actions": result.get("external_bridge_actions") or [],
            "intake_contracts": result.get("intake_contracts") or {},
            "intake_acks": result.get("intake_acks") or {},
            "intake_actions": result.get("intake_actions") or [],
            "dropzone_handshakes": result.get("dropzone_handshakes") or {},
            "dropzone_receipts": result.get("dropzone_receipts") or {},
            "dropzone_receipt_history": result.get("dropzone_receipt_history") or {},
            "dropzone_reconciliation": result.get("dropzone_reconciliation") or {},
            "dropzone_recovery": result.get("dropzone_recovery") or {},
            "dropzone_actions": result.get("dropzone_actions") or [],
            "review_required": bool(result.get("review_required", False)),
            "review_reasons": list(result.get("review_reasons", [])),
            "warnings": list(result.get("warnings", [])),
            "crew_record_path": result.get("crew_record_path"),
            "crew_update_error": result.get("crew_update_error"),
        },
        "document_entry": document_entry,
    }

    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path
