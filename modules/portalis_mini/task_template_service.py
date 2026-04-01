from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now_iso
from .task_workspace_service import TASK_TYPES, TaskWorkspaceService


TEMPLATE_TYPES = [
    "STANDARD_WORKSPACE",
    "TASK_WORKSPACE",
    "OPERATIONAL_WORKFLOW",
    "STUDIO_RECONSTRUCTION",
]

DEFAULT_TEMPLATE_CATEGORIES = [
    "Arrival Package",
    "Departure Package",
    "Crew Change",
    "Inspection / SIRE",
    "Certificate Renewal",
    "Port Package",
    "Customs / Immigration",
    "Form Reconstruction",
    "Validation Lab",
]

DEFAULT_SLOT_DEFINITIONS: Dict[str, List[Dict[str, Any]]] = {
    "ARRIVAL": [
        {"slot_id": "CREW_LIST_SLOT", "label": "Crew List Slot", "required": True, "accepted_file_types": ["XLSX", "CSV", "PDF"], "binding_type": "DOCUMENT", "validation_rules": ["required"], "tce_relationship": "CREW_CONTEXT", "default_usage": "Primary crew manifest", "allow_multiple": False, "source_role": "CREW_SOURCE"},
        {"slot_id": "VOYAGE_SLOT", "label": "Voyage Slot", "required": True, "accepted_file_types": ["JSON", "XLSX", "PDF"], "binding_type": "CONTEXT", "validation_rules": ["required"], "tce_relationship": "VOYAGE_CONTEXT", "default_usage": "Voyage and ETA context", "allow_multiple": False, "source_role": "VOYAGE_SOURCE"},
        {"slot_id": "PORT_REQUIREMENTS_SLOT", "label": "Port Requirements Slot", "required": False, "accepted_file_types": ["PDF", "DOCX", "TXT"], "binding_type": "REFERENCE", "validation_rules": [], "tce_relationship": "PORT_RULES", "default_usage": "Port-specific requirements", "allow_multiple": True, "source_role": "PORT_REQUIREMENTS"},
    ],
    "DEPARTURE": [
        {"slot_id": "CREW_DELTA_SLOT", "label": "Crew Delta Slot", "required": True, "accepted_file_types": ["XLSX", "CSV", "PDF"], "binding_type": "DOCUMENT", "validation_rules": ["required"], "tce_relationship": "CREW_CONTEXT", "default_usage": "Crew changes for departure", "allow_multiple": False, "source_role": "CREW_DELTA"},
        {"slot_id": "EXPORT_SLOT", "label": "Export Slot", "required": False, "accepted_file_types": ["PDF", "DOCX"], "binding_type": "OUTPUT", "validation_rules": [], "tce_relationship": "EXPORT_CONTEXT", "default_usage": "Departure export package", "allow_multiple": True, "source_role": "EXPORT_TARGET"},
    ],
}


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "template"


@dataclass(slots=True)
class SlotDefinitionPacket:
    slot_id: str
    label: str
    required: bool = True
    accepted_file_types: List[str] = field(default_factory=list)
    binding_type: str = "DOCUMENT"
    validation_rules: List[str] = field(default_factory=list)
    tce_relationship: str = ""
    default_usage: str = ""
    allow_multiple: bool = False
    source_role: str = ""


@dataclass(slots=True)
class SlotAssignmentPacket:
    slot_id: str
    assigned_source_id: str = ""
    assigned_source_type: str = ""
    assignment_status: str = "UNASSIGNED"
    note: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class TaskTemplatePacket:
    template_id: str
    name: str
    category: str
    template_type: str
    task_type: str
    description: str = ""
    layout_profile: Dict[str, Any] = field(default_factory=dict)
    ui_mode: str = "STUDIO"
    slot_definitions: List[Dict[str, Any]] = field(default_factory=list)
    checklist_template: List[Dict[str, Any]] = field(default_factory=list)
    stage_template: List[str] = field(default_factory=list)
    required_documents_template: List[str] = field(default_factory=list)
    default_export_goal: str = ""
    default_context_bindings: Dict[str, Any] = field(default_factory=dict)
    save_live_values: bool = False
    favorite: bool = False
    archived: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class TemplateWizardStatePacket:
    wizard_id: str
    current_step: int = 1
    template_type: str = "TASK_WORKSPACE"
    draft_name: str = ""
    draft_category: str = ""
    draft_layout_profile: Dict[str, Any] = field(default_factory=dict)
    draft_ui_mode: str = "STUDIO"
    draft_slot_definitions: List[Dict[str, Any]] = field(default_factory=list)
    draft_checklist_template: List[Dict[str, Any]] = field(default_factory=list)
    draft_stage_template: List[str] = field(default_factory=list)
    draft_save_options: Dict[str, Any] = field(default_factory=dict)
    review_ready: bool = False
    updated_at: str = ""
    draft_task_type: str = "ARRIVAL"
    draft_description: str = ""


class TaskTemplateService:
    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.template_dir = self.root / "task_templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.template_dir / "template_store.json"

    def list_templates(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        templates = list(store["templates"].values())
        return sorted(templates, key=lambda item: (bool(item.get("favorite")), item.get("updated_at") or "", item.get("name") or ""), reverse=True)

    def load_template(self, template_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(dict(store["templates"].get(str(template_id or "").strip(), {}) or {}))

    def create_template(
        self,
        *,
        name: str,
        category: str,
        template_type: str,
        task_type: str,
        description: str = "",
        layout_profile: Dict[str, Any] | None = None,
        ui_mode: str = "STUDIO",
        slot_definitions: List[Dict[str, Any]] | None = None,
        checklist_template: List[Dict[str, Any]] | None = None,
        stage_template: List[str] | None = None,
        required_documents_template: List[str] | None = None,
        default_export_goal: str = "",
        default_context_bindings: Dict[str, Any] | None = None,
        save_live_values: bool = False,
    ) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        base_name = str(name or f"{task_type.title()} Template")
        template_id = f"template_{_slugify(base_name)}"
        counter = 1
        while template_id in store["templates"]:
            counter += 1
            template_id = f"template_{_slugify(base_name)}_{counter}"
        definition = TASK_TYPES.get(str(task_type or "ARRIVAL").upper(), TASK_TYPES["ARRIVAL"])
        template = asdict(
            TaskTemplatePacket(
                template_id=template_id,
                name=base_name,
                category=str(category or definition["label"]),
                template_type=str(template_type or "TASK_WORKSPACE").upper(),
                task_type=str(task_type or "ARRIVAL").upper(),
                description=str(description or ""),
                layout_profile=dict(layout_profile or {}),
                ui_mode=str(ui_mode or "STUDIO"),
                slot_definitions=list(slot_definitions or self.default_slots_for_task_type(str(task_type or "ARRIVAL").upper())),
                checklist_template=list(checklist_template or self.default_checklist_template(str(task_type or "ARRIVAL").upper())),
                stage_template=list(stage_template or definition["stages"]),
                required_documents_template=list(required_documents_template or []),
                default_export_goal=str(default_export_goal or ""),
                default_context_bindings=dict(default_context_bindings or {}),
                save_live_values=bool(save_live_values),
                favorite=False,
                archived=False,
                created_at=now,
                updated_at=now,
            )
        )
        store["templates"][template_id] = template
        store["last_active_template_id"] = template_id
        self._save_store(store)
        return copy.deepcopy(template)

    def save_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        template = copy.deepcopy(template)
        template["updated_at"] = utc_now_iso()
        store["templates"][template["template_id"]] = template
        store["last_active_template_id"] = template["template_id"]
        self._save_store(store)
        return copy.deepcopy(template)

    def rename_template(self, *, template_id: str, new_name: str) -> Dict[str, Any]:
        template = self.load_template(template_id)
        if not template:
            return {}
        template["name"] = str(new_name or template.get("name") or template_id)
        return self.save_template(template)

    def duplicate_template(self, *, template_id: str, new_name: str = "") -> Dict[str, Any]:
        template = self.load_template(template_id)
        if not template:
            return {}
        return self.create_template(
            name=str(new_name or f"{template.get('name') or template_id} Copy"),
            category=str(template.get("category") or ""),
            template_type=str(template.get("template_type") or "TASK_WORKSPACE"),
            task_type=str(template.get("task_type") or "ARRIVAL"),
            description=str(template.get("description") or ""),
            layout_profile=dict(template.get("layout_profile") or {}),
            ui_mode=str(template.get("ui_mode") or "STUDIO"),
            slot_definitions=list(template.get("slot_definitions") or []),
            checklist_template=list(template.get("checklist_template") or []),
            stage_template=list(template.get("stage_template") or []),
            required_documents_template=list(template.get("required_documents_template") or []),
            default_export_goal=str(template.get("default_export_goal") or ""),
            default_context_bindings=dict(template.get("default_context_bindings") or {}),
            save_live_values=bool(template.get("save_live_values", False)),
        )

    def archive_template(self, template_id: str) -> Dict[str, Any]:
        template = self.load_template(template_id)
        if not template:
            return {}
        template["archived"] = True
        return self.save_template(template)

    def delete_template(self, template_id: str) -> Dict[str, Any]:
        store = self._load_store()
        removed = dict(store["templates"].pop(str(template_id or "").strip(), {}) or {})
        if store.get("last_active_template_id") == template_id:
            store["last_active_template_id"] = ""
        self._save_store(store)
        return copy.deepcopy(removed)

    def set_template_favorite(self, *, template_id: str, favorite: bool) -> Dict[str, Any]:
        template = self.load_template(template_id)
        if not template:
            return {}
        template["favorite"] = bool(favorite)
        return self.save_template(template)

    def start_template_wizard(
        self,
        *,
        template_type: str = "TASK_WORKSPACE",
        seed_template: Dict[str, Any] | None = None,
        seed_task_workspace: Dict[str, Any] | None = None,
        seed_workspace_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        store = self._load_store()
        wizard_id = f"wizard_{now.replace(':', '').replace('-', '')}"
        seed_template = dict(seed_template or {})
        seed_task_workspace = dict(seed_task_workspace or {})
        task_type = str(seed_template.get("task_type") or seed_task_workspace.get("task_type") or "ARRIVAL").upper()
        wizard = asdict(
            TemplateWizardStatePacket(
                wizard_id=wizard_id,
                current_step=1,
                template_type=str(seed_template.get("template_type") or template_type or "TASK_WORKSPACE").upper(),
                draft_name=str(seed_template.get("name") or seed_task_workspace.get("name") or ""),
                draft_category=str(seed_template.get("category") or TASK_TYPES.get(task_type, TASK_TYPES["ARRIVAL"])["label"]),
                draft_layout_profile=dict(seed_template.get("layout_profile") or (seed_workspace_payload or {}).get("layout_profile") or {}),
                draft_ui_mode=str(seed_template.get("ui_mode") or (seed_workspace_payload or {}).get("ui_mode") or "STUDIO"),
                draft_slot_definitions=list(seed_template.get("slot_definitions") or self.default_slots_for_task_type(task_type)),
                draft_checklist_template=list(seed_template.get("checklist_template") or self._checklist_template_from_task(seed_task_workspace) or self.default_checklist_template(task_type)),
                draft_stage_template=list(seed_template.get("stage_template") or seed_task_workspace.get("stage_order") or TASK_TYPES.get(task_type, TASK_TYPES["ARRIVAL"])["stages"]),
                draft_save_options={
                    "include_layout": True,
                    "include_tool_state": True,
                    "include_validation_rules": True,
                    "include_slots": True,
                    "include_checklist": True,
                    "include_context_bindings": True,
                    "include_live_values": False,
                },
                review_ready=False,
                updated_at=now,
                draft_task_type=task_type,
                draft_description=str(seed_template.get("description") or ""),
            )
        )
        store["wizards"][wizard_id] = wizard
        store["last_active_wizard_id"] = wizard_id
        self._save_store(store)
        return copy.deepcopy(wizard)

    def load_template_wizard(self, wizard_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(dict(store["wizards"].get(str(wizard_id or "").strip(), {}) or {}))

    def update_template_wizard(self, *, wizard_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        wizard = dict(store["wizards"].get(str(wizard_id or "").strip(), {}) or {})
        if not wizard:
            return {}
        wizard.update(copy.deepcopy(updates))
        wizard["updated_at"] = utc_now_iso()
        wizard["review_ready"] = bool(wizard.get("draft_name")) and bool(wizard.get("draft_category")) and bool(wizard.get("draft_stage_template"))
        store["wizards"][wizard_id] = wizard
        self._save_store(store)
        return copy.deepcopy(wizard)

    def save_template_from_wizard(self, wizard_id: str) -> Dict[str, Any]:
        wizard = self.load_template_wizard(wizard_id)
        if not wizard:
            return {}
        return self.create_template(
            name=str(wizard.get("draft_name") or "Template"),
            category=str(wizard.get("draft_category") or "Operational Workflow"),
            template_type=str(wizard.get("template_type") or "TASK_WORKSPACE"),
            task_type=str(wizard.get("draft_task_type") or "ARRIVAL"),
            description=str(wizard.get("draft_description") or ""),
            layout_profile=dict(wizard.get("draft_layout_profile") or {}),
            ui_mode=str(wizard.get("draft_ui_mode") or "STUDIO"),
            slot_definitions=list(wizard.get("draft_slot_definitions") or []),
            checklist_template=list(wizard.get("draft_checklist_template") or []),
            stage_template=list(wizard.get("draft_stage_template") or []),
            save_live_values=bool((wizard.get("draft_save_options") or {}).get("include_live_values", False)),
        )

    def save_current_as_template(
        self,
        *,
        name: str,
        category: str,
        template_type: str,
        task_type: str,
        workspace_payload: Dict[str, Any],
        active_task_workspace: Dict[str, Any] | None = None,
        include_live_values: bool = False,
    ) -> Dict[str, Any]:
        active_task_workspace = dict(active_task_workspace or {})
        checklist_template = self._checklist_template_from_task(active_task_workspace) or self.default_checklist_template(task_type)
        stage_template = list(active_task_workspace.get("stage_order") or TASK_TYPES.get(task_type, TASK_TYPES["ARRIVAL"])["stages"])
        slot_definitions = list(active_task_workspace.get("slot_definitions") or self.default_slots_for_task_type(task_type))
        return self.create_template(
            name=name,
            category=category,
            template_type=template_type,
            task_type=task_type,
            description=f"Saved from current workspace on {utc_now_iso()}",
            layout_profile=dict((workspace_payload or {}).get("layout_profile") or {}),
            ui_mode=str((workspace_payload or {}).get("ui_mode") or "STUDIO"),
            slot_definitions=slot_definitions,
            checklist_template=checklist_template,
            stage_template=stage_template,
            required_documents_template=list(active_task_workspace.get("required_documents") or []),
            default_export_goal=str(active_task_workspace.get("export_goal") or ""),
            default_context_bindings={},
            save_live_values=bool(include_live_values),
        )

    def create_task_from_template(
        self,
        *,
        template_id: str,
        task_name: str,
        workspace_id: str,
        resume_target: Dict[str, Any],
        slot_assignments: List[Dict[str, Any]],
        task_service: TaskWorkspaceService,
    ) -> Dict[str, Any]:
        template = self.load_template(template_id)
        if not template:
            raise ValueError("template_id is required")
        normalized_assignments = self._normalize_slot_assignments(template, slot_assignments)
        missing_required = [
            assignment["slot_id"]
            for assignment in normalized_assignments
            if assignment["assignment_status"] != "ASSIGNED"
            and any(slot.get("slot_id") == assignment["slot_id"] and slot.get("required", True) for slot in template.get("slot_definitions", []))
        ]
        if missing_required:
            raise ValueError(f"Required slots must be assigned before launch: {', '.join(missing_required)}")
        created = task_service.create_task_workspace(
            workspace_id=workspace_id,
            name=str(task_name or template.get("name") or "Template Task"),
            task_type=str(template.get("task_type") or "ARRIVAL"),
            resume_target=dict(resume_target or {}),
        )
        created["template_id"] = template["template_id"]
        created["slot_assignments"] = normalized_assignments
        created["objective"] = str(template.get("description") or created.get("objective") or "")
        created["stage_order"] = list(template.get("stage_template") or created.get("stage_order") or [])
        if created["stage_order"]:
            created["workflow_stage"] = str(created["stage_order"][0])
        created["checklist"] = self._instantiate_checklist(created["task_workspace_id"], template.get("checklist_template", []))
        created["required_documents"] = list(template.get("required_documents_template") or [])
        created["export_goal"] = str(template.get("default_export_goal") or "")
        created["slot_definitions"] = list(template.get("slot_definitions") or [])
        created["history_log"].append(
            {
                "entry_id": f"{created['task_workspace_id']}::history::{len(created['history_log']) + 1}",
                "timestamp": utc_now_iso(),
                "kind": "TASK_CREATED_FROM_TEMPLATE",
                "message": f"Task created from template {template.get('name') or template.get('template_id')}.",
                "source": "TEMPLATE_SERVICE",
                "related_item_id": template["template_id"],
            }
        )
        return task_service.save_task_workspace(created)

    def list_template_categories(self) -> List[str]:
        return list(DEFAULT_TEMPLATE_CATEGORIES)

    def default_slots_for_task_type(self, task_type: str) -> List[Dict[str, Any]]:
        return copy.deepcopy(DEFAULT_SLOT_DEFINITIONS.get(str(task_type or "ARRIVAL").upper(), DEFAULT_SLOT_DEFINITIONS.get("ARRIVAL", [])))

    def default_checklist_template(self, task_type: str) -> List[Dict[str, Any]]:
        definition = TASK_TYPES.get(str(task_type or "ARRIVAL").upper(), TASK_TYPES["ARRIVAL"])
        return [
            {"group": group, "label": label, "required": required}
            for group, label, required in definition["checklist"]
        ]

    def _checklist_template_from_task(self, task_workspace: Dict[str, Any]) -> List[Dict[str, Any]]:
        checklist = list(task_workspace.get("checklist", []) or [])
        return [
            {
                "group": str(item.get("group") or "GENERAL"),
                "label": str(item.get("label") or ""),
                "required": bool(item.get("required", True)),
            }
            for item in checklist
            if item.get("label")
        ]

    def _instantiate_checklist(self, task_workspace_id: str, checklist_template: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = utc_now_iso()
        checklist = []
        for index, item in enumerate(list(checklist_template or []), start=1):
            checklist.append(
                {
                    "item_id": f"{task_workspace_id}::item::{index}",
                    "label": str(item.get("label") or f"Checklist Item {index}"),
                    "status": "TODO",
                    "required": bool(item.get("required", True)),
                    "note": "",
                    "group": str(item.get("group") or "GENERAL"),
                    "updated_at": now,
                }
            )
        return checklist

    def _normalize_slot_assignments(self, template: Dict[str, Any], assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        assignment_map = {str(item.get("slot_id") or ""): dict(item) for item in list(assignments or []) if item.get("slot_id")}
        normalized = []
        for slot in list(template.get("slot_definitions", []) or []):
            slot_id = str(slot.get("slot_id") or "")
            assignment = assignment_map.get(slot_id, {})
            source_id = str(assignment.get("assigned_source_id") or "")
            normalized.append(
                asdict(
                    SlotAssignmentPacket(
                        slot_id=slot_id,
                        assigned_source_id=source_id,
                        assigned_source_type=str(assignment.get("assigned_source_type") or ""),
                        assignment_status="ASSIGNED" if source_id else "UNASSIGNED",
                        note=str(assignment.get("note") or ""),
                        updated_at=utc_now_iso(),
                    )
                )
            )
        return normalized

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {"templates": {}, "wizards": {}, "last_active_template_id": "", "last_active_wizard_id": ""}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"templates": {}, "wizards": {}, "last_active_template_id": "", "last_active_wizard_id": ""}

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
