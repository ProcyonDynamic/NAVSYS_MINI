from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now_iso


WORKSPACE_MODE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "STUDIO": {
        "name": "Studio",
        "description": "Editing-heavy posture with a larger active canvas.",
        "default_ribbon_tab": "STUDIO",
        "allowed_panels": ["LEFT_SIDEBAR", "RIGHT_INSPECTOR", "BOTTOM_PANEL", "TASK_HEADER"],
        "preferred_split_mode": "SINGLE",
    },
    "VALIDATION": {
        "name": "Validation",
        "description": "Validation-focused posture with comparison and inspector support.",
        "default_ribbon_tab": "REVIEW",
        "allowed_panels": ["LEFT_SIDEBAR", "RIGHT_INSPECTOR", "BOTTOM_PANEL", "COMPARE_SUMMARY", "REVIEW_SUMMARY"],
        "preferred_split_mode": "TWO_PANE_VERTICAL",
    },
    "PACKAGE": {
        "name": "Package",
        "description": "Packaging posture with explorer and output summaries emphasized.",
        "default_ribbon_tab": "QTR",
        "allowed_panels": ["LEFT_SIDEBAR", "BOTTOM_PANEL", "REVIEW_SUMMARY"],
        "preferred_split_mode": "SINGLE",
    },
    "TASK_EXECUTION": {
        "name": "Task Execution",
        "description": "Task-guided posture with header and checklist visibility.",
        "default_ribbon_tab": "TASKS",
        "allowed_panels": ["LEFT_SIDEBAR", "RIGHT_INSPECTOR", "BOTTOM_PANEL", "TASK_HEADER"],
        "preferred_split_mode": "SINGLE",
    },
    "REVIEW": {
        "name": "Review",
        "description": "Review and audit posture with bottom review surfaces emphasized.",
        "default_ribbon_tab": "REVIEW",
        "allowed_panels": ["LEFT_SIDEBAR", "RIGHT_INSPECTOR", "BOTTOM_PANEL", "REVIEW_SUMMARY", "COMPARE_SUMMARY"],
        "preferred_split_mode": "TWO_PANE_VERTICAL",
    },
    "BRIDGE_OPS": {
        "name": "Bridge Ops",
        "description": "Reduced-clutter operational posture for control-room work.",
        "default_ribbon_tab": "HOME",
        "allowed_panels": ["LEFT_SIDEBAR", "BOTTOM_PANEL"],
        "preferred_split_mode": "SINGLE",
    },
}


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "layout"


@dataclass(slots=True)
class WorkspaceModePacket:
    mode_id: str
    name: str
    code: str
    description: str = ""
    default_layout_profile_id: str = ""
    default_ribbon_tab: str = ""
    allowed_panels: List[str] = field(default_factory=list)
    preferred_split_mode: str = "SINGLE"
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class PanelConfigurationPacket:
    panel_configuration_id: str
    name: str
    left_sidebar_visible: bool = True
    right_inspector_visible: bool = True
    bottom_panel_visible: bool = True
    command_palette_enabled: bool = True
    review_summary_visible: bool = True
    task_header_visible: bool = True
    compare_summary_visible: bool = True
    active_sections: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class LayoutProfilePacket:
    layout_profile_id: str
    name: str
    workspace_mode_id: str = "STUDIO"
    left_width: str = "92px"
    right_width: str = "320px"
    bottom_height: str = "180px"
    left_collapsed: bool = False
    right_collapsed: bool = False
    bottom_collapsed: bool = False
    split_view_state: Dict[str, Any] = field(default_factory=dict)
    active_split_mode: str = "SINGLE"
    panel_configuration_id: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class LayoutEditorStatePacket:
    enabled: bool = False
    editing_profile_id: str = ""
    draft_panel_configuration: Dict[str, Any] = field(default_factory=dict)
    draft_dimensions: Dict[str, Any] = field(default_factory=dict)
    preview_mode: str = "LIVE"
    dirty: bool = False
    updated_at: str = ""


class WorkspaceLayoutService:
    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.layout_dir = self.root / "workspace_layouts"
        self.layout_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.layout_dir / "layout_store.json"
        self._ensure_defaults()

    def list_workspace_modes(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return sorted(store["workspace_modes"].values(), key=lambda item: item.get("name") or item.get("mode_id") or "")

    def list_layout_profiles(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return sorted(store["layout_profiles"].values(), key=lambda item: item.get("name") or item.get("layout_profile_id") or "")

    def list_panel_configurations(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return sorted(store["panel_configurations"].values(), key=lambda item: item.get("name") or item.get("panel_configuration_id") or "")

    def load_workspace_mode(self, mode_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store["workspace_modes"].get(str(mode_id or "").strip().upper(), {}))

    def switch_workspace_mode(self, mode_id: str) -> Dict[str, Any]:
        mode = self.load_workspace_mode(mode_id)
        if not mode:
            mode = self.load_workspace_mode("STUDIO")
        return mode

    def save_layout_profile(self, *, layout_profile_id: str, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        layout_profile_id = str(layout_profile_id or "").strip() or f"layout_{_slugify(name)}"
        existing = dict(store["layout_profiles"].get(layout_profile_id, {}) or {})
        profile = asdict(
            LayoutProfilePacket(
                layout_profile_id=layout_profile_id,
                name=str(name or existing.get("name") or layout_profile_id),
                workspace_mode_id=str(payload.get("workspace_mode_id") or existing.get("workspace_mode_id") or "STUDIO"),
                left_width=str(payload.get("left_width") or existing.get("left_width") or "92px"),
                right_width=str(payload.get("right_width") or existing.get("right_width") or "320px"),
                bottom_height=str(payload.get("bottom_height") or existing.get("bottom_height") or "180px"),
                left_collapsed=bool(payload.get("left_collapsed", existing.get("left_collapsed", False))),
                right_collapsed=bool(payload.get("right_collapsed", existing.get("right_collapsed", False))),
                bottom_collapsed=bool(payload.get("bottom_collapsed", existing.get("bottom_collapsed", False))),
                split_view_state=dict(payload.get("split_view_state", existing.get("split_view_state", {}))),
                active_split_mode=str(payload.get("active_split_mode") or existing.get("active_split_mode") or "SINGLE"),
                panel_configuration_id=str(payload.get("panel_configuration_id") or existing.get("panel_configuration_id") or "panel_default"),
                created_at=str(existing.get("created_at") or now),
                updated_at=now,
            )
        )
        store["layout_profiles"][layout_profile_id] = profile
        self._save_store(store)
        return copy.deepcopy(profile)

    def save_layout_profile_as(self, *, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        base = f"layout_{_slugify(name)}"
        layout_profile_id = base
        counter = 1
        while layout_profile_id in store["layout_profiles"]:
            counter += 1
            layout_profile_id = f"{base}_{counter}"
        return self.save_layout_profile(layout_profile_id=layout_profile_id, name=name, payload=payload)

    def load_layout_profile(self, layout_profile_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store["layout_profiles"].get(str(layout_profile_id or "").strip(), {}))

    def rename_layout_profile(self, *, layout_profile_id: str, new_name: str) -> Dict[str, Any]:
        store = self._load_store()
        profile = dict(store["layout_profiles"].get(str(layout_profile_id or "").strip(), {}) or {})
        if not profile:
            return {}
        profile["name"] = str(new_name or profile.get("name") or layout_profile_id)
        profile["updated_at"] = utc_now_iso()
        store["layout_profiles"][layout_profile_id] = profile
        self._save_store(store)
        return copy.deepcopy(profile)

    def duplicate_layout_profile(self, *, layout_profile_id: str, new_name: str = "") -> Dict[str, Any]:
        profile = self.load_layout_profile(layout_profile_id)
        if not profile:
            return {}
        return self.save_layout_profile_as(name=new_name or f"{profile.get('name') or layout_profile_id} Copy", payload=profile)

    def delete_layout_profile(self, layout_profile_id: str) -> Dict[str, Any]:
        store = self._load_store()
        removed = dict(store["layout_profiles"].pop(str(layout_profile_id or "").strip(), {}) or {})
        self._save_store(store)
        return copy.deepcopy(removed)

    def save_panel_configuration(self, *, panel_configuration_id: str, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        panel_configuration_id = str(panel_configuration_id or "").strip() or f"panel_{_slugify(name)}"
        existing = dict(store["panel_configurations"].get(panel_configuration_id, {}) or {})
        config = asdict(
            PanelConfigurationPacket(
                panel_configuration_id=panel_configuration_id,
                name=str(name or existing.get("name") or panel_configuration_id),
                left_sidebar_visible=bool(payload.get("left_sidebar_visible", existing.get("left_sidebar_visible", True))),
                right_inspector_visible=bool(payload.get("right_inspector_visible", existing.get("right_inspector_visible", True))),
                bottom_panel_visible=bool(payload.get("bottom_panel_visible", existing.get("bottom_panel_visible", True))),
                command_palette_enabled=bool(payload.get("command_palette_enabled", existing.get("command_palette_enabled", True))),
                review_summary_visible=bool(payload.get("review_summary_visible", existing.get("review_summary_visible", True))),
                task_header_visible=bool(payload.get("task_header_visible", existing.get("task_header_visible", True))),
                compare_summary_visible=bool(payload.get("compare_summary_visible", existing.get("compare_summary_visible", True))),
                active_sections=list(payload.get("active_sections", existing.get("active_sections", []))),
                created_at=str(existing.get("created_at") or now),
                updated_at=now,
            )
        )
        store["panel_configurations"][panel_configuration_id] = config
        self._save_store(store)
        return copy.deepcopy(config)

    def load_panel_configuration(self, panel_configuration_id: str) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store["panel_configurations"].get(str(panel_configuration_id or "").strip(), {}))

    def set_default_layout_for_mode(self, *, mode_id: str, layout_profile_id: str) -> Dict[str, Any]:
        store = self._load_store()
        mode = dict(store["workspace_modes"].get(str(mode_id or "").strip().upper(), {}) or {})
        if not mode:
            return {}
        mode["default_layout_profile_id"] = str(layout_profile_id or mode.get("default_layout_profile_id") or "")
        mode["updated_at"] = utc_now_iso()
        store["workspace_modes"][mode["mode_id"]] = mode
        self._save_store(store)
        return copy.deepcopy(mode)

    def enter_layout_editor(self, *, editing_profile_id: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        packet = asdict(
            LayoutEditorStatePacket(
                enabled=True,
                editing_profile_id=str(editing_profile_id or ""),
                draft_panel_configuration=dict(current_state.get("draft_panel_configuration") or {}),
                draft_dimensions=dict(current_state.get("draft_dimensions") or {}),
                preview_mode=str(current_state.get("preview_mode") or "LIVE"),
                dirty=bool(current_state.get("dirty", False)),
                updated_at=utc_now_iso(),
            )
        )
        store["layout_editor_state"] = packet
        self._save_store(store)
        return copy.deepcopy(packet)

    def apply_layout_editor_draft(self, *, draft_state: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        packet = asdict(
            LayoutEditorStatePacket(
                enabled=bool(draft_state.get("enabled", True)),
                editing_profile_id=str(draft_state.get("editing_profile_id") or ""),
                draft_panel_configuration=dict(draft_state.get("draft_panel_configuration") or {}),
                draft_dimensions=dict(draft_state.get("draft_dimensions") or {}),
                preview_mode=str(draft_state.get("preview_mode") or "LIVE"),
                dirty=bool(draft_state.get("dirty", True)),
                updated_at=utc_now_iso(),
            )
        )
        store["layout_editor_state"] = packet
        self._save_store(store)
        return copy.deepcopy(packet)

    def cancel_layout_editor(self) -> Dict[str, Any]:
        store = self._load_store()
        store["layout_editor_state"] = asdict(LayoutEditorStatePacket(enabled=False, updated_at=utc_now_iso()))
        self._save_store(store)
        return copy.deepcopy(store["layout_editor_state"])

    def get_layout_editor_state(self) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(store.get("layout_editor_state", {}))

    def _ensure_defaults(self) -> None:
        store = self._load_store()
        now = utc_now_iso()
        for mode_id, definition in WORKSPACE_MODE_DEFAULTS.items():
            if mode_id not in store["workspace_modes"]:
                store["workspace_modes"][mode_id] = asdict(
                    WorkspaceModePacket(
                        mode_id=mode_id,
                        name=str(definition["name"]),
                        code=mode_id,
                        description=str(definition["description"]),
                        default_layout_profile_id=f"layout_{mode_id.lower()}",
                        default_ribbon_tab=str(definition["default_ribbon_tab"]),
                        allowed_panels=list(definition["allowed_panels"]),
                        preferred_split_mode=str(definition["preferred_split_mode"]),
                        created_at=now,
                        updated_at=now,
                    )
                )
            if f"panel_{mode_id.lower()}" not in store["panel_configurations"]:
                panel_defaults = {
                    "left_sidebar_visible": True,
                    "right_inspector_visible": mode_id not in {"PACKAGE", "BRIDGE_OPS"},
                    "bottom_panel_visible": mode_id in {"VALIDATION", "REVIEW", "TASK_EXECUTION", "PACKAGE"},
                    "command_palette_enabled": True,
                    "review_summary_visible": mode_id in {"VALIDATION", "REVIEW", "PACKAGE"},
                    "task_header_visible": mode_id == "TASK_EXECUTION",
                    "compare_summary_visible": mode_id in {"VALIDATION", "REVIEW"},
                    "active_sections": list(definition["allowed_panels"]),
                }
                store["panel_configurations"][f"panel_{mode_id.lower()}"] = asdict(
                    PanelConfigurationPacket(
                        panel_configuration_id=f"panel_{mode_id.lower()}",
                        name=f"{definition['name']} Panels",
                        created_at=now,
                        updated_at=now,
                        **panel_defaults,
                    )
                )
            if f"layout_{mode_id.lower()}" not in store["layout_profiles"]:
                config_id = f"panel_{mode_id.lower()}"
                store["layout_profiles"][f"layout_{mode_id.lower()}"] = asdict(
                    LayoutProfilePacket(
                        layout_profile_id=f"layout_{mode_id.lower()}",
                        name=f"{definition['name']} Layout",
                        workspace_mode_id=mode_id,
                        left_width="92px" if mode_id != "PACKAGE" else "140px",
                        right_width="320px" if mode_id not in {"PACKAGE", "BRIDGE_OPS"} else "220px",
                        bottom_height="220px" if mode_id in {"VALIDATION", "REVIEW", "TASK_EXECUTION", "PACKAGE"} else "140px",
                        left_collapsed=False,
                        right_collapsed=mode_id in {"PACKAGE", "BRIDGE_OPS"},
                        bottom_collapsed=mode_id in {"STUDIO", "BRIDGE_OPS"},
                        split_view_state={"enabled": definition["preferred_split_mode"] != "SINGLE", "mode": definition["preferred_split_mode"], "pane_ids": ["LEFT", "RIGHT"]},
                        active_split_mode=str(definition["preferred_split_mode"]),
                        panel_configuration_id=config_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
        store.setdefault("layout_editor_state", asdict(LayoutEditorStatePacket(enabled=False, updated_at=now)))
        self._save_store(store)

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {
                "workspace_modes": {},
                "layout_profiles": {},
                "panel_configurations": {},
                "layout_editor_state": {},
            }
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {
                "workspace_modes": {},
                "layout_profiles": {},
                "panel_configurations": {},
                "layout_editor_state": {},
            }

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")
