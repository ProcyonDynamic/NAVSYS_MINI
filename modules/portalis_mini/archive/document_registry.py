from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any


class DocumentRegistry:

    def __init__(self, root_dir: Path):

        self.root_dir = root_dir
        self.registry_path = root_dir / "registry" / "document_registry.json"

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self._save_registry({"documents": []})

    def register_document(
        self,
        doc_type: str,
        owner_entity: str,
        owner_id: str,
        source_file: Path,
        parsed_fields: Dict[str, Any],
        confidence: float,
        review_required: bool = False,
        review_reasons: list[str] | None = None,
        warnings: list[str] | None = None,
        field_evidence: Dict[str, Any] | None = None,
        field_validation: Dict[str, Any] | None = None,
        field_conflicts: Dict[str, Any] | None = None,
        field_confidence: Dict[str, Any] | None = None,
        candidate_bundles: Dict[str, Any] | None = None,
        compare_ledger: list[Dict[str, Any]] | None = None,
        accepted_candidate_refs: Dict[str, Any] | None = None,
        operator_overrides: Dict[str, Any] | None = None,
        field_statuses: Dict[str, Any] | None = None,
        unresolved_fields: Dict[str, Any] | None = None,
        field_policy: Dict[str, Any] | None = None,
        prioritized_field_queue: list[Dict[str, Any]] | None = None,
        escalation_policy: Dict[str, Any] | None = None,
        triage_actions: list[Dict[str, Any]] | None = None,
        triage_state: Dict[str, Any] | None = None,
        routing_hints: Dict[str, Any] | None = None,
        assignment_actions: list[Dict[str, Any]] | None = None,
        assignment_state: Dict[str, Any] | None = None,
        sla_policy: Dict[str, Any] | None = None,
        watch_actions: list[Dict[str, Any]] | None = None,
        watch_state: Dict[str, Any] | None = None,
        reminder_stage: Dict[str, Any] | None = None,
        reminder_actions: list[Dict[str, Any]] | None = None,
        notification_prep: Dict[str, Any] | None = None,
        notification_ledger: Dict[str, Any] | None = None,
        delivery_attempts: Dict[str, Any] | None = None,
        notification_actions: list[Dict[str, Any]] | None = None,
        transport_requests: Dict[str, Any] | None = None,
        transport_results: Dict[str, Any] | None = None,
        transport_actions: list[Dict[str, Any]] | None = None,
        local_alerts: Dict[str, Any] | None = None,
        alert_actions: list[Dict[str, Any]] | None = None,
        incident_threads: Dict[str, Any] | None = None,
        incident_actions: list[Dict[str, Any]] | None = None,
        external_bridge_exports: Dict[str, Any] | None = None,
        external_bridge_results: Dict[str, Any] | None = None,
        external_bridge_actions: list[Dict[str, Any]] | None = None,
        intake_contracts: Dict[str, Any] | None = None,
        intake_acks: Dict[str, Any] | None = None,
        intake_actions: list[Dict[str, Any]] | None = None,
        dropzone_handshakes: Dict[str, Any] | None = None,
        dropzone_receipts: Dict[str, Any] | None = None,
        dropzone_receipt_history: Dict[str, Any] | None = None,
        dropzone_reconciliation: Dict[str, Any] | None = None,
        dropzone_recovery: Dict[str, Any] | None = None,
        dropzone_actions: list[Dict[str, Any]] | None = None,
        workbench_notes: str | None = None,
        workbench_status: str | None = None,
        workbench_tags: list[str] | None = None,
        workbench_history: list[Dict[str, Any]] | None = None,
        workbench_anchors: list[Dict[str, Any]] | None = None,
        workbench_anchor_history: list[Dict[str, Any]] | None = None,
        workbench_annotations: list[Dict[str, Any]] | None = None,
        workbench_annotation_history: list[Dict[str, Any]] | None = None,
        workbench_scratchpad: list[Dict[str, Any]] | None = None,
        workbench_scratchpad_history: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_cells: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_blocks: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_history: list[Dict[str, Any]] | None = None,
        workbench_opened_at: str | None = None,
        workbench_updated_at: str | None = None,
        tce_lite: Dict[str, Any] | None = None,
        operational_reason: str | None = None,
        display_name: str | None = None,
        file_id: str | None = None,
    ) -> str:
        
        registry = self._load_registry()

        doc_id = f"DOC_{len(registry['documents'])+1:06d}"

        entry = {
            "document_id": doc_id,
            "doc_type": doc_type,
            "owner_entity": owner_entity,
            "owner_id": owner_id,
            "file_id": str(file_id or ""),
            "display_name": str(display_name or source_file.name or doc_id),
            "source_file": str(source_file),
            "parsed_fields": parsed_fields,
            "final_fields": {},
            "accepted_fields": {},
            "field_evidence": field_evidence or {},
            "field_validation": field_validation or {},
            "field_conflicts": field_conflicts or {},
            "field_confidence": field_confidence or {},
            "candidate_bundles": candidate_bundles or {},
            "compare_ledger": compare_ledger or [],
            "accepted_candidate_refs": accepted_candidate_refs or {},
            "operator_overrides": operator_overrides or {},
            "field_statuses": field_statuses or {},
            "unresolved_fields": unresolved_fields or {},
            "field_policy": field_policy or {},
            "prioritized_field_queue": prioritized_field_queue or [],
            "escalation_policy": escalation_policy or {},
            "triage_actions": triage_actions or [],
            "triage_state": triage_state or {},
            "routing_hints": routing_hints or {},
            "assignment_actions": assignment_actions or [],
            "assignment_state": assignment_state or {},
            "sla_policy": sla_policy or {},
            "watch_actions": watch_actions or [],
            "watch_state": watch_state or {},
            "reminder_stage": reminder_stage or {},
            "reminder_actions": reminder_actions or [],
            "notification_prep": notification_prep or {},
            "notification_ledger": notification_ledger or {},
            "delivery_attempts": delivery_attempts or {},
            "notification_actions": notification_actions or [],
            "transport_requests": transport_requests or {},
            "transport_results": transport_results or {},
            "transport_actions": transport_actions or [],
            "local_alerts": local_alerts or {},
            "alert_actions": alert_actions or [],
            "incident_threads": incident_threads or {},
            "incident_actions": incident_actions or [],
            "external_bridge_exports": external_bridge_exports or {},
            "external_bridge_results": external_bridge_results or {},
            "external_bridge_actions": external_bridge_actions or [],
            "intake_contracts": intake_contracts or {},
            "intake_acks": intake_acks or {},
            "intake_actions": intake_actions or [],
            "dropzone_handshakes": dropzone_handshakes or {},
            "dropzone_receipts": dropzone_receipts or {},
            "dropzone_receipt_history": dropzone_receipt_history or {},
            "dropzone_reconciliation": dropzone_reconciliation or {},
            "dropzone_recovery": dropzone_recovery or {},
            "dropzone_actions": dropzone_actions or [],
            "workbench_notes": workbench_notes or "",
            "workbench_status": workbench_status or "STORED",
            "workbench_tags": workbench_tags or [],
            "workbench_history": workbench_history or [],
            "workbench_anchors": workbench_anchors or [],
            "workbench_anchor_history": workbench_anchor_history or [],
            "workbench_annotations": workbench_annotations or [],
            "workbench_annotation_history": workbench_annotation_history or [],
            "workbench_scratchpad": workbench_scratchpad or [],
            "workbench_scratchpad_history": workbench_scratchpad_history or [],
            "workbench_reconstruction_cells": workbench_reconstruction_cells or [],
            "workbench_reconstruction_blocks": workbench_reconstruction_blocks or [],
            "workbench_reconstruction_history": workbench_reconstruction_history or [],
            "workbench_opened_at": workbench_opened_at or "",
            "workbench_updated_at": workbench_updated_at or "",
            "confidence": confidence,
            "review_required": review_required,
            "review_status": "PENDING" if review_required else "ACCEPTED",
            "review_reasons": review_reasons or [],
            "warnings": warnings or [],
            "tce_lite": tce_lite or {},
            "operational_reason": operational_reason or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        registry["documents"].append(entry)

        self._save_registry(registry)

        return doc_id

    def _load_registry(self):

        if not self.registry_path.exists():
            return {"documents": []}

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {"documents": []}

        if "documents" not in data or not isinstance(data["documents"], list):
            data["documents"] = []

        return data
    
    def _save_registry(self, registry):

        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            
    def list_documents(self) -> list[Dict[str, Any]]:
        registry = self._load_registry()
        return registry.get("documents", [])
    
    def get_document(self, document_id: str) -> Dict[str, Any] | None:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") == document_id:
                return entry

        return None

    def duplicate_document(self, document_id: str, *, new_display_name: str = "") -> str:
        entry = self.get_document(document_id)
        if not entry:
            raise KeyError(f"Document not found: {document_id}")

        source_path = Path(str(entry.get("source_file") or ""))
        target_path = source_path
        if source_path.exists():
            target_dir = source_path.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            stem = source_path.stem
            suffix = source_path.suffix
            candidate = target_dir / f"{stem}_copy{suffix}"
            counter = 1
            while candidate.exists():
                counter += 1
                candidate = target_dir / f"{stem}_copy_{counter}{suffix}"
            shutil.copy2(source_path, candidate)
            target_path = candidate

        return self.register_document(
            doc_type=str(entry.get("doc_type") or "document"),
            owner_entity=str(entry.get("owner_entity") or ""),
            owner_id=str(entry.get("owner_id") or ""),
            source_file=target_path,
            display_name=str(new_display_name or entry.get("display_name") or target_path.name),
            parsed_fields=dict(entry.get("parsed_fields") or {}),
            confidence=float(entry.get("confidence") or 0.0),
            review_required=bool(entry.get("review_required", False)),
            review_reasons=list(entry.get("review_reasons") or []),
            warnings=list(entry.get("warnings") or []),
            field_evidence=dict(entry.get("field_evidence") or {}),
            field_validation=dict(entry.get("field_validation") or {}),
            field_conflicts=dict(entry.get("field_conflicts") or {}),
            field_confidence=dict(entry.get("field_confidence") or {}),
            candidate_bundles=dict(entry.get("candidate_bundles") or {}),
            compare_ledger=list(entry.get("compare_ledger") or []),
            accepted_candidate_refs=dict(entry.get("accepted_candidate_refs") or {}),
            operator_overrides=dict(entry.get("operator_overrides") or {}),
            field_statuses=dict(entry.get("field_statuses") or {}),
            unresolved_fields=dict(entry.get("unresolved_fields") or {}),
            field_policy=dict(entry.get("field_policy") or {}),
            prioritized_field_queue=list(entry.get("prioritized_field_queue") or []),
            escalation_policy=dict(entry.get("escalation_policy") or {}),
            triage_actions=list(entry.get("triage_actions") or []),
            triage_state=dict(entry.get("triage_state") or {}),
            routing_hints=dict(entry.get("routing_hints") or {}),
            assignment_actions=list(entry.get("assignment_actions") or []),
            assignment_state=dict(entry.get("assignment_state") or {}),
            sla_policy=dict(entry.get("sla_policy") or {}),
            watch_actions=list(entry.get("watch_actions") or []),
            watch_state=dict(entry.get("watch_state") or {}),
            reminder_stage=dict(entry.get("reminder_stage") or {}),
            reminder_actions=list(entry.get("reminder_actions") or []),
            notification_prep=dict(entry.get("notification_prep") or {}),
            notification_ledger=dict(entry.get("notification_ledger") or {}),
            delivery_attempts=dict(entry.get("delivery_attempts") or {}),
            notification_actions=list(entry.get("notification_actions") or []),
            transport_requests=dict(entry.get("transport_requests") or {}),
            transport_results=dict(entry.get("transport_results") or {}),
            transport_actions=list(entry.get("transport_actions") or []),
            local_alerts=dict(entry.get("local_alerts") or {}),
            alert_actions=list(entry.get("alert_actions") or []),
            incident_threads=dict(entry.get("incident_threads") or {}),
            incident_actions=list(entry.get("incident_actions") or []),
            external_bridge_exports=dict(entry.get("external_bridge_exports") or {}),
            external_bridge_results=dict(entry.get("external_bridge_results") or {}),
            external_bridge_actions=list(entry.get("external_bridge_actions") or []),
            intake_contracts=dict(entry.get("intake_contracts") or {}),
            intake_acks=dict(entry.get("intake_acks") or {}),
            intake_actions=list(entry.get("intake_actions") or []),
            dropzone_handshakes=dict(entry.get("dropzone_handshakes") or {}),
            dropzone_receipts=dict(entry.get("dropzone_receipts") or {}),
            dropzone_receipt_history=dict(entry.get("dropzone_receipt_history") or {}),
            dropzone_reconciliation=dict(entry.get("dropzone_reconciliation") or {}),
            dropzone_recovery=dict(entry.get("dropzone_recovery") or {}),
            dropzone_actions=list(entry.get("dropzone_actions") or []),
            workbench_notes=str(entry.get("workbench_notes") or ""),
            workbench_status=str(entry.get("workbench_status") or "STORED"),
            workbench_tags=list(entry.get("workbench_tags") or []),
            workbench_history=list(entry.get("workbench_history") or []),
            workbench_anchors=list(entry.get("workbench_anchors") or []),
            workbench_anchor_history=list(entry.get("workbench_anchor_history") or []),
            workbench_annotations=list(entry.get("workbench_annotations") or []),
            workbench_annotation_history=list(entry.get("workbench_annotation_history") or []),
            workbench_scratchpad=list(entry.get("workbench_scratchpad") or []),
            workbench_scratchpad_history=list(entry.get("workbench_scratchpad_history") or []),
            workbench_reconstruction_cells=list(entry.get("workbench_reconstruction_cells") or []),
            workbench_reconstruction_blocks=list(entry.get("workbench_reconstruction_blocks") or []),
            workbench_reconstruction_history=list(entry.get("workbench_reconstruction_history") or []),
            workbench_opened_at=str(entry.get("workbench_opened_at") or ""),
            workbench_updated_at=str(entry.get("workbench_updated_at") or ""),
            tce_lite=dict(entry.get("tce_lite") or {}),
            operational_reason=str(new_display_name or f"Duplicated from {document_id}"),
            file_id="",
        )

    def update_document_resolution(
        self,
        document_id: str,
        *,
        review_status: str,
        final_fields: Dict[str, Any],
        accepted_fields: Dict[str, Any],
        field_evidence: Dict[str, Any],
        field_validation: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_confidence: Dict[str, Any],
        candidate_bundles: Dict[str, Any],
        compare_ledger: list[Dict[str, Any]],
        accepted_candidate_refs: Dict[str, Any],
        operator_overrides: Dict[str, Any],
        field_statuses: Dict[str, Any],
        unresolved_fields: Dict[str, Any],
        field_policy: Dict[str, Any],
        prioritized_field_queue: list[Dict[str, Any]],
        escalation_policy: Dict[str, Any] | None = None,
        triage_actions: list[Dict[str, Any]] | None = None,
        triage_state: Dict[str, Any] | None = None,
        routing_hints: Dict[str, Any] | None = None,
        assignment_actions: list[Dict[str, Any]] | None = None,
        assignment_state: Dict[str, Any] | None = None,
        sla_policy: Dict[str, Any] | None = None,
        watch_actions: list[Dict[str, Any]] | None = None,
        watch_state: Dict[str, Any] | None = None,
        reminder_stage: Dict[str, Any] | None = None,
        reminder_actions: list[Dict[str, Any]] | None = None,
        notification_prep: Dict[str, Any] | None = None,
        notification_ledger: Dict[str, Any] | None = None,
        delivery_attempts: Dict[str, Any] | None = None,
        notification_actions: list[Dict[str, Any]] | None = None,
        transport_requests: Dict[str, Any] | None = None,
        transport_results: Dict[str, Any] | None = None,
        transport_actions: list[Dict[str, Any]] | None = None,
        local_alerts: Dict[str, Any] | None = None,
        alert_actions: list[Dict[str, Any]] | None = None,
        incident_threads: Dict[str, Any] | None = None,
        incident_actions: list[Dict[str, Any]] | None = None,
        external_bridge_exports: Dict[str, Any] | None = None,
        external_bridge_results: Dict[str, Any] | None = None,
        external_bridge_actions: list[Dict[str, Any]] | None = None,
        intake_contracts: Dict[str, Any] | None = None,
        intake_acks: Dict[str, Any] | None = None,
        intake_actions: list[Dict[str, Any]] | None = None,
        dropzone_handshakes: Dict[str, Any] | None = None,
        dropzone_receipts: Dict[str, Any] | None = None,
        dropzone_receipt_history: Dict[str, Any] | None = None,
        dropzone_reconciliation: Dict[str, Any] | None = None,
        dropzone_recovery: Dict[str, Any] | None = None,
        dropzone_actions: list[Dict[str, Any]] | None = None,
        resolved_by: str,
        resolved_at: str,
        resolution_reason: str,
        resolution_mode: str,
        tce_lite: Dict[str, Any],
    ) -> Dict[str, Any]:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") != document_id:
                continue

            entry["review_status"] = review_status
            entry["review_required"] = review_status == "PENDING"
            entry["final_fields"] = final_fields
            entry["accepted_fields"] = accepted_fields
            entry["field_evidence"] = field_evidence
            entry["field_validation"] = field_validation
            entry["field_conflicts"] = field_conflicts
            entry["field_confidence"] = field_confidence
            entry["candidate_bundles"] = candidate_bundles
            entry["compare_ledger"] = compare_ledger
            entry["accepted_candidate_refs"] = accepted_candidate_refs
            entry["operator_overrides"] = operator_overrides
            entry["field_statuses"] = field_statuses
            entry["unresolved_fields"] = unresolved_fields
            entry["field_policy"] = field_policy
            entry["prioritized_field_queue"] = prioritized_field_queue
            if escalation_policy is not None:
                entry["escalation_policy"] = escalation_policy
            if triage_actions is not None:
                entry["triage_actions"] = triage_actions
            if triage_state is not None:
                entry["triage_state"] = triage_state
            if routing_hints is not None:
                entry["routing_hints"] = routing_hints
            if assignment_actions is not None:
                entry["assignment_actions"] = assignment_actions
            if assignment_state is not None:
                entry["assignment_state"] = assignment_state
            if sla_policy is not None:
                entry["sla_policy"] = sla_policy
            if watch_actions is not None:
                entry["watch_actions"] = watch_actions
            if watch_state is not None:
                entry["watch_state"] = watch_state
            if reminder_stage is not None:
                entry["reminder_stage"] = reminder_stage
            if reminder_actions is not None:
                entry["reminder_actions"] = reminder_actions
            if notification_prep is not None:
                entry["notification_prep"] = notification_prep
            if notification_ledger is not None:
                entry["notification_ledger"] = notification_ledger
            if delivery_attempts is not None:
                entry["delivery_attempts"] = delivery_attempts
            if notification_actions is not None:
                entry["notification_actions"] = notification_actions
            if transport_requests is not None:
                entry["transport_requests"] = transport_requests
            if transport_results is not None:
                entry["transport_results"] = transport_results
            if transport_actions is not None:
                entry["transport_actions"] = transport_actions
            if local_alerts is not None:
                entry["local_alerts"] = local_alerts
            if alert_actions is not None:
                entry["alert_actions"] = alert_actions
            if incident_threads is not None:
                entry["incident_threads"] = incident_threads
            if incident_actions is not None:
                entry["incident_actions"] = incident_actions
            if external_bridge_exports is not None:
                entry["external_bridge_exports"] = external_bridge_exports
            if external_bridge_results is not None:
                entry["external_bridge_results"] = external_bridge_results
            if external_bridge_actions is not None:
                entry["external_bridge_actions"] = external_bridge_actions
            if intake_contracts is not None:
                entry["intake_contracts"] = intake_contracts
            if intake_acks is not None:
                entry["intake_acks"] = intake_acks
            if intake_actions is not None:
                entry["intake_actions"] = intake_actions
            if dropzone_handshakes is not None:
                entry["dropzone_handshakes"] = dropzone_handshakes
            if dropzone_receipts is not None:
                entry["dropzone_receipts"] = dropzone_receipts
            if dropzone_receipt_history is not None:
                entry["dropzone_receipt_history"] = dropzone_receipt_history
            if dropzone_reconciliation is not None:
                entry["dropzone_reconciliation"] = dropzone_reconciliation
            if dropzone_recovery is not None:
                entry["dropzone_recovery"] = dropzone_recovery
            if dropzone_actions is not None:
                entry["dropzone_actions"] = dropzone_actions
            entry["resolved_by"] = resolved_by
            entry["resolved_at"] = resolved_at
            entry["resolution_reason"] = resolution_reason
            entry["resolution_mode"] = resolution_mode
            entry["tce_lite"] = tce_lite

            self._save_registry(registry)
            return entry

        raise KeyError(f"Document not found: {document_id}")

    def update_document_qtr_artifacts(
        self,
        document_id: str,
        *,
        candidate_bundles: Dict[str, Any],
        compare_ledger: list[Dict[str, Any]],
        accepted_candidate_refs: Dict[str, Any],
        operator_overrides: Dict[str, Any],
        field_statuses: Dict[str, Any] | None = None,
        unresolved_fields: Dict[str, Any] | None = None,
        field_policy: Dict[str, Any] | None = None,
        prioritized_field_queue: list[Dict[str, Any]] | None = None,
        escalation_policy: Dict[str, Any] | None = None,
        triage_actions: list[Dict[str, Any]] | None = None,
        triage_state: Dict[str, Any] | None = None,
        routing_hints: Dict[str, Any] | None = None,
        assignment_actions: list[Dict[str, Any]] | None = None,
        assignment_state: Dict[str, Any] | None = None,
        sla_policy: Dict[str, Any] | None = None,
        watch_actions: list[Dict[str, Any]] | None = None,
        watch_state: Dict[str, Any] | None = None,
        reminder_stage: Dict[str, Any] | None = None,
        reminder_actions: list[Dict[str, Any]] | None = None,
        notification_prep: Dict[str, Any] | None = None,
        notification_ledger: Dict[str, Any] | None = None,
        delivery_attempts: Dict[str, Any] | None = None,
        notification_actions: list[Dict[str, Any]] | None = None,
        transport_requests: Dict[str, Any] | None = None,
        transport_results: Dict[str, Any] | None = None,
        transport_actions: list[Dict[str, Any]] | None = None,
        local_alerts: Dict[str, Any] | None = None,
        alert_actions: list[Dict[str, Any]] | None = None,
        incident_threads: Dict[str, Any] | None = None,
        incident_actions: list[Dict[str, Any]] | None = None,
        external_bridge_exports: Dict[str, Any] | None = None,
        external_bridge_results: Dict[str, Any] | None = None,
        external_bridge_actions: list[Dict[str, Any]] | None = None,
        intake_contracts: Dict[str, Any] | None = None,
        intake_acks: Dict[str, Any] | None = None,
        intake_actions: list[Dict[str, Any]] | None = None,
        dropzone_handshakes: Dict[str, Any] | None = None,
        dropzone_receipts: Dict[str, Any] | None = None,
        dropzone_receipt_history: Dict[str, Any] | None = None,
        dropzone_reconciliation: Dict[str, Any] | None = None,
        dropzone_recovery: Dict[str, Any] | None = None,
        dropzone_actions: list[Dict[str, Any]] | None = None,
        tce_lite: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") != document_id:
                continue

            entry["candidate_bundles"] = candidate_bundles
            entry["compare_ledger"] = compare_ledger
            entry["accepted_candidate_refs"] = accepted_candidate_refs
            entry["operator_overrides"] = operator_overrides
            if field_statuses is not None:
                entry["field_statuses"] = field_statuses
            if unresolved_fields is not None:
                entry["unresolved_fields"] = unresolved_fields
            if field_policy is not None:
                entry["field_policy"] = field_policy
            if prioritized_field_queue is not None:
                entry["prioritized_field_queue"] = prioritized_field_queue
            if escalation_policy is not None:
                entry["escalation_policy"] = escalation_policy
            if triage_actions is not None:
                entry["triage_actions"] = triage_actions
            if triage_state is not None:
                entry["triage_state"] = triage_state
            if routing_hints is not None:
                entry["routing_hints"] = routing_hints
            if assignment_actions is not None:
                entry["assignment_actions"] = assignment_actions
            if assignment_state is not None:
                entry["assignment_state"] = assignment_state
            if sla_policy is not None:
                entry["sla_policy"] = sla_policy
            if watch_actions is not None:
                entry["watch_actions"] = watch_actions
            if watch_state is not None:
                entry["watch_state"] = watch_state
            if reminder_stage is not None:
                entry["reminder_stage"] = reminder_stage
            if reminder_actions is not None:
                entry["reminder_actions"] = reminder_actions
            if notification_prep is not None:
                entry["notification_prep"] = notification_prep
            if notification_ledger is not None:
                entry["notification_ledger"] = notification_ledger
            if delivery_attempts is not None:
                entry["delivery_attempts"] = delivery_attempts
            if notification_actions is not None:
                entry["notification_actions"] = notification_actions
            if transport_requests is not None:
                entry["transport_requests"] = transport_requests
            if transport_results is not None:
                entry["transport_results"] = transport_results
            if transport_actions is not None:
                entry["transport_actions"] = transport_actions
            if local_alerts is not None:
                entry["local_alerts"] = local_alerts
            if alert_actions is not None:
                entry["alert_actions"] = alert_actions
            if incident_threads is not None:
                entry["incident_threads"] = incident_threads
            if incident_actions is not None:
                entry["incident_actions"] = incident_actions
            if external_bridge_exports is not None:
                entry["external_bridge_exports"] = external_bridge_exports
            if external_bridge_results is not None:
                entry["external_bridge_results"] = external_bridge_results
            if external_bridge_actions is not None:
                entry["external_bridge_actions"] = external_bridge_actions
            if intake_contracts is not None:
                entry["intake_contracts"] = intake_contracts
            if intake_acks is not None:
                entry["intake_acks"] = intake_acks
            if intake_actions is not None:
                entry["intake_actions"] = intake_actions
            if dropzone_handshakes is not None:
                entry["dropzone_handshakes"] = dropzone_handshakes
            if dropzone_receipts is not None:
                entry["dropzone_receipts"] = dropzone_receipts
            if dropzone_receipt_history is not None:
                entry["dropzone_receipt_history"] = dropzone_receipt_history
            if dropzone_reconciliation is not None:
                entry["dropzone_reconciliation"] = dropzone_reconciliation
            if dropzone_recovery is not None:
                entry["dropzone_recovery"] = dropzone_recovery
            if dropzone_actions is not None:
                entry["dropzone_actions"] = dropzone_actions
            if tce_lite is not None:
                entry["tce_lite"] = tce_lite

            self._save_registry(registry)
            return entry

        raise KeyError(f"Document not found: {document_id}")

    def update_document_control_room(
        self,
        document_id: str,
        *,
        escalation_policy: Dict[str, Any],
        triage_actions: list[Dict[str, Any]],
        triage_state: Dict[str, Any],
        routing_hints: Dict[str, Any] | None = None,
        assignment_actions: list[Dict[str, Any]] | None = None,
        assignment_state: Dict[str, Any] | None = None,
        sla_policy: Dict[str, Any] | None = None,
        watch_actions: list[Dict[str, Any]] | None = None,
        watch_state: Dict[str, Any] | None = None,
        reminder_stage: Dict[str, Any] | None = None,
        reminder_actions: list[Dict[str, Any]] | None = None,
        notification_prep: Dict[str, Any] | None = None,
        notification_ledger: Dict[str, Any] | None = None,
        delivery_attempts: Dict[str, Any] | None = None,
        notification_actions: list[Dict[str, Any]] | None = None,
        transport_requests: Dict[str, Any] | None = None,
        transport_results: Dict[str, Any] | None = None,
        transport_actions: list[Dict[str, Any]] | None = None,
        local_alerts: Dict[str, Any] | None = None,
        alert_actions: list[Dict[str, Any]] | None = None,
        incident_threads: Dict[str, Any] | None = None,
        incident_actions: list[Dict[str, Any]] | None = None,
        external_bridge_exports: Dict[str, Any] | None = None,
        external_bridge_results: Dict[str, Any] | None = None,
        external_bridge_actions: list[Dict[str, Any]] | None = None,
        intake_contracts: Dict[str, Any] | None = None,
        intake_acks: Dict[str, Any] | None = None,
        intake_actions: list[Dict[str, Any]] | None = None,
        dropzone_handshakes: Dict[str, Any] | None = None,
        dropzone_receipts: Dict[str, Any] | None = None,
        dropzone_receipt_history: Dict[str, Any] | None = None,
        dropzone_reconciliation: Dict[str, Any] | None = None,
        dropzone_recovery: Dict[str, Any] | None = None,
        dropzone_actions: list[Dict[str, Any]] | None = None,
        tce_lite: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") != document_id:
                continue

            entry["escalation_policy"] = escalation_policy
            entry["triage_actions"] = triage_actions
            entry["triage_state"] = triage_state
            if routing_hints is not None:
                entry["routing_hints"] = routing_hints
            if assignment_actions is not None:
                entry["assignment_actions"] = assignment_actions
            if assignment_state is not None:
                entry["assignment_state"] = assignment_state
            if sla_policy is not None:
                entry["sla_policy"] = sla_policy
            if watch_actions is not None:
                entry["watch_actions"] = watch_actions
            if watch_state is not None:
                entry["watch_state"] = watch_state
            if reminder_stage is not None:
                entry["reminder_stage"] = reminder_stage
            if reminder_actions is not None:
                entry["reminder_actions"] = reminder_actions
            if notification_prep is not None:
                entry["notification_prep"] = notification_prep
            if notification_ledger is not None:
                entry["notification_ledger"] = notification_ledger
            if delivery_attempts is not None:
                entry["delivery_attempts"] = delivery_attempts
            if notification_actions is not None:
                entry["notification_actions"] = notification_actions
            if transport_requests is not None:
                entry["transport_requests"] = transport_requests
            if transport_results is not None:
                entry["transport_results"] = transport_results
            if transport_actions is not None:
                entry["transport_actions"] = transport_actions
            if local_alerts is not None:
                entry["local_alerts"] = local_alerts
            if alert_actions is not None:
                entry["alert_actions"] = alert_actions
            if incident_threads is not None:
                entry["incident_threads"] = incident_threads
            if incident_actions is not None:
                entry["incident_actions"] = incident_actions
            if external_bridge_exports is not None:
                entry["external_bridge_exports"] = external_bridge_exports
            if external_bridge_results is not None:
                entry["external_bridge_results"] = external_bridge_results
            if external_bridge_actions is not None:
                entry["external_bridge_actions"] = external_bridge_actions
            if intake_contracts is not None:
                entry["intake_contracts"] = intake_contracts
            if intake_acks is not None:
                entry["intake_acks"] = intake_acks
            if intake_actions is not None:
                entry["intake_actions"] = intake_actions
            if dropzone_handshakes is not None:
                entry["dropzone_handshakes"] = dropzone_handshakes
            if dropzone_receipts is not None:
                entry["dropzone_receipts"] = dropzone_receipts
            if dropzone_receipt_history is not None:
                entry["dropzone_receipt_history"] = dropzone_receipt_history
            if dropzone_reconciliation is not None:
                entry["dropzone_reconciliation"] = dropzone_reconciliation
            if dropzone_recovery is not None:
                entry["dropzone_recovery"] = dropzone_recovery
            if dropzone_actions is not None:
                entry["dropzone_actions"] = dropzone_actions
            if tce_lite is not None:
                entry["tce_lite"] = tce_lite

            self._save_registry(registry)
            return entry

        raise KeyError(f"Document not found: {document_id}")

    def update_document_workbench(
        self,
        document_id: str,
        *,
        workbench_notes: str | None = None,
        workbench_status: str | None = None,
        workbench_tags: list[str] | None = None,
        workbench_history: list[Dict[str, Any]] | None = None,
        workbench_anchors: list[Dict[str, Any]] | None = None,
        workbench_anchor_history: list[Dict[str, Any]] | None = None,
        workbench_annotations: list[Dict[str, Any]] | None = None,
        workbench_annotation_history: list[Dict[str, Any]] | None = None,
        workbench_scratchpad: list[Dict[str, Any]] | None = None,
        workbench_scratchpad_history: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_cells: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_blocks: list[Dict[str, Any]] | None = None,
        workbench_reconstruction_history: list[Dict[str, Any]] | None = None,
        workbench_opened_at: str | None = None,
        workbench_updated_at: str | None = None,
        tce_lite: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        registry = self._load_registry()

        for entry in registry.get("documents", []):
            if entry.get("document_id") != document_id:
                continue

            if workbench_notes is not None:
                entry["workbench_notes"] = workbench_notes
            if workbench_status is not None:
                entry["workbench_status"] = workbench_status
            if workbench_tags is not None:
                entry["workbench_tags"] = workbench_tags
            if workbench_history is not None:
                entry["workbench_history"] = workbench_history
            if workbench_anchors is not None:
                entry["workbench_anchors"] = workbench_anchors
            if workbench_anchor_history is not None:
                entry["workbench_anchor_history"] = workbench_anchor_history
            if workbench_annotations is not None:
                entry["workbench_annotations"] = workbench_annotations
            if workbench_annotation_history is not None:
                entry["workbench_annotation_history"] = workbench_annotation_history
            if workbench_scratchpad is not None:
                entry["workbench_scratchpad"] = workbench_scratchpad
            if workbench_scratchpad_history is not None:
                entry["workbench_scratchpad_history"] = workbench_scratchpad_history
            if workbench_reconstruction_cells is not None:
                entry["workbench_reconstruction_cells"] = workbench_reconstruction_cells
            if workbench_reconstruction_blocks is not None:
                entry["workbench_reconstruction_blocks"] = workbench_reconstruction_blocks
            if workbench_reconstruction_history is not None:
                entry["workbench_reconstruction_history"] = workbench_reconstruction_history
            if workbench_opened_at is not None:
                entry["workbench_opened_at"] = workbench_opened_at
            if workbench_updated_at is not None:
                entry["workbench_updated_at"] = workbench_updated_at
            if tce_lite is not None:
                entry["tce_lite"] = tce_lite

            self._save_registry(registry)
            return entry

        raise KeyError(f"Document not found: {document_id}")
