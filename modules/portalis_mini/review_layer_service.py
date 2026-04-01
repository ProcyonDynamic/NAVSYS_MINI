from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now_iso


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "review"


@dataclass(slots=True)
class ReviewItemPacket:
    review_item_id: str
    kind: str
    status: str
    severity: str
    document_id: str
    document_tab_id: str = ""
    pane_id: str = "LEFT"
    target_object_id: str = ""
    target_region: Dict[str, Any] = field(default_factory=dict)
    title: str = ""
    body: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "operator"
    resolved_at: str = ""
    resolved_by: str = ""
    review_session_id: str = ""


@dataclass(slots=True)
class AnnotationPacket:
    annotation_id: str
    document_id: str
    pane_id: str = "LEFT"
    target_object_id: str = ""
    target_region: Dict[str, Any] = field(default_factory=dict)
    annotation_type: str = "NOTE_MARKER"
    content: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    review_session_id: str = ""


@dataclass(slots=True)
class CommentPacket:
    comment_id: str
    review_item_id: str
    document_id: str
    target_object_id: str = ""
    body: str = ""
    created_at: str = ""
    created_by: str = "operator"
    edited_at: str = ""


@dataclass(slots=True)
class ApprovalActionPacket:
    approval_action_id: str
    target_type: str
    target_id: str
    action: str
    note: str = ""
    timestamp: str = ""
    actor: str = "operator"


@dataclass(slots=True)
class AuditTrailEntryPacket:
    entry_id: str
    timestamp: str
    kind: str
    message: str
    source: str
    related_review_item_id: str = ""
    related_document_id: str = ""
    related_task_workspace_id: str = ""
    related_review_session_id: str = ""


@dataclass(slots=True)
class ReviewSessionPacket:
    review_session_id: str
    scope_type: str
    scope_id: str
    status: str = "ACTIVE"
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    signed_off: bool = False
    signed_off_at: str = ""
    updated_at: str = ""
    task_workspace_id: str = ""


class ReviewLayerService:
    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.review_dir = self.root / "review_layer"
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.review_dir / "review_store.json"

    def get_or_create_review_session(
        self,
        *,
        scope_type: str,
        scope_id: str,
        task_workspace_id: str = "",
    ) -> Dict[str, Any]:
        scope_type = str(scope_type or "DOCUMENT").strip().upper()
        scope_id = str(scope_id or "GLOBAL").strip() or "GLOBAL"
        store = self._load_store()
        session = next(
            (
                item
                for item in store["review_sessions"].values()
                if item.get("scope_type") == scope_type and item.get("scope_id") == scope_id
            ),
            {},
        )
        if session:
            return copy.deepcopy(session)
        now = utc_now_iso()
        review_session_id = f"review_session_{scope_type.lower()}_{_slugify(scope_id)}"
        counter = 1
        while review_session_id in store["review_sessions"]:
            counter += 1
            review_session_id = f"review_session_{scope_type.lower()}_{_slugify(scope_id)}_{counter}"
        session = asdict(
            ReviewSessionPacket(
                review_session_id=review_session_id,
                scope_type=scope_type,
                scope_id=scope_id,
                updated_at=now,
                task_workspace_id=str(task_workspace_id or ""),
            )
        )
        store["review_sessions"][review_session_id] = session
        self._save_store(store)
        self.append_audit_entry(
            kind="REVIEW_SESSION_CREATED",
            message=f"Review session created for {scope_type}:{scope_id}.",
            source="REVIEW_LAYER",
            related_review_session_id=review_session_id,
            related_task_workspace_id=task_workspace_id,
        )
        return copy.deepcopy(session)

    def load_review_session(self, review_session_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store["review_sessions"].get(str(review_session_id or "").strip(), {}))

    def list_review_items(
        self,
        *,
        review_session_id: str = "",
        document_id: str = "",
        status_filter: str = "",
    ) -> List[Dict[str, Any]]:
        store = self._load_store()
        items = list(store["review_items"].values())
        if review_session_id:
            items = [item for item in items if item.get("review_session_id") == review_session_id]
        if document_id:
            items = [item for item in items if item.get("document_id") == document_id]
        status_filter = str(status_filter or "").strip().upper()
        if status_filter in {"OPEN", "IN_REVIEW", "RESOLVED", "REJECTED", "APPROVED"}:
            items = [item for item in items if str(item.get("status") or "").upper() == status_filter]
        return sorted(items, key=lambda item: (item.get("updated_at") or "", item.get("created_at") or ""), reverse=True)

    def get_review_item(self, review_item_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store["review_items"].get(str(review_item_id or "").strip(), {}))

    def create_review_item(
        self,
        *,
        review_session_id: str,
        document_id: str,
        document_tab_id: str = "",
        pane_id: str = "LEFT",
        target_object_id: str = "",
        target_region: Dict[str, Any] | None = None,
        kind: str = "ISSUE",
        severity: str = "MEDIUM",
        title: str = "",
        body: str = "",
        tags: List[str] | None = None,
        created_by: str = "operator",
        task_workspace_id: str = "",
    ) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        review_item_id = f"review_item_{_slugify(document_id)}_{len(store['review_items']) + 1}"
        while review_item_id in store["review_items"]:
            review_item_id = f"{review_item_id}_x"
        packet = asdict(
            ReviewItemPacket(
                review_item_id=review_item_id,
                kind=str(kind or "ISSUE").strip().upper(),
                status="OPEN",
                severity=str(severity or "MEDIUM").strip().upper(),
                document_id=str(document_id or ""),
                document_tab_id=str(document_tab_id or document_id or ""),
                pane_id=str(pane_id or "LEFT").strip().upper(),
                target_object_id=str(target_object_id or ""),
                target_region=dict(target_region or {}),
                title=str(title or "Review item"),
                body=str(body or ""),
                tags=list(tags or []),
                created_at=now,
                updated_at=now,
                created_by=str(created_by or "operator"),
                review_session_id=str(review_session_id or ""),
            )
        )
        store["review_items"][review_item_id] = packet
        self._save_store(store)
        self._refresh_review_session(review_session_id)
        self.append_audit_entry(
            kind="REVIEW_ITEM_CREATED",
            message=f"Review item created: {packet['title']}.",
            source="REVIEW_LAYER",
            related_review_item_id=review_item_id,
            related_document_id=document_id,
            related_task_workspace_id=task_workspace_id,
            related_review_session_id=review_session_id,
        )
        return self.get_review_item(review_item_id)

    def update_review_item_status(
        self,
        *,
        review_item_id: str,
        status: str,
        actor: str = "operator",
        note: str = "",
    ) -> Dict[str, Any]:
        store = self._load_store()
        item = store["review_items"].get(str(review_item_id or "").strip(), {})
        if not item:
            return {}
        now = utc_now_iso()
        item["status"] = str(status or item.get("status") or "OPEN").strip().upper()
        item["updated_at"] = now
        if item["status"] in {"RESOLVED", "APPROVED", "REJECTED"}:
            item["resolved_at"] = now
            item["resolved_by"] = str(actor or "operator")
        else:
            item["resolved_at"] = ""
            item["resolved_by"] = ""
        store["review_items"][review_item_id] = item
        self._save_store(store)
        self._record_approval_action(
            target_type="REVIEW_ITEM",
            target_id=review_item_id,
            action=item["status"],
            note=note,
            actor=actor,
        )
        self._refresh_review_session(str(item.get("review_session_id") or ""))
        self.append_audit_entry(
            kind=f"REVIEW_ITEM_{item['status']}",
            message=f"Review item {review_item_id} set to {item['status']}.",
            source="REVIEW_LAYER",
            related_review_item_id=review_item_id,
            related_document_id=str(item.get("document_id") or ""),
            related_review_session_id=str(item.get("review_session_id") or ""),
        )
        return copy.deepcopy(item)

    def resolve_review_item(self, review_item_id: str, *, actor: str = "operator", note: str = "") -> Dict[str, Any]:
        return self.update_review_item_status(review_item_id=review_item_id, status="RESOLVED", actor=actor, note=note)

    def reopen_review_item(self, review_item_id: str, *, actor: str = "operator", note: str = "") -> Dict[str, Any]:
        return self.update_review_item_status(review_item_id=review_item_id, status="OPEN", actor=actor, note=note)

    def approve_review_item(self, review_item_id: str, *, actor: str = "operator", note: str = "") -> Dict[str, Any]:
        return self.update_review_item_status(review_item_id=review_item_id, status="APPROVED", actor=actor, note=note)

    def reject_review_item(self, review_item_id: str, *, actor: str = "operator", note: str = "") -> Dict[str, Any]:
        return self.update_review_item_status(review_item_id=review_item_id, status="REJECTED", actor=actor, note=note)

    def add_comment(
        self,
        *,
        review_item_id: str,
        document_id: str,
        target_object_id: str = "",
        body: str,
        created_by: str = "operator",
    ) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        comment_id = f"comment_{_slugify(review_item_id)}_{len(store['comments']) + 1}"
        while comment_id in store["comments"]:
            comment_id = f"{comment_id}_x"
        packet = asdict(
            CommentPacket(
                comment_id=comment_id,
                review_item_id=str(review_item_id or ""),
                document_id=str(document_id or ""),
                target_object_id=str(target_object_id or ""),
                body=str(body or ""),
                created_at=now,
                created_by=str(created_by or "operator"),
            )
        )
        store["comments"][comment_id] = packet
        self._save_store(store)
        self.append_audit_entry(
            kind="COMMENT_ADDED",
            message=f"Comment added to {review_item_id}.",
            source="REVIEW_LAYER",
            related_review_item_id=review_item_id,
            related_document_id=document_id,
        )
        return copy.deepcopy(packet)

    def list_comments(self, *, review_item_id: str = "") -> List[Dict[str, Any]]:
        store = self._load_store()
        comments = list(store["comments"].values())
        if review_item_id:
            comments = [item for item in comments if item.get("review_item_id") == review_item_id]
        return sorted(comments, key=lambda item: item.get("created_at") or "", reverse=True)

    def create_annotation(
        self,
        *,
        document_id: str,
        pane_id: str = "LEFT",
        target_object_id: str = "",
        target_region: Dict[str, Any] | None = None,
        annotation_type: str = "NOTE_MARKER",
        content: str = "",
        style: Dict[str, Any] | None = None,
        review_session_id: str = "",
    ) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        annotation_id = f"annotation_{_slugify(document_id)}_{len(store['annotations']) + 1}"
        while annotation_id in store["annotations"]:
            annotation_id = f"{annotation_id}_x"
        packet = asdict(
            AnnotationPacket(
                annotation_id=annotation_id,
                document_id=str(document_id or ""),
                pane_id=str(pane_id or "LEFT").strip().upper(),
                target_object_id=str(target_object_id or ""),
                target_region=dict(target_region or {}),
                annotation_type=str(annotation_type or "NOTE_MARKER").strip().upper(),
                content=str(content or ""),
                style=dict(style or {}),
                created_at=now,
                updated_at=now,
                review_session_id=str(review_session_id or ""),
            )
        )
        store["annotations"][annotation_id] = packet
        self._save_store(store)
        self.append_audit_entry(
            kind="ANNOTATION_CREATED",
            message=f"Annotation created on {document_id}.",
            source="REVIEW_LAYER",
            related_document_id=document_id,
            related_review_session_id=review_session_id,
        )
        return copy.deepcopy(packet)

    def delete_annotation(self, annotation_id: str) -> Dict[str, Any]:
        store = self._load_store()
        annotation = copy.deepcopy(store["annotations"].get(str(annotation_id or "").strip(), {}))
        if not annotation:
            return {}
        del store["annotations"][annotation_id]
        self._save_store(store)
        self.append_audit_entry(
            kind="ANNOTATION_DELETED",
            message=f"Annotation deleted: {annotation_id}.",
            source="REVIEW_LAYER",
            related_document_id=str(annotation.get("document_id") or ""),
            related_review_session_id=str(annotation.get("review_session_id") or ""),
        )
        return annotation

    def list_annotations(self, *, document_id: str = "", pane_id: str = "", review_session_id: str = "") -> List[Dict[str, Any]]:
        store = self._load_store()
        annotations = list(store["annotations"].values())
        if document_id:
            annotations = [item for item in annotations if item.get("document_id") == document_id]
        if pane_id:
            annotations = [item for item in annotations if item.get("pane_id") == pane_id]
        if review_session_id:
            annotations = [item for item in annotations if item.get("review_session_id") == review_session_id]
        return sorted(annotations, key=lambda item: item.get("updated_at") or "", reverse=True)

    def signoff_review_session(
        self,
        *,
        review_session_id: str,
        actor: str = "operator",
        note: str = "",
    ) -> Dict[str, Any]:
        store = self._load_store()
        session = store["review_sessions"].get(str(review_session_id or "").strip(), {})
        if not session:
            return {}
        now = utc_now_iso()
        session["signed_off"] = True
        session["signed_off_at"] = now
        session["status"] = "SIGNED_OFF"
        session["updated_at"] = now
        store["review_sessions"][review_session_id] = session
        self._save_store(store)
        self._record_approval_action(
            target_type="REVIEW_SESSION",
            target_id=review_session_id,
            action="SIGN_OFF",
            note=note,
            actor=actor,
        )
        self.append_audit_entry(
            kind="REVIEW_SESSION_SIGNED_OFF",
            message=f"Review session {review_session_id} signed off.",
            source="REVIEW_LAYER",
            related_review_session_id=review_session_id,
            related_task_workspace_id=str(session.get("task_workspace_id") or ""),
        )
        return copy.deepcopy(session)

    def list_audit_entries(
        self,
        *,
        review_session_id: str = "",
        document_id: str = "",
        related_review_item_id: str = "",
    ) -> List[Dict[str, Any]]:
        store = self._load_store()
        entries = list(store["audit_entries"].values())
        if review_session_id:
            entries = [entry for entry in entries if entry.get("related_review_session_id") == review_session_id]
        if document_id:
            entries = [entry for entry in entries if entry.get("related_document_id") == document_id]
        if related_review_item_id:
            entries = [entry for entry in entries if entry.get("related_review_item_id") == related_review_item_id]
        return sorted(entries, key=lambda entry: entry.get("timestamp") or "", reverse=True)

    def append_audit_entry(
        self,
        *,
        kind: str,
        message: str,
        source: str,
        related_review_item_id: str = "",
        related_document_id: str = "",
        related_task_workspace_id: str = "",
        related_review_session_id: str = "",
    ) -> Dict[str, Any]:
        store = self._load_store()
        entry_id = f"audit_{len(store['audit_entries']) + 1}"
        while entry_id in store["audit_entries"]:
            entry_id = f"{entry_id}_x"
        packet = asdict(
            AuditTrailEntryPacket(
                entry_id=entry_id,
                timestamp=utc_now_iso(),
                kind=str(kind or "AUDIT"),
                message=str(message or ""),
                source=str(source or "REVIEW_LAYER"),
                related_review_item_id=str(related_review_item_id or ""),
                related_document_id=str(related_document_id or ""),
                related_task_workspace_id=str(related_task_workspace_id or ""),
                related_review_session_id=str(related_review_session_id or ""),
            )
        )
        store["audit_entries"][entry_id] = packet
        self._save_store(store)
        return copy.deepcopy(packet)

    def _record_approval_action(
        self,
        *,
        target_type: str,
        target_id: str,
        action: str,
        note: str,
        actor: str,
    ) -> Dict[str, Any]:
        store = self._load_store()
        approval_action_id = f"approval_{len(store['approval_actions']) + 1}"
        while approval_action_id in store["approval_actions"]:
            approval_action_id = f"{approval_action_id}_x"
        packet = asdict(
            ApprovalActionPacket(
                approval_action_id=approval_action_id,
                target_type=str(target_type or ""),
                target_id=str(target_id or ""),
                action=str(action or ""),
                note=str(note or ""),
                timestamp=utc_now_iso(),
                actor=str(actor or "operator"),
            )
        )
        store["approval_actions"][approval_action_id] = packet
        self._save_store(store)
        return copy.deepcopy(packet)

    def _refresh_review_session(self, review_session_id: str) -> Dict[str, Any]:
        if not review_session_id:
            return {}
        store = self._load_store()
        session = store["review_sessions"].get(review_session_id, {})
        if not session:
            return {}
        items = [item for item in store["review_items"].values() if item.get("review_session_id") == review_session_id]
        pending = len([item for item in items if item.get("status") in {"OPEN", "IN_REVIEW"}])
        approved = len([item for item in items if item.get("status") == "APPROVED"])
        rejected = len([item for item in items if item.get("status") == "REJECTED"])
        session["pending_count"] = pending
        session["approved_count"] = approved
        session["rejected_count"] = rejected
        session["updated_at"] = utc_now_iso()
        if not session.get("signed_off"):
            session["status"] = "ACTIVE" if pending else "READY_FOR_SIGNOFF"
        store["review_sessions"][review_session_id] = session
        self._save_store(store)
        return copy.deepcopy(session)

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {
                "review_items": {},
                "annotations": {},
                "comments": {},
                "approval_actions": {},
                "audit_entries": {},
                "review_sessions": {},
            }
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {
                "review_items": {},
                "annotations": {},
                "comments": {},
                "approval_actions": {},
                "audit_entries": {},
                "review_sessions": {},
            }

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")
