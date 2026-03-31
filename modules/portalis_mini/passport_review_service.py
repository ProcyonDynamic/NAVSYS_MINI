from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


PASSPORT_REVIEW_FIELDS = [
    "passport.number",
    "crew.surname",
    "crew.given_names",
    "crew.nationality",
    "crew.date_of_birth",
    "passport.issue_date",
    "passport.expiry_date",
]

PASSPORT_FIELD_CRITICALITY = {
    "passport.number": ("CRITICAL", 100),
    "crew.surname": ("HIGH", 80),
    "crew.given_names": ("HIGH", 80),
    "crew.date_of_birth": ("HIGH", 78),
    "passport.expiry_date": ("HIGH", 76),
    "crew.nationality": ("MEDIUM", 55),
    "passport.issue_date": ("LOW", 35),
}


@dataclass(slots=True)
class FieldEvidencePacket:
    field_name: str
    parsed_value: str
    candidate_text: str = ""
    source_engine: Optional[str] = None
    source_kind: Optional[str] = None
    source_method: Optional[str] = None
    source_line: str = ""
    source_snippet: str = ""
    candidate_index: Optional[int] = None
    provenance_branch: str = "unknown"
    provenance_path: str = "unknown"
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    alternate_values: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ValidationResultPacket:
    field_name: str
    status: str
    normalized_value: Optional[str] = None
    validator_messages: List[str] = field(default_factory=list)
    compared_fields: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ConflictScorePacket:
    field_name: str
    agreement_present: Optional[bool]
    agreement_source_count: int = 0
    conflict_level: str = "UNKNOWN"
    compared_sources: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FieldConfidencePacket:
    field_name: str
    confidence_score: float
    confidence_band: str
    conflict_level: str
    agreement_sources: int = 0
    warning_flags: List[str] = field(default_factory=list)
    recommended_action: str = "REVIEW"
    rationale: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FieldCandidatePacket:
    candidate_id: str
    field_name: str
    candidate_value: str
    normalized_value: str = ""
    source_engine: Optional[str] = None
    source_kind: Optional[str] = None
    source_method: Optional[str] = None
    provenance_branch: str = "unknown"
    provenance_path: str = "unknown"
    source_line: str = ""
    source_snippet: str = ""
    candidate_index: Optional[int] = None
    validation_status: Optional[str] = None
    confidence_hint: Optional[float] = None
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateBundlePacket:
    field_name: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_candidate_id: Optional[str] = None
    selected_value: str = ""
    alternate_candidate_ids: List[str] = field(default_factory=list)
    agreement_summary: Dict[str, Any] = field(default_factory=dict)
    conflict_level: str = "UNKNOWN"
    confidence_summary: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = "REVIEW"


@dataclass(slots=True)
class CompareLedgerPacket:
    document_id: str
    field_name: str
    compared_at: str
    candidate_bundle_snapshot: Dict[str, Any]
    selected_candidate_id: Optional[str] = None
    selected_value: str = ""
    conflict_level: str = "UNKNOWN"
    confidence_summary: Dict[str, Any] = field(default_factory=dict)
    operator_override: bool = False
    operator_selected_value: str = ""
    rationale: List[str] = field(default_factory=list)
    decision_notes: str = ""
    review_status: str = "PENDING"


@dataclass(slots=True)
class FieldResolutionActionPacket:
    document_id: str
    field_name: str
    action: str
    selected_candidate_id: str = ""
    operator_value: str = ""
    reason: str = ""
    status: str = "PENDING"
    acted_at: str = ""


@dataclass(slots=True)
class UnresolvedFieldPacket:
    document_id: str
    field_name: str
    unresolved_reason: str
    conflict_level: str = "UNKNOWN"
    confidence_band: str = "UNKNOWN"
    recommended_action: str = "REVIEW"
    candidate_bundle_ref: str = ""
    last_updated: str = ""
    status: str = "UNRESOLVED"


@dataclass(slots=True)
class FieldPolicyPacket:
    field_name: str
    criticality: str
    base_priority: int
    priority_score: int
    priority_band: str
    priority_reason: List[str] = field(default_factory=list)
    attention_state: str = "CLEAR"


@dataclass(slots=True)
class PrioritizedFieldQueuePacket:
    document_id: str
    field_name: str
    queue_rank: int
    priority_score: int
    priority_band: str
    priority_reason: List[str] = field(default_factory=list)
    current_status: str = "PENDING"
    conflict_level: str = "UNKNOWN"
    confidence_band: str = "UNKNOWN"
    recommended_action: str = "REVIEW"
    attention_state: str = "CLEAR"


def build_passport_field_evidence(raw_field_evidence: Dict[str, Any], parsed_fields: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        parsed_value = str(parsed_fields.get(field_name) or "")
        raw = dict(raw_field_evidence.get(field_name) or {})
        packet = FieldEvidencePacket(
            field_name=field_name,
            parsed_value=parsed_value,
            candidate_text=str(raw.get("candidate_text") or ""),
            source_engine=raw.get("source_engine"),
            source_kind=raw.get("source_kind"),
            source_method=raw.get("source_method"),
            source_line=str(raw.get("source_line") or raw.get("candidate_text") or ""),
            source_snippet=str(raw.get("source_snippet") or raw.get("candidate_text") or raw.get("parsed_value") or ""),
            candidate_index=raw.get("candidate_index"),
            provenance_branch=str(raw.get("provenance_branch") or _derive_branch(raw)),
            provenance_path=str(raw.get("provenance_path") or "mapped_canonical"),
            notes=list(raw.get("notes", [])),
            warnings=list(raw.get("warnings", [])),
            alternate_values=[_normalize_alternate_value(item, idx + 1) for idx, item in enumerate(raw.get("alternate_values", []))],
        )
        packets[field_name] = asdict(packet)

    return packets


def build_passport_candidate_bundles(
    fields: Dict[str, Any],
    field_evidence: Dict[str, Dict[str, Any]],
    field_validation: Dict[str, Dict[str, Any]],
    field_conflicts: Dict[str, Dict[str, Any]],
    field_confidence: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    bundles: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        field_value = str(fields.get(field_name) or "")
        evidence = dict(field_evidence.get(field_name) or {})
        validation = dict(field_validation.get(field_name) or {})
        conflict = dict(field_conflicts.get(field_name) or {})
        confidence = dict(field_confidence.get(field_name) or {})
        candidates = _build_candidates_for_field(
            field_name=field_name,
            field_value=field_value,
            evidence=evidence,
            validation=validation,
        )
        selected_candidate_id, selected_value = _select_candidate(candidates, field_value)
        alternate_candidate_ids = [
            candidate["candidate_id"]
            for candidate in candidates
            if candidate["candidate_id"] != selected_candidate_id
        ]
        bundles[field_name] = asdict(
            CandidateBundlePacket(
                field_name=field_name,
                candidates=candidates,
                selected_candidate_id=selected_candidate_id,
                selected_value=selected_value,
                alternate_candidate_ids=alternate_candidate_ids,
                agreement_summary={
                    "agreement_present": conflict.get("agreement_present"),
                    "agreement_source_count": conflict.get("agreement_source_count", 0),
                    "compared_sources": list(conflict.get("compared_sources", [])),
                },
                conflict_level=str(conflict.get("conflict_level") or "UNKNOWN"),
                confidence_summary={
                    "confidence_score": confidence.get("confidence_score"),
                    "confidence_band": confidence.get("confidence_band"),
                },
                recommended_action=str(confidence.get("recommended_action") or "REVIEW"),
            )
        )

    return bundles


def build_compare_ledger_entries(
    *,
    document_id: str,
    candidate_bundles: Dict[str, Dict[str, Any]],
    field_confidence: Dict[str, Dict[str, Any]],
    review_status: str,
    decision_notes: str = "",
    operator_overrides: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    compared_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    overrides = operator_overrides or {}
    entries: List[Dict[str, Any]] = []

    for field_name in PASSPORT_REVIEW_FIELDS:
        bundle = dict(candidate_bundles.get(field_name) or {})
        confidence = dict(field_confidence.get(field_name) or {})
        operator_value = str(overrides.get(field_name) or "")
        entries.append(
            asdict(
                CompareLedgerPacket(
                    document_id=document_id,
                    field_name=field_name,
                    compared_at=compared_at,
                    candidate_bundle_snapshot=bundle,
                    selected_candidate_id=bundle.get("selected_candidate_id"),
                    selected_value=str(bundle.get("selected_value") or ""),
                    conflict_level=str(bundle.get("conflict_level") or "UNKNOWN"),
                    confidence_summary={
                        "confidence_score": confidence.get("confidence_score"),
                        "confidence_band": confidence.get("confidence_band"),
                        "recommended_action": confidence.get("recommended_action"),
                    },
                    operator_override=bool(operator_value),
                    operator_selected_value=operator_value,
                    rationale=list(confidence.get("rationale", [])),
                    decision_notes=decision_notes,
                    review_status=review_status,
                )
            )
        )

    return entries


def build_field_statuses(
    candidate_bundles: Dict[str, Dict[str, Any]],
    accepted_candidate_refs: Dict[str, Any] | None = None,
    operator_overrides: Dict[str, Any] | None = None,
    unresolved_fields: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    accepted_candidate_refs = accepted_candidate_refs or {}
    operator_overrides = operator_overrides or {}
    unresolved_fields = unresolved_fields or {}
    statuses: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        if field_name in unresolved_fields:
            statuses[field_name] = {"status": "UNRESOLVED"}
        elif field_name in operator_overrides:
            statuses[field_name] = {"status": "OVERRIDDEN"}
        elif field_name in accepted_candidate_refs:
            statuses[field_name] = {"status": "ACCEPTED"}
        elif (candidate_bundles.get(field_name) or {}).get("selected_candidate_id"):
            statuses[field_name] = {"status": "PENDING"}
        else:
            statuses[field_name] = {"status": "PENDING"}
    return statuses


def build_unresolved_field_packets(
    *,
    document_id: str,
    candidate_bundles: Dict[str, Dict[str, Any]],
    field_confidence: Dict[str, Dict[str, Any]],
    field_conflicts: Dict[str, Dict[str, Any]],
    field_statuses: Dict[str, Dict[str, Any]],
    unresolved_reasons: Dict[str, str] | None = None,
) -> Dict[str, Dict[str, Any]]:
    unresolved_reasons = unresolved_reasons or {}
    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        status = str((field_statuses.get(field_name) or {}).get("status") or "PENDING")
        bundle = dict(candidate_bundles.get(field_name) or {})
        confidence = dict(field_confidence.get(field_name) or {})
        conflict = dict(field_conflicts.get(field_name) or {})
        recommended_action = str(confidence.get("recommended_action") or bundle.get("recommended_action") or "REVIEW")

        should_surface = status == "UNRESOLVED" or recommended_action in {"REVIEW", "HIGH_ATTENTION"}
        if not should_surface:
            continue

        packets[field_name] = asdict(
            UnresolvedFieldPacket(
                document_id=document_id,
                field_name=field_name,
                unresolved_reason=str(unresolved_reasons.get(field_name) or _default_unresolved_reason(status, recommended_action)),
                conflict_level=str(conflict.get("conflict_level") or bundle.get("conflict_level") or "UNKNOWN"),
                confidence_band=str(confidence.get("confidence_band") or "UNKNOWN"),
                recommended_action=recommended_action,
                candidate_bundle_ref=str(bundle.get("selected_candidate_id") or ""),
                last_updated=last_updated,
                status="UNRESOLVED" if status == "UNRESOLVED" else "PENDING",
            )
        )

    return packets


def build_field_policy_packets(
    *,
    candidate_bundles: Dict[str, Dict[str, Any]],
    field_validation: Dict[str, Dict[str, Any]],
    field_confidence: Dict[str, Dict[str, Any]],
    field_conflicts: Dict[str, Dict[str, Any]],
    field_statuses: Dict[str, Dict[str, Any]],
    unresolved_fields: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        criticality, base_priority = PASSPORT_FIELD_CRITICALITY.get(field_name, ("LOW", 20))
        validation = dict(field_validation.get(field_name) or {})
        confidence = dict(field_confidence.get(field_name) or {})
        conflict = dict(field_conflicts.get(field_name) or {})
        status = str((field_statuses.get(field_name) or {}).get("status") or "PENDING")
        recommended_action = str(confidence.get("recommended_action") or (candidate_bundles.get(field_name) or {}).get("recommended_action") or "REVIEW")
        attention_state = _derive_attention_state(
            field_name=field_name,
            status=status,
            unresolved_fields=unresolved_fields,
            conflict=conflict,
            confidence=confidence,
            recommended_action=recommended_action,
        )

        priority_score = base_priority
        reasons = [f"criticality={criticality}"]

        if attention_state == "UNRESOLVED":
            priority_score += 80
            reasons.append("explicitly unresolved")
        elif attention_state == "ATTENTION":
            priority_score += 35
            reasons.append("attention needed")

        conflict_level = str(conflict.get("conflict_level") or "UNKNOWN")
        if conflict_level == "HIGH":
            priority_score += 30
            reasons.append("high conflict")
        elif conflict_level == "MEDIUM":
            priority_score += 18
            reasons.append("medium conflict")
        elif conflict_level == "LOW":
            priority_score += 8

        confidence_band = str(confidence.get("confidence_band") or "UNKNOWN")
        if confidence_band in {"LOW", "UNKNOWN"}:
            priority_score += 20
            reasons.append("low confidence")
        elif confidence_band == "MEDIUM":
            priority_score += 8

        validation_status = str(validation.get("status") or "UNKNOWN")
        if validation_status == "FAIL":
            priority_score += 24
            reasons.append("validation fail")
        elif validation_status == "WARN":
            priority_score += 8
            reasons.append("validation warn")

        if status in {"ACCEPTED", "OVERRIDDEN"} and attention_state == "CLEAR":
            priority_score = max(0, priority_score - 90)
            reasons.append("field already resolved")

        packets[field_name] = asdict(
            FieldPolicyPacket(
                field_name=field_name,
                criticality=criticality,
                base_priority=base_priority,
                priority_score=priority_score,
                priority_band=_priority_band(priority_score),
                priority_reason=reasons,
                attention_state=attention_state,
            )
        )

    return packets


def build_prioritized_field_queue(
    *,
    document_id: str,
    field_policy: Dict[str, Dict[str, Any]],
    field_statuses: Dict[str, Dict[str, Any]],
    field_conflicts: Dict[str, Dict[str, Any]],
    field_confidence: Dict[str, Dict[str, Any]],
    candidate_bundles: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    queue_rows: List[Dict[str, Any]] = []

    for field_name in PASSPORT_REVIEW_FIELDS:
        policy = dict(field_policy.get(field_name) or {})
        confidence = dict(field_confidence.get(field_name) or {})
        conflict = dict(field_conflicts.get(field_name) or {})
        bundle = dict(candidate_bundles.get(field_name) or {})
        status = str((field_statuses.get(field_name) or {}).get("status") or "PENDING")
        queue_rows.append(
            asdict(
                PrioritizedFieldQueuePacket(
                    document_id=document_id,
                    field_name=field_name,
                    queue_rank=0,
                    priority_score=int(policy.get("priority_score") or 0),
                    priority_band=str(policy.get("priority_band") or "LOW"),
                    priority_reason=list(policy.get("priority_reason", [])),
                    current_status=status,
                    conflict_level=str(conflict.get("conflict_level") or bundle.get("conflict_level") or "UNKNOWN"),
                    confidence_band=str(confidence.get("confidence_band") or "UNKNOWN"),
                    recommended_action=str(confidence.get("recommended_action") or bundle.get("recommended_action") or "REVIEW"),
                    attention_state=str(policy.get("attention_state") or "CLEAR"),
                )
            )
        )

    queue_rows.sort(
        key=lambda item: (
            -(item.get("priority_score") or 0),
            0 if item.get("attention_state") == "UNRESOLVED" else 1 if item.get("attention_state") == "ATTENTION" else 2,
            item.get("field_name") or "",
        )
    )
    for idx, item in enumerate(queue_rows, start=1):
        item["queue_rank"] = idx
    return queue_rows


def validate_passport_review_fields(fields: Dict[str, Any], evidence: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}

    birth_value, birth_date = _normalize_date(fields.get("crew.date_of_birth"))
    issue_value, issue_date = _normalize_date(fields.get("passport.issue_date"))
    expiry_value, expiry_date = _normalize_date(fields.get("passport.expiry_date"))

    packets["passport.number"] = asdict(_validate_passport_number(str(fields.get("passport.number") or ""), evidence.get("passport.number") or {}))
    packets["crew.surname"] = asdict(_validate_name_field("crew.surname", str(fields.get("crew.surname") or "")))
    packets["crew.given_names"] = asdict(_validate_name_field("crew.given_names", str(fields.get("crew.given_names") or "")))
    packets["crew.nationality"] = asdict(_validate_nationality(str(fields.get("crew.nationality") or "")))
    packets["crew.date_of_birth"] = asdict(_validate_birth_date(str(fields.get("crew.date_of_birth") or ""), birth_value, birth_date))
    packets["passport.issue_date"] = asdict(_validate_date_field("passport.issue_date", str(fields.get("passport.issue_date") or ""), issue_value, issue_date))
    packets["passport.expiry_date"] = asdict(
        _validate_expiry_date(
            str(fields.get("passport.expiry_date") or ""),
            expiry_value,
            expiry_date,
            issue_date,
            birth_date,
        )
    )
    return packets


def score_passport_field_conflicts(
    fields: Dict[str, Any],
    field_evidence: Dict[str, Dict[str, Any]],
    field_validation: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        parsed_value = str(fields.get(field_name) or "")
        evidence = dict(field_evidence.get(field_name) or {})
        validation = dict(field_validation.get(field_name) or {})
        packets[field_name] = asdict(
            _build_conflict_score_packet(
                field_name=field_name,
                parsed_value=parsed_value,
                evidence=evidence,
                validation=validation,
            )
        )

    return packets


def build_passport_field_confidence(
    field_conflicts: Dict[str, Dict[str, Any]],
    field_validation: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    packets: Dict[str, Dict[str, Any]] = {}

    for field_name in PASSPORT_REVIEW_FIELDS:
        conflict = dict(field_conflicts.get(field_name) or {})
        validation = dict(field_validation.get(field_name) or {})
        packets[field_name] = asdict(
            _build_confidence_packet(
                field_name=field_name,
                conflict=conflict,
                validation=validation,
            )
        )

    return packets


def build_passport_review_tce_delta(
    *,
    field_evidence: Dict[str, Dict[str, Any]],
    field_validation: Dict[str, Dict[str, Any]],
    field_conflicts: Dict[str, Dict[str, Any]] | None = None,
    field_confidence: Dict[str, Dict[str, Any]] | None = None,
    candidate_bundles: Dict[str, Dict[str, Any]] | None = None,
    compare_ledger: List[Dict[str, Any]] | None = None,
    selection_mode: str | None = None,
    override_reason: str = "",
    field_statuses: Dict[str, Dict[str, Any]] | None = None,
    unresolved_fields: Dict[str, Dict[str, Any]] | None = None,
    field_policy: Dict[str, Dict[str, Any]] | None = None,
    prioritized_field_queue: List[Dict[str, Any]] | None = None,
    review_focus: str = "passport_evidence_validation",
) -> Dict[str, Any]:
    validation_summary = {"PASS": 0, "WARN": 0, "FAIL": 0, "UNKNOWN": 0}
    for payload in field_validation.values():
        status = str(payload.get("status") or "UNKNOWN")
        validation_summary[status] = validation_summary.get(status, 0) + 1

    evidence_sources = sorted(
        {
            f"{payload.get('source_engine') or 'unknown'}:{payload.get('source_kind') or 'unknown'}:{payload.get('provenance_branch') or 'unknown'}"
            for payload in field_evidence.values()
            if payload
        }
    )

    conflict_summary = {"NONE": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}
    for payload in (field_conflicts or {}).values():
        level = str(payload.get("conflict_level") or "UNKNOWN")
        conflict_summary[level] = conflict_summary.get(level, 0) + 1

    confidence_summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    attention_flags: List[str] = []
    for field_name, payload in (field_confidence or {}).items():
        band = str(payload.get("confidence_band") or "UNKNOWN")
        confidence_summary[band] = confidence_summary.get(band, 0) + 1
        action = str(payload.get("recommended_action") or "")
        if action in {"REVIEW", "HIGH_ATTENTION"}:
            attention_flags.append(f"{field_name}:{action}")

    return {
        "HOW": {
            "validation_summary": validation_summary,
            "validation_fields_checked": list(field_validation.keys()),
            "evidence_sources": evidence_sources,
            "provenance_sources": evidence_sources,
            "conflict_summary": conflict_summary,
            "confidence_summary": confidence_summary,
            "candidate_summary": {
                key: len((bundle or {}).get("candidates", []))
                for key, bundle in (candidate_bundles or {}).items()
            },
            "compare_summary": {
                "ledger_entries": len(compare_ledger or []),
                "fields_compared": sorted({entry.get("field_name") for entry in (compare_ledger or []) if entry.get("field_name")}),
            },
            "selection_mode": selection_mode or "machine_selected",
            "field_resolution_summary": {
                key: (payload or {}).get("status")
                for key, payload in (field_statuses or {}).items()
            },
            "unresolved_fields": sorted((unresolved_fields or {}).keys()),
            "priority_summary": {
                band: len([item for item in (prioritized_field_queue or []) if item.get("priority_band") == band])
                for band in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            },
            "prioritized_fields": [item.get("field_name") for item in (prioritized_field_queue or [])[:5] if item.get("field_name")],
        },
        "WHY": {
            "review_focus": review_focus,
            "attention_flags": attention_flags,
            "override_reason": override_reason,
            "unresolved_reasons": {
                key: (payload or {}).get("unresolved_reason")
                for key, payload in (unresolved_fields or {}).items()
            },
            "priority_reasons": {
                key: (payload or {}).get("priority_reason")
                for key, payload in (field_policy or {}).items()
            },
        },
        "WHEN": {
            "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "compared_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "field_resolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "field_marked_unresolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "prioritized_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }


def _build_conflict_score_packet(
    *,
    field_name: str,
    parsed_value: str,
    evidence: Dict[str, Any],
    validation: Dict[str, Any],
) -> ConflictScorePacket:
    normalized_value = _normalize_compare_value(parsed_value)
    candidates = []
    primary_candidate = _normalize_compare_value(evidence.get("candidate_text") or evidence.get("parsed_value") or parsed_value)
    if primary_candidate:
        candidates.append(
            (
                primary_candidate,
                f"{evidence.get('source_engine') or 'unknown'}:{evidence.get('source_kind') or 'unknown'}:{evidence.get('provenance_branch') or 'unknown'}",
            )
        )

    for alt in evidence.get("alternate_values", []) or []:
        alt_value = _normalize_compare_value(alt.get("value") or alt.get("source_snippet") or alt.get("source_line"))
        if not alt_value:
            continue
        candidates.append(
            (
                alt_value,
                f"{evidence.get('source_engine') or 'unknown'}:{alt.get('source_kind') or 'unknown'}:{alt.get('provenance_branch') or 'unknown'}",
            )
        )

    unique_values = {value for value, _ in candidates if value}
    compared_sources = sorted({source for _, source in candidates if source})
    warning_flags = list(evidence.get("warnings", []) or [])
    rationale: List[str] = []
    agreement_present: Optional[bool] = None
    agreement_source_count = 0
    conflict_level = "UNKNOWN"

    if not normalized_value:
        warning_flags.append("missing_value")
        rationale.append("Field value is missing")
    if not candidates:
        warning_flags.append("missing_evidence")
        rationale.append("No supporting evidence candidates available")
    else:
        agreement_source_count = len({source for value, source in candidates if value == normalized_value})
        agreement_present = agreement_source_count > 0
        if len(unique_values) <= 1 and agreement_source_count >= 1:
            conflict_level = "NONE"
            rationale.append("Available evidence agrees on one value")
        elif agreement_source_count >= 2:
            conflict_level = "LOW"
            rationale.append("Primary value is supported by multiple evidence sources")
        elif agreement_source_count == 1 and len(unique_values) > 1:
            conflict_level = "MEDIUM"
            warning_flags.append("candidate_disagreement")
            rationale.append("Evidence contains differing candidate values")
        else:
            conflict_level = "HIGH"
            warning_flags.append("no_agreeing_source")
            rationale.append("No evidence source clearly supports the current value")

    validation_status = str(validation.get("status") or "UNKNOWN")
    if validation_status == "FAIL":
        warning_flags.append("validation_fail")
        conflict_level = "HIGH"
        rationale.append("Validation failed for this field")
    elif validation_status == "WARN" and conflict_level in {"NONE", "LOW"}:
        conflict_level = "MEDIUM"
        warning_flags.append("validation_warn")
        rationale.append("Validation warning raises review attention")
    elif validation_status == "UNKNOWN" and conflict_level == "UNKNOWN":
        rationale.append("Validation is unavailable")

    return ConflictScorePacket(
        field_name=field_name,
        agreement_present=agreement_present,
        agreement_source_count=agreement_source_count,
        conflict_level=conflict_level,
        compared_sources=compared_sources,
        warning_flags=sorted(set(warning_flags)),
        rationale=rationale,
    )


def _build_confidence_packet(
    *,
    field_name: str,
    conflict: Dict[str, Any],
    validation: Dict[str, Any],
) -> FieldConfidencePacket:
    validation_status = str(validation.get("status") or "UNKNOWN")
    conflict_level = str(conflict.get("conflict_level") or "UNKNOWN")
    agreement_sources = int(conflict.get("agreement_source_count") or 0)
    warning_flags = list(conflict.get("warning_flags", []) or [])
    rationale = list(conflict.get("rationale", []) or [])

    score = 0.45
    if validation_status == "PASS":
        score += 0.25
    elif validation_status == "WARN":
        score -= 0.05
    elif validation_status == "FAIL":
        score -= 0.3

    if conflict_level == "NONE":
        score += 0.25
    elif conflict_level == "LOW":
        score += 0.15
    elif conflict_level == "MEDIUM":
        score -= 0.15
    elif conflict_level == "HIGH":
        score -= 0.3
    else:
        score -= 0.05

    if agreement_sources >= 2:
        score += 0.1
    elif agreement_sources == 0:
        score -= 0.1

    score = max(0.0, min(1.0, round(score, 2)))
    if score >= 0.8:
        confidence_band = "HIGH"
        recommended_action = "ACCEPTABLE"
    elif score >= 0.55:
        confidence_band = "MEDIUM"
        recommended_action = "REVIEW"
    elif score > 0.0:
        confidence_band = "LOW"
        recommended_action = "HIGH_ATTENTION"
    else:
        confidence_band = "UNKNOWN"
        recommended_action = "HIGH_ATTENTION"

    if validation_status == "FAIL" or conflict_level == "HIGH":
        recommended_action = "HIGH_ATTENTION"
    elif conflict_level == "MEDIUM" or validation_status == "WARN":
        recommended_action = "REVIEW"

    rationale.append(f"validation={validation_status}")
    rationale.append(f"conflict={conflict_level}")

    return FieldConfidencePacket(
        field_name=field_name,
        confidence_score=score,
        confidence_band=confidence_band,
        conflict_level=conflict_level,
        agreement_sources=agreement_sources,
        warning_flags=sorted(set(warning_flags)),
        recommended_action=recommended_action,
        rationale=rationale,
    )


def _validate_passport_number(value: str, evidence: Dict[str, Any]) -> ValidationResultPacket:
    value = value.strip().upper()
    messages: List[str] = []
    status = "UNKNOWN"

    if not value:
        return ValidationResultPacket("passport.number", "FAIL", normalized_value=None, validator_messages=["Passport number is empty"])

    if re.fullmatch(r"[A-Z0-9]{6,12}", value):
        status = "PASS"
        messages.append("Passport number format looks sane")
    else:
        status = "WARN"
        messages.append("Passport number format looks unusual")

    mrz_values = [alt.get("value") for alt in evidence.get("alternate_values", []) if alt.get("source_kind") == "mrz_field"]
    if evidence.get("source_kind") == "mrz_field":
        messages.append("MRZ-derived value present")
    elif mrz_values:
        if value in mrz_values:
            messages.append("Agrees with MRZ alternate evidence")
        else:
            status = "WARN"
            messages.append("Does not agree with MRZ alternate evidence")

    return ValidationResultPacket("passport.number", status, normalized_value=value, validator_messages=messages, compared_fields=["mrz"])


def _validate_name_field(field_name: str, value: str) -> ValidationResultPacket:
    value = " ".join(value.split())
    if not value:
        return ValidationResultPacket(field_name, "FAIL", normalized_value=None, validator_messages=["Value is empty"])

    messages = []
    status = "PASS"
    if len(value) < 2:
        status = "WARN"
        messages.append("Value is very short")
    if not re.search(r"[A-Za-z]", value):
        status = "FAIL"
        messages.append("Value has no alphabetic content")
    if not messages:
        messages.append("Name structure looks sane")

    return ValidationResultPacket(field_name, status, normalized_value=value, validator_messages=messages)


def _validate_nationality(value: str) -> ValidationResultPacket:
    value = " ".join(value.upper().split())
    if not value:
        return ValidationResultPacket("crew.nationality", "UNKNOWN", normalized_value=None, validator_messages=["Nationality unavailable"])

    status = "PASS"
    messages = ["Nationality present"]
    if len(value) < 3:
        status = "WARN"
        messages.append("Nationality value is very short")
    if re.search(r"[^A-Z /-]", value):
        status = "WARN"
        messages.append("Nationality contains unusual characters")
    return ValidationResultPacket("crew.nationality", status, normalized_value=value, validator_messages=messages)


def _validate_birth_date(raw_value: str, normalized_value: Optional[str], parsed_date: Optional[datetime]) -> ValidationResultPacket:
    if not raw_value:
        return ValidationResultPacket("crew.date_of_birth", "UNKNOWN", normalized_value=None, validator_messages=["Birth date unavailable"])
    if not parsed_date:
        return ValidationResultPacket("crew.date_of_birth", "FAIL", normalized_value=raw_value, validator_messages=["Birth date could not be normalized"])

    today = datetime.now(timezone.utc).date()
    age_years = today.year - parsed_date.date().year
    status = "PASS"
    messages = ["Birth date parsed successfully"]

    if parsed_date.date() > today:
        status = "FAIL"
        messages.append("Birth date is in the future")
    elif age_years > 100 or age_years < 14:
        status = "WARN"
        messages.append("Birth date is plausible but unusual for crew context")

    return ValidationResultPacket("crew.date_of_birth", status, normalized_value=normalized_value, validator_messages=messages)


def _validate_date_field(field_name: str, raw_value: str, normalized_value: Optional[str], parsed_date: Optional[datetime]) -> ValidationResultPacket:
    if not raw_value:
        return ValidationResultPacket(field_name, "UNKNOWN", normalized_value=None, validator_messages=["Date unavailable"])
    if not parsed_date:
        return ValidationResultPacket(field_name, "WARN", normalized_value=raw_value, validator_messages=["Date could not be normalized"])
    return ValidationResultPacket(field_name, "PASS", normalized_value=normalized_value, validator_messages=["Date parsed successfully"])


def _validate_expiry_date(
    raw_value: str,
    normalized_value: Optional[str],
    expiry_date: Optional[datetime],
    issue_date: Optional[datetime],
    birth_date: Optional[datetime],
) -> ValidationResultPacket:
    if not raw_value:
        return ValidationResultPacket("passport.expiry_date", "UNKNOWN", normalized_value=None, validator_messages=["Expiry date unavailable"])
    if not expiry_date:
        return ValidationResultPacket("passport.expiry_date", "WARN", normalized_value=raw_value, validator_messages=["Expiry date could not be normalized"])

    messages = ["Expiry date parsed successfully"]
    status = "PASS"

    if issue_date and expiry_date <= issue_date:
        status = "FAIL"
        messages.append("Expiry date is not after issue date")
    if birth_date and expiry_date <= birth_date:
        status = "FAIL"
        messages.append("Expiry date is not after birth date")
    if expiry_date.date() < datetime.now(timezone.utc).date():
        status = "WARN" if status != "FAIL" else status
        messages.append("Passport appears expired")

    compared_fields = ["passport.issue_date", "crew.date_of_birth"]
    return ValidationResultPacket("passport.expiry_date", status, normalized_value=normalized_value, validator_messages=messages, compared_fields=compared_fields)


def _normalize_date(value: Any) -> tuple[Optional[str], Optional[datetime]]:
    text = str(value or "").strip()
    if not text:
        return None, None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%d %b %y", "%d %B %y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date().isoformat(), parsed
        except ValueError:
            continue

    return None, None


def _normalize_alternate_value(item: Dict[str, Any], fallback_index: int) -> Dict[str, Any]:
    payload = dict(item or {})
    payload.setdefault("source_snippet", payload.get("source_line") or payload.get("value") or "")
    payload.setdefault("candidate_index", fallback_index)
    payload.setdefault("provenance_branch", _derive_branch(payload))
    payload.setdefault("provenance_path", "alternate_candidate")
    return payload


def _derive_branch(payload: Dict[str, Any]) -> str:
    source_kind = str(payload.get("source_kind") or "")
    source_method = str(payload.get("source_method") or "")
    if source_kind == "mrz_field" or "mrz" in source_method.lower():
        return "mrz"
    if source_kind or source_method:
        return "ocr"
    return "fallback"


def _normalize_compare_value(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _build_candidates_for_field(
    *,
    field_name: str,
    field_value: str,
    evidence: Dict[str, Any],
    validation: Dict[str, Any],
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    primary_value = str(evidence.get("parsed_value") or field_value or evidence.get("candidate_text") or "").strip()
    if primary_value:
        candidates.append(
            asdict(
                FieldCandidatePacket(
                    candidate_id=_candidate_id(field_name, 0, evidence),
                    field_name=field_name,
                    candidate_value=primary_value,
                    normalized_value=_normalize_compare_value(primary_value),
                    source_engine=evidence.get("source_engine"),
                    source_kind=evidence.get("source_kind"),
                    source_method=evidence.get("source_method"),
                    provenance_branch=str(evidence.get("provenance_branch") or "unknown"),
                    provenance_path=str(evidence.get("provenance_path") or "mapped_canonical"),
                    source_line=str(evidence.get("source_line") or ""),
                    source_snippet=str(evidence.get("source_snippet") or evidence.get("candidate_text") or primary_value),
                    candidate_index=evidence.get("candidate_index", 0),
                    validation_status=str(validation.get("status") or "UNKNOWN"),
                    confidence_hint=_confidence_hint(evidence),
                    notes=list(evidence.get("notes", [])),
                    warnings=list(evidence.get("warnings", [])),
                )
            )
        )

    for idx, alt in enumerate(evidence.get("alternate_values", []) or [], start=1):
        candidate_value = str(alt.get("value") or alt.get("source_snippet") or alt.get("source_line") or "").strip()
        if not candidate_value:
            continue
        candidates.append(
            asdict(
                FieldCandidatePacket(
                    candidate_id=_candidate_id(field_name, idx, alt),
                    field_name=field_name,
                    candidate_value=candidate_value,
                    normalized_value=_normalize_compare_value(candidate_value),
                    source_engine=evidence.get("source_engine"),
                    source_kind=alt.get("source_kind"),
                    source_method=alt.get("source_method"),
                    provenance_branch=str(alt.get("provenance_branch") or "unknown"),
                    provenance_path=str(alt.get("provenance_path") or "alternate_candidate"),
                    source_line=str(alt.get("source_line") or ""),
                    source_snippet=str(alt.get("source_snippet") or candidate_value),
                    candidate_index=alt.get("candidate_index", idx),
                    validation_status="UNKNOWN",
                    confidence_hint=_confidence_hint(alt),
                    notes=[],
                    warnings=[],
                )
            )
        )

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for candidate in candidates:
        key = (
            candidate.get("normalized_value"),
            candidate.get("source_kind"),
            candidate.get("source_method"),
            candidate.get("provenance_branch"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _select_candidate(candidates: List[Dict[str, Any]], field_value: str) -> tuple[Optional[str], str]:
    normalized_field = _normalize_compare_value(field_value)
    for candidate in candidates:
        if candidate.get("normalized_value") == normalized_field and normalized_field:
            return candidate.get("candidate_id"), str(candidate.get("candidate_value") or field_value)
    if candidates:
        return candidates[0].get("candidate_id"), str(candidates[0].get("candidate_value") or "")
    return None, str(field_value or "")


def _candidate_id(field_name: str, idx: int, payload: Dict[str, Any]) -> str:
    branch = str(payload.get("provenance_branch") or _derive_branch(payload) or "unknown")
    kind = str(payload.get("source_kind") or "unknown")
    return f"{field_name}::{branch}::{kind}::{idx}"


def _confidence_hint(payload: Dict[str, Any]) -> Optional[float]:
    branch = str(payload.get("provenance_branch") or _derive_branch(payload))
    if branch == "mrz":
        return 0.85
    if branch == "ocr":
        return 0.65
    if branch == "fallback":
        return 0.4
    return None


def _default_unresolved_reason(status: str, recommended_action: str) -> str:
    if status == "UNRESOLVED":
        return "Marked unresolved by operator"
    if recommended_action == "HIGH_ATTENTION":
        return "High-attention field remains unresolved"
    return "Field still pending review"


def _derive_attention_state(
    *,
    field_name: str,
    status: str,
    unresolved_fields: Dict[str, Dict[str, Any]],
    conflict: Dict[str, Any],
    confidence: Dict[str, Any],
    recommended_action: str,
) -> str:
    if field_name in unresolved_fields or status == "UNRESOLVED":
        return "UNRESOLVED"
    conflict_level = str(conflict.get("conflict_level") or "UNKNOWN")
    confidence_band = str(confidence.get("confidence_band") or "UNKNOWN")
    if recommended_action in {"REVIEW", "HIGH_ATTENTION"} or conflict_level in {"MEDIUM", "HIGH"} or confidence_band in {"LOW", "UNKNOWN"}:
        return "ATTENTION"
    return "CLEAR"


def _priority_band(score: int) -> str:
    if score >= 140:
        return "CRITICAL"
    if score >= 95:
        return "HIGH"
    if score >= 55:
        return "MEDIUM"
    return "LOW"
