from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .archive.document_registry import DocumentRegistry
from .models import ReviewQueueItem, TCELiteEnvelope
from .storage import load_review_queue, save_review_queue, utc_now_iso

TRIAGE_ACTION_STATUS = {
    "ACKNOWLEDGE": "ACKNOWLEDGED",
    "PIN": "PINNED",
    "DEFER": "DEFERRED",
    "MARK_FOR_REVIEW": "MARKED_FOR_REVIEW",
    "ESCALATE_NOW": "ESCALATED",
    "CLEAR_TRIAGE_FLAG": "CLEARED",
}
ASSIGNMENT_ACTION_STATUS = {
    "ACCEPT_ROUTING_HINT": "ASSIGNED",
    "ASSIGN_TO_BUCKET": "ASSIGNED",
    "CLEAR_ASSIGNMENT": "CLEARED",
}
WATCH_ACTION_STATUS = {
    "ACKNOWLEDGE_WATCH": "ACKNOWLEDGED",
    "CLEAR_WATCH_ACK": "CLEARED",
}
REMINDER_ACTION_STATUS = {
    "SNOOZE_30M": "SNOOZED",
    "SNOOZE_2H": "SNOOZED",
    "SNOOZE_1D": "SNOOZED",
    "CLEAR_SNOOZE": "CLEARED",
    "MARK_PREP_SENT": "SENT",
    "CLEAR_PREP_STATE": "CLEARED",
}
NOTIFICATION_ACTION_STATUS = {
    "MARK_EMITTED": "EMITTED",
    "MARK_FAILED": "FAILED",
    "CANCEL_NOTIFICATION": "CANCELED",
    "RESTAGE_NOTIFICATION": "READY",
    "RETRY_NOTIFICATION": "READY",
    "CLEAR_FAILED_STATE": "READY",
}
TRANSPORT_ACTION_STATUS = {
    "STAGE_FOR_HANDOFF": "HANDOFF_READY",
    "MARK_HANDOFF_ACCEPTED": "HANDOFF_ACCEPTED",
    "MARK_HANDOFF_REJECTED": "HANDOFF_REJECTED",
    "MARK_HANDOFF_FAILED": "HANDOFF_FAILED",
    "CLEAR_HANDOFF_STATE": "CLEARED",
    "RETRY_HANDOFF": "HANDOFF_READY",
    "REQUEUE_HANDOFF": "HANDOFF_READY",
}
ALERT_ACTION_STATUS = {
    "ACKNOWLEDGE_ALERT": "ACKNOWLEDGED",
    "CLEAR_ALERT": "CLEARED",
    "PIN_ALERT": "ACTIVE",
    "REOPEN_ALERT": "REOPENED",
}
INCIDENT_ACTION_STATUS = {
    "ACK_INCIDENT": "ACKNOWLEDGED",
    "PIN_INCIDENT": "PINNED",
    "CLOSE_INCIDENT": "CLOSED",
    "REOPEN_INCIDENT": "REOPENED",
    "CLEAR_INCIDENT_PIN": "OPEN",
}
EXTERNAL_BRIDGE_ACTION_STATUS = {
    "STAGE_EXPORT": "EXPORT_READY",
    "MARK_EXPORT_ACCEPTED": "EXPORT_ACCEPTED",
    "MARK_EXPORT_REJECTED": "EXPORT_REJECTED",
    "MARK_EXPORT_FAILED": "EXPORT_FAILED",
    "CLEAR_EXPORT_STATE": "EXPORT_SKIPPED",
    "RETRY_EXPORT": "EXPORT_READY",
    "REQUEUE_EXPORT": "EXPORT_READY",
}
INTAKE_ACTION_STATUS = {
    "MARK_INTAKE_ACCEPTED": "INTAKE_ACCEPTED",
    "MARK_INTAKE_REJECTED": "INTAKE_REJECTED",
    "MARK_INTAKE_INVALID": "INTAKE_INVALID",
    "CLEAR_INTAKE_STATE": "INTAKE_SKIPPED",
    "RETRY_INTAKE": "INTAKE_PENDING",
    "REQUEUE_INTAKE": "INTAKE_PENDING",
}
DROPZONE_ACTION_STATUS = {
    "STAGE_TO_DROPZONE": "DROPZONE_STAGED",
    "CHECK_FOR_RECEIPT": "RECEIPT_PENDING",
    "MARK_RECEIPT_ACCEPTED": "RECEIPT_ACCEPTED",
    "MARK_RECEIPT_REJECTED": "RECEIPT_REJECTED",
    "MARK_RECEIPT_FAILED": "RECEIPT_FAILED",
    "CLEAR_HANDSHAKE_STATE": "RECEIPT_MISSING",
    "RESTAGE_TO_DROPZONE": "DROPZONE_STAGED",
    "ARCHIVE_HANDSHAKE": "DROPZONE_WRITTEN",
    "MARK_HANDSHAKE_STALE": "HANDSHAKE_STALE",
    "MARK_RECOVERY_NEEDED": "HANDSHAKE_RECOVERY_NEEDED",
    "RESTAGE_STALE_HANDSHAKE": "HANDSHAKE_RESTAGE_RECOMMENDED",
    "ACK_RECOVERY": "HANDSHAKE_NORMAL",
    "CLEAR_RECOVERY_STATE": "HANDSHAKE_NORMAL",
    "IGNORE_DUPLICATE_RECEIPT": "HANDSHAKE_NORMAL",
    "MARK_RECEIPT_SUPERSEDED": "HANDSHAKE_NORMAL",
}

# Portalis Control Room policy defaults.
SLA_TIMER_DEFAULTS = {
    "attention_unresolved": 20,
    "attention_review": 8,
    "escalation_critical": 35,
    "escalation_high": 20,
    "staleness_aged": 30,
    "staleness_stale": 18,
    "staleness_active": 6,
    "assignment_aging_penalty": 12,
    "assignment_active_relief": -8,
    "routed_unassigned_penalty": 15,
    "triage_deferred_relief": -10,
    "triage_pinned_penalty": 5,
    "triage_ack_relief": -4,
}

SLA_STATE_THRESHOLDS = {
    "breach_min": 70,
    "warning_min": 45,
    "watch_min": 18,
}

REMINDER_STAGE_DEFAULTS = {
    "warning_minutes": 30,
    "breach_minutes": 5,
    "watch_minutes": 120,
    "default_snooze_minutes": {
        "SNOOZE_30M": 30,
        "SNOOZE_2H": 120,
        "SNOOZE_1D": 1440,
    },
}

HANDSHAKE_RECOVERY_DEFAULTS = {
    "stale_written_hours": 4,
    "stale_pending_hours": 2,
    "restage_count_recovery": 2,
}


@dataclass(slots=True)
class EscalationPolicyPacket:
    document_id: str
    field_name: str
    escalation_level: str
    escalation_reason: List[str] = field(default_factory=list)
    trigger_source: List[str] = field(default_factory=list)
    age_context: Dict[str, Any] = field(default_factory=dict)
    conflict_context: Dict[str, Any] = field(default_factory=dict)
    confidence_context: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = "REVIEW"
    override_count: int = 0
    evaluated_at: str = ""


@dataclass(slots=True)
class TriageActionPacket:
    document_id: str
    field_name: str
    triage_action: str
    operator_name: str = "operator"
    triage_note: str = ""
    triage_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class RoutingHintPacket:
    document_id: str
    field_name: str
    routing_bucket: str
    owner_hint: str
    assignment_reason: List[str] = field(default_factory=list)
    priority_context: Dict[str, Any] = field(default_factory=dict)
    escalation_context: Dict[str, Any] = field(default_factory=dict)
    triage_context: Dict[str, Any] = field(default_factory=dict)
    recommended_next_action: str = "REVIEW"
    evaluated_at: str = ""


@dataclass(slots=True)
class AssignmentHintPacket:
    document_id: str
    field_name: str
    assigned_bucket: str
    owner_hint: str
    assignment_status: str
    assigned_at: str = ""
    last_assignment_refresh: str = ""
    assigned_by: str = "operator"
    owner_acknowledged: bool = False
    owner_note: str = ""
    assignment_reason: List[str] = field(default_factory=list)
    routing_bucket: str = ""


@dataclass(slots=True)
class SLAPolicyPacket:
    document_id: str
    field_name: str
    sla_state: str
    watch_level: str
    notification_ready: bool = False
    watch_trigger_reason: List[str] = field(default_factory=list)
    requires_ack: bool = False
    notification_severity: str = "NONE"
    evaluated_at: str = ""


@dataclass(slots=True)
class WatchActionPacket:
    document_id: str
    field_name: str
    watch_action: str
    operator_name: str = "operator"
    watch_note: str = ""
    watch_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class WatchQueuePacket:
    document_id: str
    review_item_id: str
    field_name: str
    watch_level: str
    sla_state: str
    age_hours: float
    age_bucket: str
    staleness_band: str
    escalation_level: str
    routing_bucket: str
    assignment_state: str
    attention_state: str
    notification_ready: bool = False
    watch_trigger_reason: List[str] = field(default_factory=list)
    requires_ack: bool = False
    watch_acknowledged_at: str = ""
    notification_severity: str = "NONE"
    last_updated: str = ""
    created_at: str = ""


@dataclass(slots=True)
class ReminderActionPacket:
    document_id: str
    field_name: str
    reminder_action: str
    operator_name: str = "operator"
    reminder_note: str = ""
    reminder_status: str = ""
    acted_at: str = ""
    snoozed_until: str = ""


@dataclass(slots=True)
class ReminderStagePacket:
    document_id: str
    review_item_id: str
    field_name: str
    reminder_state: str
    reminder_due_at: str = ""
    notification_severity: str = "NONE"
    source_watch_level: str = "NONE"
    source_sla_state: str = "NORMAL"
    notification_ready: bool = False
    requires_ack: bool = False
    snooze_until: str = ""
    staged_reason: List[str] = field(default_factory=list)
    last_updated: str = ""
    created_at: str = ""


@dataclass(slots=True)
class NotificationPrepPacket:
    document_id: str
    field_name: str
    prep_state: str
    prep_reason: List[str] = field(default_factory=list)
    severity: str = "NONE"
    ready_at: str = ""
    sent_at: str = ""
    snoozed_until: str = ""


@dataclass(slots=True)
class NotificationLedgerPacket:
    notification_id: str
    document_id: str
    review_item_id: str
    field_name: str
    prep_state: str
    severity: str = "NONE"
    source_reminder_state: str = "CLEARED"
    source_watch_state: str = ""
    source_sla_state: str = "NORMAL"
    notification_reason: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    is_active: bool = False


@dataclass(slots=True)
class DeliveryAttemptPacket:
    notification_id: str
    attempt_number: int
    attempt_state: str
    attempted_at: str
    channel_hint: str = "CONTROL_ROOM_PREP"
    result_reason: str = ""
    operator_action_source: str = ""
    payload_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NotificationActionPacket:
    document_id: str
    field_name: str
    notification_action: str
    operator_name: str = "operator"
    notification_note: str = ""
    notification_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class TransportRequestPacket:
    notification_id: str
    request_id: str
    document_id: str
    review_item_id: str
    field_name: str
    channel_hint: str
    severity: str = "NONE"
    payload_summary: Dict[str, Any] = field(default_factory=dict)
    handoff_reason: List[str] = field(default_factory=list)
    created_at: str = ""


@dataclass(slots=True)
class TransportResultPacket:
    notification_id: str
    request_id: str
    channel_hint: str
    result_state: str
    result_reason: str = ""
    handed_off_at: str = ""
    adapter_name: str = "PORTALIS_TRANSPORT_ADAPTER"
    adapter_status: str = ""


@dataclass(slots=True)
class TransportActionPacket:
    document_id: str
    field_name: str
    transport_action: str
    operator_name: str = "operator"
    transport_note: str = ""
    transport_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class LocalAlertPacket:
    alert_id: str
    source_notification_id: str
    document_id: str
    review_item_id: str
    field_name: str
    severity: str
    message: str
    alert_state: str
    source_type: str
    created_at: str = ""
    updated_at: str = ""
    acknowledged_at: str = ""
    cleared_at: str = ""
    is_pinned: bool = False
    source_context_summary: Dict[str, Any] = field(default_factory=dict)
    alert_reason: List[str] = field(default_factory=list)


@dataclass(slots=True)
class AlertActionPacket:
    document_id: str
    field_name: str
    alert_action: str
    operator_name: str = "operator"
    alert_note: str = ""
    alert_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class IncidentThreadPacket:
    incident_id: str
    document_id: str
    review_item_id: str
    field_name: str
    source_type: str
    incident_reason: List[str] = field(default_factory=list)
    severity: str = "LOW"
    incident_state: str = "OPEN"
    created_at: str = ""
    updated_at: str = ""
    last_alert_at: str = ""
    occurrence_count: int = 1
    related_alert_ids: List[str] = field(default_factory=list)
    current_alert_id: str = ""
    source_context_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IncidentActionPacket:
    document_id: str
    field_name: str
    incident_action: str
    operator_name: str = "operator"
    incident_note: str = ""
    incident_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class ExternalBridgeExportPacket:
    export_id: str
    incident_id: str
    document_id: str
    review_item_id: str
    field_name: str
    export_type: str
    severity: str
    routing_bucket: str
    owner_bucket: str
    incident_state: str
    escalation_level: str
    watch_state: str
    reminder_state: str
    notification_state: str
    target_hint: str
    source_summary: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass(slots=True)
class ExternalBridgeResultPacket:
    export_id: str
    target_hint: str
    result_state: str
    result_reason: str = ""
    exported_at: str = ""
    adapter_name: str = "PORTALIS_EXTERNAL_BRIDGE"
    adapter_status: str = ""
    export_file_path: str = ""


@dataclass(slots=True)
class ExternalBridgeActionPacket:
    document_id: str
    field_name: str
    bridge_action: str
    operator_name: str = "operator"
    bridge_note: str = ""
    bridge_status: str = ""
    acted_at: str = ""
    target_hint: str = ""


@dataclass(slots=True)
class IntakeValidationPacket:
    intake_id: str
    export_id: str
    validation_state: str
    validation_messages: List[str] = field(default_factory=list)
    validated_at: str = ""
    contract_version: str = "portalis-intake-v1"


@dataclass(slots=True)
class IntakeContractPacket:
    intake_id: str
    export_id: str
    export_type: str
    target_hint: str
    document_id: str
    review_item_id: str
    field_name: str
    incident_id: str = ""
    received_at: str = ""
    source_summary: Dict[str, Any] = field(default_factory=dict)
    contract_version: str = "portalis-intake-v1"
    validation: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IntakeAckPacket:
    intake_id: str
    export_id: str
    ack_state: str
    ack_reason: str = ""
    acknowledged_at: str = ""
    receiver_name: str = "PORTALIS_INTAKE"
    receiver_status: str = ""


@dataclass(slots=True)
class IntakeActionPacket:
    document_id: str
    field_name: str
    intake_action: str
    operator_name: str = "operator"
    intake_note: str = ""
    intake_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class DropZoneHandshakePacket:
    handshake_id: str
    export_id: str
    intake_id: str = ""
    target_hint: str = "COUPLER_DROP"
    dropzone_path: str = ""
    payload_filename: str = ""
    handshake_state: str = "DROPZONE_STAGED"
    staged_at: str = ""
    last_checked_at: str = ""
    archive_path: str = ""


@dataclass(slots=True)
class DropZoneReceiptPacket:
    handshake_id: str
    export_id: str
    receipt_state: str
    receipt_reason: str = ""
    receipt_filename: str = ""
    received_at: str = ""
    receiver_name: str = "PORTALIS_DROPZONE"
    receiver_status: str = ""
    receipt_path: str = ""
    archived_path: str = ""


@dataclass(slots=True)
class DropZoneActionPacket:
    document_id: str
    field_name: str
    handshake_action: str
    operator_name: str = "operator"
    handshake_note: str = ""
    handshake_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class ReceiptReconciliationPacket:
    handshake_id: str
    export_id: str
    latest_receipt_state: str
    receipt_count: int = 0
    duplicate_detected: bool = False
    conflicting_receipts: bool = False
    duplicate_receipt_count: int = 0
    latest_receipt_filename: str = ""
    recovery_state: str = "HANDSHAKE_NORMAL"
    recovery_reason: List[str] = field(default_factory=list)
    restage_recommended: bool = False
    reconciled_at: str = ""


@dataclass(slots=True)
class HandshakeRecoveryPacket:
    handshake_id: str
    export_id: str
    recovery_state: str
    recovery_reason: List[str] = field(default_factory=list)
    restage_recommended: bool = False
    stale_detected: bool = False
    receipt_count: int = 0
    marked_at: str = ""


@dataclass(slots=True)
class RecoveryActionPacket:
    document_id: str
    field_name: str
    recovery_action: str
    operator_name: str = "operator"
    recovery_note: str = ""
    recovery_status: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class GlobalReviewQueuePacket:
    document_id: str
    review_item_id: str
    document_type: str
    field_name: str
    queue_rank: int
    priority_score: int
    priority_band: str
    attention_state: str
    current_status: str
    conflict_level: str
    confidence_band: str
    recommended_action: str
    last_updated: str
    created_at: str
    age_hours: float
    age_bucket: str
    staleness_band: str
    escalation_level: str = "NONE"
    escalation_reason: List[str] = field(default_factory=list)
    triage_status: str = ""
    triage_action: str = ""
    triage_note: str = ""
    triaged_at: str = ""
    routing_bucket: str = "CLEAR_NO_ROUTING"
    owner_hint: str = "OPERATOR"
    assignment_reason: List[str] = field(default_factory=list)
    assignment_status: str = ""
    assigned_bucket: str = ""
    assigned_owner_hint: str = ""
    assigned_at: str = ""
    assignment_note: str = ""
    sla_state: str = "NORMAL"
    watch_level: str = "NONE"
    notification_ready: bool = False
    requires_watch_ack: bool = False
    notification_severity: str = "NONE"


@dataclass(slots=True)
class DashboardSummaryPacket:
    total_pending_review_documents: int
    total_unresolved_fields: int
    total_attention_fields: int
    total_high_escalation_fields: int = 0
    total_critical_escalation_fields: int = 0
    total_routed_fields: int = 0
    total_assigned_fields: int = 0
    total_unassigned_escalated_fields: int = 0
    total_watch_items: int = 0
    total_warning_watch_items: int = 0
    total_breach_watch_items: int = 0
    total_reminder_ready_items: int = 0
    total_reminder_snoozed_items: int = 0
    total_reminder_sent_items: int = 0
    total_notification_ready_items: int = 0
    total_notification_emitted_items: int = 0
    total_notification_failed_items: int = 0
    total_notification_canceled_items: int = 0
    total_transport_ready_items: int = 0
    total_transport_accepted_items: int = 0
    total_transport_failed_items: int = 0
    total_transport_rejected_items: int = 0
    total_active_alerts: int = 0
    total_acknowledged_alerts: int = 0
    total_cleared_alerts: int = 0
    total_pinned_alerts: int = 0
    total_open_incidents: int = 0
    total_acknowledged_incidents: int = 0
    total_closed_incidents: int = 0
    total_pinned_incidents: int = 0
    total_export_ready_items: int = 0
    total_export_accepted_items: int = 0
    total_export_failed_items: int = 0
    total_export_rejected_items: int = 0
    total_intake_pending_items: int = 0
    total_intake_accepted_items: int = 0
    total_intake_rejected_items: int = 0
    total_intake_invalid_items: int = 0
    total_dropzone_staged_items: int = 0
    total_receipt_pending_items: int = 0
    total_receipt_accepted_items: int = 0
    total_receipt_rejected_items: int = 0
    total_receipt_failed_items: int = 0
    total_stale_handshake_items: int = 0
    total_recovery_needed_items: int = 0
    total_duplicate_receipt_items: int = 0
    highest_priority_items: List[Dict[str, Any]] = field(default_factory=list)
    oldest_pending_documents: List[Dict[str, Any]] = field(default_factory=list)
    escalated_items: List[Dict[str, Any]] = field(default_factory=list)
    routed_items: List[Dict[str, Any]] = field(default_factory=list)
    watch_items: List[Dict[str, Any]] = field(default_factory=list)
    reminder_items: List[Dict[str, Any]] = field(default_factory=list)
    notification_items: List[Dict[str, Any]] = field(default_factory=list)
    transport_items: List[Dict[str, Any]] = field(default_factory=list)
    alert_items: List[Dict[str, Any]] = field(default_factory=list)
    incident_items: List[Dict[str, Any]] = field(default_factory=list)
    export_items: List[Dict[str, Any]] = field(default_factory=list)
    intake_items: List[Dict[str, Any]] = field(default_factory=list)
    dropzone_items: List[Dict[str, Any]] = field(default_factory=list)


def apply_triage_action(portalis_root: str | Path, *, document_id: str, field_name: str, triage_action: str, operator_name: str = "operator", triage_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(triage_action or "").strip().upper()
    if action not in TRIAGE_ACTION_STATUS:
        raise ValueError(f"Unsupported triage action: {triage_action}")
    items = load_review_queue(root)
    matched_item = _find_review_item(items, document_id)
    acted_at = utc_now_iso()
    packet = asdict(TriageActionPacket(document_id=document_id, field_name=field_name, triage_action=action, operator_name=operator_name or "operator", triage_note=triage_note or "", triage_status=TRIAGE_ACTION_STATUS[action], acted_at=acted_at))
    matched_item.triage_actions = list(matched_item.triage_actions or []) + [packet]
    triage_state = dict(matched_item.triage_state or {})
    if action == "CLEAR_TRIAGE_FLAG":
        triage_state.pop(field_name, None)
    else:
        triage_state[field_name] = packet
    matched_item.triage_state = triage_state
    matched_item.updated_at = acted_at
    save_review_queue(root, items)
    refreshed = refresh_control_room_state(root)
    return _control_room_action_result(refreshed, document_id, field_name, "triage_packet", packet)


def apply_assignment_action(portalis_root: str | Path, *, document_id: str, field_name: str, assignment_action: str, operator_name: str = "operator", assignment_note: str = "", assigned_bucket: str = "", owner_hint: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(assignment_action or "").strip().upper()
    if action not in ASSIGNMENT_ACTION_STATUS:
        raise ValueError(f"Unsupported assignment action: {assignment_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    routing_by_document = refreshed["routing_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    routing_hint = dict((routing_by_document.get(document_id, {}) or {}).get(field_name, {}) or {})
    acted_at = utc_now_iso()
    assignment_actions = list(matched_item.assignment_actions or [])
    assignment_state = dict(matched_item.assignment_state or {})
    if action == "CLEAR_ASSIGNMENT":
        packet = asdict(AssignmentHintPacket(document_id=document_id, field_name=field_name, assigned_bucket="", owner_hint="", assignment_status="CLEARED", assigned_at=acted_at, last_assignment_refresh=acted_at, assigned_by=operator_name or "operator", owner_note=assignment_note or "", assignment_reason=["manual assignment cleared"], routing_bucket=str(routing_hint.get("routing_bucket") or "")))
        assignment_state.pop(field_name, None)
    else:
        bucket_value = assigned_bucket or str(routing_hint.get("routing_bucket") or "CLEAR_NO_ROUTING")
        owner_value = owner_hint or str(routing_hint.get("owner_hint") or _owner_hint_from_bucket(bucket_value))
        packet = asdict(AssignmentHintPacket(document_id=document_id, field_name=field_name, assigned_bucket=bucket_value, owner_hint=owner_value, assignment_status=ASSIGNMENT_ACTION_STATUS[action], assigned_at=acted_at, last_assignment_refresh=acted_at, assigned_by=operator_name or "operator", owner_note=assignment_note or "", assignment_reason=list(routing_hint.get("assignment_reason", [])), routing_bucket=str(routing_hint.get("routing_bucket") or bucket_value)))
        assignment_state[field_name] = packet
    assignment_actions.append(dict(packet, assignment_action=action))
    matched_item.assignment_actions = assignment_actions
    matched_item.assignment_state = assignment_state
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "assignment_packet", packet)


def apply_watch_action(portalis_root: str | Path, *, document_id: str, field_name: str, watch_action: str, operator_name: str = "operator", watch_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(watch_action or "").strip().upper()
    if action not in WATCH_ACTION_STATUS:
        raise ValueError(f"Unsupported watch action: {watch_action}")
    items = load_review_queue(root)
    matched_item = _find_review_item(items, document_id)
    acted_at = utc_now_iso()
    packet = asdict(WatchActionPacket(document_id=document_id, field_name=field_name, watch_action=action, operator_name=operator_name or "operator", watch_note=watch_note or "", watch_status=WATCH_ACTION_STATUS[action], acted_at=acted_at))
    matched_item.watch_actions = list(matched_item.watch_actions or []) + [packet]
    watch_state = dict(matched_item.watch_state or {})
    if action == "CLEAR_WATCH_ACK":
        watch_state.pop(field_name, None)
    else:
        watch_state[field_name] = {
            "watch_status": "ACKNOWLEDGED",
            "watch_acknowledged_at": acted_at,
            "operator_name": operator_name or "operator",
            "watch_note": watch_note or "",
        }
    matched_item.watch_state = watch_state
    matched_item.updated_at = acted_at
    save_review_queue(root, items)
    refreshed = refresh_control_room_state(root)
    return _control_room_action_result(refreshed, document_id, field_name, "watch_packet", packet)


def apply_reminder_action(portalis_root: str | Path, *, document_id: str, field_name: str, reminder_action: str, operator_name: str = "operator", reminder_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(reminder_action or "").strip().upper()
    if action not in REMINDER_ACTION_STATUS:
        raise ValueError(f"Unsupported reminder action: {reminder_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    reminder_by_document = refreshed["reminder_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    reminder_stage = dict((reminder_by_document.get(document_id, {}) or {}).get(field_name, {}) or {})
    acted_at = utc_now_iso()
    reminder_actions = list(matched_item.reminder_actions or [])
    notification_prep = dict(matched_item.notification_prep or {})

    snoozed_until = ""
    if action in REMINDER_STAGE_DEFAULTS["default_snooze_minutes"]:
        snoozed_until = _offset_iso(acted_at, REMINDER_STAGE_DEFAULTS["default_snooze_minutes"][action])
        notification_prep[field_name] = asdict(
            NotificationPrepPacket(
                document_id=document_id,
                field_name=field_name,
                prep_state="SNOOZED",
                prep_reason=["operator snoozed reminder prep"],
                severity=str(reminder_stage.get("notification_severity") or "NONE"),
                ready_at=str(reminder_stage.get("reminder_due_at") or acted_at),
                snoozed_until=snoozed_until,
            )
        )
    elif action == "MARK_PREP_SENT":
        notification_prep[field_name] = asdict(
            NotificationPrepPacket(
                document_id=document_id,
                field_name=field_name,
                prep_state="SENT",
                prep_reason=["operator marked prep as sent"],
                severity=str(reminder_stage.get("notification_severity") or "NONE"),
                ready_at=str(reminder_stage.get("reminder_due_at") or acted_at),
                sent_at=acted_at,
            )
        )
    elif action in {"CLEAR_SNOOZE", "CLEAR_PREP_STATE"}:
        notification_prep.pop(field_name, None)

    packet = asdict(
        ReminderActionPacket(
            document_id=document_id,
            field_name=field_name,
            reminder_action=action,
            operator_name=operator_name or "operator",
            reminder_note=reminder_note or "",
            reminder_status=REMINDER_ACTION_STATUS[action],
            acted_at=acted_at,
            snoozed_until=snoozed_until,
        )
    )
    reminder_actions.append(packet)
    matched_item.reminder_actions = reminder_actions
    matched_item.notification_prep = notification_prep
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "reminder_packet", packet)


def apply_notification_action(portalis_root: str | Path, *, document_id: str, field_name: str, notification_action: str, operator_name: str = "operator", notification_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(notification_action or "").strip().upper()
    if action not in NOTIFICATION_ACTION_STATUS:
        raise ValueError(f"Unsupported notification action: {notification_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    notification_by_document = refreshed["notification_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    notification_ledger = dict(matched_item.notification_ledger or {})
    delivery_attempts = dict(matched_item.delivery_attempts or {})
    acted_at = utc_now_iso()
    action_packet = asdict(
        NotificationActionPacket(
            document_id=document_id,
            field_name=field_name,
            notification_action=action,
            operator_name=operator_name or "operator",
            notification_note=notification_note or "",
            notification_status=NOTIFICATION_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.notification_actions = list(matched_item.notification_actions or []) + [action_packet]
    current_entry = dict((notification_by_document.get(document_id, {}) or {}).get(field_name, {}) or notification_ledger.get(field_name, {}))
    if not current_entry:
        current_entry = asdict(
            NotificationLedgerPacket(
                notification_id=_notification_id(document_id, field_name),
                document_id=document_id,
                review_item_id=document_id,
                field_name=field_name,
                prep_state="READY",
                created_at=acted_at,
                updated_at=acted_at,
                is_active=True,
            )
        )
    current_entry["updated_at"] = acted_at
    current_entry["is_active"] = action not in {"CANCEL_NOTIFICATION"} and current_entry.get("source_reminder_state") != "CLEARED"
    attempts = list(delivery_attempts.get(field_name, []) or [])

    if action == "MARK_EMITTED":
        current_entry["prep_state"] = "EMITTED"
        current_entry["is_active"] = False
        attempts.append(asdict(DeliveryAttemptPacket(
            notification_id=str(current_entry.get("notification_id") or _notification_id(document_id, field_name)),
            attempt_number=len(attempts) + 1,
            attempt_state="EMITTED",
            attempted_at=acted_at,
            result_reason=notification_note or "operator marked emitted",
            operator_action_source=action,
            payload_summary={"field_name": field_name, "severity": current_entry.get("severity")},
        )))
    elif action == "MARK_FAILED":
        current_entry["prep_state"] = "FAILED"
        current_entry["is_active"] = True
        attempts.append(asdict(DeliveryAttemptPacket(
            notification_id=str(current_entry.get("notification_id") or _notification_id(document_id, field_name)),
            attempt_number=len(attempts) + 1,
            attempt_state="FAILED",
            attempted_at=acted_at,
            result_reason=notification_note or "operator marked failed",
            operator_action_source=action,
            payload_summary={"field_name": field_name, "severity": current_entry.get("severity")},
        )))
    elif action == "CANCEL_NOTIFICATION":
        current_entry["prep_state"] = "CANCELED"
        current_entry["is_active"] = False
    else:
        current_entry["prep_state"] = "READY"
        current_entry["is_active"] = True
        current_entry["updated_at"] = acted_at

    notification_ledger[field_name] = current_entry
    delivery_attempts[field_name] = attempts
    matched_item.notification_ledger = notification_ledger
    matched_item.delivery_attempts = delivery_attempts
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "notification_packet", action_packet)


def apply_transport_action(portalis_root: str | Path, *, document_id: str, field_name: str, transport_action: str, operator_name: str = "operator", transport_note: str = "", channel_hint: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(transport_action or "").strip().upper()
    if action not in TRANSPORT_ACTION_STATUS:
        raise ValueError(f"Unsupported transport action: {transport_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    transport_by_document = refreshed["transport_by_document"]
    notification_by_document = refreshed["notification_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    transport_requests = dict(matched_item.transport_requests or {})
    transport_results = dict(matched_item.transport_results or {})
    matched_item.transport_actions = list(matched_item.transport_actions or [])
    acted_at = utc_now_iso()

    request_payload = dict((transport_by_document.get(document_id, {}) or {}).get(field_name, {}) or (transport_requests.get(field_name) or {}))
    notification_payload = dict((notification_by_document.get(document_id, {}) or {}).get(field_name, {}) or {})
    current_channel = channel_hint or str(request_payload.get("channel_hint") or _derive_channel_hint(
        severity=str(notification_payload.get("severity") or "NONE"),
        source_sla_state=str(notification_payload.get("source_sla_state") or "NORMAL"),
        source_reminder_state=str(notification_payload.get("source_reminder_state") or "CLEARED"),
    ))

    action_packet = asdict(
        TransportActionPacket(
            document_id=document_id,
            field_name=field_name,
            transport_action=action,
            operator_name=operator_name or "operator",
            transport_note=transport_note or "",
            transport_status=TRANSPORT_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.transport_actions.append(action_packet)

    if action == "CLEAR_HANDOFF_STATE":
        transport_requests.pop(field_name, None)
    else:
        request_id = str(request_payload.get("request_id") or _transport_request_id(document_id, field_name))
        transport_requests[field_name] = asdict(
            TransportRequestPacket(
                notification_id=str(request_payload.get("notification_id") or notification_payload.get("notification_id") or _notification_id(document_id, field_name)),
                request_id=request_id,
                document_id=document_id,
                review_item_id=document_id,
                field_name=field_name,
                channel_hint=current_channel,
                severity=str(notification_payload.get("severity") or request_payload.get("severity") or "NONE"),
                payload_summary=dict(request_payload.get("payload_summary") or {
                    "field_name": field_name,
                    "prep_state": notification_payload.get("prep_state"),
                    "severity": notification_payload.get("severity"),
                }),
                handoff_reason=list(notification_payload.get("notification_reason", request_payload.get("handoff_reason", []))),
                created_at=str(request_payload.get("created_at") or acted_at),
            )
        )

    if action != "CLEAR_HANDOFF_STATE":
        request_id = str((transport_requests.get(field_name) or {}).get("request_id") or request_payload.get("request_id") or _transport_request_id(document_id, field_name))
        result_state = TRANSPORT_ACTION_STATUS[action]
        result_packet = asdict(
            TransportResultPacket(
                notification_id=str(request_payload.get("notification_id") or notification_payload.get("notification_id") or _notification_id(document_id, field_name)),
                request_id=request_id,
                channel_hint=current_channel,
                result_state=result_state,
                result_reason=transport_note or _transport_result_reason(action),
                handed_off_at=acted_at,
                adapter_name="PORTALIS_TRANSPORT_ADAPTER",
                adapter_status="ACTIVE" if result_state in {"HANDOFF_READY", "HANDOFF_ACCEPTED"} else "ATTENTION",
            )
        )
        field_results = list(transport_results.get(field_name, []) or [])
        field_results.append(result_packet)
        transport_results[field_name] = field_results

        delivery_state = result_state
        attempts = list((matched_item.delivery_attempts or {}).get(field_name, []) or [])
        attempts.append(asdict(DeliveryAttemptPacket(
            notification_id=str(request_payload.get("notification_id") or notification_payload.get("notification_id") or _notification_id(document_id, field_name)),
            attempt_number=len(attempts) + 1,
            attempt_state=delivery_state,
            attempted_at=acted_at,
            channel_hint=current_channel,
            result_reason=transport_note or _transport_result_reason(action),
            operator_action_source=action,
            payload_summary={"field_name": field_name, "request_id": request_id, "channel_hint": current_channel},
        )))
        matched_item.delivery_attempts = dict(matched_item.delivery_attempts or {})
        matched_item.delivery_attempts[field_name] = attempts

    matched_item.transport_requests = transport_requests
    matched_item.transport_results = transport_results
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "transport_packet", action_packet)


def apply_alert_action(portalis_root: str | Path, *, document_id: str, field_name: str, alert_action: str, operator_name: str = "operator", alert_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(alert_action or "").strip().upper()
    if action not in ALERT_ACTION_STATUS:
        raise ValueError(f"Unsupported alert action: {alert_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    alert_by_document = refreshed["alert_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    local_alerts = dict(matched_item.local_alerts or {})
    current_alert = dict((alert_by_document.get(document_id, {}) or {}).get(field_name, {}) or local_alerts.get(field_name, {}))
    acted_at = utc_now_iso()
    packet = asdict(
        AlertActionPacket(
            document_id=document_id,
            field_name=field_name,
            alert_action=action,
            operator_name=operator_name or "operator",
            alert_note=alert_note or "",
            alert_status=ALERT_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.alert_actions = list(matched_item.alert_actions or []) + [packet]
    if current_alert:
        current_alert["updated_at"] = acted_at
        current_alert["alert_reason"] = list(current_alert.get("alert_reason", []))
        current_alert["source_context_summary"] = dict(current_alert.get("source_context_summary", {}))
        if action == "ACKNOWLEDGE_ALERT":
            current_alert["alert_state"] = "ACKNOWLEDGED"
            current_alert["acknowledged_at"] = acted_at
        elif action == "CLEAR_ALERT":
            current_alert["alert_state"] = "CLEARED"
            current_alert["cleared_at"] = acted_at
        elif action == "PIN_ALERT":
            current_alert["is_pinned"] = True
        elif action == "REOPEN_ALERT":
            current_alert["alert_state"] = "REOPENED"
            current_alert["cleared_at"] = ""
        local_alerts[field_name] = current_alert
    matched_item.local_alerts = local_alerts
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "alert_packet", packet)


def apply_incident_action(portalis_root: str | Path, *, document_id: str, field_name: str, incident_action: str, operator_name: str = "operator", incident_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(incident_action or "").strip().upper()
    if action not in INCIDENT_ACTION_STATUS:
        raise ValueError(f"Unsupported incident action: {incident_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    incident_by_document = refreshed["incident_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    incident_threads = dict(matched_item.incident_threads or {})
    current_incident = dict((incident_by_document.get(document_id, {}) or {}).get(field_name, {}) or incident_threads.get(field_name, {}))
    acted_at = utc_now_iso()
    packet = asdict(
        IncidentActionPacket(
            document_id=document_id,
            field_name=field_name,
            incident_action=action,
            operator_name=operator_name or "operator",
            incident_note=incident_note or "",
            incident_status=INCIDENT_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.incident_actions = list(matched_item.incident_actions or []) + [packet]
    if current_incident:
        current_incident["updated_at"] = acted_at
        if action == "ACK_INCIDENT":
            current_incident["incident_state"] = "ACKNOWLEDGED"
            current_incident["acknowledged_at"] = acted_at
        elif action == "PIN_INCIDENT":
            current_incident["incident_state"] = "PINNED"
            current_incident["is_pinned"] = True
        elif action == "CLOSE_INCIDENT":
            current_incident["incident_state"] = "CLOSED"
            current_incident["closed_at"] = acted_at
        elif action == "REOPEN_INCIDENT":
            current_incident["incident_state"] = "REOPENED"
            current_incident["closed_at"] = ""
        elif action == "CLEAR_INCIDENT_PIN":
            current_incident["is_pinned"] = False
            if str(current_incident.get("incident_state") or "") == "PINNED":
                current_incident["incident_state"] = "OPEN"
        if incident_note:
            current_incident["incident_note"] = incident_note
        incident_threads[field_name] = current_incident
    matched_item.incident_threads = incident_threads
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "incident_packet", packet)


def apply_external_bridge_action(portalis_root: str | Path, *, document_id: str, field_name: str, bridge_action: str, operator_name: str = "operator", bridge_note: str = "", target_hint: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(bridge_action or "").strip().upper()
    if action not in EXTERNAL_BRIDGE_ACTION_STATUS:
        raise ValueError(f"Unsupported external bridge action: {bridge_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    export_by_document = refreshed["export_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    export_state = dict(matched_item.external_bridge_exports or {})
    result_state = dict(matched_item.external_bridge_results or {})
    current_export = dict((export_by_document.get(document_id, {}) or {}).get(field_name, {}) or export_state.get(field_name, {}))
    acted_at = utc_now_iso()
    current_target = str(target_hint or current_export.get("target_hint") or "LOCAL_EXPORT_FILE")
    packet = asdict(
        ExternalBridgeActionPacket(
            document_id=document_id,
            field_name=field_name,
            bridge_action=action,
            operator_name=operator_name or "operator",
            bridge_note=bridge_note or "",
            bridge_status=EXTERNAL_BRIDGE_ACTION_STATUS[action],
            acted_at=acted_at,
            target_hint=current_target,
        )
    )
    matched_item.external_bridge_actions = list(matched_item.external_bridge_actions or []) + [packet]
    if action == "CLEAR_EXPORT_STATE":
        export_state.pop(field_name, None)
    elif current_export:
        current_export["created_at"] = str(current_export.get("created_at") or acted_at)
        current_export["target_hint"] = current_target
        export_state[field_name] = current_export

    result_reason = bridge_note or _external_bridge_result_reason(action)
    if action != "CLEAR_EXPORT_STATE":
        result_packet = asdict(
            ExternalBridgeResultPacket(
                export_id=str((export_state.get(field_name) or {}).get("export_id") or current_export.get("export_id") or _external_export_id(document_id, field_name)),
                target_hint=current_target,
                result_state=EXTERNAL_BRIDGE_ACTION_STATUS[action],
                result_reason=result_reason,
                exported_at=acted_at,
                adapter_name="PORTALIS_EXTERNAL_BRIDGE",
                adapter_status="ACTIVE" if EXTERNAL_BRIDGE_ACTION_STATUS[action] in {"EXPORT_READY", "EXPORT_ACCEPTED"} else "ATTENTION",
                export_file_path=str((result_state.get(field_name) or {}).get("export_file_path") or ""),
            )
        )
        if action in {"STAGE_EXPORT", "RETRY_EXPORT", "REQUEUE_EXPORT"}:
            export_packet = dict(export_state.get(field_name, {}) or current_export or {})
            if export_packet:
                export_file_path = _write_external_bridge_export(root, export_packet, target_hint=current_target)
                result_packet["export_file_path"] = str(export_file_path)
                export_state[field_name] = dict(export_packet, export_file_path=str(export_file_path))
        result_state[field_name] = result_packet
    else:
        result_state[field_name] = asdict(
            ExternalBridgeResultPacket(
                export_id=str(current_export.get("export_id") or _external_export_id(document_id, field_name)),
                target_hint=current_target,
                result_state="EXPORT_SKIPPED",
                result_reason=result_reason,
                exported_at=acted_at,
                adapter_name="PORTALIS_EXTERNAL_BRIDGE",
                adapter_status="CLEARED",
            )
        )

    matched_item.external_bridge_exports = export_state
    matched_item.external_bridge_results = result_state
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "external_bridge_packet", packet)


def apply_intake_action(portalis_root: str | Path, *, document_id: str, field_name: str, intake_action: str, operator_name: str = "operator", intake_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(intake_action or "").strip().upper()
    if action not in INTAKE_ACTION_STATUS:
        raise ValueError(f"Unsupported intake action: {intake_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    intake_by_document = refreshed["intake_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    intake_contracts = dict(matched_item.intake_contracts or {})
    intake_acks = dict(matched_item.intake_acks or {})
    current_intake = dict((intake_by_document.get(document_id, {}) or {}).get(field_name, {}) or intake_contracts.get(field_name, {}))
    acted_at = utc_now_iso()
    packet = asdict(
        IntakeActionPacket(
            document_id=document_id,
            field_name=field_name,
            intake_action=action,
            operator_name=operator_name or "operator",
            intake_note=intake_note or "",
            intake_status=INTAKE_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.intake_actions = list(matched_item.intake_actions or []) + [packet]
    if action == "CLEAR_INTAKE_STATE":
        intake_contracts.pop(field_name, None)
    elif current_intake:
        intake_contracts[field_name] = current_intake
    export_id = str((current_intake.get("export_id") or ""))
    if current_intake or action == "CLEAR_INTAKE_STATE":
        intake_acks[field_name] = asdict(
            IntakeAckPacket(
                intake_id=str(current_intake.get("intake_id") or _intake_id(document_id, field_name)),
                export_id=export_id,
                ack_state=INTAKE_ACTION_STATUS[action],
                ack_reason=intake_note or _intake_result_reason(action),
                acknowledged_at=acted_at,
                receiver_name=operator_name or "PORTALIS_INTAKE",
                receiver_status="ACTIVE" if INTAKE_ACTION_STATUS[action] in {"INTAKE_PENDING", "INTAKE_ACCEPTED"} else "ATTENTION",
            )
        )
    matched_item.intake_contracts = intake_contracts
    matched_item.intake_acks = intake_acks
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "intake_packet", packet)


def apply_dropzone_action(portalis_root: str | Path, *, document_id: str, field_name: str, handshake_action: str, operator_name: str = "operator", handshake_note: str = "") -> Dict[str, Any]:
    root = Path(portalis_root)
    action = str(handshake_action or "").strip().upper()
    if action not in DROPZONE_ACTION_STATUS:
        raise ValueError(f"Unsupported dropzone action: {handshake_action}")
    refreshed = refresh_control_room_state(root)
    review_items = refreshed["review_items"]
    export_by_document = refreshed["export_by_document"]
    intake_by_document = refreshed["intake_by_document"]
    handshake_by_document = refreshed["dropzone_by_document"]
    matched_item = _find_review_item(review_items, document_id)
    handshakes = dict(matched_item.dropzone_handshakes or {})
    receipts = dict(matched_item.dropzone_receipts or {})
    receipt_history = dict(matched_item.dropzone_receipt_history or {})
    reconciliation_state = dict(matched_item.dropzone_reconciliation or {})
    recovery_state = dict(matched_item.dropzone_recovery or {})
    current_handshake = dict((handshake_by_document.get(document_id, {}) or {}).get(field_name, {}) or handshakes.get(field_name, {}))
    export_payload = dict((export_by_document.get(document_id, {}) or {}).get(field_name, {}) or {})
    intake_payload = dict((intake_by_document.get(document_id, {}) or {}).get(field_name, {}) or {})
    field_history = list(receipt_history.get(field_name, []) or [])
    acted_at = utc_now_iso()
    packet = asdict(
        DropZoneActionPacket(
            document_id=document_id,
            field_name=field_name,
            handshake_action=action,
            operator_name=operator_name or "operator",
            handshake_note=handshake_note or "",
            handshake_status=DROPZONE_ACTION_STATUS[action],
            acted_at=acted_at,
        )
    )
    matched_item.dropzone_actions = list(matched_item.dropzone_actions or []) + [packet]

    if action == "CLEAR_HANDSHAKE_STATE":
        handshakes.pop(field_name, None)
        receipts.pop(field_name, None)
        receipt_history.pop(field_name, None)
        reconciliation_state.pop(field_name, None)
        recovery_state.pop(field_name, None)
    else:
        if not current_handshake and export_payload:
            current_handshake = _build_dropzone_handshake_payload(
                export_payload=export_payload,
                intake_payload=intake_payload,
                existing_payload={},
                root=root,
                staged_at=acted_at,
            )
        elif current_handshake:
            current_handshake["last_checked_at"] = acted_at

        if action in {"STAGE_TO_DROPZONE", "RESTAGE_TO_DROPZONE"}:
            current_handshake = _build_dropzone_handshake_payload(
                export_payload=export_payload or current_handshake,
                intake_payload=intake_payload,
                existing_payload=current_handshake,
                root=root,
                staged_at=acted_at,
            )
            if action == "RESTAGE_TO_DROPZONE":
                current_handshake["restage_count"] = int(current_handshake.get("restage_count") or 0) + 1
            staged_path = _write_dropzone_handshake(root, current_handshake, export_payload, intake_payload)
            current_handshake["payload_filename"] = staged_path.name
            current_handshake["dropzone_path"] = str(staged_path)
            current_handshake["handshake_state"] = "DROPZONE_WRITTEN"
            receipts[field_name] = asdict(
                DropZoneReceiptPacket(
                    handshake_id=str(current_handshake.get("handshake_id") or ""),
                    export_id=str(current_handshake.get("export_id") or ""),
                    receipt_state="RECEIPT_PENDING",
                    receipt_reason=handshake_note or "waiting for drop-zone receipt",
                    receipt_filename="",
                    received_at="",
                    receiver_name="PORTALIS_DROPZONE",
                    receiver_status="PENDING",
                )
            )
            field_history.append(dict(receipts[field_name], action_source=action))
        elif action == "CHECK_FOR_RECEIPT":
            receipt_payloads = _load_dropzone_receipts(root, current_handshake)
            if receipt_payloads:
                field_history.extend(receipt_payloads)
                reconciled = _reconcile_receipt_history(
                    handshake_payload=current_handshake,
                    receipt_history=field_history,
                    now=acted_at,
                )
                latest_effective = dict(reconciled.get("latest_effective_receipt", {}) or {})
                if latest_effective:
                    receipts[field_name] = latest_effective
                    current_handshake["handshake_state"] = str(latest_effective.get("receipt_state") or "RECEIPT_ACCEPTED")
                reconciliation_state[field_name] = dict(reconciled.get("reconciliation", {}) or {})
                recovery_state[field_name] = dict(reconciled.get("recovery", {}) or {})
            else:
                existing_receipt = dict(receipts.get(field_name, {}) or {})
                receipts[field_name] = asdict(
                    DropZoneReceiptPacket(
                        handshake_id=str(current_handshake.get("handshake_id") or _dropzone_handshake_id(document_id, field_name)),
                        export_id=str(current_handshake.get("export_id") or export_payload.get("export_id") or _external_export_id(document_id, field_name)),
                        receipt_state="RECEIPT_MISSING",
                        receipt_reason=handshake_note or "no receipt file found in drop-zone",
                        receipt_filename=str(existing_receipt.get("receipt_filename") or ""),
                        received_at=str(existing_receipt.get("received_at") or ""),
                        receiver_name=str(existing_receipt.get("receiver_name") or "PORTALIS_DROPZONE"),
                        receiver_status="MISSING",
                        receipt_path=str(existing_receipt.get("receipt_path") or ""),
                        archived_path=str(existing_receipt.get("archived_path") or ""),
                    )
                )
                current_handshake["handshake_state"] = "RECEIPT_MISSING"
                field_history.append(dict(receipts[field_name], action_source=action))
        elif action == "ARCHIVE_HANDSHAKE":
            archive_path = _archive_dropzone_outgoing(root, current_handshake)
            current_handshake["archive_path"] = str(archive_path or current_handshake.get("archive_path") or "")
            current_handshake["handshake_state"] = "DROPZONE_WRITTEN"
        else:
            recovery_actions = {"MARK_HANDSHAKE_STALE", "MARK_RECOVERY_NEEDED", "RESTAGE_STALE_HANDSHAKE", "ACK_RECOVERY", "CLEAR_RECOVERY_STATE", "IGNORE_DUPLICATE_RECEIPT", "MARK_RECEIPT_SUPERSEDED"}
            if action in recovery_actions:
                recovery_packet = asdict(
                    HandshakeRecoveryPacket(
                        handshake_id=str(current_handshake.get("handshake_id") or _dropzone_handshake_id(document_id, field_name)),
                        export_id=str(current_handshake.get("export_id") or export_payload.get("export_id") or _external_export_id(document_id, field_name)),
                        recovery_state=DROPZONE_ACTION_STATUS[action],
                        recovery_reason=[handshake_note or _dropzone_result_reason(action)],
                        restage_recommended=action in {"RESTAGE_STALE_HANDSHAKE", "MARK_RECOVERY_NEEDED"},
                        stale_detected=action in {"MARK_HANDSHAKE_STALE", "MARK_RECOVERY_NEEDED", "RESTAGE_STALE_HANDSHAKE"},
                        receipt_count=len(field_history),
                        marked_at=acted_at,
                    )
                )
                recovery_state[field_name] = recovery_packet
                if action == "RESTAGE_STALE_HANDSHAKE":
                    current_handshake["handshake_state"] = "HANDSHAKE_RESTAGE_RECOMMENDED"
                    current_handshake["restage_count"] = int(current_handshake.get("restage_count") or 0) + 1
                elif action in {"ACK_RECOVERY", "CLEAR_RECOVERY_STATE", "IGNORE_DUPLICATE_RECEIPT", "MARK_RECEIPT_SUPERSEDED"}:
                    current_handshake["handshake_state"] = str((receipts.get(field_name) or {}).get("receipt_state") or current_handshake.get("handshake_state") or "DROPZONE_WRITTEN")
                else:
                    current_handshake["handshake_state"] = DROPZONE_ACTION_STATUS[action]
            else:
                receipt_state = DROPZONE_ACTION_STATUS[action]
                receipts[field_name] = asdict(
                    DropZoneReceiptPacket(
                        handshake_id=str(current_handshake.get("handshake_id") or _dropzone_handshake_id(document_id, field_name)),
                        export_id=str(current_handshake.get("export_id") or export_payload.get("export_id") or _external_export_id(document_id, field_name)),
                        receipt_state=receipt_state,
                        receipt_reason=handshake_note or _dropzone_result_reason(action),
                        receipt_filename=str((receipts.get(field_name) or {}).get("receipt_filename") or ""),
                        received_at=acted_at,
                        receiver_name=operator_name or "PORTALIS_DROPZONE",
                        receiver_status="ACTIVE" if receipt_state in {"RECEIPT_ACCEPTED", "RECEIPT_PENDING"} else "ATTENTION",
                        receipt_path=str((receipts.get(field_name) or {}).get("receipt_path") or ""),
                        archived_path=str((receipts.get(field_name) or {}).get("archived_path") or ""),
                    )
                )
                field_history.append(dict(receipts[field_name], action_source=action))
                current_handshake["handshake_state"] = receipt_state

        current_handshake["last_checked_at"] = acted_at
        handshakes[field_name] = current_handshake
        receipt_history[field_name] = field_history
        if field_name not in reconciliation_state:
            reconciled = _reconcile_receipt_history(
                handshake_payload=current_handshake,
                receipt_history=field_history,
                now=acted_at,
            )
            reconciliation_state[field_name] = dict(reconciled.get("reconciliation", {}) or {})
            recovery_state[field_name] = dict(reconciled.get("recovery", recovery_state.get(field_name, {})) or {})

    matched_item.dropzone_handshakes = handshakes
    matched_item.dropzone_receipts = receipts
    matched_item.dropzone_receipt_history = receipt_history
    matched_item.dropzone_reconciliation = reconciliation_state
    matched_item.dropzone_recovery = recovery_state
    matched_item.updated_at = acted_at
    save_review_queue(root, review_items)
    latest = refresh_control_room_state(root)
    return _control_room_action_result(latest, document_id, field_name, "dropzone_packet", packet)


def refresh_control_room_state(portalis_root: str | Path, now: datetime | None = None) -> Dict[str, Any]:
    root = Path(portalis_root)
    now = now or datetime.now(timezone.utc)
    registry = DocumentRegistry(root)
    review_items = load_review_queue(root)
    escalation_by_document = build_document_escalation_policies(review_items, now=now)
    routing_by_document = build_document_routing_hints(review_items, escalation_by_document=escalation_by_document, now=now)
    sla_by_document = build_document_sla_policies(review_items, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, now=now)
    reminder_by_document = build_document_reminder_stage(review_items, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, sla_by_document=sla_by_document, now=now)
    notification_by_document = build_notification_ledger(review_items, reminder_by_document=reminder_by_document, sla_by_document=sla_by_document, now=now)
    transport_by_document = build_transport_requests(review_items, notification_by_document=notification_by_document, now=now)
    alert_by_document = build_local_alert_feed(
        review_items,
        escalation_by_document=escalation_by_document,
        routing_by_document=routing_by_document,
        sla_by_document=sla_by_document,
        reminder_by_document=reminder_by_document,
        transport_by_document=transport_by_document,
        now=now,
    )
    incident_by_document = build_incident_threads(
        review_items,
        alert_by_document=alert_by_document,
        now=now,
    )
    export_by_document = build_external_bridge_exports(
        review_items,
        incident_by_document=incident_by_document,
        escalation_by_document=escalation_by_document,
        routing_by_document=routing_by_document,
        sla_by_document=sla_by_document,
        reminder_by_document=reminder_by_document,
        notification_by_document=notification_by_document,
        now=now,
    )
    intake_by_document = build_intake_contracts(
        review_items,
        export_by_document=export_by_document,
        now=now,
    )
    dropzone_by_document = build_dropzone_handshakes(
        review_items,
        export_by_document=export_by_document,
        intake_by_document=intake_by_document,
        root=root,
        now=now,
    )
    reconciliation_by_document = build_dropzone_reconciliation(review_items, dropzone_by_document=dropzone_by_document, now=now)
    refreshed_at = utc_now_iso()

    for item in review_items:
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        routing_hints = dict(routing_by_document.get(item.document_id, {}))
        assignment_state = _refresh_assignment_state(item.assignment_state, routing_hints=routing_hints, refreshed_at=refreshed_at)
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        reminder_stage = dict(reminder_by_document.get(item.document_id, {}))
        notification_ledger = dict(notification_by_document.get(item.document_id, {}))
        transport_requests = dict(transport_by_document.get(item.document_id, {}))
        local_alerts = dict(alert_by_document.get(item.document_id, {}))
        incident_threads = dict(incident_by_document.get(item.document_id, {}))
        external_bridge_exports = dict(export_by_document.get(item.document_id, {}))
        intake_contracts = dict(intake_by_document.get(item.document_id, {}))
        dropzone_handshakes = dict(dropzone_by_document.get(item.document_id, {}))
        dropzone_reconciliation = dict(reconciliation_by_document.get(item.document_id, {}).get("reconciliation", {}))
        dropzone_recovery = dict(reconciliation_by_document.get(item.document_id, {}).get("recovery", {}))
        item.escalation_policy = escalation_policy
        item.routing_hints = routing_hints
        item.assignment_state = assignment_state
        item.sla_policy = sla_policy
        item.reminder_stage = reminder_stage
        item.notification_ledger = notification_ledger
        item.transport_requests = transport_requests
        item.local_alerts = local_alerts
        item.incident_threads = incident_threads
        item.external_bridge_exports = external_bridge_exports
        item.intake_contracts = intake_contracts
        item.dropzone_handshakes = dropzone_handshakes
        item.dropzone_reconciliation = dropzone_reconciliation
        item.dropzone_recovery = dropzone_recovery
        item.tce = _merge_tce(
            item.tce,
            build_control_room_tce_delta(
                escalation_policy=escalation_policy,
                triage_state=dict(item.triage_state or {}),
                routing_hints=routing_hints,
                assignment_state=assignment_state,
                sla_policy=sla_policy,
                watch_state=dict(item.watch_state or {}),
                reminder_stage=reminder_stage,
                notification_prep=dict(item.notification_prep or {}),
                notification_ledger=notification_ledger,
                delivery_attempts=dict(item.delivery_attempts or {}),
                transport_requests=transport_requests,
                transport_results=dict(item.transport_results or {}),
                local_alerts=local_alerts,
                incident_threads=incident_threads,
                external_bridge_exports=external_bridge_exports,
                external_bridge_results=dict(item.external_bridge_results or {}),
                intake_contracts=intake_contracts,
                intake_acks=dict(item.intake_acks or {}),
                dropzone_handshakes=dropzone_handshakes,
                dropzone_receipts=dict(item.dropzone_receipts or {}),
                dropzone_reconciliation=dropzone_reconciliation,
                dropzone_recovery=dropzone_recovery,
                evaluated_at=refreshed_at,
            ),
        )
        try:
            registry.update_document_control_room(
                item.document_id,
                escalation_policy=escalation_policy,
                triage_actions=list(item.triage_actions or []),
                triage_state=dict(item.triage_state or {}),
                routing_hints=routing_hints,
                assignment_actions=list(item.assignment_actions or []),
                assignment_state=assignment_state,
                sla_policy=sla_policy,
                watch_actions=list(item.watch_actions or []),
                watch_state=dict(item.watch_state or {}),
                reminder_stage=reminder_stage,
                reminder_actions=list(item.reminder_actions or []),
                notification_prep=dict(item.notification_prep or {}),
                notification_ledger=notification_ledger,
                delivery_attempts=dict(item.delivery_attempts or {}),
                notification_actions=list(item.notification_actions or []),
                transport_requests=transport_requests,
                transport_results=dict(item.transport_results or {}),
                transport_actions=list(item.transport_actions or []),
                local_alerts=local_alerts,
                alert_actions=list(item.alert_actions or []),
                incident_threads=incident_threads,
                incident_actions=list(item.incident_actions or []),
                external_bridge_exports=external_bridge_exports,
                external_bridge_results=dict(item.external_bridge_results or {}),
                external_bridge_actions=list(item.external_bridge_actions or []),
                intake_contracts=intake_contracts,
                intake_acks=dict(item.intake_acks or {}),
                intake_actions=list(item.intake_actions or []),
                dropzone_handshakes=dropzone_handshakes,
                dropzone_receipts=dict(item.dropzone_receipts or {}),
                dropzone_receipt_history=dict(item.dropzone_receipt_history or {}),
                dropzone_reconciliation=dropzone_reconciliation,
                dropzone_recovery=dropzone_recovery,
                dropzone_actions=list(item.dropzone_actions or []),
                tce_lite={
                    "WHAT": dict(item.tce.WHAT),
                    "WHO": dict(item.tce.WHO),
                    "WHEN": dict(item.tce.WHEN),
                    "WHERE": dict(item.tce.WHERE),
                    "HOW": dict(item.tce.HOW),
                    "WHY": dict(item.tce.WHY),
                },
            )
        except KeyError:
            pass

    save_review_queue(root, review_items)
    global_queue = build_cross_document_review_queue(review_items, now=now, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, sla_by_document=sla_by_document)
    watch_queue = build_watch_queue(review_items, now=now, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, sla_by_document=sla_by_document)
    reminder_queue = build_reminder_queue(review_items, now=now, reminder_by_document=reminder_by_document)
    notification_queue = build_notification_queue(review_items, now=now, notification_by_document=notification_by_document)
    transport_queue = build_transport_queue(review_items, now=now, transport_by_document=transport_by_document)
    alert_feed = build_alert_queue(review_items, now=now, alert_by_document=alert_by_document)
    incident_feed = build_incident_feed(review_items, now=now, incident_by_document=incident_by_document)
    export_queue = build_external_bridge_queue(review_items, now=now, export_by_document=export_by_document)
    intake_queue = build_intake_queue(review_items, now=now, intake_by_document=intake_by_document)
    dropzone_queue = build_dropzone_queue(review_items, now=now, dropzone_by_document=dropzone_by_document)
    dashboard_summary = build_dashboard_summary(review_items, global_queue, watch_queue, reminder_queue, notification_queue, transport_queue, alert_feed, incident_feed, export_queue, intake_queue, dropzone_queue, now=now)
    dashboard_tce_delta = build_dashboard_tce_delta(global_queue, dashboard_summary, refreshed_at=refreshed_at)
    return {
        "review_items": review_items,
        "global_review_queue": global_queue,
        "watch_queue": watch_queue,
        "reminder_queue": reminder_queue,
        "notification_queue": notification_queue,
        "transport_queue": transport_queue,
        "alert_feed": alert_feed,
        "incident_feed": incident_feed,
        "export_queue": export_queue,
        "intake_queue": intake_queue,
        "dropzone_queue": dropzone_queue,
        "dashboard_summary": dashboard_summary,
        "dashboard_tce_delta": dashboard_tce_delta,
        "escalation_by_document": escalation_by_document,
        "routing_by_document": routing_by_document,
        "sla_by_document": sla_by_document,
        "reminder_by_document": reminder_by_document,
        "notification_by_document": notification_by_document,
        "transport_by_document": transport_by_document,
        "alert_by_document": alert_by_document,
        "incident_by_document": incident_by_document,
        "export_by_document": export_by_document,
        "intake_by_document": intake_by_document,
        "dropzone_by_document": dropzone_by_document,
        "reconciliation_by_document": reconciliation_by_document,
    }


def build_document_escalation_policies(review_items: List[ReviewQueueItem], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "passport")
        if doc_type != "passport":
            continue
        triage_state = dict(item.triage_state or {})
        field_packets: Dict[str, Any] = {}
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            if not field_name:
                continue
            conflict_level = str(queue_item.get("conflict_level") or "UNKNOWN")
            confidence_band = str(queue_item.get("confidence_band") or "UNKNOWN")
            attention_state = str(queue_item.get("attention_state") or "CLEAR")
            criticality = str(((item.field_policy or {}).get(field_name) or {}).get("criticality") or "LOW")
            current_status = str(queue_item.get("current_status") or item.status or "PENDING")
            created_at = _best_timestamp(item.created_at, item.updated_at, "")
            age_hours = _age_hours(created_at, now)
            staleness_band = _staleness_band(age_hours)
            override_count = _count_operator_overrides(item.compare_ledger or [], field_name)
            triage_status = str((triage_state.get(field_name) or {}).get("triage_status") or "")
            level, reasons, triggers = _derive_escalation_level(
                field_name=field_name,
                attention_state=attention_state,
                criticality=criticality,
                conflict_level=conflict_level,
                confidence_band=confidence_band,
                staleness_band=staleness_band,
                override_count=override_count,
                current_status=current_status,
                recommended_action=str(queue_item.get("recommended_action") or "REVIEW"),
                triage_status=triage_status,
            )
            field_packets[field_name] = asdict(EscalationPolicyPacket(
                document_id=item.document_id,
                field_name=field_name,
                escalation_level=level,
                escalation_reason=reasons,
                trigger_source=triggers,
                age_context={"created_at": created_at, "age_hours": age_hours, "age_bucket": _age_bucket(age_hours), "staleness_band": staleness_band},
                conflict_context={"conflict_level": conflict_level, "attention_state": attention_state},
                confidence_context={"confidence_band": confidence_band, "recommended_action": str(queue_item.get("recommended_action") or "REVIEW")},
                recommended_action=_escalation_recommended_action(level, str(queue_item.get("recommended_action") or "REVIEW"), triage_status),
                override_count=override_count,
                evaluated_at=utc_now_iso(),
            ))
        packets[item.document_id] = field_packets
    return packets


def build_document_routing_hints(review_items: List[ReviewQueueItem], *, escalation_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "passport")
        if doc_type != "passport":
            continue
        triage_state = dict(item.triage_state or {})
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        field_packets: Dict[str, Any] = {}
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            if not field_name:
                continue
            escalation = dict(escalation_policy.get(field_name, {}) or {})
            policy = dict((item.field_policy or {}).get(field_name, {}) or {})
            confidence = dict((item.field_confidence or {}).get(field_name, {}) or {})
            conflict = dict((item.field_conflicts or {}).get(field_name, {}) or {})
            evidence = dict((item.field_evidence or {}).get(field_name, {}) or {})
            triage_payload = dict(triage_state.get(field_name, {}) or {})
            routing_bucket, owner_hint, reasons = _derive_routing_hint(
                field_name=field_name,
                escalation_level=str(escalation.get("escalation_level") or "NONE"),
                attention_state=str(queue_item.get("attention_state") or "CLEAR"),
                current_status=str(queue_item.get("current_status") or item.status or "PENDING"),
                criticality=str(policy.get("criticality") or "LOW"),
                conflict_level=str(queue_item.get("conflict_level") or conflict.get("conflict_level") or "UNKNOWN"),
                confidence_band=str(queue_item.get("confidence_band") or confidence.get("confidence_band") or "UNKNOWN"),
                staleness_band=str((escalation.get("age_context") or {}).get("staleness_band") or "FRESH"),
                triage_status=str(triage_payload.get("triage_status") or ""),
                override_count=_count_operator_overrides(item.compare_ledger or [], field_name),
                evidence=evidence,
            )
            field_packets[field_name] = asdict(RoutingHintPacket(
                document_id=item.document_id,
                field_name=field_name,
                routing_bucket=routing_bucket,
                owner_hint=owner_hint,
                assignment_reason=reasons,
                priority_context={"priority_score": queue_item.get("priority_score"), "priority_band": queue_item.get("priority_band"), "attention_state": queue_item.get("attention_state")},
                escalation_context=escalation,
                triage_context=triage_payload,
                recommended_next_action=_routing_recommended_action(routing_bucket, triage_payload),
                evaluated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))
        packets[item.document_id] = field_packets
    return packets


def build_document_sla_policies(review_items: List[ReviewQueueItem], *, escalation_by_document: Dict[str, Dict[str, Any]], routing_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "passport")
        if doc_type != "passport":
            continue
        triage_state = dict(item.triage_state or {})
        assignment_state = dict(item.assignment_state or {})
        watch_state = dict(item.watch_state or {})
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        routing_hints = dict(routing_by_document.get(item.document_id, {}))
        field_packets: Dict[str, Any] = {}
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            if not field_name:
                continue
            escalation = dict(escalation_policy.get(field_name, {}) or {})
            routing = dict(routing_hints.get(field_name, {}) or {})
            triage_payload = dict(triage_state.get(field_name, {}) or {})
            assignment_payload = dict(assignment_state.get(field_name, {}) or {})
            watch_payload = dict(watch_state.get(field_name, {}) or {})
            created_at = _best_timestamp(item.created_at, item.updated_at, "")
            age_hours = _age_hours(created_at, now)
            staleness_band = _staleness_band(age_hours)
            sla_state, watch_level, reasons = _derive_sla_state(
                age_hours=age_hours,
                staleness_band=staleness_band,
                escalation_level=str(escalation.get("escalation_level") or "NONE"),
                assignment_status=str(assignment_payload.get("assignment_status") or ""),
                routing_bucket=str(routing.get("routing_bucket") or "CLEAR_NO_ROUTING"),
                attention_state=str(queue_item.get("attention_state") or "CLEAR"),
                current_status=str(queue_item.get("current_status") or item.status or "PENDING"),
                triage_status=str(triage_payload.get("triage_status") or ""),
            )
            notification_ready = sla_state in {"WARNING", "BREACH"} or (
                str(escalation.get("escalation_level") or "NONE") == "CRITICAL" and str(assignment_payload.get("assignment_status") or "") != "ASSIGNED"
            )
            field_packets[field_name] = asdict(SLAPolicyPacket(
                document_id=item.document_id,
                field_name=field_name,
                sla_state=sla_state,
                watch_level=watch_level,
                notification_ready=notification_ready,
                watch_trigger_reason=reasons,
                requires_ack=notification_ready and not bool(watch_payload.get("watch_acknowledged_at")),
                notification_severity="CRITICAL" if sla_state == "BREACH" else "HIGH" if sla_state == "WARNING" else "LOW" if sla_state == "WATCH" else "NONE",
                evaluated_at=utc_now_iso(),
            ))
        packets[item.document_id] = field_packets
    return packets


def build_watch_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, escalation_by_document: Dict[str, Dict[str, Any]] | None = None, routing_by_document: Dict[str, Dict[str, Any]] | None = None, sla_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    escalation_by_document = escalation_by_document or build_document_escalation_policies(review_items, now=now)
    routing_by_document = routing_by_document or build_document_routing_hints(review_items, escalation_by_document=escalation_by_document, now=now)
    sla_by_document = sla_by_document or build_document_sla_policies(review_items, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, now=now)
    watch_rows: List[Dict[str, Any]] = []
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "")
        if doc_type and doc_type != "passport":
            continue
        if str(item.status or "") == "REJECTED":
            continue
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        routing_hints = dict(routing_by_document.get(item.document_id, {}))
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        watch_state = dict(item.watch_state or {})
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            sla_payload = dict(sla_policy.get(field_name, {}) or {})
            if str(sla_payload.get("sla_state") or "NORMAL") == "NORMAL" and not bool(sla_payload.get("notification_ready")):
                continue
            created_at = _best_timestamp(item.created_at, item.updated_at, "")
            age_hours = _age_hours(created_at, now)
            watch_payload = dict(watch_state.get(field_name, {}) or {})
            watch_rows.append(asdict(WatchQueuePacket(
                document_id=item.document_id,
                review_item_id=item.document_id,
                field_name=field_name,
                watch_level=str(sla_payload.get("watch_level") or "NONE"),
                sla_state=str(sla_payload.get("sla_state") or "NORMAL"),
                age_hours=age_hours,
                age_bucket=_age_bucket(age_hours),
                staleness_band=_staleness_band(age_hours),
                escalation_level=str((escalation_policy.get(field_name) or {}).get("escalation_level") or "NONE"),
                routing_bucket=str((routing_hints.get(field_name) or {}).get("routing_bucket") or "CLEAR_NO_ROUTING"),
                assignment_state=str((item.assignment_state or {}).get(field_name, {}).get("assignment_status") or ""),
                attention_state=str(queue_item.get("attention_state") or "CLEAR"),
                notification_ready=bool(sla_payload.get("notification_ready")),
                watch_trigger_reason=list(sla_payload.get("watch_trigger_reason", [])),
                requires_ack=bool(sla_payload.get("requires_ack")),
                watch_acknowledged_at=str(watch_payload.get("watch_acknowledged_at") or ""),
                notification_severity=str(sla_payload.get("notification_severity") or "NONE"),
                last_updated=_best_timestamp(((item.unresolved_fields or {}).get(field_name) or {}).get("last_updated"), item.updated_at, item.created_at),
                created_at=created_at,
            )))
    watch_rows.sort(key=lambda row: (-_sla_rank(str(row.get("sla_state") or "NORMAL")), -_escalation_rank(str(row.get("escalation_level") or "NONE")), -(row.get("age_hours") or 0.0), row.get("document_id") or "", row.get("field_name") or ""))
    return watch_rows


def build_document_reminder_stage(review_items: List[ReviewQueueItem], *, escalation_by_document: Dict[str, Dict[str, Any]], routing_by_document: Dict[str, Dict[str, Any]], sla_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "passport")
        if doc_type != "passport":
            continue
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        watch_state = dict(item.watch_state or {})
        notification_prep = dict(item.notification_prep or {})
        field_packets: Dict[str, Any] = {}
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            if not field_name:
                continue
            sla_payload = dict(sla_policy.get(field_name, {}) or {})
            prep_payload = dict(notification_prep.get(field_name, {}) or {})
            watch_payload = dict(watch_state.get(field_name, {}) or {})
            reminder_state, due_at, reasons = _derive_reminder_state(
                now=now,
                current_status=str(queue_item.get("current_status") or item.status or "PENDING"),
                sla_payload=sla_payload,
                prep_payload=prep_payload,
                watch_payload=watch_payload,
            )
            field_packets[field_name] = asdict(
                ReminderStagePacket(
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    reminder_state=reminder_state,
                    reminder_due_at=due_at,
                    notification_severity=str(sla_payload.get("notification_severity") or "NONE"),
                    source_watch_level=str(sla_payload.get("watch_level") or "NONE"),
                    source_sla_state=str(sla_payload.get("sla_state") or "NORMAL"),
                    notification_ready=bool(sla_payload.get("notification_ready")),
                    requires_ack=bool(sla_payload.get("requires_ack")),
                    snooze_until=str(prep_payload.get("snoozed_until") or ""),
                    staged_reason=reasons,
                    last_updated=_best_timestamp((watch_payload or {}).get("watch_acknowledged_at"), item.updated_at, item.created_at),
                    created_at=_best_timestamp(item.created_at, item.updated_at, ""),
                )
            )
        packets[item.document_id] = field_packets
    return packets


def build_reminder_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, reminder_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    reminder_by_document = reminder_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        doc_reminders = dict(reminder_by_document.get(item.document_id, {}))
        if not doc_reminders:
            continue
        for field_name, payload in doc_reminders.items():
            reminder_state = str((payload or {}).get("reminder_state") or "CLEARED")
            if reminder_state == "CLEARED":
                continue
            rows.append(dict(payload))
    rows.sort(key=lambda row: (-_reminder_rank(str(row.get("reminder_state") or "CLEARED")), _parse_iso(str(row.get("reminder_due_at") or "")) or now, row.get("document_id") or "", row.get("field_name") or ""))
    return rows


def build_notification_ledger(review_items: List[ReviewQueueItem], *, reminder_by_document: Dict[str, Dict[str, Any]], sla_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "passport")
        if doc_type != "passport":
            continue
        doc_packets: Dict[str, Any] = {}
        existing_ledger = dict(item.notification_ledger or {})
        reminder_stage = dict(reminder_by_document.get(item.document_id, {}))
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        watch_state = dict(item.watch_state or {})
        for field_name, reminder_payload in reminder_stage.items():
            existing = dict(existing_ledger.get(field_name, {}) or {})
            reminder_state = str((reminder_payload or {}).get("reminder_state") or "CLEARED")
            sla_payload = dict(sla_policy.get(field_name, {}) or {})
            created_at = str(existing.get("created_at") or now.strftime("%Y-%m-%dT%H:%M:%SZ"))
            updated_at = str(existing.get("updated_at") or created_at)
            prep_state = str(existing.get("prep_state") or reminder_state)
            if reminder_state == "CLEARED":
                prep_state = "CANCELED" if prep_state in {"READY", "FAILED"} else "CANCELED"
            elif prep_state not in {"EMITTED", "FAILED", "CANCELED"}:
                prep_state = "READY" if reminder_state == "READY" else ("EMITTED" if reminder_state == "SENT" else reminder_state)
            is_active = prep_state in {"READY", "FAILED"} and reminder_state != "CLEARED"
            if prep_state == "EMITTED":
                is_active = False
            if prep_state == "CANCELED":
                is_active = False
            doc_packets[field_name] = asdict(
                NotificationLedgerPacket(
                    notification_id=str(existing.get("notification_id") or _notification_id(item.document_id, field_name)),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    prep_state=prep_state,
                    severity=str((reminder_payload or {}).get("notification_severity") or "NONE"),
                    source_reminder_state=reminder_state,
                    source_watch_state=str((watch_state.get(field_name) or {}).get("watch_status") or ""),
                    source_sla_state=str(sla_payload.get("sla_state") or "NORMAL"),
                    notification_reason=list((reminder_payload or {}).get("staged_reason", [])),
                    created_at=created_at,
                    updated_at=updated_at,
                    is_active=is_active,
                )
            )
        packets[item.document_id] = doc_packets
    return packets


def build_notification_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, notification_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    notification_by_document = notification_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        doc_notifications = dict(notification_by_document.get(item.document_id, {}))
        attempts_by_field = dict(item.delivery_attempts or {})
        for field_name, payload in doc_notifications.items():
            row = dict(payload)
            attempts = list(attempts_by_field.get(field_name, []) or [])
            row["attempt_count"] = len(attempts)
            row["last_attempt"] = dict(attempts[-1]) if attempts else {}
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_notification_rank(str(row.get("prep_state") or "CANCELED")),
            -len(list((row.get("notification_reason") or []))),
            _parse_iso(str(row.get("updated_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_transport_requests(review_items: List[ReviewQueueItem], *, notification_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_notifications = dict(notification_by_document.get(item.document_id, {}))
        existing_requests = dict(item.transport_requests or {})
        existing_results = dict(item.transport_results or {})
        doc_packets: Dict[str, Any] = {}
        for field_name, payload in doc_notifications.items():
            existing_request = dict(existing_requests.get(field_name, {}) or {})
            latest_result = list(existing_results.get(field_name, []) or [])
            latest_state = str((latest_result[-1] or {}).get("result_state") or "") if latest_result else ""
            prep_state = str((payload or {}).get("prep_state") or "CANCELED")
            if prep_state == "CANCELED":
                continue
            doc_packets[field_name] = asdict(
                TransportRequestPacket(
                    notification_id=str((payload or {}).get("notification_id") or existing_request.get("notification_id") or _notification_id(item.document_id, field_name)),
                    request_id=str(existing_request.get("request_id") or _transport_request_id(item.document_id, field_name)),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    channel_hint=str(existing_request.get("channel_hint") or _derive_channel_hint(
                        severity=str((payload or {}).get("severity") or "NONE"),
                        source_sla_state=str((payload or {}).get("source_sla_state") or "NORMAL"),
                        source_reminder_state=str((payload or {}).get("source_reminder_state") or "CLEARED"),
                    )),
                    severity=str((payload or {}).get("severity") or "NONE"),
                    payload_summary=dict(existing_request.get("payload_summary") or {
                        "field_name": field_name,
                        "notification_state": prep_state,
                        "severity": (payload or {}).get("severity"),
                        "latest_result_state": latest_state,
                    }),
                    handoff_reason=list((payload or {}).get("notification_reason", [])),
                    created_at=str(existing_request.get("created_at") or now.strftime("%Y-%m-%dT%H:%M:%SZ")),
                )
            )
        packets[item.document_id] = doc_packets
    return packets


def build_transport_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, transport_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    transport_by_document = transport_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        doc_requests = dict(transport_by_document.get(item.document_id, {}))
        doc_results = dict(item.transport_results or {})
        for field_name, payload in doc_requests.items():
            results = list(doc_results.get(field_name, []) or [])
            latest_result = dict(results[-1]) if results else {}
            row = dict(payload)
            row["latest_result"] = latest_result
            row["latest_result_state"] = str(latest_result.get("result_state") or "HANDOFF_READY")
            row["latest_result_reason"] = str(latest_result.get("result_reason") or "")
            row["latest_result_at"] = str(latest_result.get("handed_off_at") or "")
            row["result_count"] = len(results)
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_transport_rank(str(row.get("latest_result_state") or "HANDOFF_READY")),
            _parse_iso(str(row.get("latest_result_at") or row.get("created_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_local_alert_feed(review_items: List[ReviewQueueItem], *, escalation_by_document: Dict[str, Dict[str, Any]], routing_by_document: Dict[str, Dict[str, Any]], sla_by_document: Dict[str, Dict[str, Any]], reminder_by_document: Dict[str, Dict[str, Any]], transport_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    packets: Dict[str, Dict[str, Any]] = {}
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in review_items:
        doc_packets: Dict[str, Any] = {}
        existing_alerts = dict(item.local_alerts or {})
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        routing_hints = dict(routing_by_document.get(item.document_id, {}))
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        reminder_stage = dict(reminder_by_document.get(item.document_id, {}))
        transport_requests = dict(transport_by_document.get(item.document_id, {}))
        transport_results = dict(item.transport_results or {})
        queue_map = {str(q.get("field_name") or ""): dict(q) for q in (item.prioritized_field_queue or []) if str(q.get("field_name") or "")}

        field_names = set(queue_map.keys()) | set(sla_policy.keys()) | set(reminder_stage.keys()) | set(transport_requests.keys())
        for field_name in sorted(field_names):
            queue_item = dict(queue_map.get(field_name, {}) or {})
            escalation = dict(escalation_policy.get(field_name, {}) or {})
            routing = dict(routing_hints.get(field_name, {}) or {})
            sla = dict(sla_policy.get(field_name, {}) or {})
            reminder = dict(reminder_stage.get(field_name, {}) or {})
            transport_request = dict(transport_requests.get(field_name, {}) or {})
            transport_result_list = list((transport_results.get(field_name) or []))
            latest_transport = dict(transport_result_list[-1]) if transport_result_list else {}

            trigger = _derive_alert_trigger(
                field_name=field_name,
                queue_item=queue_item,
                escalation=escalation,
                routing=routing,
                sla=sla,
                reminder=reminder,
                latest_transport=latest_transport,
                override_count=_count_operator_overrides(item.compare_ledger or [], field_name),
            )
            existing = dict(existing_alerts.get(field_name, {}) or {})
            if not trigger:
                if existing:
                    if str(existing.get("alert_state") or "") not in {"CLEARED"}:
                        existing["alert_state"] = "CLEARED"
                        existing["updated_at"] = now_iso
                        existing["cleared_at"] = existing.get("cleared_at") or now_iso
                    doc_packets[field_name] = existing
                continue

            existing_key = str((existing.get("source_context_summary") or {}).get("trigger_key") or "")
            alert_state = "ACTIVE"
            acknowledged_at = str(existing.get("acknowledged_at") or "")
            cleared_at = str(existing.get("cleared_at") or "")
            is_pinned = bool(existing.get("is_pinned"))
            if existing:
                if str(existing.get("alert_state") or "") == "ACKNOWLEDGED" and existing_key == trigger["trigger_key"]:
                    alert_state = "ACKNOWLEDGED"
                elif str(existing.get("alert_state") or "") == "CLEARED" and existing_key == trigger["trigger_key"]:
                    alert_state = "CLEARED"
                elif existing_key and existing_key != trigger["trigger_key"]:
                    alert_state = "REOPENED"
                elif str(existing.get("alert_state") or "") == "REOPENED":
                    alert_state = "REOPENED"

            doc_packets[field_name] = asdict(
                LocalAlertPacket(
                    alert_id=str(existing.get("alert_id") or _alert_id(item.document_id, field_name, trigger["source_type"])),
                    source_notification_id=str((transport_request or {}).get("notification_id") or _notification_id(item.document_id, field_name)),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    severity=trigger["severity"],
                    message=trigger["message"],
                    alert_state=alert_state,
                    source_type=trigger["source_type"],
                    created_at=str(existing.get("created_at") or now_iso),
                    updated_at=now_iso,
                    acknowledged_at=acknowledged_at,
                    cleared_at=cleared_at if alert_state == "CLEARED" else "",
                    is_pinned=is_pinned,
                    source_context_summary=trigger["source_context_summary"],
                    alert_reason=trigger["alert_reason"],
                )
            )
        packets[item.document_id] = doc_packets
    return packets


def build_alert_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, alert_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    alert_by_document = alert_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        for field_name, payload in dict(alert_by_document.get(item.document_id, {})).items():
            row = dict(payload)
            row["field_name"] = field_name
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_alert_state_rank(str(row.get("alert_state") or "ACTIVE")),
            -_alert_severity_rank(str(row.get("severity") or "LOW")),
            0 if row.get("is_pinned") else 1,
            _parse_iso(str(row.get("updated_at") or row.get("created_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_incident_threads(review_items: List[ReviewQueueItem], *, alert_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        existing_threads = dict(item.incident_threads or {})
        doc_packets: Dict[str, Any] = {}
        for field_name, alert_payload in dict(alert_by_document.get(item.document_id, {}) or {}).items():
            alert = dict(alert_payload or {})
            if not alert:
                continue
            existing = dict(existing_threads.get(field_name, {}) or {})
            correlation_key = _incident_correlation_key(item.document_id, field_name, alert)
            incident_state = str(existing.get("incident_state") or "OPEN")
            created_at = str(existing.get("created_at") or alert.get("created_at") or now_iso)
            occurrence_count = int(existing.get("occurrence_count") or 1)
            if not existing:
                occurrence_count = 1
            elif str(alert.get("alert_state") or "") == "REOPENED" or (
                incident_state == "CLOSED" and str(alert.get("alert_state") or "") in {"ACTIVE", "ACKNOWLEDGED", "REOPENED"}
            ):
                occurrence_count += 1
            if str(alert.get("alert_state") or "") == "ACKNOWLEDGED":
                incident_state = "ACKNOWLEDGED"
            elif bool(alert.get("is_pinned")) or incident_state == "PINNED":
                incident_state = "PINNED"
            elif str(alert.get("alert_state") or "") == "CLEARED":
                incident_state = "CLOSED"
            elif str(alert.get("alert_state") or "") == "REOPENED":
                incident_state = "REOPENED"
            elif incident_state not in {"ACKNOWLEDGED", "PINNED", "CLOSED", "REOPENED"}:
                incident_state = "OPEN"
            related_alert_ids = list(dict.fromkeys(list(existing.get("related_alert_ids", []) or []) + [str(alert.get("alert_id") or "")]))
            doc_packets[field_name] = asdict(
                IncidentThreadPacket(
                    incident_id=str(existing.get("incident_id") or correlation_key),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    source_type=str(alert.get("source_type") or "CONTROL_ROOM_ALERT"),
                    incident_reason=list(alert.get("alert_reason", []) or []),
                    severity=str(alert.get("severity") or "LOW"),
                    incident_state=incident_state,
                    created_at=created_at,
                    updated_at=now_iso,
                    last_alert_at=str(alert.get("updated_at") or alert.get("created_at") or now_iso),
                    occurrence_count=max(1, occurrence_count),
                    related_alert_ids=related_alert_ids,
                    current_alert_id=str(alert.get("alert_id") or ""),
                    source_context_summary=dict(alert.get("source_context_summary", {}) or {}),
                )
            )
        for field_name, existing in existing_threads.items():
            if field_name not in doc_packets and existing:
                existing_copy = dict(existing or {})
                if str(existing_copy.get("incident_state") or "") != "CLOSED":
                    existing_copy["incident_state"] = "CLOSED"
                    existing_copy["updated_at"] = now_iso
                    existing_copy["closed_at"] = existing_copy.get("closed_at") or now_iso
                doc_packets[field_name] = existing_copy
        packets[item.document_id] = doc_packets
    return packets


def build_incident_feed(review_items: List[ReviewQueueItem], now: datetime | None = None, incident_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    incident_by_document = incident_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        for field_name, payload in dict(incident_by_document.get(item.document_id, {}) or {}).items():
            row = dict(payload or {})
            row["field_name"] = field_name
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_incident_state_rank(str(row.get("incident_state") or "OPEN")),
            -_alert_severity_rank(str(row.get("severity") or "LOW")),
            -(int(row.get("occurrence_count") or 0)),
            _parse_iso(str(row.get("updated_at") or row.get("created_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_external_bridge_exports(
    review_items: List[ReviewQueueItem],
    *,
    incident_by_document: Dict[str, Dict[str, Any]],
    escalation_by_document: Dict[str, Dict[str, Any]],
    routing_by_document: Dict[str, Dict[str, Any]],
    sla_by_document: Dict[str, Dict[str, Any]],
    reminder_by_document: Dict[str, Dict[str, Any]],
    notification_by_document: Dict[str, Dict[str, Any]],
    now: datetime | None = None,
) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        existing_exports = dict(item.external_bridge_exports or {})
        existing_results = dict(item.external_bridge_results or {})
        doc_packets: Dict[str, Any] = {}
        incidents = dict(incident_by_document.get(item.document_id, {}) or {})
        escalation = dict(escalation_by_document.get(item.document_id, {}) or {})
        routing = dict(routing_by_document.get(item.document_id, {}) or {})
        sla = dict(sla_by_document.get(item.document_id, {}) or {})
        reminder = dict(reminder_by_document.get(item.document_id, {}) or {})
        notification = dict(notification_by_document.get(item.document_id, {}) or {})
        for field_name, incident in incidents.items():
            incident_payload = dict(incident or {})
            if not incident_payload:
                continue
            incident_state = str(incident_payload.get("incident_state") or "OPEN")
            incident_severity = str(incident_payload.get("severity") or "LOW")
            escalation_level = str((escalation.get(field_name) or {}).get("escalation_level") or "NONE")
            reminder_state = str((reminder.get(field_name) or {}).get("reminder_state") or "CLEARED")
            watch_state = str((sla.get(field_name) or {}).get("sla_state") or "NORMAL")
            notification_state = str((notification.get(field_name) or {}).get("prep_state") or "CANCELED")
            occurrence_count = int(incident_payload.get("occurrence_count") or 1)
            export_needed = (
                incident_state in {"OPEN", "REOPENED", "PINNED"}
                and incident_severity in {"CRITICAL", "HIGH"}
            ) or occurrence_count >= 2 or escalation_level == "CRITICAL"
            if not export_needed:
                if field_name in existing_exports:
                    doc_packets[field_name] = dict(existing_exports.get(field_name, {}), export_state="EXPORT_SKIPPED")
                continue
            existing_export = dict(existing_exports.get(field_name, {}) or {})
            latest_result = dict(existing_results.get(field_name, {}) or {})
            current_result_state = str(latest_result.get("result_state") or "EXPORT_READY")
            if current_result_state in {"EXPORT_ACCEPTED", "EXPORT_REJECTED", "EXPORT_FAILED"}:
                export_state = current_result_state
            else:
                export_state = "EXPORT_READY"
            target_hint = str(existing_export.get("target_hint") or _derive_export_target_hint(
                severity=incident_severity,
                escalation_level=escalation_level,
                reminder_state=reminder_state,
                watch_state=watch_state,
            ))
            source_summary = {
                "incident_state": incident_state,
                "occurrence_count": occurrence_count,
                "routing_bucket": str((routing.get(field_name) or {}).get("routing_bucket") or "CLEAR_NO_ROUTING"),
                "owner_bucket": str((routing.get(field_name) or {}).get("owner_hint") or "OPERATOR"),
                "watch_state": watch_state,
                "reminder_state": reminder_state,
                "notification_state": notification_state,
                "incident_reason": list(incident_payload.get("incident_reason", []) or []),
            }
            doc_packets[field_name] = asdict(
                ExternalBridgeExportPacket(
                    export_id=str(existing_export.get("export_id") or _external_export_id(item.document_id, field_name)),
                    incident_id=str(incident_payload.get("incident_id") or ""),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    export_type="INCIDENT_CONTROL_ROOM_EXPORT",
                    severity=incident_severity,
                    routing_bucket=str((routing.get(field_name) or {}).get("routing_bucket") or "CLEAR_NO_ROUTING"),
                    owner_bucket=str((routing.get(field_name) or {}).get("owner_hint") or "OPERATOR"),
                    incident_state=incident_state,
                    escalation_level=escalation_level,
                    watch_state=watch_state,
                    reminder_state=reminder_state,
                    notification_state=notification_state,
                    target_hint=target_hint,
                    source_summary=source_summary,
                    created_at=str(existing_export.get("created_at") or now_iso),
                )
            )
            doc_packets[field_name]["export_state"] = export_state
            if existing_export.get("export_file_path"):
                doc_packets[field_name]["export_file_path"] = existing_export.get("export_file_path")
        packets[item.document_id] = doc_packets
    return packets


def build_external_bridge_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, export_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    export_by_document = export_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        result_map = dict(item.external_bridge_results or {})
        for field_name, payload in dict(export_by_document.get(item.document_id, {}) or {}).items():
            row = dict(payload or {})
            latest_result = dict(result_map.get(field_name, {}) or {})
            row["field_name"] = field_name
            row["latest_result_state"] = str(latest_result.get("result_state") or row.get("export_state") or "EXPORT_READY")
            row["latest_result_reason"] = str(latest_result.get("result_reason") or "")
            row["target_hint"] = str(row.get("target_hint") or latest_result.get("target_hint") or "LOCAL_EXPORT_FILE")
            row["exported_at"] = str(latest_result.get("exported_at") or "")
            row["adapter_name"] = str(latest_result.get("adapter_name") or "PORTALIS_EXTERNAL_BRIDGE")
            row["export_file_path"] = str(latest_result.get("export_file_path") or row.get("export_file_path") or "")
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_external_bridge_rank(str(row.get("latest_result_state") or "EXPORT_READY")),
            -_alert_severity_rank(str(row.get("severity") or "LOW")),
            -(int((row.get("source_summary") or {}).get("occurrence_count") or 0)),
            _parse_iso(str(row.get("exported_at") or row.get("created_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_intake_contracts(review_items: List[ReviewQueueItem], *, export_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        existing_contracts = dict(item.intake_contracts or {})
        existing_acks = dict(item.intake_acks or {})
        doc_packets: Dict[str, Any] = {}
        for field_name, export_payload in dict(export_by_document.get(item.document_id, {}) or {}).items():
            export_row = dict(export_payload or {})
            if not export_row:
                continue
            existing_contract = dict(existing_contracts.get(field_name, {}) or {})
            validation = _validate_intake_contract(export_row)
            ack_payload = dict(existing_acks.get(field_name, {}) or {})
            result_state = str((ack_payload.get("ack_state") or "") or "INTAKE_PENDING")
            if result_state == "":
                result_state = "INTAKE_PENDING"
            doc_packets[field_name] = asdict(
                IntakeContractPacket(
                    intake_id=str(existing_contract.get("intake_id") or _intake_id(item.document_id, field_name)),
                    export_id=str(export_row.get("export_id") or export_row.get("export_id") or _external_export_id(item.document_id, field_name)),
                    export_type=str(export_row.get("export_type") or "INCIDENT_CONTROL_ROOM_EXPORT"),
                    target_hint=str(export_row.get("target_hint") or "LOCAL_EXPORT_FILE"),
                    document_id=item.document_id,
                    review_item_id=item.document_id,
                    field_name=field_name,
                    incident_id=str(export_row.get("incident_id") or ""),
                    received_at=str(existing_contract.get("received_at") or now_iso),
                    source_summary=dict(export_row.get("source_summary", {}) or {}),
                    contract_version=str(existing_contract.get("contract_version") or "portalis-intake-v1"),
                    validation=validation,
                )
            )
            doc_packets[field_name]["latest_ack_state"] = result_state
            if validation.get("validation_state") != "VALID":
                doc_packets[field_name]["latest_ack_state"] = "INTAKE_INVALID"
        packets[item.document_id] = doc_packets
    return packets


def build_intake_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, intake_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    intake_by_document = intake_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        ack_map = dict(item.intake_acks or {})
        for field_name, payload in dict(intake_by_document.get(item.document_id, {}) or {}).items():
            row = dict(payload or {})
            ack_payload = dict(ack_map.get(field_name, {}) or {})
            row["field_name"] = field_name
            row["latest_ack_state"] = str(ack_payload.get("ack_state") or row.get("latest_ack_state") or "INTAKE_PENDING")
            row["latest_ack_reason"] = str(ack_payload.get("ack_reason") or "")
            row["acknowledged_at"] = str(ack_payload.get("acknowledged_at") or "")
            row["receiver_name"] = str(ack_payload.get("receiver_name") or "PORTALIS_INTAKE")
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_intake_rank(str(row.get("latest_ack_state") or "INTAKE_PENDING")),
            -_external_bridge_rank(str(row.get("latest_ack_state") or "INTAKE_PENDING")),
            _parse_iso(str(row.get("acknowledged_at") or row.get("received_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_dropzone_handshakes(
    review_items: List[ReviewQueueItem],
    *,
    export_by_document: Dict[str, Dict[str, Any]],
    intake_by_document: Dict[str, Dict[str, Any]],
    root: Path,
    now: datetime | None = None,
) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        existing_handshakes = dict(item.dropzone_handshakes or {})
        existing_receipts = dict(item.dropzone_receipts or {})
        doc_packets: Dict[str, Any] = {}
        for field_name, export_payload in dict(export_by_document.get(item.document_id, {}) or {}).items():
            export_row = dict(export_payload or {})
            if not export_row:
                continue
            existing_payload = dict(existing_handshakes.get(field_name, {}) or {})
            intake_payload = dict((intake_by_document.get(item.document_id, {}) or {}).get(field_name, {}) or {})
            handshake = _build_dropzone_handshake_payload(
                export_payload=export_row,
                intake_payload=intake_payload,
                existing_payload=existing_payload,
                root=root,
                staged_at=str(existing_payload.get("staged_at") or now_iso),
            )
            latest_receipt = dict(existing_receipts.get(field_name, {}) or {})
            if latest_receipt:
                handshake["handshake_state"] = str(latest_receipt.get("receipt_state") or handshake.get("handshake_state") or "DROPZONE_STAGED")
            doc_packets[field_name] = handshake
        packets[item.document_id] = doc_packets
    return packets


def build_dropzone_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, dropzone_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    dropzone_by_document = dropzone_by_document or {}
    rows: List[Dict[str, Any]] = []
    for item in review_items:
        receipt_map = dict(item.dropzone_receipts or {})
        reconciliation_map = dict(item.dropzone_reconciliation or {})
        recovery_map = dict(item.dropzone_recovery or {})
        for field_name, payload in dict(dropzone_by_document.get(item.document_id, {}) or {}).items():
            row = dict(payload or {})
            receipt_payload = dict(receipt_map.get(field_name, {}) or {})
            reconciliation_payload = dict(reconciliation_map.get(field_name, {}) or {})
            recovery_payload = dict(recovery_map.get(field_name, {}) or {})
            row["field_name"] = field_name
            row["latest_receipt_state"] = str(receipt_payload.get("receipt_state") or row.get("handshake_state") or "DROPZONE_STAGED")
            row["latest_receipt_reason"] = str(receipt_payload.get("receipt_reason") or "")
            row["receipt_filename"] = str(receipt_payload.get("receipt_filename") or "")
            row["received_at"] = str(receipt_payload.get("received_at") or "")
            row["receipt_path"] = str(receipt_payload.get("receipt_path") or "")
            row["archived_path"] = str(receipt_payload.get("archived_path") or row.get("archive_path") or "")
            row["reconciliation"] = reconciliation_payload
            row["recovery"] = recovery_payload
            rows.append(row)
    rows.sort(
        key=lambda row: (
            -_dropzone_rank(str(row.get("latest_receipt_state") or "DROPZONE_STAGED")),
            _parse_iso(str(row.get("received_at") or row.get("last_checked_at") or row.get("staged_at") or "")) or now,
            row.get("document_id") or "",
            row.get("field_name") or "",
        )
    )
    return rows


def build_dropzone_reconciliation(review_items: List[ReviewQueueItem], *, dropzone_by_document: Dict[str, Dict[str, Any]], now: datetime | None = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    packets: Dict[str, Dict[str, Any]] = {}
    for item in review_items:
        doc_packets: Dict[str, Dict[str, Any]] = {"reconciliation": {}, "recovery": {}}
        receipt_history_map = dict(item.dropzone_receipt_history or {})
        existing_recovery = dict(item.dropzone_recovery or {})
        for field_name, handshake_payload in dict(dropzone_by_document.get(item.document_id, {}) or {}).items():
            history = list(receipt_history_map.get(field_name, []) or [])
            reconciled = _reconcile_receipt_history(
                handshake_payload=dict(handshake_payload or {}),
                receipt_history=history,
                now=now_iso,
            )
            recovery_payload = dict(reconciled.get("recovery", {}) or {})
            existing_recovery_payload = dict(existing_recovery.get(field_name, {}) or {})
            if existing_recovery_payload:
                derived_state = str(recovery_payload.get("recovery_state") or "HANDSHAKE_NORMAL")
                existing_state = str(existing_recovery_payload.get("recovery_state") or "HANDSHAKE_NORMAL")
                if derived_state == "HANDSHAKE_NORMAL" and existing_state != "HANDSHAKE_NORMAL":
                    recovery_payload = dict(recovery_payload, **existing_recovery_payload)
                else:
                    recovery_payload = dict(existing_recovery_payload, **recovery_payload)
            doc_packets["reconciliation"][field_name] = dict(reconciled.get("reconciliation", {}) or {})
            doc_packets["recovery"][field_name] = recovery_payload
        packets[item.document_id] = doc_packets
    return packets


def _validate_intake_contract(export_row: Dict[str, Any]) -> Dict[str, Any]:
    messages: List[str] = []
    if not str(export_row.get("export_id") or "").strip():
        messages.append("missing export_id")
    if not str(export_row.get("target_hint") or "").strip():
        messages.append("missing target_hint")
    if not str(export_row.get("export_type") or "").strip():
        messages.append("missing export_type")
    if not str(export_row.get("document_id") or "").strip():
        messages.append("missing document_id")
    if not str(export_row.get("field_name") or "").strip():
        messages.append("missing field_name")
    if not dict(export_row.get("source_summary", {}) or {}):
        messages.append("missing source_summary")
    validation_state = "VALID" if not messages else "INVALID"
    return asdict(
        IntakeValidationPacket(
            intake_id=str(export_row.get("intake_id") or _intake_id(str(export_row.get("document_id") or ""), str(export_row.get("field_name") or ""))),
            export_id=str(export_row.get("export_id") or ""),
            validation_state=validation_state,
            validation_messages=messages or ["intake contract shape valid"],
            validated_at=utc_now_iso(),
            contract_version=str(export_row.get("contract_version") or "portalis-intake-v1"),
        )
    )


def build_cross_document_review_queue(review_items: List[ReviewQueueItem], now: datetime | None = None, escalation_by_document: Dict[str, Dict[str, Any]] | None = None, routing_by_document: Dict[str, Dict[str, Any]] | None = None, sla_by_document: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    queue_rows: List[Dict[str, Any]] = []
    escalation_by_document = escalation_by_document or build_document_escalation_policies(review_items, now=now)
    routing_by_document = routing_by_document or build_document_routing_hints(review_items, escalation_by_document=escalation_by_document, now=now)
    sla_by_document = sla_by_document or build_document_sla_policies(review_items, escalation_by_document=escalation_by_document, routing_by_document=routing_by_document, now=now)
    for item in review_items:
        doc_type = str((item.tce.WHAT or {}).get("document_type") or "")
        if doc_type and doc_type != "passport":
            continue
        if str(item.status or "") == "REJECTED":
            continue
        triage_state = dict(item.triage_state or {})
        assignment_state = dict(item.assignment_state or {})
        escalation_policy = dict(escalation_by_document.get(item.document_id, {}))
        routing_hints = dict(routing_by_document.get(item.document_id, {}))
        sla_policy = dict(sla_by_document.get(item.document_id, {}))
        for queue_item in item.prioritized_field_queue or []:
            field_name = str(queue_item.get("field_name") or "")
            attention_state = str(queue_item.get("attention_state") or "CLEAR")
            if not field_name or attention_state == "CLEAR":
                continue
            triage_payload = dict(triage_state.get(field_name, {}) or {})
            assignment_payload = dict(assignment_state.get(field_name, {}) or {})
            escalation_payload = dict(escalation_policy.get(field_name, {}) or {})
            routing_payload = dict(routing_hints.get(field_name, {}) or {})
            sla_payload = dict(sla_policy.get(field_name, {}) or {})
            created_at = _best_timestamp(item.created_at, item.updated_at, "")
            age_hours = _age_hours(created_at, now)
            queue_rows.append(asdict(GlobalReviewQueuePacket(
                document_id=item.document_id,
                review_item_id=item.document_id,
                document_type=doc_type or "passport",
                field_name=field_name,
                queue_rank=0,
                priority_score=int(queue_item.get("priority_score") or 0),
                priority_band=str(queue_item.get("priority_band") or "LOW"),
                attention_state=attention_state,
                current_status=str(queue_item.get("current_status") or item.status or "PENDING"),
                conflict_level=str(queue_item.get("conflict_level") or "UNKNOWN"),
                confidence_band=str(queue_item.get("confidence_band") or "UNKNOWN"),
                recommended_action=str(queue_item.get("recommended_action") or "REVIEW"),
                last_updated=_best_timestamp(((item.unresolved_fields or {}).get(field_name) or {}).get("last_updated"), triage_payload.get("acted_at"), assignment_payload.get("last_assignment_refresh"), item.updated_at, item.created_at),
                created_at=created_at,
                age_hours=age_hours,
                age_bucket=_age_bucket(age_hours),
                staleness_band=_staleness_band(age_hours),
                escalation_level=str(escalation_payload.get("escalation_level") or "NONE"),
                escalation_reason=list(escalation_payload.get("escalation_reason", [])),
                triage_status=str(triage_payload.get("triage_status") or ""),
                triage_action=str(triage_payload.get("triage_action") or ""),
                triage_note=str(triage_payload.get("triage_note") or ""),
                triaged_at=str(triage_payload.get("acted_at") or ""),
                routing_bucket=str(routing_payload.get("routing_bucket") or "CLEAR_NO_ROUTING"),
                owner_hint=str(routing_payload.get("owner_hint") or "OPERATOR"),
                assignment_reason=list(routing_payload.get("assignment_reason", [])),
                assignment_status=str(assignment_payload.get("assignment_status") or ""),
                assigned_bucket=str(assignment_payload.get("assigned_bucket") or ""),
                assigned_owner_hint=str(assignment_payload.get("owner_hint") or ""),
                assigned_at=str(assignment_payload.get("assigned_at") or ""),
                assignment_note=str(assignment_payload.get("owner_note") or ""),
                sla_state=str(sla_payload.get("sla_state") or "NORMAL"),
                watch_level=str(sla_payload.get("watch_level") or "NONE"),
                notification_ready=bool(sla_payload.get("notification_ready")),
                requires_watch_ack=bool(sla_payload.get("requires_ack")),
                notification_severity=str(sla_payload.get("notification_severity") or "NONE"),
            )))
    queue_rows.sort(key=lambda row: (-_escalation_rank(str(row.get("escalation_level") or "NONE")), -_assignment_sort_bonus(str(row.get("assignment_status") or "")), -_triage_sort_bonus(str(row.get("triage_status") or "")), -(row.get("priority_score") or 0), 0 if row.get("attention_state") == "UNRESOLVED" else 1, -(row.get("age_hours") or 0.0), row.get("document_id") or "", row.get("field_name") or ""))
    for idx, row in enumerate(queue_rows, start=1):
        row["queue_rank"] = idx
    return queue_rows


def build_dashboard_summary(review_items: List[ReviewQueueItem], global_queue: List[Dict[str, Any]], watch_queue: List[Dict[str, Any]], reminder_queue: List[Dict[str, Any]], notification_queue: List[Dict[str, Any]], transport_queue: List[Dict[str, Any]], alert_feed: List[Dict[str, Any]], incident_feed: List[Dict[str, Any]] | None = None, export_queue: List[Dict[str, Any]] | None = None, intake_queue: List[Dict[str, Any]] | None = None, dropzone_queue: List[Dict[str, Any]] | None = None, now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    incident_feed = incident_feed or []
    export_queue = export_queue or []
    intake_queue = intake_queue or []
    dropzone_queue = dropzone_queue or []
    pending_docs = [item for item in review_items if str((item.tce.WHAT or {}).get("document_type") or "passport") == "passport" and str(item.status or "") != "REJECTED"]
    oldest_pending_documents = []
    for item in pending_docs:
        created_at = _best_timestamp(item.created_at, item.updated_at, "")
        age_hours = _age_hours(created_at, now)
        oldest_pending_documents.append({"document_id": item.document_id, "status": item.status, "created_at": created_at, "age_hours": age_hours, "age_bucket": _age_bucket(age_hours), "staleness_band": _staleness_band(age_hours)})
    oldest_pending_documents.sort(key=lambda row: -(row.get("age_hours") or 0.0))
    return asdict(DashboardSummaryPacket(
        total_pending_review_documents=len(pending_docs),
        total_unresolved_fields=len([row for row in global_queue if row.get("attention_state") == "UNRESOLVED"]),
        total_attention_fields=len([row for row in global_queue if row.get("attention_state") in {"UNRESOLVED", "ATTENTION"}]),
        total_high_escalation_fields=len([row for row in global_queue if row.get("escalation_level") == "HIGH"]),
        total_critical_escalation_fields=len([row for row in global_queue if row.get("escalation_level") == "CRITICAL"]),
        total_routed_fields=len([row for row in global_queue if row.get("routing_bucket") not in {"", "CLEAR_NO_ROUTING"}]),
        total_assigned_fields=len([row for row in global_queue if row.get("assignment_status") == "ASSIGNED"]),
        total_unassigned_escalated_fields=len([row for row in global_queue if row.get("escalation_level") in {"HIGH", "CRITICAL"} and row.get("assignment_status") != "ASSIGNED"]),
        total_watch_items=len(watch_queue),
        total_warning_watch_items=len([row for row in watch_queue if row.get("sla_state") == "WARNING"]),
        total_breach_watch_items=len([row for row in watch_queue if row.get("sla_state") == "BREACH"]),
        total_reminder_ready_items=len([row for row in reminder_queue if row.get("reminder_state") == "READY"]),
        total_reminder_snoozed_items=len([row for row in reminder_queue if row.get("reminder_state") == "SNOOZED"]),
        total_reminder_sent_items=len([row for row in reminder_queue if row.get("reminder_state") == "SENT"]),
        total_notification_ready_items=len([row for row in notification_queue if row.get("prep_state") == "READY"]),
        total_notification_emitted_items=len([row for row in notification_queue if row.get("prep_state") == "EMITTED"]),
        total_notification_failed_items=len([row for row in notification_queue if row.get("prep_state") == "FAILED"]),
        total_notification_canceled_items=len([row for row in notification_queue if row.get("prep_state") == "CANCELED"]),
        total_transport_ready_items=len([row for row in transport_queue if row.get("latest_result_state") == "HANDOFF_READY"]),
        total_transport_accepted_items=len([row for row in transport_queue if row.get("latest_result_state") == "HANDOFF_ACCEPTED"]),
        total_transport_failed_items=len([row for row in transport_queue if row.get("latest_result_state") == "HANDOFF_FAILED"]),
        total_transport_rejected_items=len([row for row in transport_queue if row.get("latest_result_state") == "HANDOFF_REJECTED"]),
        total_active_alerts=len([row for row in alert_feed if row.get("alert_state") in {"ACTIVE", "REOPENED"}]),
        total_acknowledged_alerts=len([row for row in alert_feed if row.get("alert_state") == "ACKNOWLEDGED"]),
        total_cleared_alerts=len([row for row in alert_feed if row.get("alert_state") == "CLEARED"]),
        total_pinned_alerts=len([row for row in alert_feed if row.get("is_pinned") is True]),
        total_open_incidents=len([row for row in incident_feed if row.get("incident_state") in {"OPEN", "REOPENED"}]),
        total_acknowledged_incidents=len([row for row in incident_feed if row.get("incident_state") == "ACKNOWLEDGED"]),
        total_closed_incidents=len([row for row in incident_feed if row.get("incident_state") == "CLOSED"]),
        total_pinned_incidents=len([row for row in incident_feed if row.get("incident_state") == "PINNED"]),
        total_export_ready_items=len([row for row in export_queue if row.get("latest_result_state") == "EXPORT_READY"]),
        total_export_accepted_items=len([row for row in export_queue if row.get("latest_result_state") == "EXPORT_ACCEPTED"]),
        total_export_failed_items=len([row for row in export_queue if row.get("latest_result_state") == "EXPORT_FAILED"]),
        total_export_rejected_items=len([row for row in export_queue if row.get("latest_result_state") == "EXPORT_REJECTED"]),
        total_intake_pending_items=len([row for row in intake_queue if row.get("latest_ack_state") == "INTAKE_PENDING"]),
        total_intake_accepted_items=len([row for row in intake_queue if row.get("latest_ack_state") == "INTAKE_ACCEPTED"]),
        total_intake_rejected_items=len([row for row in intake_queue if row.get("latest_ack_state") == "INTAKE_REJECTED"]),
        total_intake_invalid_items=len([row for row in intake_queue if row.get("latest_ack_state") == "INTAKE_INVALID"]),
        total_dropzone_staged_items=len([row for row in dropzone_queue if row.get("handshake_state") in {"DROPZONE_STAGED", "DROPZONE_WRITTEN"}]),
        total_receipt_pending_items=len([row for row in dropzone_queue if row.get("latest_receipt_state") == "RECEIPT_PENDING"]),
        total_receipt_accepted_items=len([row for row in dropzone_queue if row.get("latest_receipt_state") == "RECEIPT_ACCEPTED"]),
        total_receipt_rejected_items=len([row for row in dropzone_queue if row.get("latest_receipt_state") == "RECEIPT_REJECTED"]),
        total_receipt_failed_items=len([row for row in dropzone_queue if row.get("latest_receipt_state") in {"RECEIPT_FAILED", "RECEIPT_MISSING"}]),
        total_stale_handshake_items=len([row for row in dropzone_queue if str((row.get("recovery") or {}).get("recovery_state") or "") == "HANDSHAKE_STALE"]),
        total_recovery_needed_items=len([row for row in dropzone_queue if str((row.get("recovery") or {}).get("recovery_state") or "") in {"HANDSHAKE_RECOVERY_NEEDED", "HANDSHAKE_RESTAGE_RECOMMENDED"}]),
        total_duplicate_receipt_items=len([row for row in dropzone_queue if bool((row.get("reconciliation") or {}).get("duplicate_detected"))]),
        highest_priority_items=list(global_queue[:5]),
        oldest_pending_documents=oldest_pending_documents[:5],
        escalated_items=[row for row in global_queue if str(row.get("escalation_level") or "NONE") in {"HIGH", "CRITICAL"}][:5],
        routed_items=[row for row in global_queue if str(row.get("routing_bucket") or "") not in {"", "CLEAR_NO_ROUTING"}][:5],
        watch_items=list(watch_queue[:5]),
        reminder_items=list(reminder_queue[:5]),
        notification_items=list(notification_queue[:5]),
        transport_items=list(transport_queue[:5]),
        alert_items=list(alert_feed[:5]),
        incident_items=list(incident_feed[:5]),
        export_items=list(export_queue[:5]),
        intake_items=list(intake_queue[:5]),
        dropzone_items=list(dropzone_queue[:5]),
    ))


def build_dashboard_tce_delta(global_queue: List[Dict[str, Any]], dashboard_summary: Dict[str, Any], refreshed_at: str | None = None) -> Dict[str, Any]:
    refreshed_at = refreshed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "HOW": {
            "queue_summary": {
                "total_queue_items": len(global_queue),
                "top_document_ids": [row.get("document_id") for row in global_queue[:5]],
                "escalated_items": len([row for row in global_queue if row.get("escalation_level") in {"HIGH", "CRITICAL"}]),
                "assigned_items": len([row for row in global_queue if row.get("assignment_status") == "ASSIGNED"]),
            },
            "dashboard_summary": {
                "total_pending_review_documents": dashboard_summary.get("total_pending_review_documents", 0),
                "total_unresolved_fields": dashboard_summary.get("total_unresolved_fields", 0),
                "total_attention_fields": dashboard_summary.get("total_attention_fields", 0),
                "total_high_escalation_fields": dashboard_summary.get("total_high_escalation_fields", 0),
                "total_critical_escalation_fields": dashboard_summary.get("total_critical_escalation_fields", 0),
                "total_routed_fields": dashboard_summary.get("total_routed_fields", 0),
                "total_assigned_fields": dashboard_summary.get("total_assigned_fields", 0),
                "total_watch_items": dashboard_summary.get("total_watch_items", 0),
                "total_warning_watch_items": dashboard_summary.get("total_warning_watch_items", 0),
                "total_breach_watch_items": dashboard_summary.get("total_breach_watch_items", 0),
                "total_reminder_ready_items": dashboard_summary.get("total_reminder_ready_items", 0),
                "total_reminder_snoozed_items": dashboard_summary.get("total_reminder_snoozed_items", 0),
                "total_reminder_sent_items": dashboard_summary.get("total_reminder_sent_items", 0),
                "total_notification_ready_items": dashboard_summary.get("total_notification_ready_items", 0),
                "total_notification_emitted_items": dashboard_summary.get("total_notification_emitted_items", 0),
                "total_notification_failed_items": dashboard_summary.get("total_notification_failed_items", 0),
                "total_notification_canceled_items": dashboard_summary.get("total_notification_canceled_items", 0),
                "total_transport_ready_items": dashboard_summary.get("total_transport_ready_items", 0),
                "total_transport_accepted_items": dashboard_summary.get("total_transport_accepted_items", 0),
                "total_transport_failed_items": dashboard_summary.get("total_transport_failed_items", 0),
                "total_transport_rejected_items": dashboard_summary.get("total_transport_rejected_items", 0),
                "total_active_alerts": dashboard_summary.get("total_active_alerts", 0),
                "total_acknowledged_alerts": dashboard_summary.get("total_acknowledged_alerts", 0),
                "total_cleared_alerts": dashboard_summary.get("total_cleared_alerts", 0),
                "total_pinned_alerts": dashboard_summary.get("total_pinned_alerts", 0),
                "total_open_incidents": dashboard_summary.get("total_open_incidents", 0),
                "total_acknowledged_incidents": dashboard_summary.get("total_acknowledged_incidents", 0),
                "total_closed_incidents": dashboard_summary.get("total_closed_incidents", 0),
                "total_pinned_incidents": dashboard_summary.get("total_pinned_incidents", 0),
                "total_export_ready_items": dashboard_summary.get("total_export_ready_items", 0),
                "total_export_accepted_items": dashboard_summary.get("total_export_accepted_items", 0),
                "total_export_failed_items": dashboard_summary.get("total_export_failed_items", 0),
                "total_export_rejected_items": dashboard_summary.get("total_export_rejected_items", 0),
                "total_intake_pending_items": dashboard_summary.get("total_intake_pending_items", 0),
                "total_intake_accepted_items": dashboard_summary.get("total_intake_accepted_items", 0),
                "total_intake_rejected_items": dashboard_summary.get("total_intake_rejected_items", 0),
                "total_intake_invalid_items": dashboard_summary.get("total_intake_invalid_items", 0),
                "total_dropzone_staged_items": dashboard_summary.get("total_dropzone_staged_items", 0),
                "total_receipt_pending_items": dashboard_summary.get("total_receipt_pending_items", 0),
                "total_receipt_accepted_items": dashboard_summary.get("total_receipt_accepted_items", 0),
                "total_receipt_rejected_items": dashboard_summary.get("total_receipt_rejected_items", 0),
                "total_receipt_failed_items": dashboard_summary.get("total_receipt_failed_items", 0),
                "total_stale_handshake_items": dashboard_summary.get("total_stale_handshake_items", 0),
                "total_recovery_needed_items": dashboard_summary.get("total_recovery_needed_items", 0),
                "total_duplicate_receipt_items": dashboard_summary.get("total_duplicate_receipt_items", 0),
            },
        },
        "WHY": {"dashboard_priority_reason": [f"{row.get('document_id')}:{row.get('field_name')}:{row.get('priority_band')}:{row.get('escalation_level')}:{row.get('routing_bucket')}" for row in global_queue[:5]]},
        "WHEN": {"dashboard_refreshed_at": refreshed_at},
    }


def build_control_room_tce_delta(*, escalation_policy: Dict[str, Any], triage_state: Dict[str, Any], routing_hints: Dict[str, Any], assignment_state: Dict[str, Any], sla_policy: Dict[str, Any], watch_state: Dict[str, Any], reminder_stage: Dict[str, Any], notification_prep: Dict[str, Any], notification_ledger: Dict[str, Any], delivery_attempts: Dict[str, Any], transport_requests: Dict[str, Any], transport_results: Dict[str, Any], local_alerts: Dict[str, Any], incident_threads: Dict[str, Any], external_bridge_exports: Dict[str, Any], external_bridge_results: Dict[str, Any], intake_contracts: Dict[str, Any], intake_acks: Dict[str, Any], dropzone_handshakes: Dict[str, Any], dropzone_receipts: Dict[str, Any], dropzone_reconciliation: Dict[str, Any], dropzone_recovery: Dict[str, Any], evaluated_at: str) -> Dict[str, Any]:
    escalation_summary = {"NONE": 0, "LOW": 0, "HIGH": 0, "CRITICAL": 0}
    escalation_reason = {}
    for field_name, payload in (escalation_policy or {}).items():
        level = str((payload or {}).get("escalation_level") or "NONE")
        escalation_summary[level] = escalation_summary.get(level, 0) + 1
        escalation_reason[field_name] = list((payload or {}).get("escalation_reason", []))
    reminder_summary = {"READY": 0, "SNOOZED": 0, "SENT": 0, "CLEARED": 0}
    reminder_reason = {}
    notification_reason = {}
    reminder_due_at = {}
    reminder_sent_at = {}
    snoozed_until = {}
    for field_name, payload in (reminder_stage or {}).items():
        state = str((payload or {}).get("reminder_state") or "CLEARED")
        reminder_summary[state] = reminder_summary.get(state, 0) + 1
        reminder_reason[field_name] = list((payload or {}).get("staged_reason", []))
        reminder_due_at[field_name] = str((payload or {}).get("reminder_due_at") or "")
        if (payload or {}).get("snooze_until"):
            snoozed_until[field_name] = str(payload.get("snooze_until") or "")
    for field_name, payload in (notification_prep or {}).items():
        notification_reason[field_name] = list((payload or {}).get("prep_reason", []))
        if (payload or {}).get("sent_at"):
            reminder_sent_at[field_name] = str(payload.get("sent_at") or "")
        if (payload or {}).get("snoozed_until"):
            snoozed_until[field_name] = str(payload.get("snoozed_until") or "")
    notification_ledger_summary = {"READY": 0, "EMITTED": 0, "FAILED": 0, "CANCELED": 0}
    delivery_attempt_summary = {}
    delivery_reason = {}
    notification_created_at = {}
    delivery_attempted_at = {}
    notification_canceled_at = {}
    transport_summary = {"HANDOFF_READY": 0, "HANDOFF_ACCEPTED": 0, "HANDOFF_REJECTED": 0, "HANDOFF_FAILED": 0}
    handoff_summary = {}
    handoff_reason = {}
    transport_reason = {}
    handoff_requested_at = {}
    handoff_completed_at = {}
    alert_feed_summary = {"ACTIVE": 0, "ACKNOWLEDGED": 0, "CLEARED": 0, "REOPENED": 0}
    alert_reason = {}
    alert_created_at = {}
    alert_acknowledged_at = {}
    alert_cleared_at = {}
    incident_summary = {"OPEN": 0, "ACKNOWLEDGED": 0, "PINNED": 0, "CLOSED": 0, "REOPENED": 0}
    incident_reason = {}
    incident_opened_at = {}
    incident_last_seen_at = {}
    incident_closed_at = {}
    export_summary = {"EXPORT_READY": 0, "EXPORT_ACCEPTED": 0, "EXPORT_REJECTED": 0, "EXPORT_FAILED": 0, "EXPORT_SKIPPED": 0}
    bridge_summary = {}
    export_reason = {}
    bridge_reason = {}
    export_staged_at = {}
    export_completed_at = {}
    intake_summary = {"INTAKE_PENDING": 0, "INTAKE_ACCEPTED": 0, "INTAKE_REJECTED": 0, "INTAKE_INVALID": 0, "INTAKE_SKIPPED": 0}
    intake_validation_summary = {}
    intake_reason = {}
    intake_rejection_reason = {}
    intake_received_at = {}
    intake_acknowledged_at = {}
    handshake_summary = {"DROPZONE_STAGED": 0, "DROPZONE_WRITTEN": 0, "RECEIPT_PENDING": 0, "RECEIPT_ACCEPTED": 0, "RECEIPT_REJECTED": 0, "RECEIPT_FAILED": 0, "RECEIPT_MISSING": 0}
    dropzone_summary = {}
    handshake_reason = {}
    receipt_reason = {}
    dropzone_staged_at = {}
    receipt_received_at = {}
    reconciliation_summary = {}
    recovery_summary = {}
    recovery_marked_at = {}
    for field_name, payload in (notification_ledger or {}).items():
        state = str((payload or {}).get("prep_state") or "CANCELED")
        notification_ledger_summary[state] = notification_ledger_summary.get(state, 0) + 1
        notification_created_at[field_name] = str((payload or {}).get("created_at") or "")
        if state == "CANCELED":
            notification_canceled_at[field_name] = str((payload or {}).get("updated_at") or "")
    for field_name, attempts in (delivery_attempts or {}).items():
        attempts_list = list(attempts or [])
        delivery_attempt_summary[field_name] = {
            "attempt_count": len(attempts_list),
            "last_attempt_state": str((attempts_list[-1] or {}).get("attempt_state") or "") if attempts_list else "",
        }
        delivery_reason[field_name] = [str((attempt or {}).get("result_reason") or "") for attempt in attempts_list if str((attempt or {}).get("result_reason") or "")]
        if attempts_list:
            delivery_attempted_at[field_name] = str((attempts_list[-1] or {}).get("attempted_at") or "")
    for field_name, payload in (transport_requests or {}).items():
        handoff_requested_at[field_name] = str((payload or {}).get("created_at") or "")
        handoff_reason[field_name] = list((payload or {}).get("handoff_reason", []))
        if field_name not in (transport_results or {}) or not list((transport_results or {}).get(field_name, []) or []):
            transport_summary["HANDOFF_READY"] = transport_summary.get("HANDOFF_READY", 0) + 1
            handoff_summary[field_name] = {
                "channel_hint": str((payload or {}).get("channel_hint") or ""),
                "latest_result_state": "HANDOFF_READY",
                "result_count": 0,
            }
    for field_name, results in (transport_results or {}).items():
        results_list = list(results or [])
        latest_result = dict(results_list[-1]) if results_list else {}
        state = str(latest_result.get("result_state") or "HANDOFF_READY")
        transport_summary[state] = transport_summary.get(state, 0) + 1
        handoff_summary[field_name] = {
            "channel_hint": str((transport_requests.get(field_name) or {}).get("channel_hint") or ""),
            "latest_result_state": state,
            "result_count": len(results_list),
        }
        transport_reason[field_name] = [str((result or {}).get("result_reason") or "") for result in results_list if str((result or {}).get("result_reason") or "")]
        if latest_result.get("handed_off_at"):
            handoff_completed_at[field_name] = str(latest_result.get("handed_off_at") or "")
    for field_name, payload in (local_alerts or {}).items():
        state = str((payload or {}).get("alert_state") or "ACTIVE")
        alert_feed_summary[state] = alert_feed_summary.get(state, 0) + 1
        alert_reason[field_name] = list((payload or {}).get("alert_reason", []))
        alert_created_at[field_name] = str((payload or {}).get("created_at") or "")
        if (payload or {}).get("acknowledged_at"):
            alert_acknowledged_at[field_name] = str(payload.get("acknowledged_at") or "")
        if (payload or {}).get("cleared_at"):
            alert_cleared_at[field_name] = str(payload.get("cleared_at") or "")
    for field_name, payload in (incident_threads or {}).items():
        state = str((payload or {}).get("incident_state") or "OPEN")
        incident_summary[state] = incident_summary.get(state, 0) + 1
        incident_reason[field_name] = list((payload or {}).get("incident_reason", []))
        incident_opened_at[field_name] = str((payload or {}).get("created_at") or "")
        incident_last_seen_at[field_name] = str((payload or {}).get("last_alert_at") or (payload or {}).get("updated_at") or "")
        if (payload or {}).get("closed_at"):
            incident_closed_at[field_name] = str(payload.get("closed_at") or "")
    for field_name, payload in (external_bridge_exports or {}).items():
        latest_result = dict((external_bridge_results or {}).get(field_name, {}) or {})
        state = str(latest_result.get("result_state") or (payload or {}).get("export_state") or "EXPORT_READY")
        export_summary[state] = export_summary.get(state, 0) + 1
        bridge_summary[field_name] = {
            "target_hint": str((payload or {}).get("target_hint") or latest_result.get("target_hint") or ""),
            "result_state": state,
            "adapter_name": str(latest_result.get("adapter_name") or "PORTALIS_EXTERNAL_BRIDGE"),
        }
        export_reason[field_name] = list((((payload or {}).get("source_summary") or {}).get("incident_reason", [])) or [])
        bridge_reason[field_name] = [str(latest_result.get("result_reason") or "")] if str(latest_result.get("result_reason") or "") else []
        export_staged_at[field_name] = str((payload or {}).get("created_at") or "")
        if latest_result.get("exported_at"):
            export_completed_at[field_name] = str(latest_result.get("exported_at") or "")
    for field_name, payload in (intake_contracts or {}).items():
        latest_ack = dict((intake_acks or {}).get(field_name, {}) or {})
        state = str(latest_ack.get("ack_state") or (payload or {}).get("latest_ack_state") or "INTAKE_PENDING")
        intake_summary[state] = intake_summary.get(state, 0) + 1
        intake_validation_summary[field_name] = dict((payload or {}).get("validation", {}) or {})
        intake_reason[field_name] = list(((payload or {}).get("validation", {}) or {}).get("validation_messages", []) or [])
        intake_received_at[field_name] = str((payload or {}).get("received_at") or "")
        if latest_ack.get("ack_reason"):
            intake_rejection_reason[field_name] = [str(latest_ack.get("ack_reason") or "")]
        if latest_ack.get("acknowledged_at"):
            intake_acknowledged_at[field_name] = str(latest_ack.get("acknowledged_at") or "")
    for field_name, payload in (dropzone_handshakes or {}).items():
        latest_receipt = dict((dropzone_receipts or {}).get(field_name, {}) or {})
        reconciliation_payload = dict((dropzone_reconciliation or {}).get(field_name, {}) or {})
        recovery_payload = dict((dropzone_recovery or {}).get(field_name, {}) or {})
        state = str(latest_receipt.get("receipt_state") or (payload or {}).get("handshake_state") or "DROPZONE_STAGED")
        handshake_summary[state] = handshake_summary.get(state, 0) + 1
        dropzone_summary[field_name] = {
            "target_hint": str((payload or {}).get("target_hint") or ""),
            "handshake_state": str((payload or {}).get("handshake_state") or ""),
            "receipt_state": state,
            "payload_filename": str((payload or {}).get("payload_filename") or ""),
        }
        handshake_reason[field_name] = [str((payload or {}).get("dropzone_path") or "")]
        if latest_receipt.get("receipt_reason"):
            receipt_reason[field_name] = [str(latest_receipt.get("receipt_reason") or "")]
        dropzone_staged_at[field_name] = str((payload or {}).get("staged_at") or "")
        if latest_receipt.get("received_at"):
            receipt_received_at[field_name] = str(latest_receipt.get("received_at") or "")
        if reconciliation_payload:
            reconciliation_summary[field_name] = reconciliation_payload
        if recovery_payload:
            recovery_summary[field_name] = recovery_payload
            if recovery_payload.get("marked_at"):
                recovery_marked_at[field_name] = str(recovery_payload.get("marked_at") or "")
    return {
        "HOW": {
            "escalation_summary": escalation_summary,
            "triage_summary": {field_name: {"triage_action": payload.get("triage_action"), "triage_status": payload.get("triage_status")} for field_name, payload in (triage_state or {}).items()},
            "routing_summary": {field_name: {"routing_bucket": payload.get("routing_bucket"), "owner_hint": payload.get("owner_hint")} for field_name, payload in (routing_hints or {}).items()},
            "assignment_summary": {field_name: {"assigned_bucket": payload.get("assigned_bucket"), "owner_hint": payload.get("owner_hint"), "assignment_status": payload.get("assignment_status")} for field_name, payload in (assignment_state or {}).items()},
            "sla_summary": {field_name: {"sla_state": payload.get("sla_state"), "watch_level": payload.get("watch_level"), "notification_ready": payload.get("notification_ready")} for field_name, payload in (sla_policy or {}).items()},
            "watch_summary": {field_name: {"watch_status": payload.get("watch_status"), "watch_acknowledged_at": payload.get("watch_acknowledged_at")} for field_name, payload in (watch_state or {}).items()},
            "reminder_summary": reminder_summary,
            "notification_prep_summary": {field_name: {"prep_state": payload.get("prep_state"), "severity": payload.get("severity"), "ready_at": payload.get("ready_at")} for field_name, payload in (notification_prep or {}).items()},
            "notification_ledger_summary": notification_ledger_summary,
            "delivery_attempt_summary": delivery_attempt_summary,
            "transport_summary": transport_summary,
            "handoff_summary": handoff_summary,
            "alert_feed_summary": alert_feed_summary,
            "incident_summary": incident_summary,
            "export_summary": export_summary,
            "bridge_summary": bridge_summary,
            "intake_summary": intake_summary,
            "intake_validation_summary": intake_validation_summary,
            "handshake_summary": handshake_summary,
            "dropzone_summary": dropzone_summary,
            "reconciliation_summary": reconciliation_summary,
            "recovery_summary": recovery_summary,
        },
        "WHY": {
            "escalation_reason": escalation_reason,
            "triage_reason": {field_name: str((payload or {}).get("triage_note") or "") for field_name, payload in (triage_state or {}).items()},
            "routing_reason": {field_name: list((payload or {}).get("assignment_reason", [])) for field_name, payload in (routing_hints or {}).items()},
            "assignment_reason": {field_name: list((payload or {}).get("assignment_reason", [])) for field_name, payload in (assignment_state or {}).items()},
            "sla_reason": {field_name: list((payload or {}).get("watch_trigger_reason", [])) for field_name, payload in (sla_policy or {}).items()},
            "watch_reason": {field_name: str((payload or {}).get("watch_note") or "") for field_name, payload in (watch_state or {}).items()},
            "reminder_reason": reminder_reason,
            "notification_reason": notification_reason,
            "delivery_reason": delivery_reason,
            "handoff_reason": handoff_reason,
            "transport_reason": transport_reason,
            "alert_reason": alert_reason,
            "incident_reason": incident_reason,
            "export_reason": export_reason,
            "bridge_reason": bridge_reason,
            "intake_reason": intake_reason,
            "intake_rejection_reason": intake_rejection_reason,
            "handshake_reason": handshake_reason,
            "receipt_reason": receipt_reason,
            "recovery_reason": {field_name: list((payload or {}).get("recovery_reason", [])) for field_name, payload in (dropzone_recovery or {}).items()},
            "restage_reason": {field_name: list((payload or {}).get("recovery_reason", [])) for field_name, payload in (dropzone_recovery or {}).items() if bool((payload or {}).get("restage_recommended"))},
        },
        "WHEN": {
            "escalated_at": evaluated_at,
            "triaged_at": max([str((payload or {}).get("acted_at") or "") for payload in (triage_state or {}).values()] or [evaluated_at]),
            "assigned_at": max([str((payload or {}).get("assigned_at") or "") for payload in (assignment_state or {}).values()] or [evaluated_at]),
            "routing_evaluated_at": evaluated_at,
            "watch_triggered_at": max([str((payload or {}).get("evaluated_at") or "") for payload in (sla_policy or {}).values()] or [evaluated_at]),
            "sla_evaluated_at": evaluated_at,
            "reminder_due_at": reminder_due_at,
            "reminder_staged_at": evaluated_at,
            "reminder_sent_at": reminder_sent_at,
            "snoozed_until": snoozed_until,
            "notification_created_at": notification_created_at,
            "delivery_attempted_at": delivery_attempted_at,
            "notification_canceled_at": notification_canceled_at,
            "handoff_requested_at": handoff_requested_at,
            "handoff_completed_at": handoff_completed_at,
            "alert_created_at": alert_created_at,
            "alert_acknowledged_at": alert_acknowledged_at,
            "alert_cleared_at": alert_cleared_at,
            "incident_opened_at": incident_opened_at,
            "incident_last_seen_at": incident_last_seen_at,
            "incident_closed_at": incident_closed_at,
            "export_staged_at": export_staged_at,
            "export_completed_at": export_completed_at,
            "intake_received_at": intake_received_at,
            "intake_acknowledged_at": intake_acknowledged_at,
            "dropzone_staged_at": dropzone_staged_at,
            "receipt_received_at": receipt_received_at,
            "reconciled_at": {field_name: str((payload or {}).get("reconciled_at") or "") for field_name, payload in (dropzone_reconciliation or {}).items()},
            "recovery_marked_at": recovery_marked_at,
        },
    }


def _derive_escalation_level(*, field_name: str, attention_state: str, criticality: str, conflict_level: str, confidence_band: str, staleness_band: str, override_count: int, current_status: str, recommended_action: str, triage_status: str) -> Tuple[str, List[str], List[str]]:
    if current_status in {"ACCEPTED", "RESOLVED", "REJECTED"} and attention_state != "UNRESOLVED":
        return "NONE", ["field already resolved"], ["field_status"]
    reasons: List[str] = []
    triggers: List[str] = []
    score = 0
    if attention_state == "UNRESOLVED":
        score += 45; reasons.append("explicitly unresolved"); triggers.append("attention_state")
    elif attention_state == "ATTENTION":
        score += 15; reasons.append("attention required"); triggers.append("attention_state")
    if criticality == "CRITICAL":
        score += 28; reasons.append("critical field"); triggers.append("field_criticality")
    elif criticality == "HIGH":
        score += 20; reasons.append("high-criticality field"); triggers.append("field_criticality")
    elif criticality == "MEDIUM":
        score += 10
    if conflict_level == "HIGH":
        score += 30; reasons.append("high conflict"); triggers.append("conflict_level")
    elif conflict_level == "MEDIUM":
        score += 16; reasons.append("medium conflict"); triggers.append("conflict_level")
    if confidence_band == "LOW":
        score += 18; reasons.append("low confidence"); triggers.append("confidence_band")
    elif confidence_band == "UNKNOWN":
        score += 14; reasons.append("unknown confidence"); triggers.append("confidence_band")
    if staleness_band == "AGED":
        score += 25; reasons.append("aged queue item"); triggers.append("staleness")
    elif staleness_band == "STALE":
        score += 12; reasons.append("stale queue item"); triggers.append("staleness")
    if override_count >= 2:
        score += 24; reasons.append("repeated operator overrides"); triggers.append("override_pattern")
    elif override_count == 1:
        score += 8
    if field_name == "passport.number" and conflict_level == "HIGH":
        score += 25; reasons.append("passport number disagreement"); triggers.append("passport_number_conflict")
    if recommended_action == "HIGH_ATTENTION":
        score += 12; reasons.append("recommended high attention"); triggers.append("recommended_action")
    elif recommended_action == "REVIEW":
        score += 6
    if triage_status == "PINNED":
        score += 10; reasons.append("operator pinned item"); triggers.append("triage_state")
    elif triage_status == "ESCALATED":
        score += 20; reasons.append("operator escalated item"); triggers.append("triage_state")
    elif triage_status == "DEFERRED":
        score = max(0, score - 8); reasons.append("operator deferred item"); triggers.append("triage_state")
    if score >= 95:
        return "CRITICAL", reasons, triggers
    if score >= 60:
        return "HIGH", reasons, triggers
    if score >= 25:
        return "LOW", reasons, triggers
    return "NONE", reasons or ["routine queue item"], triggers or ["policy_default"]


def _derive_routing_hint(*, field_name: str, escalation_level: str, attention_state: str, current_status: str, criticality: str, conflict_level: str, confidence_band: str, staleness_band: str, triage_status: str, override_count: int, evidence: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    if current_status in {"ACCEPTED", "RESOLVED", "REJECTED"} and attention_state == "CLEAR":
        return "CLEAR_NO_ROUTING", "OPERATOR", ["field already resolved"]
    reasons: List[str] = []
    missing_evidence = "missing_evidence" in list(evidence.get("warnings", []) or [])
    if escalation_level == "CRITICAL" and field_name == "passport.number":
        return "ASSIGN_SENIOR_REVIEW", "SENIOR_REVIEW", ["critical passport number conflict"]
    if missing_evidence and confidence_band in {"LOW", "UNKNOWN"}:
        return "HOLD_FOR_SOURCE_DOC", "DOCUMENT_REVIEW", ["missing source evidence for low-confidence field"]
    if override_count >= 2:
        return "FOLLOW_UP_REQUIRED", "FOLLOW_UP_QUEUE", ["repeated override pattern requires follow-up"]
    if attention_state == "UNRESOLVED" and staleness_band in {"STALE", "AGED"}:
        return "REVIEW_NOW", "OPERATOR", ["stale unresolved field"]
    if escalation_level == "CRITICAL":
        return "ASSIGN_SENIOR_REVIEW", "SENIOR_REVIEW", ["critical escalation"]
    if escalation_level == "HIGH":
        if criticality in {"CRITICAL", "HIGH"}:
            return "ASSIGN_DOC_REVIEW", "DOCUMENT_REVIEW", ["high escalation on important field"]
        return "REVIEW_NOW", "OPERATOR", ["high escalation"]
    if triage_status == "DEFERRED":
        return "FOLLOW_UP_REQUIRED", "FOLLOW_UP_QUEUE", ["triage deferred item"]
    if attention_state in {"UNRESOLVED", "ATTENTION"} and confidence_band in {"LOW", "UNKNOWN"}:
        return "ASSIGN_DOC_REVIEW", "DOCUMENT_REVIEW", ["attention item with low confidence"]
    if attention_state in {"UNRESOLVED", "ATTENTION"} and conflict_level in {"MEDIUM", "HIGH"}:
        return "REVIEW_NOW", "OPERATOR", ["conflict needs targeted review"]
    return "CLEAR_NO_ROUTING", "OPERATOR", ["no explicit routing needed"]


def _derive_sla_state(*, age_hours: float, staleness_band: str, escalation_level: str, assignment_status: str, routing_bucket: str, attention_state: str, current_status: str, triage_status: str) -> Tuple[str, str, List[str]]:
    if current_status in {"ACCEPTED", "RESOLVED", "REJECTED"} and attention_state == "CLEAR":
        return "NORMAL", "NONE", ["field already resolved"]
    reasons: List[str] = []
    score = 0
    if attention_state == "UNRESOLVED":
        score += SLA_TIMER_DEFAULTS["attention_unresolved"]; reasons.append("unresolved field")
    elif attention_state == "ATTENTION":
        score += SLA_TIMER_DEFAULTS["attention_review"]; reasons.append("attention field")
    if escalation_level == "CRITICAL":
        score += SLA_TIMER_DEFAULTS["escalation_critical"]; reasons.append("critical escalation")
    elif escalation_level == "HIGH":
        score += SLA_TIMER_DEFAULTS["escalation_high"]; reasons.append("high escalation")
    if staleness_band == "AGED":
        score += SLA_TIMER_DEFAULTS["staleness_aged"]; reasons.append("aged item")
    elif staleness_band == "STALE":
        score += SLA_TIMER_DEFAULTS["staleness_stale"]; reasons.append("stale item")
    elif staleness_band == "ACTIVE":
        score += SLA_TIMER_DEFAULTS["staleness_active"]
    if assignment_status == "ASSIGNED":
        if staleness_band in {"STALE", "AGED"}:
            score += SLA_TIMER_DEFAULTS["assignment_aging_penalty"]; reasons.append("assigned but still aging")
        else:
            score += SLA_TIMER_DEFAULTS["assignment_active_relief"]; reasons.append("actively assigned")
    else:
        if routing_bucket not in {"", "CLEAR_NO_ROUTING"}:
            score += SLA_TIMER_DEFAULTS["routed_unassigned_penalty"]; reasons.append("routed but unassigned")
    if triage_status == "DEFERRED":
        score = max(0, score + SLA_TIMER_DEFAULTS["triage_deferred_relief"]); reasons.append("triage deferred")
    elif triage_status == "PINNED":
        score += SLA_TIMER_DEFAULTS["triage_pinned_penalty"]; reasons.append("operator pinned")
    elif triage_status == "ACKNOWLEDGED":
        score = max(0, score + SLA_TIMER_DEFAULTS["triage_ack_relief"]); reasons.append("operator acknowledged")
    if score >= SLA_STATE_THRESHOLDS["breach_min"]:
        return "BREACH", "CRITICAL", reasons
    if score >= SLA_STATE_THRESHOLDS["warning_min"]:
        return "WARNING", "HIGH", reasons
    if score >= SLA_STATE_THRESHOLDS["watch_min"]:
        return "WATCH", "MEDIUM", reasons
    return "NORMAL", "LOW", reasons or ["within normal timer window"]


def _routing_recommended_action(routing_bucket: str, triage_payload: Dict[str, Any]) -> str:
    if str((triage_payload or {}).get("triage_status") or "") == "PINNED":
        return "PINNED_REVIEW"
    return {
        "REVIEW_NOW": "OPEN_REVIEW",
        "FOLLOW_UP_REQUIRED": "TRACK_FOLLOW_UP",
        "HOLD_FOR_SOURCE_DOC": "REQUEST_SOURCE_DOC",
        "ASSIGN_SENIOR_REVIEW": "ROUTE_TO_SENIOR",
        "ASSIGN_DOC_REVIEW": "ROUTE_TO_DOC_REVIEW",
        "CLEAR_NO_ROUTING": "NO_ACTION",
    }.get(routing_bucket, "REVIEW")


def _refresh_assignment_state(current_state: Dict[str, Any] | None, *, routing_hints: Dict[str, Any], refreshed_at: str) -> Dict[str, Any]:
    current_state = dict(current_state or {})
    refreshed: Dict[str, Any] = {}
    for field_name, payload in current_state.items():
        payload_dict = dict(payload or {})
        if not payload_dict or payload_dict.get("assignment_status") == "CLEARED":
            continue
        routing_payload = dict(routing_hints.get(field_name, {}) or {})
        payload_dict["last_assignment_refresh"] = refreshed_at
        payload_dict["routing_bucket"] = str(routing_payload.get("routing_bucket") or payload_dict.get("routing_bucket") or "")
        payload_dict["assignment_reason"] = list(routing_payload.get("assignment_reason", payload_dict.get("assignment_reason", [])))
        refreshed[field_name] = payload_dict
    return refreshed


def _escalation_recommended_action(level: str, recommended_action: str, triage_status: str) -> str:
    if triage_status == "PINNED":
        return "PINNED_REVIEW"
    if triage_status == "DEFERRED":
        return "DEFERRED_REVIEW"
    if level == "CRITICAL":
        return "ESCALATE_NOW"
    if level == "HIGH":
        return "MARK_FOR_REVIEW"
    return recommended_action or "REVIEW"


def _control_room_action_result(refresh: Dict[str, Any], document_id: str, field_name: str, packet_key: str, packet: Dict[str, Any]) -> Dict[str, Any]:
    queue_row = next((row for row in refresh["global_review_queue"] if row.get("document_id") == document_id and row.get("field_name") == field_name), None)
    return {packet_key: packet, "queue_row": queue_row, "dashboard_summary": refresh["dashboard_summary"]}


def _find_review_item(items: List[ReviewQueueItem], document_id: str) -> ReviewQueueItem:
    for item in items:
        if item.document_id == document_id:
            return item
    raise KeyError(f"Review item not found: {document_id}")


def _count_operator_overrides(compare_ledger: List[Dict[str, Any]], field_name: str) -> int:
    count = 0
    for entry in compare_ledger or []:
        if str(entry.get("field_name") or "") == field_name and bool(entry.get("operator_override")):
            count += 1
    return count


def _merge_tce(base_tce: TCELiteEnvelope, delta: Dict[str, Any]) -> TCELiteEnvelope:
    merged = TCELiteEnvelope(WHAT=dict(base_tce.WHAT or {}), WHO=dict(base_tce.WHO or {}), WHEN=dict(base_tce.WHEN or {}), WHERE=dict(base_tce.WHERE or {}), HOW=dict(base_tce.HOW or {}), WHY=dict(base_tce.WHY or {}))
    for key in ("WHAT", "WHO", "WHEN", "WHERE", "HOW", "WHY"):
        getattr(merged, key).update(dict(delta.get(key, {}) or {}))
    return merged


def _owner_hint_from_bucket(bucket: str) -> str:
    return {
        "REVIEW_NOW": "OPERATOR",
        "FOLLOW_UP_REQUIRED": "FOLLOW_UP_QUEUE",
        "HOLD_FOR_SOURCE_DOC": "DOCUMENT_REVIEW",
        "ASSIGN_SENIOR_REVIEW": "SENIOR_REVIEW",
        "ASSIGN_DOC_REVIEW": "DOCUMENT_REVIEW",
        "CLEAR_NO_ROUTING": "OPERATOR",
    }.get(str(bucket or ""), "OPERATOR")


def _best_timestamp(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _age_hours(timestamp: str, now: datetime) -> float:
    parsed = _parse_iso(timestamp) if timestamp else None
    if parsed is None:
        return 0.0
    return round(max((now - parsed).total_seconds(), 0.0) / 3600.0, 2)


def _age_bucket(age_hours: float) -> str:
    if age_hours < 4:
        return "0-4h"
    if age_hours < 24:
        return "4-24h"
    if age_hours < 72:
        return "1-3d"
    return "3d+"


def _staleness_band(age_hours: float) -> str:
    if age_hours < 4:
        return "FRESH"
    if age_hours < 24:
        return "ACTIVE"
    if age_hours < 72:
        return "STALE"
    return "AGED"


def _parse_iso(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _escalation_rank(level: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "LOW": 2, "NONE": 1}.get(str(level or "NONE"), 0)


def _triage_sort_bonus(status: str) -> int:
    return {"ESCALATED": 4, "PINNED": 3, "MARKED_FOR_REVIEW": 2, "ACKNOWLEDGED": 1, "DEFERRED": -1, "CLEARED": 0}.get(str(status or ""), 0)


def _assignment_sort_bonus(status: str) -> int:
    return {"ASSIGNED": 3, "ACKNOWLEDGED": 1, "CLEARED": 0}.get(str(status or ""), 0)


def _sla_rank(state: str) -> int:
    return {"BREACH": 4, "WARNING": 3, "WATCH": 2, "NORMAL": 1}.get(str(state or "NORMAL"), 0)


def _derive_reminder_state(*, now: datetime, current_status: str, sla_payload: Dict[str, Any], prep_payload: Dict[str, Any], watch_payload: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    if current_status in {"ACCEPTED", "RESOLVED", "REJECTED"}:
        return "CLEARED", "", ["field no longer pending"]
    reasons: List[str] = []
    prep_state = str(prep_payload.get("prep_state") or "").upper()
    snoozed_until = str(prep_payload.get("snoozed_until") or "")
    sent_at = str(prep_payload.get("sent_at") or "")
    notification_ready = bool(sla_payload.get("notification_ready"))
    requires_ack = bool(sla_payload.get("requires_ack"))
    sla_state = str(sla_payload.get("sla_state") or "NORMAL")

    if prep_state == "SENT" and sent_at:
        return "SENT", str(prep_payload.get("ready_at") or sent_at), ["prep marked sent"]

    snooze_dt = _parse_iso(snoozed_until) if snoozed_until else None
    if prep_state == "SNOOZED" and snooze_dt and snooze_dt > now:
        reasons.append("operator snooze active")
        return "SNOOZED", snoozed_until, reasons

    if not notification_ready and sla_state == "NORMAL":
        return "CLEARED", "", ["not notification ready"]

    if requires_ack and not (watch_payload or {}).get("watch_acknowledged_at"):
        reasons.append("watch acknowledgment pending")
    if notification_ready:
        reasons.append("notification-ready watch item")
    if sla_state == "BREACH":
        due_at = _offset_iso(now.strftime("%Y-%m-%dT%H:%M:%SZ"), REMINDER_STAGE_DEFAULTS["breach_minutes"])
        reasons.append("breach reminder threshold")
        return "READY", due_at, reasons
    if sla_state == "WARNING":
        due_at = _offset_iso(now.strftime("%Y-%m-%dT%H:%M:%SZ"), REMINDER_STAGE_DEFAULTS["warning_minutes"])
        reasons.append("warning reminder threshold")
        return "READY", due_at, reasons
    if sla_state == "WATCH" and notification_ready:
        due_at = _offset_iso(now.strftime("%Y-%m-%dT%H:%M:%SZ"), REMINDER_STAGE_DEFAULTS["watch_minutes"])
        reasons.append("watch reminder threshold")
        return "READY", due_at, reasons
    return "CLEARED", "", reasons or ["no active reminder stage"]


def _offset_iso(timestamp: str, minutes: int) -> str:
    base = _parse_iso(timestamp) or datetime.now(timezone.utc)
    shifted = base.timestamp() + (int(minutes) * 60)
    return datetime.fromtimestamp(shifted, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reminder_rank(state: str) -> int:
    return {"READY": 4, "SNOOZED": 3, "SENT": 2, "CLEARED": 1}.get(str(state or "CLEARED"), 0)


def _notification_rank(state: str) -> int:
    return {"FAILED": 4, "READY": 3, "EMITTED": 2, "CANCELED": 1}.get(str(state or "CANCELED"), 0)


def _notification_id(document_id: str, field_name: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    return f"NOTIFY::{document_id}::{safe_field}"


def _transport_request_id(document_id: str, field_name: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    return f"HANDOFF::{document_id}::{safe_field}"


def _derive_channel_hint(*, severity: str, source_sla_state: str, source_reminder_state: str) -> str:
    if source_sla_state == "BREACH" or severity == "CRITICAL":
        return "CONTROL_ROOM_FEED"
    if severity == "HIGH":
        return "FUTURE_EXTERNAL"
    if source_reminder_state in {"READY", "SENT"}:
        return "LOCAL_UI"
    return "FUTURE_EMAIL"


def _transport_result_reason(action: str) -> str:
    return {
        "STAGE_FOR_HANDOFF": "staged for transport handoff",
        "MARK_HANDOFF_ACCEPTED": "adapter accepted handoff",
        "MARK_HANDOFF_REJECTED": "adapter rejected handoff",
        "MARK_HANDOFF_FAILED": "adapter handoff failed",
        "CLEAR_HANDOFF_STATE": "handoff state cleared",
        "RETRY_HANDOFF": "handoff retried",
        "REQUEUE_HANDOFF": "handoff requeued",
    }.get(str(action or ""), "transport action recorded")


def _transport_rank(state: str) -> int:
    return {
        "HANDOFF_FAILED": 4,
        "HANDOFF_REJECTED": 3,
        "HANDOFF_READY": 2,
        "HANDOFF_ACCEPTED": 1,
    }.get(str(state or "HANDOFF_READY"), 0)


def _alert_id(document_id: str, field_name: str, source_type: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    safe_source = str(source_type or "CONTROL_ROOM").replace(".", "_")
    return f"ALERT::{document_id}::{safe_field}::{safe_source}"


def _alert_state_rank(state: str) -> int:
    return {
        "REOPENED": 4,
        "ACTIVE": 3,
        "ACKNOWLEDGED": 2,
        "CLEARED": 1,
    }.get(str(state or "ACTIVE"), 0)


def _alert_severity_rank(severity: str) -> int:
    return {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }.get(str(severity or "LOW"), 0)


def _incident_correlation_key(document_id: str, field_name: str, alert: Dict[str, Any]) -> str:
    reason_bits = "|".join(sorted(str(part or "") for part in list(alert.get("alert_reason", []) or [])))
    source_type = str(alert.get("source_type") or "CONTROL_ROOM_ALERT")
    return f"INCIDENT::{document_id}::{field_name}::{source_type}::{reason_bits}"


def _incident_state_rank(state: str) -> int:
    return {
        "REOPENED": 5,
        "PINNED": 4,
        "OPEN": 3,
        "ACKNOWLEDGED": 2,
        "CLOSED": 1,
    }.get(str(state or "OPEN"), 0)


def _external_export_id(document_id: str, field_name: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    return f"EXPORT::{document_id}::{safe_field}"


def _derive_export_target_hint(*, severity: str, escalation_level: str, reminder_state: str, watch_state: str) -> str:
    if escalation_level == "CRITICAL" or severity == "CRITICAL":
        return "ADMIN_BRIDGE"
    if watch_state == "BREACH":
        return "COUPLER_DROP"
    if reminder_state in {"READY", "SENT"}:
        return "LOCAL_EXPORT_FILE"
    return "FUTURE_EXTERNAL_CHANNEL"


def _external_bridge_result_reason(action: str) -> str:
    return {
        "STAGE_EXPORT": "staged for external bridge export",
        "MARK_EXPORT_ACCEPTED": "external bridge accepted export",
        "MARK_EXPORT_REJECTED": "external bridge rejected export",
        "MARK_EXPORT_FAILED": "external bridge export failed",
        "CLEAR_EXPORT_STATE": "external bridge state cleared",
        "RETRY_EXPORT": "external bridge export retried",
        "REQUEUE_EXPORT": "external bridge export requeued",
    }.get(str(action or ""), "external bridge action recorded")


def _external_bridge_rank(state: str) -> int:
    return {
        "EXPORT_FAILED": 5,
        "EXPORT_REJECTED": 4,
        "EXPORT_READY": 3,
        "EXPORT_ACCEPTED": 2,
        "EXPORT_SKIPPED": 1,
    }.get(str(state or "EXPORT_READY"), 0)


def _intake_id(document_id: str, field_name: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    return f"INTAKE::{document_id}::{safe_field}"


def _intake_result_reason(action: str) -> str:
    return {
        "MARK_INTAKE_ACCEPTED": "intake accepted",
        "MARK_INTAKE_REJECTED": "intake rejected",
        "MARK_INTAKE_INVALID": "intake invalid",
        "CLEAR_INTAKE_STATE": "intake state cleared",
        "RETRY_INTAKE": "intake retried",
        "REQUEUE_INTAKE": "intake requeued",
    }.get(str(action or ""), "intake action recorded")


def _intake_rank(state: str) -> int:
    return {
        "INTAKE_INVALID": 5,
        "INTAKE_REJECTED": 4,
        "INTAKE_PENDING": 3,
        "INTAKE_ACCEPTED": 2,
        "INTAKE_SKIPPED": 1,
    }.get(str(state or "INTAKE_PENDING"), 0)


def _dropzone_handshake_id(document_id: str, field_name: str) -> str:
    safe_field = str(field_name or "").replace(".", "_")
    return f"HANDSHAKE::{document_id}::{safe_field}"


def _dropzone_result_reason(action: str) -> str:
    return {
        "STAGE_TO_DROPZONE": "staged to local drop-zone",
        "CHECK_FOR_RECEIPT": "checked drop-zone receipts",
        "MARK_RECEIPT_ACCEPTED": "receipt accepted",
        "MARK_RECEIPT_REJECTED": "receipt rejected",
        "MARK_RECEIPT_FAILED": "receipt failed",
        "CLEAR_HANDSHAKE_STATE": "handshake state cleared",
        "RESTAGE_TO_DROPZONE": "restaged to local drop-zone",
        "ARCHIVE_HANDSHAKE": "drop-zone payload archived",
    }.get(str(action or ""), "drop-zone action recorded")


def _dropzone_rank(state: str) -> int:
    return {
        "RECEIPT_FAILED": 6,
        "RECEIPT_MISSING": 5,
        "RECEIPT_REJECTED": 4,
        "RECEIPT_PENDING": 3,
        "DROPZONE_WRITTEN": 2,
        "DROPZONE_STAGED": 1,
        "RECEIPT_ACCEPTED": 1,
    }.get(str(state or "DROPZONE_STAGED"), 0)


def _dropzone_dirs(root: Path) -> tuple[Path, Path, Path]:
    base = root / "exports" / "dropzone"
    outgoing = base / "outgoing"
    receipts = base / "receipts"
    archive = base / "archive"
    outgoing.mkdir(parents=True, exist_ok=True)
    receipts.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    return outgoing, receipts, archive


def _reconcile_receipt_history(*, handshake_payload: Dict[str, Any], receipt_history: List[Dict[str, Any]], now: str) -> Dict[str, Any]:
    normalized_history = [dict(item or {}) for item in receipt_history if dict(item or {})]
    state_counts: Dict[str, int] = {}
    filename_counts: Dict[str, int] = {}
    for payload in normalized_history:
        state = str(payload.get("receipt_state") or "")
        filename = str(payload.get("receipt_filename") or "")
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
        if filename:
            filename_counts[filename] = filename_counts.get(filename, 0) + 1
    latest_effective = dict(normalized_history[-1] if normalized_history else {})
    unique_states = {state for state in state_counts if state}
    duplicate_detected = len(normalized_history) > 1 or any(count > 1 for count in filename_counts.values()) or len(normalized_history) > len(filename_counts)
    conflicting_receipts = len(unique_states) > 1

    stale_state, recovery_reasons, restage_recommended = _derive_handshake_recovery(
        handshake_payload=handshake_payload,
        latest_receipt=latest_effective,
        receipt_count=len(normalized_history),
        conflicting_receipts=conflicting_receipts,
        duplicate_detected=duplicate_detected,
        now=now,
    )
    reconciliation = asdict(
        ReceiptReconciliationPacket(
            handshake_id=str(handshake_payload.get("handshake_id") or ""),
            export_id=str(handshake_payload.get("export_id") or ""),
            latest_receipt_state=str(latest_effective.get("receipt_state") or "RECEIPT_PENDING"),
            receipt_count=len(normalized_history),
            duplicate_detected=duplicate_detected,
            conflicting_receipts=conflicting_receipts,
            duplicate_receipt_count=max(sum(count - 1 for count in filename_counts.values() if count > 1), 0),
            latest_receipt_filename=str(latest_effective.get("receipt_filename") or ""),
            recovery_state=stale_state,
            recovery_reason=recovery_reasons,
            restage_recommended=restage_recommended,
            reconciled_at=now,
        )
    )
    recovery = asdict(
        HandshakeRecoveryPacket(
            handshake_id=str(handshake_payload.get("handshake_id") or ""),
            export_id=str(handshake_payload.get("export_id") or ""),
            recovery_state=stale_state,
            recovery_reason=recovery_reasons,
            restage_recommended=restage_recommended,
            stale_detected=stale_state in {"HANDSHAKE_STALE", "HANDSHAKE_RECOVERY_NEEDED", "HANDSHAKE_RESTAGE_RECOMMENDED"},
            receipt_count=len(normalized_history),
            marked_at=now,
        )
    )
    return {
        "latest_effective_receipt": latest_effective,
        "reconciliation": reconciliation,
        "recovery": recovery,
    }


def _derive_handshake_recovery(*, handshake_payload: Dict[str, Any], latest_receipt: Dict[str, Any], receipt_count: int, conflicting_receipts: bool, duplicate_detected: bool, now: str) -> tuple[str, List[str], bool]:
    reasons: List[str] = []
    handshake_state = str(handshake_payload.get("handshake_state") or "DROPZONE_STAGED")
    latest_receipt_state = str(latest_receipt.get("receipt_state") or "")
    last_seen = str(latest_receipt.get("received_at") or handshake_payload.get("last_checked_at") or handshake_payload.get("staged_at") or "")
    age_hours = _age_hours(last_seen, _parse_iso(now) or datetime.now(timezone.utc))
    restage_count = int(handshake_payload.get("restage_count") or 0)

    if conflicting_receipts:
        reasons.append("conflicting repeated receipts detected")
    if duplicate_detected:
        reasons.append("duplicate receipt detected")
    if handshake_state in {"DROPZONE_WRITTEN", "DROPZONE_STAGED"} and not latest_receipt_state and age_hours >= HANDSHAKE_RECOVERY_DEFAULTS["stale_written_hours"]:
        reasons.append("drop-zone payload stale without receipt")
        return "HANDSHAKE_STALE", reasons, False
    if latest_receipt_state in {"RECEIPT_PENDING", "RECEIPT_MISSING"} and age_hours >= HANDSHAKE_RECOVERY_DEFAULTS["stale_pending_hours"]:
        reasons.append("receipt pending beyond threshold")
        state = "HANDSHAKE_RESTAGE_RECOMMENDED" if restage_count < HANDSHAKE_RECOVERY_DEFAULTS["restage_count_recovery"] else "HANDSHAKE_RECOVERY_NEEDED"
        if state == "HANDSHAKE_RECOVERY_NEEDED":
            reasons.append("restage threshold exhausted")
        return state, reasons, state == "HANDSHAKE_RESTAGE_RECOMMENDED"
    if conflicting_receipts:
        return "HANDSHAKE_RECOVERY_NEEDED", reasons, False
    return "HANDSHAKE_NORMAL", reasons or ["handshake within normal bounds"], False


def _build_dropzone_handshake_payload(*, export_payload: Dict[str, Any], intake_payload: Dict[str, Any], existing_payload: Dict[str, Any], root: Path, staged_at: str) -> Dict[str, Any]:
    outgoing_dir, _, archive_dir = _dropzone_dirs(root)
    handshake_id = str(existing_payload.get("handshake_id") or _dropzone_handshake_id(str(export_payload.get("document_id") or ""), str(export_payload.get("field_name") or "")))
    payload_filename = str(existing_payload.get("payload_filename") or f"{handshake_id.replace(':', '_')}.json")
    payload_path = outgoing_dir / payload_filename
    payload = asdict(
        DropZoneHandshakePacket(
            handshake_id=handshake_id,
            export_id=str(existing_payload.get("export_id") or export_payload.get("export_id") or ""),
            intake_id=str(existing_payload.get("intake_id") or intake_payload.get("intake_id") or ""),
            target_hint=str(existing_payload.get("target_hint") or export_payload.get("target_hint") or "COUPLER_DROP"),
            dropzone_path=str(existing_payload.get("dropzone_path") or payload_path),
            payload_filename=payload_filename,
            handshake_state=str(existing_payload.get("handshake_state") or "DROPZONE_STAGED"),
            staged_at=str(existing_payload.get("staged_at") or staged_at),
            last_checked_at=str(existing_payload.get("last_checked_at") or ""),
            archive_path=str(existing_payload.get("archive_path") or (archive_dir / payload_filename)),
        )
    )
    payload["restage_count"] = int(existing_payload.get("restage_count") or 0)
    return payload


def _write_dropzone_handshake(root: Path, handshake_payload: Dict[str, Any], export_payload: Dict[str, Any], intake_payload: Dict[str, Any]) -> Path:
    outgoing_dir, _, _ = _dropzone_dirs(root)
    payload_filename = str(handshake_payload.get("payload_filename") or f"{str(handshake_payload.get('handshake_id') or 'handshake').replace(':', '_')}.json")
    output_path = outgoing_dir / payload_filename
    payload = {
        "handshake_packet": handshake_payload,
        "export_packet": export_payload,
        "intake_packet": intake_payload,
        "written_at": utc_now_iso(),
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def _load_dropzone_receipts(root: Path, handshake_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    _, receipts_dir, archive_dir = _dropzone_dirs(root)
    handshake_id = str(handshake_payload.get("handshake_id") or "")
    export_id = str(handshake_payload.get("export_id") or "")
    if not handshake_id and not export_id:
        return []
    matched: List[Dict[str, Any]] = []
    for receipt_file in sorted(receipts_dir.glob("*.json")):
        try:
            payload = json.loads(receipt_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payload_handshake_id = str(payload.get("handshake_id") or "")
        payload_export_id = str(payload.get("export_id") or "")
        if payload_handshake_id not in {"", handshake_id} and payload_export_id not in {"", export_id}:
            continue
        original_path = str(receipt_file)
        archived_path = archive_dir / receipt_file.name
        try:
            shutil.move(str(receipt_file), str(archived_path))
        except OSError:
            archived_path = receipt_file
        matched.append(asdict(
            DropZoneReceiptPacket(
                handshake_id=payload_handshake_id or handshake_id,
                export_id=payload_export_id or export_id,
                receipt_state=str(payload.get("receipt_state") or "RECEIPT_ACCEPTED"),
                receipt_reason=str(payload.get("receipt_reason") or "receipt file processed"),
                receipt_filename=receipt_file.name,
                received_at=str(payload.get("received_at") or utc_now_iso()),
                receiver_name=str(payload.get("receiver_name") or "EXTERNAL_COUPLER"),
                receiver_status=str(payload.get("receiver_status") or "ACTIVE"),
                receipt_path=original_path,
                archived_path=str(archived_path),
            )
        ))
    return matched


def _archive_dropzone_outgoing(root: Path, handshake_payload: Dict[str, Any]) -> Path | None:
    outgoing_dir, _, archive_dir = _dropzone_dirs(root)
    payload_filename = str(handshake_payload.get("payload_filename") or "")
    if not payload_filename:
        return None
    source_path = outgoing_dir / payload_filename
    target_path = archive_dir / payload_filename
    if not source_path.exists():
        return target_path if target_path.exists() else None
    try:
        shutil.move(str(source_path), str(target_path))
    except OSError:
        return None
    return target_path


def _write_external_bridge_export(root: Path, export_packet: Dict[str, Any], *, target_hint: str) -> Path:
    export_dir = root / "exports" / "control_room"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_id = str(export_packet.get("export_id") or "export")
    safe_export_id = export_id.replace(":", "_")
    export_path = export_dir / f"{safe_export_id}.json"
    payload = {
        "target_hint": target_hint,
        "export_packet": export_packet,
        "written_at": utc_now_iso(),
    }
    export_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return export_path


def _derive_alert_trigger(
    *,
    field_name: str,
    queue_item: Dict[str, Any],
    escalation: Dict[str, Any],
    routing: Dict[str, Any],
    sla: Dict[str, Any],
    reminder: Dict[str, Any],
    latest_transport: Dict[str, Any],
    override_count: int,
) -> Dict[str, Any]:
    reasons: List[str] = []
    source_type = "CONTROL_ROOM_ALERT"
    severity = "LOW"
    message = ""

    current_status = str(queue_item.get("current_status") or "")
    attention_state = str(queue_item.get("attention_state") or "CLEAR")
    escalation_level = str(escalation.get("escalation_level") or "NONE")
    routing_bucket = str(routing.get("routing_bucket") or "CLEAR_NO_ROUTING")
    owner_hint = str(routing.get("owner_hint") or "OPERATOR")
    sla_state = str(sla.get("sla_state") or "NORMAL")
    reminder_state = str(reminder.get("reminder_state") or "CLEARED")
    transport_state = str(latest_transport.get("result_state") or "")

    if transport_state == "HANDOFF_FAILED":
        severity = "HIGH"
        source_type = "TRANSPORT_HANDOFF_FAILED"
        message = f"Transport handoff failed for {field_name}"
        reasons.append("notification handoff failed")
    elif sla_state == "BREACH":
        severity = "CRITICAL"
        source_type = "SLA_BREACH"
        message = f"SLA breach on {field_name}"
        reasons.extend(list(sla.get("watch_trigger_reason", [])) or ["breach watch item"])
    elif field_name == "passport.number" and current_status == "UNRESOLVED":
        severity = "CRITICAL"
        source_type = "CRITICAL_UNRESOLVED_FIELD"
        message = "Critical unresolved passport field"
        reasons.append("passport.number unresolved")
    elif escalation_level in {"CRITICAL", "HIGH"} and routing_bucket not in {"", "CLEAR_NO_ROUTING"} and owner_hint in {"", "OPERATOR"}:
        severity = "HIGH" if escalation_level == "HIGH" else "CRITICAL"
        source_type = "ESCALATED_UNASSIGNED"
        message = f"Escalated item still needs assignment for {field_name}"
        reasons.append("escalated unassigned item")
    elif override_count >= 2:
        severity = "MEDIUM"
        source_type = "REPEATED_OVERRIDE_PATTERN"
        message = f"Repeated overrides detected for {field_name}"
        reasons.append("repeated operator overrides")
    elif reminder_state == "READY":
        severity = "MEDIUM"
        source_type = "REMINDER_OVERDUE"
        message = f"Reminder-ready item waiting on {field_name}"
        reasons.extend(list(reminder.get("staged_reason", [])) or ["reminder due"])
    elif attention_state == "UNRESOLVED":
        severity = "MEDIUM"
        source_type = "UNRESOLVED_FIELD"
        message = f"Unresolved field requires operator attention: {field_name}"
        reasons.append("field unresolved")
    else:
        return {}

    context = {
        "trigger_key": f"{source_type}:{severity}:{sla_state}:{transport_state}:{reminder_state}:{attention_state}:{escalation_level}:{override_count}",
        "current_status": current_status,
        "attention_state": attention_state,
        "escalation_level": escalation_level,
        "routing_bucket": routing_bucket,
        "sla_state": sla_state,
        "reminder_state": reminder_state,
        "transport_state": transport_state,
        "override_count": override_count,
    }
    return {
        "severity": severity,
        "message": message,
        "source_type": source_type,
        "source_context_summary": context,
        "alert_reason": reasons,
        "trigger_key": context["trigger_key"],
    }
