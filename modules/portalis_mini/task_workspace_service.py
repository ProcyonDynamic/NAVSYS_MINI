from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now_iso


TASK_TYPES: Dict[str, Dict[str, Any]] = {
    "ARRIVAL": {
        "label": "Arrival",
        "objective": "Prepare and validate an arrival package.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Load vessel and voyage context", True),
            ("INTAKE", "Open required arrival documents", True),
            ("VALIDATE", "Validate critical arrival fields", True),
            ("REVIEW", "Review discrepancies and notes", True),
            ("EXPORT", "Prepare export package", False),
        ],
    },
    "DEPARTURE": {
        "label": "Departure",
        "objective": "Prepare departure-facing document outputs.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open departure documents", True),
            ("VALIDATE", "Validate departure data", True),
            ("EXPORT", "Prepare departure packet", True),
        ],
    },
    "CREW_CHANGE": {
        "label": "Crew Change",
        "objective": "Track crew document deltas and approvals.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Load crew list and deltas", True),
            ("VALIDATE", "Validate crew identity docs", True),
            ("REVIEW", "Resolve crew discrepancies", True),
        ],
    },
    "INSPECTION": {
        "label": "Inspection / SIRE",
        "objective": "Organize inspection evidence and review state.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open inspection evidence", True),
            ("REVIEW", "Capture findings and notes", True),
            ("EXPORT", "Prepare inspection output", False),
        ],
    },
    "CERTIFICATE_RENEWAL": {
        "label": "Certificate Renewal",
        "objective": "Track certificate renewal package readiness.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open certificate set", True),
            ("VALIDATE", "Validate expiry and authority", True),
            ("REVIEW", "Review renewal blockers", True),
        ],
    },
    "PORT_PACKAGE": {
        "label": "Port Package",
        "objective": "Prepare a port-facing package of documents and context.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open package documents", True),
            ("VALIDATE", "Validate package completeness", True),
            ("EXPORT", "Prepare package output", True),
        ],
    },
    "CUSTOMS_IMMIGRATION": {
        "label": "Customs / Immigration",
        "objective": "Prepare customs and immigration records for submission.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open customs documents", True),
            ("VALIDATE", "Validate immigration records", True),
            ("REVIEW", "Review border-related issues", True),
        ],
    },
    "FORM_RECONSTRUCTION": {
        "label": "Form Reconstruction",
        "objective": "Rebuild a document structure in Studio.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open source form", True),
            ("VALIDATE", "Mark anchor and cell structure", True),
            ("REVIEW", "Review reconstruction fidelity", True),
        ],
    },
    "VALIDATION_LAB": {
        "label": "Validation Lab",
        "objective": "Run validation-focused review and correction work.",
        "stages": ["INTAKE", "VALIDATE", "REVIEW", "EXPORT", "COMPLETE"],
        "checklist": [
            ("INTAKE", "Open validation targets", True),
            ("VALIDATE", "Run validation pass", True),
            ("REVIEW", "Review unresolved conflicts", True),
        ],
    },
}


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "task"


@dataclass(slots=True)
class TaskChecklistItemPacket:
    item_id: str
    label: str
    status: str = "TODO"
    required: bool = True
    note: str = ""
    group: str = "GENERAL"
    updated_at: str = ""


@dataclass(slots=True)
class TaskHistoryEntryPacket:
    entry_id: str
    timestamp: str
    kind: str
    message: str
    source: str
    related_item_id: str = ""


@dataclass(slots=True)
class TaskWorkspacePacket:
    task_workspace_id: str
    workspace_id: str
    name: str
    task_type: str
    objective: str
    workflow_stage: str
    stage_order: List[str] = field(default_factory=list)
    progress_percent: int = 0
    required_documents: List[str] = field(default_factory=list)
    pending_items: List[str] = field(default_factory=list)
    checklist: List[Dict[str, Any]] = field(default_factory=list)
    validation_state: str = "PENDING"
    export_goal: str = ""
    completion_status: str = "IN_PROGRESS"
    resume_target: Dict[str, Any] = field(default_factory=dict)
    history_log: List[Dict[str, Any]] = field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""


class TaskWorkspaceService:
    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.task_dir = self.root / "task_workspaces"
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.task_dir / "task_store.json"

    def list_task_workspaces(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        tasks = list(store["tasks"].values())
        return sorted(tasks, key=lambda item: (item.get("updated_at") or "", item.get("name") or ""), reverse=True)

    def create_task_workspace(
        self,
        *,
        workspace_id: str,
        name: str,
        task_type: str,
        resume_target: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        task_type = str(task_type or "ARRIVAL").strip().upper()
        definition = TASK_TYPES.get(task_type, TASK_TYPES["ARRIVAL"])
        now = utc_now_iso()
        task_workspace_id = f"task_{task_type.lower()}_{_slugify(name)}"
        counter = 1
        store = self._load_store()
        while task_workspace_id in store["tasks"]:
            counter += 1
            task_workspace_id = f"task_{task_type.lower()}_{_slugify(name)}_{counter}"
        checklist = [
            asdict(
                TaskChecklistItemPacket(
                    item_id=f"{task_workspace_id}::item::{index + 1}",
                    label=label,
                    required=required,
                    group=group,
                    updated_at=now,
                )
            )
            for index, (group, label, required) in enumerate(definition["checklist"])
        ]
        task = asdict(
            TaskWorkspacePacket(
                task_workspace_id=task_workspace_id,
                workspace_id=str(workspace_id or ""),
                name=str(name or definition["label"]),
                task_type=task_type,
                objective=definition["objective"],
                workflow_stage=definition["stages"][0],
                stage_order=list(definition["stages"]),
                checklist=checklist,
                resume_target=dict(resume_target or {}),
                history_log=[
                    asdict(
                        TaskHistoryEntryPacket(
                            entry_id=f"{task_workspace_id}::history::1",
                            timestamp=now,
                            kind="TASK_WORKSPACE_CREATED",
                            message=f"Task workspace created for {definition['label']}.",
                            source="TASK_SERVICE",
                        )
                    )
                ],
                started_at=now,
                updated_at=now,
            )
        )
        task = self._recalculate_task(task)
        store["tasks"][task_workspace_id] = task
        store["last_active_task_id"] = task_workspace_id
        self._save_store(store)
        return copy.deepcopy(task)

    def load_task_workspace(self, task_workspace_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(dict(store["tasks"].get(str(task_workspace_id or "").strip(), {}) or {}))

    def save_task_workspace(self, task_workspace: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        task_workspace = self._recalculate_task(copy.deepcopy(task_workspace))
        task_workspace["updated_at"] = utc_now_iso()
        store["tasks"][task_workspace["task_workspace_id"]] = task_workspace
        store["last_active_task_id"] = task_workspace["task_workspace_id"]
        self._save_store(store)
        return copy.deepcopy(task_workspace)

    def start_task_workspace(self, task_workspace_id: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task = self._append_history(task, "TASK_WORKSPACE_STARTED", "Task workspace started.", related_item_id="")
        return self.save_task_workspace(task)

    def resume_task_workspace(self, task_workspace_id: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task = self._append_history(task, "TASK_WORKSPACE_RESUMED", "Task workspace resumed.", related_item_id="")
        store = self._load_store()
        store["last_active_task_id"] = task_workspace_id
        self._save_store(store)
        return self.save_task_workspace(task)

    def rename_task_workspace(self, *, task_workspace_id: str, new_name: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task["name"] = str(new_name or task.get("name") or task_workspace_id)
        task = self._append_history(task, "TASK_WORKSPACE_RENAMED", f"Task renamed to {task['name']}.", related_item_id="")
        return self.save_task_workspace(task)

    def duplicate_task_workspace(self, *, task_workspace_id: str, new_name: str = "") -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        duplicated = self.create_task_workspace(
            workspace_id=str(task.get("workspace_id") or ""),
            name=str(new_name or f"{task.get('name') or task_workspace_id} Copy"),
            task_type=str(task.get("task_type") or "ARRIVAL"),
            resume_target=dict(task.get("resume_target", {})),
        )
        duplicated["checklist"] = copy.deepcopy(task.get("checklist", []))
        duplicated["history_log"] = copy.deepcopy(task.get("history_log", []))
        duplicated = self._append_history(duplicated, "TASK_WORKSPACE_DUPLICATED", "Task duplicated from an existing task workspace.", related_item_id=task_workspace_id)
        return self.save_task_workspace(duplicated)

    def delete_task_workspace(self, task_workspace_id: str) -> Dict[str, Any]:
        store = self._load_store()
        removed = dict(store["tasks"].pop(str(task_workspace_id or "").strip(), {}) or {})
        if store.get("last_active_task_id") == task_workspace_id:
            store["last_active_task_id"] = ""
        self._save_store(store)
        return copy.deepcopy(removed)

    def update_checklist_item(
        self,
        *,
        task_workspace_id: str,
        item_id: str,
        status: str,
        note: str = "",
    ) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        status = str(status or "TODO").strip().upper()
        for item in task.get("checklist", []):
            if item.get("item_id") == item_id:
                item["status"] = status
                item["note"] = note
                item["updated_at"] = utc_now_iso()
                task = self._append_history(task, "TASK_CHECKLIST_ITEM_UPDATED", f"Checklist item updated to {status}.", related_item_id=item_id)
                break
        return self.save_task_workspace(task)

    def change_task_stage(self, *, task_workspace_id: str, stage: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        stage = str(stage or task.get("workflow_stage") or "INTAKE").strip().upper()
        task["workflow_stage"] = stage
        task = self._append_history(task, "TASK_STAGE_CHANGED", f"Task stage changed to {stage}.", related_item_id=stage)
        return self.save_task_workspace(task)

    def append_task_history(
        self,
        *,
        task_workspace_id: str,
        kind: str,
        message: str,
        source: str = "TASK_SERVICE",
        related_item_id: str = "",
    ) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task = self._append_history(task, kind, message, related_item_id=related_item_id, source=source)
        return self.save_task_workspace(task)

    def mark_task_complete(self, task_workspace_id: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task["workflow_stage"] = "COMPLETE"
        task["completion_status"] = "COMPLETE"
        task = self._append_history(task, "TASK_MARKED_COMPLETE", "Task marked complete.", related_item_id="")
        return self.save_task_workspace(task)

    def save_task_checkpoint(self, *, task_workspace_id: str, note: str) -> Dict[str, Any]:
        task = self.load_task_workspace(task_workspace_id)
        if not task:
            return {}
        task = self._append_history(task, "TASK_CHECKPOINT_SAVED", note or "Checkpoint saved.", related_item_id="")
        return self.save_task_workspace(task)

    def get_last_active_task_workspace(self) -> Dict[str, Any]:
        store = self._load_store()
        task_workspace_id = str(store.get("last_active_task_id") or "")
        if not task_workspace_id:
            return {}
        return self.load_task_workspace(task_workspace_id)

    def _append_history(
        self,
        task: Dict[str, Any],
        kind: str,
        message: str,
        *,
        related_item_id: str,
        source: str = "TASK_SERVICE",
    ) -> Dict[str, Any]:
        history = list(task.get("history_log", []) or [])
        history.append(
            asdict(
                TaskHistoryEntryPacket(
                    entry_id=f"{task.get('task_workspace_id')}::history::{len(history) + 1}",
                    timestamp=utc_now_iso(),
                    kind=kind,
                    message=message,
                    source=source,
                    related_item_id=related_item_id,
                )
            )
        )
        task["history_log"] = history
        return task

    def _recalculate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        checklist = list(task.get("checklist", []) or [])
        required_items = [item for item in checklist if item.get("required", True)]
        weighted_total = len(required_items) * 2 + max(0, len(checklist) - len(required_items))
        done_score = 0
        pending_items: List[str] = []
        for item in checklist:
            weight = 2 if item.get("required", True) else 1
            status = str(item.get("status") or "TODO").upper()
            if status == "DONE":
                done_score += weight
            if item.get("required", True) and status != "DONE":
                pending_items.append(str(item.get("label") or item.get("item_id") or ""))
        progress = int(round((done_score / weighted_total) * 100)) if weighted_total else 0
        task["progress_percent"] = progress
        task["pending_items"] = pending_items
        task["validation_state"] = "READY" if not pending_items else "PENDING"
        if str(task.get("workflow_stage") or "").upper() == "COMPLETE" or str(task.get("completion_status") or "").upper() == "COMPLETE":
            task["completion_status"] = "COMPLETE"
        else:
            task["completion_status"] = "COMPLETE" if not pending_items and checklist else "IN_PROGRESS"
        task["updated_at"] = utc_now_iso()
        return task

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {"tasks": {}, "last_active_task_id": ""}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"tasks": {}, "last_active_task_id": ""}

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
