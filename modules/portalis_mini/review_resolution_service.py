from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .archive.document_registry import DocumentRegistry
from .models import ReviewQueueItem, TCELiteEnvelope
from .passport_review_service import (
    build_compare_ledger_entries,
    build_field_statuses,
    build_field_policy_packets,
    build_passport_candidate_bundles,
    build_passport_field_evidence,
    build_passport_field_confidence,
    build_prioritized_field_queue,
    build_passport_review_tce_delta,
    build_unresolved_field_packets,
    score_passport_field_conflicts,
    validate_passport_review_fields,
)
from .record_update_service import RecordUpdateService
from .storage import load_review_queue, save_review_queue, utc_now_iso


class ReviewResolutionError(Exception):
    pass


@dataclass(slots=True)
class ReviewResolutionCoupler:
    review_item: ReviewQueueItem
    operator_action: str
    edited_fields: Dict[str, Any] = field(default_factory=dict)
    selected_candidate_ids: Dict[str, str] = field(default_factory=dict)
    field_actions: Dict[str, str] = field(default_factory=dict)
    unresolved_reasons: Dict[str, str] = field(default_factory=dict)
    operator_name: str = "operator"
    resolution_reason: str = ""


@dataclass(slots=True)
class ResolutionPacket:
    document_id: str
    review_status: str
    parsed_fields: Dict[str, Any]
    final_fields: Dict[str, Any]
    accepted_fields: Dict[str, Any]
    field_evidence: Dict[str, Any]
    field_validation: Dict[str, Any]
    field_conflicts: Dict[str, Any]
    field_confidence: Dict[str, Any]
    candidate_bundles: Dict[str, Any]
    compare_ledger: List[Dict[str, Any]]
    accepted_candidate_refs: Dict[str, Any]
    operator_overrides: Dict[str, Any]
    field_statuses: Dict[str, Any]
    unresolved_fields: Dict[str, Any]
    field_policy: Dict[str, Any]
    prioritized_field_queue: List[Dict[str, Any]]
    operator_name: str
    resolution_reason: str
    resolution_mode: str
    resolved_at: str
    owner_entity: str = ""
    owner_id: str = ""
    tce_lite: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RegistryWriteCoupler:
    resolution_packet: ResolutionPacket
    registry_entry: Optional[Dict[str, Any]] = None
    crew_record_path: Optional[str] = None


class ReviewResolutionService:
    def __init__(self, portalis_root: str | Path) -> None:
        self.root = Path(portalis_root)
        self.registry = DocumentRegistry(self.root)
        self.record_update_service = RecordUpdateService(self.root)

    def list_review_items(self) -> List[ReviewQueueItem]:
        return load_review_queue(self.root)

    def get_review_item(self, document_id: str) -> ReviewQueueItem:
        for item in load_review_queue(self.root):
            if item.document_id == document_id:
                return item
        raise ReviewResolutionError(f"Review item not found: {document_id}")

    def resolve(self, coupler: ReviewResolutionCoupler) -> RegistryWriteCoupler:
        document_entry = self.registry.get_document(coupler.review_item.document_id)
        if not document_entry:
            raise ReviewResolutionError(f"Document not found: {coupler.review_item.document_id}")

        packet = self._build_resolution_packet(document_entry=document_entry, coupler=coupler)
        updated_entry = self.registry.update_document_resolution(
            packet.document_id,
            review_status=packet.review_status,
            final_fields=packet.final_fields,
            accepted_fields=packet.accepted_fields,
            field_evidence=packet.field_evidence,
            field_validation=packet.field_validation,
            field_conflicts=packet.field_conflicts,
            field_confidence=packet.field_confidence,
            candidate_bundles=packet.candidate_bundles,
            compare_ledger=packet.compare_ledger,
            accepted_candidate_refs=packet.accepted_candidate_refs,
            operator_overrides=packet.operator_overrides,
            field_statuses=packet.field_statuses,
            unresolved_fields=packet.unresolved_fields,
            field_policy=packet.field_policy,
            prioritized_field_queue=packet.prioritized_field_queue,
            resolved_by=packet.operator_name,
            resolved_at=packet.resolved_at,
            resolution_reason=packet.resolution_reason,
            resolution_mode=packet.resolution_mode,
            tce_lite=packet.tce_lite,
        )

        crew_record_path = None
        if packet.review_status in {"ACCEPTED", "RESOLVED"} and packet.owner_entity == "crew" and packet.owner_id:
            crew_record_path = str(
                self.record_update_service.update_crew_from_mapped_fields(
                    crew_id=packet.owner_id,
                    mapped_fields={
                        key: value
                        for key, value in packet.accepted_fields.items()
                        if str((packet.field_statuses.get(key) or {}).get("status") or "") in {"ACCEPTED", "OVERRIDDEN"}
                    },
                    source_file=document_entry.get("source_file"),
                )
            )

        self._update_review_queue(packet)
        return RegistryWriteCoupler(
            resolution_packet=packet,
            registry_entry=updated_entry,
            crew_record_path=crew_record_path,
        )

    def _build_resolution_packet(
        self,
        *,
        document_entry: Dict[str, Any],
        coupler: ReviewResolutionCoupler,
    ) -> ResolutionPacket:
        action = (coupler.operator_action or "").strip().upper()
        if action not in {"ACCEPT", "REJECT", "RESOLVE"}:
            raise ReviewResolutionError(f"Unsupported review action: {action}")

        parsed_fields = dict(coupler.review_item.parsed_fields or document_entry.get("parsed_fields", {}))
        document_type = str(document_entry.get("doc_type") or "").strip().lower()
        edited_fields = {key: value for key, value in coupler.edited_fields.items() if value not in (None, "")}
        final_fields = dict(parsed_fields)
        final_fields.update(edited_fields)

        if action == "REJECT":
            review_status = "REJECTED"
            accepted_fields: Dict[str, Any] = {}
            resolution_mode = "operator_reject"
        elif edited_fields:
            review_status = "RESOLVED"
            accepted_fields = dict(final_fields)
            resolution_mode = "operator_edit_accept"
        elif action == "RESOLVE":
            review_status = "RESOLVED"
            accepted_fields = dict(final_fields)
            resolution_mode = "operator_resolve"
        else:
            review_status = "ACCEPTED"
            accepted_fields = dict(final_fields)
            resolution_mode = "operator_accept"

        resolved_at = utc_now_iso()
        field_evidence = self._build_field_evidence(
            document_type=document_type,
            review_item=coupler.review_item,
            document_entry=document_entry,
            parsed_fields=parsed_fields,
        )
        candidate_target_fields = dict(final_fields if review_status in {"ACCEPTED", "RESOLVED"} else parsed_fields)
        field_validation = self._build_field_validation(
            document_type=document_type,
            fields=candidate_target_fields,
            field_evidence=field_evidence,
        )
        field_conflicts = self._build_field_conflicts(
            document_type=document_type,
            fields=candidate_target_fields,
            field_evidence=field_evidence,
            field_validation=field_validation,
        )
        field_confidence = self._build_field_confidence(
            document_type=document_type,
            field_conflicts=field_conflicts,
            field_validation=field_validation,
        )
        candidate_bundles = self._build_candidate_bundles(
            document_type=document_type,
            fields=candidate_target_fields,
            field_evidence=field_evidence,
            field_validation=field_validation,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            selected_candidate_ids=coupler.selected_candidate_ids,
        )
        if review_status in {"ACCEPTED", "RESOLVED"}:
            final_fields = self._apply_selected_candidate_values(
                final_fields=final_fields,
                edited_fields=edited_fields,
                candidate_bundles=candidate_bundles,
            )
            accepted_fields = dict(final_fields)
            candidate_target_fields = dict(final_fields)
            field_validation = self._build_field_validation(
                document_type=document_type,
                fields=candidate_target_fields,
                field_evidence=field_evidence,
            )
            field_conflicts = self._build_field_conflicts(
                document_type=document_type,
                fields=candidate_target_fields,
                field_evidence=field_evidence,
                field_validation=field_validation,
            )
            field_confidence = self._build_field_confidence(
                document_type=document_type,
                field_conflicts=field_conflicts,
                field_validation=field_validation,
            )
            candidate_bundles = self._build_candidate_bundles(
                document_type=document_type,
                fields=candidate_target_fields,
                field_evidence=field_evidence,
                field_validation=field_validation,
                field_conflicts=field_conflicts,
                field_confidence=field_confidence,
                selected_candidate_ids=coupler.selected_candidate_ids,
            )
        accepted_candidate_refs = self._build_accepted_candidate_refs(
            review_status=review_status,
            candidate_bundles=candidate_bundles,
            field_actions=coupler.field_actions,
        )
        operator_overrides = self._build_operator_overrides(
            review_status=review_status,
            accepted_fields=accepted_fields,
            candidate_bundles=candidate_bundles,
            edited_fields=edited_fields,
            field_actions=coupler.field_actions,
        )
        field_statuses = self._build_field_statuses(
            review_status=review_status,
            candidate_bundles=candidate_bundles,
            accepted_candidate_refs=accepted_candidate_refs,
            operator_overrides=operator_overrides,
            field_actions=coupler.field_actions,
        )
        unresolved_fields = self._build_unresolved_fields(
            document_id=str(document_entry["document_id"]),
            candidate_bundles=candidate_bundles,
            field_confidence=field_confidence,
            field_conflicts=field_conflicts,
            field_statuses=field_statuses,
            unresolved_reasons=coupler.unresolved_reasons,
        )
        field_policy = self._build_field_policy(
            candidate_bundles=candidate_bundles,
            field_validation=field_validation,
            field_confidence=field_confidence,
            field_conflicts=field_conflicts,
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
        )
        prioritized_field_queue = self._build_prioritized_field_queue(
            document_id=str(document_entry["document_id"]),
            field_policy=field_policy,
            field_statuses=field_statuses,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            candidate_bundles=candidate_bundles,
        )
        review_status = self._derive_review_status(
            action=action,
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
        )
        compare_ledger = self._build_compare_ledger(
            document_id=str(document_entry["document_id"]),
            review_status=review_status,
            existing_ledger=list(document_entry.get("compare_ledger", []) or []),
            candidate_bundles=candidate_bundles,
            field_confidence=field_confidence,
            operator_overrides=operator_overrides,
            field_statuses=field_statuses,
            unresolved_reasons=coupler.unresolved_reasons,
            decision_notes=coupler.resolution_reason or "",
        )
        tce_lite = self._build_resolved_tce(
            base_tce=document_entry.get("tce_lite") or {},
            operator_name=coupler.operator_name or "operator",
            resolution_reason=coupler.resolution_reason or "",
            resolution_mode=resolution_mode,
            resolved_at=resolved_at,
            field_evidence=field_evidence,
            field_validation=field_validation,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            candidate_bundles=candidate_bundles,
            compare_ledger=compare_ledger,
            selection_mode="operator_override" if operator_overrides else "candidate_selected",
            override_reason=coupler.resolution_reason or "",
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
            field_policy=field_policy,
            prioritized_field_queue=prioritized_field_queue,
        )

        return ResolutionPacket(
            document_id=document_entry["document_id"],
            review_status=review_status,
            parsed_fields=parsed_fields,
            final_fields=final_fields,
            accepted_fields=accepted_fields,
            field_evidence=field_evidence,
            field_validation=field_validation,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            candidate_bundles=candidate_bundles,
            compare_ledger=compare_ledger,
            accepted_candidate_refs=accepted_candidate_refs,
            operator_overrides=operator_overrides,
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
            field_policy=field_policy,
            prioritized_field_queue=prioritized_field_queue,
            operator_name=coupler.operator_name or "operator",
            resolution_reason=coupler.resolution_reason or "",
            resolution_mode=resolution_mode,
            resolved_at=resolved_at,
            owner_entity=str(document_entry.get("owner_entity") or ""),
            owner_id=str(document_entry.get("owner_id") or ""),
            tce_lite=tce_lite,
        )

    def _build_resolved_tce(
        self,
        *,
        base_tce: Dict[str, Any],
        operator_name: str,
        resolution_reason: str,
        resolution_mode: str,
        resolved_at: str,
        field_evidence: Dict[str, Any],
        field_validation: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_confidence: Dict[str, Any],
        candidate_bundles: Dict[str, Any],
        compare_ledger: List[Dict[str, Any]],
        selection_mode: str,
        override_reason: str,
        field_statuses: Dict[str, Any],
        unresolved_fields: Dict[str, Any],
        field_policy: Dict[str, Any],
        prioritized_field_queue: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        tce = TCELiteEnvelope(
            WHAT=dict((base_tce.get("WHAT") or {})),
            WHO=dict((base_tce.get("WHO") or {})),
            WHEN=dict((base_tce.get("WHEN") or {})),
            WHERE=dict((base_tce.get("WHERE") or {})),
            HOW=dict((base_tce.get("HOW") or {})),
            WHY=dict((base_tce.get("WHY") or {})),
        )

        tce.HOW["resolved_by"] = operator_name
        tce.HOW["resolution_mode"] = resolution_mode
        tce.WHEN["resolved_at"] = resolved_at
        tce.WHY["resolution_reason"] = resolution_reason
        if field_evidence or field_validation:
            delta = build_passport_review_tce_delta(
                field_evidence=field_evidence,
                field_validation=field_validation,
                field_conflicts=field_conflicts,
                field_confidence=field_confidence,
                candidate_bundles=candidate_bundles,
                compare_ledger=compare_ledger,
                selection_mode=selection_mode,
                override_reason=override_reason,
                field_statuses=field_statuses,
                unresolved_fields=unresolved_fields,
                field_policy=field_policy,
                prioritized_field_queue=prioritized_field_queue,
                review_focus="operator_resolution" if resolution_mode != "operator_reject" else "operator_rejection_review",
            )
            tce.WHEN.update(delta.get("WHEN", {}))
            tce.HOW.update(delta.get("HOW", {}))
            tce.WHY.update(delta.get("WHY", {}))
        return {
            "WHAT": tce.WHAT,
            "WHO": tce.WHO,
            "WHEN": tce.WHEN,
            "WHERE": tce.WHERE,
            "HOW": tce.HOW,
            "WHY": tce.WHY,
        }

    def _update_review_queue(self, packet: ResolutionPacket) -> None:
        items = load_review_queue(self.root)
        for item in items:
            if item.document_id != packet.document_id:
                continue

            item.status = packet.review_status
            item.final_fields = dict(packet.final_fields)
            item.accepted_fields = dict(packet.accepted_fields)
            item.field_evidence = dict(packet.field_evidence)
            item.field_validation = dict(packet.field_validation)
            item.field_conflicts = dict(packet.field_conflicts)
            item.field_confidence = dict(packet.field_confidence)
            item.candidate_bundles = dict(packet.candidate_bundles)
            item.compare_ledger = list(packet.compare_ledger)
            item.accepted_candidate_refs = dict(packet.accepted_candidate_refs)
            item.operator_overrides = dict(packet.operator_overrides)
            item.field_statuses = dict(packet.field_statuses)
            item.unresolved_fields = dict(packet.unresolved_fields)
            item.field_policy = dict(packet.field_policy)
            item.prioritized_field_queue = list(packet.prioritized_field_queue)
            item.resolution_reason = packet.resolution_reason
            item.resolved_by = packet.operator_name
            item.updated_at = packet.resolved_at
            item.tce = TCELiteEnvelope(
                WHAT=dict(packet.tce_lite.get("WHAT", {})),
                WHO=dict(packet.tce_lite.get("WHO", {})),
                WHEN=dict(packet.tce_lite.get("WHEN", {})),
                WHERE=dict(packet.tce_lite.get("WHERE", {})),
                HOW=dict(packet.tce_lite.get("HOW", {})),
                WHY=dict(packet.tce_lite.get("WHY", {})),
            )
            break

        save_review_queue(self.root, items)

    def _build_field_evidence(
        self,
        *,
        document_type: str,
        review_item: ReviewQueueItem,
        document_entry: Dict[str, Any],
        parsed_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        if document_type != "passport":
            return dict(review_item.field_evidence or document_entry.get("field_evidence", {}))

        raw_field_evidence = dict(document_entry.get("field_evidence", {}))
        if not raw_field_evidence:
            raw_field_evidence = dict(review_item.field_evidence or {})

        return build_passport_field_evidence(raw_field_evidence, parsed_fields)

    def _build_field_validation(
        self,
        *,
        document_type: str,
        fields: Dict[str, Any],
        field_evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        if document_type != "passport":
            return {}

        return validate_passport_review_fields(fields, field_evidence)

    def _build_field_conflicts(
        self,
        *,
        document_type: str,
        fields: Dict[str, Any],
        field_evidence: Dict[str, Any],
        field_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        if document_type != "passport":
            return {}

        return score_passport_field_conflicts(fields, field_evidence, field_validation)

    def _build_field_confidence(
        self,
        *,
        document_type: str,
        field_conflicts: Dict[str, Any],
        field_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        if document_type != "passport":
            return {}

        return build_passport_field_confidence(field_conflicts, field_validation)

    def _apply_selected_candidate_values(
        self,
        *,
        final_fields: Dict[str, Any],
        edited_fields: Dict[str, Any],
        candidate_bundles: Dict[str, Any],
    ) -> Dict[str, Any]:
        patched = dict(final_fields)
        for field_name, bundle in candidate_bundles.items():
            if field_name in edited_fields:
                continue
            selected_value = str(bundle.get("selected_value") or "")
            if selected_value:
                patched[field_name] = selected_value
        return patched

    def _build_candidate_bundles(
        self,
        *,
        document_type: str,
        fields: Dict[str, Any],
        field_evidence: Dict[str, Any],
        field_validation: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_confidence: Dict[str, Any],
        selected_candidate_ids: Dict[str, str],
    ) -> Dict[str, Any]:
        if document_type != "passport":
            return {}

        bundles = build_passport_candidate_bundles(
            fields,
            field_evidence,
            field_validation,
            field_conflicts,
            field_confidence,
        )
        for field_name, selected_id in (selected_candidate_ids or {}).items():
            bundle = bundles.get(field_name)
            if not bundle or not selected_id:
                continue
            for candidate in bundle.get("candidates", []):
                if candidate.get("candidate_id") == selected_id:
                    bundle["selected_candidate_id"] = selected_id
                    bundle["selected_value"] = candidate.get("candidate_value") or ""
                    break
        return bundles

    def _build_accepted_candidate_refs(
        self,
        *,
        review_status: str,
        candidate_bundles: Dict[str, Any],
        field_actions: Dict[str, str],
    ) -> Dict[str, Any]:
        if review_status not in {"ACCEPTED", "RESOLVED"}:
            return {}

        refs = {}
        for field_name, bundle in candidate_bundles.items():
            action = str((field_actions or {}).get(field_name) or "")
            if action == "MARK_UNRESOLVED":
                continue
            if bundle.get("selected_candidate_id"):
                refs[field_name] = bundle.get("selected_candidate_id")
        return refs

    def _build_operator_overrides(
        self,
        *,
        review_status: str,
        accepted_fields: Dict[str, Any],
        candidate_bundles: Dict[str, Any],
        edited_fields: Dict[str, Any],
        field_actions: Dict[str, str],
    ) -> Dict[str, Any]:
        if review_status not in {"ACCEPTED", "RESOLVED"}:
            return {}

        overrides = {}
        for field_name, accepted_value in accepted_fields.items():
            action = str((field_actions or {}).get(field_name) or "")
            if action == "MARK_UNRESOLVED":
                continue
            bundle = candidate_bundles.get(field_name) or {}
            selected_value = str(bundle.get("selected_value") or "")
            accepted_text = str(accepted_value or "")
            if field_name in edited_fields and accepted_text != selected_value:
                overrides[field_name] = accepted_text
        return overrides

    def _build_compare_ledger(
        self,
        *,
        document_id: str,
        review_status: str,
        existing_ledger: List[Dict[str, Any]],
        candidate_bundles: Dict[str, Any],
        field_confidence: Dict[str, Any],
        operator_overrides: Dict[str, Any],
        field_statuses: Dict[str, Any],
        unresolved_reasons: Dict[str, str],
        decision_notes: str,
    ) -> List[Dict[str, Any]]:
        new_entries = build_compare_ledger_entries(
            document_id=document_id,
            candidate_bundles=candidate_bundles,
            field_confidence=field_confidence,
            review_status=review_status,
            decision_notes=decision_notes,
            operator_overrides=operator_overrides,
        )
        for entry in new_entries:
            field_name = entry.get("field_name")
            entry["field_status"] = str((field_statuses.get(field_name) or {}).get("status") or "PENDING")
            if field_name in unresolved_reasons:
                entry["unresolved_reason"] = unresolved_reasons[field_name]
        return list(existing_ledger) + new_entries

    def _build_field_statuses(
        self,
        *,
        review_status: str,
        candidate_bundles: Dict[str, Any],
        accepted_candidate_refs: Dict[str, Any],
        operator_overrides: Dict[str, Any],
        field_actions: Dict[str, str],
    ) -> Dict[str, Any]:
        statuses = build_field_statuses(
            candidate_bundles,
            accepted_candidate_refs=accepted_candidate_refs,
            operator_overrides=operator_overrides,
        )
        for field_name, action in (field_actions or {}).items():
            if action == "MARK_UNRESOLVED":
                statuses[field_name] = {"status": "UNRESOLVED"}
            elif action == "APPLY_OPERATOR_OVERRIDE":
                statuses[field_name] = {"status": "OVERRIDDEN"}
            elif action == "ACCEPT_SELECTED_CANDIDATE":
                statuses[field_name] = {"status": "ACCEPTED"}
        if review_status == "REJECTED":
            for field_name in candidate_bundles.keys():
                statuses[field_name] = {"status": "REJECTED"}
        return statuses

    def _build_unresolved_fields(
        self,
        *,
        document_id: str,
        candidate_bundles: Dict[str, Any],
        field_confidence: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_statuses: Dict[str, Any],
        unresolved_reasons: Dict[str, str],
    ) -> Dict[str, Any]:
        return build_unresolved_field_packets(
            document_id=document_id,
            candidate_bundles=candidate_bundles,
            field_confidence=field_confidence,
            field_conflicts=field_conflicts,
            field_statuses=field_statuses,
            unresolved_reasons=unresolved_reasons,
        )

    def _derive_review_status(
        self,
        *,
        action: str,
        field_statuses: Dict[str, Any],
        unresolved_fields: Dict[str, Any],
    ) -> str:
        if action == "REJECT":
            return "REJECTED"
        if any(str((payload or {}).get("status") or "") == "UNRESOLVED" for payload in unresolved_fields.values()):
            return "PENDING"
        if any(str((payload or {}).get("status") or "") == "OVERRIDDEN" for payload in field_statuses.values()):
            return "RESOLVED"
        if any(str((payload or {}).get("status") or "") == "ACCEPTED" for payload in field_statuses.values()):
            return "ACCEPTED"
        return "PENDING"

    def _build_field_policy(
        self,
        *,
        candidate_bundles: Dict[str, Any],
        field_validation: Dict[str, Any],
        field_confidence: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_statuses: Dict[str, Any],
        unresolved_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        return build_field_policy_packets(
            candidate_bundles=candidate_bundles,
            field_validation=field_validation,
            field_confidence=field_confidence,
            field_conflicts=field_conflicts,
            field_statuses=field_statuses,
            unresolved_fields=unresolved_fields,
        )

    def _build_prioritized_field_queue(
        self,
        *,
        document_id: str,
        field_policy: Dict[str, Any],
        field_statuses: Dict[str, Any],
        field_conflicts: Dict[str, Any],
        field_confidence: Dict[str, Any],
        candidate_bundles: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return build_prioritized_field_queue(
            document_id=document_id,
            field_policy=field_policy,
            field_statuses=field_statuses,
            field_conflicts=field_conflicts,
            field_confidence=field_confidence,
            candidate_bundles=candidate_bundles,
        )
