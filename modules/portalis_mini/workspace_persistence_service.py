from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now_iso


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "workspace"


class WorkspacePersistenceService:
    """Small file-backed persistence layer for Phase 3 workstation continuity."""

    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.workspace_dir = self.root / "shell_workspaces"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.workspace_dir / "workspace_store.json"

    def list_workspaces(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        workspaces = list(store["workspaces"].values())
        return sorted(workspaces, key=lambda item: (item.get("name") or item.get("workspace_id") or "").lower())

    def save_workspace(self, *, workspace_id: str, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        now = utc_now_iso()
        workspace_id = str(workspace_id or "").strip() or f"workspace_{_slugify(name)}"
        existing = dict(store["workspaces"].get(workspace_id, {}) or {})
        snapshots = list(existing.get("snapshot_history", []) or [])
        workspace = {
            "workspace_id": workspace_id,
            "name": str(name or existing.get("name") or workspace_id),
            "ui_mode": payload.get("ui_mode", "STUDIO"),
            "open_tabs": list(payload.get("open_tabs", [])),
            "tab_order": list(payload.get("tab_order", [])),
            "active_document_tab_id": str(payload.get("active_document_tab_id") or ""),
            "pinned_tabs": list(payload.get("pinned_tabs", [])),
            "tab_groups": list(payload.get("tab_groups", [])),
            "layout_profile_id": str(payload.get("layout_profile_id") or "DEFAULT"),
            "linked_context_files": list(payload.get("linked_context_files", [])),
            "selected_file_id": str(payload.get("selected_file_id") or ""),
            "active_ribbon_tab": str(payload.get("active_ribbon_tab") or ""),
            "left_pane_state": str(payload.get("left_pane_state") or ""),
            "right_pane_state": str(payload.get("right_pane_state") or ""),
            "bottom_pane_state": str(payload.get("bottom_pane_state") or ""),
            "left_section_state": dict(payload.get("left_section_state", {})),
            "favorites": dict(payload.get("favorites", {})),
            "snapshot_history": snapshots,
            "autosave_enabled": bool(payload.get("autosave_enabled", True)),
            "layout_profile": dict(payload.get("layout_profile", {})),
            "shell_state": copy.deepcopy(payload),
            "created_at": str(existing.get("created_at") or now),
            "updated_at": now,
        }
        store["workspaces"][workspace_id] = workspace
        store["last_session"] = {
            "workspace_id": workspace_id,
            "saved_at": now,
            "shell_state": copy.deepcopy(payload),
        }
        self._save_store(store)
        return copy.deepcopy(workspace)

    def save_workspace_as(self, *, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        store = self._load_store()
        base = _slugify(name)
        workspace_id = f"workspace_{base}"
        counter = 1
        while workspace_id in store["workspaces"]:
            counter += 1
            workspace_id = f"workspace_{base}_{counter}"
        return self.save_workspace(workspace_id=workspace_id, name=name, payload=payload)

    def load_workspace(self, workspace_id: str) -> Dict[str, Any]:
        store = self._load_store()
        workspace = dict(store["workspaces"].get(str(workspace_id or "").strip(), {}) or {})
        return copy.deepcopy(workspace)

    def rename_workspace(self, *, workspace_id: str, new_name: str) -> Dict[str, Any]:
        store = self._load_store()
        workspace = dict(store["workspaces"].get(str(workspace_id or "").strip(), {}) or {})
        if not workspace:
            return {}
        workspace["name"] = str(new_name or workspace.get("name") or workspace_id)
        workspace["updated_at"] = utc_now_iso()
        store["workspaces"][workspace_id] = workspace
        self._save_store(store)
        return copy.deepcopy(workspace)

    def duplicate_workspace(self, *, workspace_id: str, new_name: str = "") -> Dict[str, Any]:
        existing = self.load_workspace(workspace_id)
        if not existing:
            return {}
        payload = copy.deepcopy(existing.get("shell_state", {}))
        duplicate_name = new_name or f"{existing.get('name') or workspace_id} Copy"
        return self.save_workspace_as(name=duplicate_name, payload=payload)

    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        store = self._load_store()
        removed = dict(store["workspaces"].pop(str(workspace_id or "").strip(), {}) or {})
        if store.get("last_session", {}).get("workspace_id") == workspace_id:
            store["last_session"] = {}
        self._save_store(store)
        return copy.deepcopy(removed)

    def save_snapshot(self, *, workspace_id: str, payload: Dict[str, Any], note: str = "", autosave: bool = False) -> Dict[str, Any]:
        store = self._load_store()
        workspace = dict(store["workspaces"].get(str(workspace_id or "").strip(), {}) or {})
        if not workspace:
            workspace = self.save_workspace(
                workspace_id=str(workspace_id or "workspace_autosave"),
                name=str(workspace_id or "Workspace"),
                payload=payload,
            )
            store = self._load_store()
        snapshot_id = f"{workspace_id}::snapshot::{len(workspace.get('snapshot_history', [])) + 1}"
        snapshot = {
            "snapshot_id": snapshot_id,
            "workspace_id": workspace_id,
            "label": note or ("Autosave Recovery" if autosave else "Manual Snapshot"),
            "source_kind": "AUTOSAVE" if autosave else "SNAPSHOT",
            "created_at": utc_now_iso(),
            "shell_state": copy.deepcopy(payload),
        }
        workspace = dict(store["workspaces"].get(workspace_id, {}) or workspace)
        workspace.setdefault("snapshot_history", []).append(snapshot)
        workspace["updated_at"] = utc_now_iso()
        store["workspaces"][workspace_id] = workspace
        if autosave:
            store["recovery_state"] = {
                "workspace_id": workspace_id,
                "snapshot_id": snapshot_id,
                "saved_at": snapshot["created_at"],
                "shell_state": copy.deepcopy(payload),
            }
        self._save_store(store)
        return copy.deepcopy(snapshot)

    def list_snapshots(self, workspace_id: str) -> List[Dict[str, Any]]:
        workspace = self.load_workspace(workspace_id)
        return list(workspace.get("snapshot_history", []) or [])

    def restore_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        store = self._load_store()
        for workspace in store["workspaces"].values():
            for snapshot in list(workspace.get("snapshot_history", []) or []):
                if snapshot.get("snapshot_id") == snapshot_id:
                    return copy.deepcopy(snapshot)
        return {}

    def load_last_session(self) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(dict(store.get("last_session", {}) or {}))

    def load_recovery_state(self) -> Dict[str, Any]:
        store = self._load_store()
        return copy.deepcopy(dict(store.get("recovery_state", {}) or {}))

    def autosave_workspace(self, *, workspace_id: str, payload: Dict[str, Any], note: str = "Autosave Recovery") -> Dict[str, Any]:
        self.save_workspace(
            workspace_id=workspace_id,
            name=str(payload.get("workspace_name") or workspace_id),
            payload=payload,
        )
        return self.save_snapshot(workspace_id=workspace_id, payload=payload, note=note, autosave=True)

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {
                "workspaces": {},
                "last_session": {},
                "recovery_state": {},
            }
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "workspaces": {},
                "last_session": {},
                "recovery_state": {},
            }

    def _save_store(self, store: Dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(store, indent=2), encoding="utf-8")
