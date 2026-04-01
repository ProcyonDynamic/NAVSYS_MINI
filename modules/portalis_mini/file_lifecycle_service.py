from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .archive.document_registry import DocumentRegistry
from .storage import utc_now_iso


@dataclass(slots=True)
class PhysicalFilePacket:
    file_id: str
    display_name: str
    original_filename: str
    absolute_path: str
    file_hash: str = ""
    file_type: str = "DOCUMENT"
    status: str = "ACTIVE"
    linked: bool = False
    archived: bool = False
    favorite: bool = False
    workspace_membership: List[str] = field(default_factory=list)
    imported_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class DocumentInstancePacket:
    document_id: str
    file_id: str
    workspace_id: str = ""
    task_workspace_id: str = ""
    mode: str = "WORKSPACE"
    status: str = "ACTIVE"
    active: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class FileImportSessionPacket:
    import_session_id: str
    source_path: str
    import_mode: str
    file_id: str = ""
    document_id: str = ""
    created_at: str = ""


@dataclass(slots=True)
class FileExplorerItemPacket:
    file_id: str
    display_name: str
    source_path: str
    file_type: str
    status: str = "ACTIVE"
    workspace_membership: List[str] = field(default_factory=list)
    archived: bool = False
    linked: bool = False
    favorite: bool = False
    opened_in_tabs: bool = False
    created_at: str = ""
    updated_at: str = ""
    original_filename: str = ""
    absolute_path: str = ""
    file_hash: str = ""
    instances: List[Dict[str, Any]] = field(default_factory=list)
    default_document_id: str = ""
    instance_count: int = 0


@dataclass(slots=True)
class FileLifecycleActionPacket:
    action_id: str
    action_type: str
    target_file_id: str = ""
    target_workspace_id: str = ""
    target_task_workspace_id: str = ""
    requested_name: str = ""
    requested_at: str = ""
    requested_by: str = "operator"
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FileLifecycleResultPacket:
    action_id: str
    success: bool
    result_file_id: str = ""
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    updated_refs: Dict[str, Any] = field(default_factory=dict)
    completed_at: str = ""


@dataclass(slots=True)
class ArchiveRecordPacket:
    archive_id: str
    file_id: str
    archived_at: str
    archive_reason: str = ""
    source_workspace_id: str = ""
    restorable: bool = True
    restored_at: str = ""


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "file"


def _detect_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "PDF"
    if suffix in {".doc", ".docx"}:
        return "DOCX"
    if suffix in {".xls", ".xlsx", ".csv"}:
        return "XLSX"
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        return "IMAGE"
    if suffix in {".eml", ".msg"}:
        return "EMAIL"
    if suffix in {".txt", ".md"}:
        return "TEXT"
    return suffix.replace(".", "").upper() or "DOCUMENT"


class FileLifecycleService:
    def __init__(self, portalis_root: str | Path):
        self.root = Path(portalis_root)
        self.registry = DocumentRegistry(self.root)
        self.store_dir = self.root / "file_lifecycle"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.store_dir / "file_store.json"

    def create_file(self, *, workspace_id: str = "", file_name: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        name = str(file_name or "New Workspace File").strip()
        target_dir = self.root / "documents" / "workspace_note"
        target_dir.mkdir(parents=True, exist_ok=True)
        stub = _slugify(name)
        target_path = target_dir / f"{stub}.txt"
        counter = 1
        while target_path.exists():
            counter += 1
            target_path = target_dir / f"{stub}_{counter}.txt"
        target_path.write_text("", encoding="utf-8")
        return self.import_external_file(
            workspace_id=workspace_id,
            file_path=str(target_path),
            import_mode="IMPORT",
            requested_by=requested_by,
            requested_name=name,
            owner_entity="workspace",
            owner_id=str(workspace_id or "workspace_session"),
            doc_type="workspace_note",
            operational_reason="Created from file lifecycle workstation shell.",
        )

    def import_external_file(
        self,
        *,
        workspace_id: str = "",
        file_path: str = "",
        import_mode: str = "IMPORT",
        requested_by: str = "operator",
        requested_name: str = "",
        owner_entity: str = "workspace",
        owner_id: str = "",
        doc_type: str = "",
        operational_reason: str = "",
        force_new_physical: bool = False,
    ) -> Dict[str, Any]:
        source_path = Path(str(file_path or "").strip())
        mode = str(import_mode or "IMPORT").strip().upper()
        if not source_path.exists() or not source_path.is_file():
            return self._record_action(
                FileLifecycleActionPacket(
                    action_id="FILE_IMPORT_FAILED",
                    action_type="IMPORT_EXTERNAL_FILE",
                    target_workspace_id=str(workspace_id or ""),
                    requested_name=str(requested_name or ""),
                    requested_at=utc_now_iso(),
                    requested_by=requested_by,
                    options={"file_path": str(source_path), "import_mode": mode},
                ),
                success=False,
                result_file_id="",
                message="External file path does not exist.",
                warnings=[str(source_path)],
            )
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        resolved_source = str(source_path.resolve())
        file_hash = self._compute_hash(source_path)
        target_path = source_path
        matched_file_id = "" if force_new_physical else self._find_matching_physical_file(store, resolved_source, file_hash, source_path)
        linked = mode == "LINK"
        if not matched_file_id and mode != "LINK":
            intake_dir = self.root / "documents" / "external_intake"
            intake_dir.mkdir(parents=True, exist_ok=True)
            target_path = intake_dir / source_path.name
            counter = 1
            while target_path.exists():
                if not force_new_physical and self._compute_hash(target_path) == file_hash:
                    break
                counter += 1
                target_path = intake_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
            if not target_path.exists():
                shutil.copy2(source_path, target_path)
            matched_file_id = "" if force_new_physical else self._find_matching_physical_file(store, str(target_path.resolve()), file_hash, target_path)
        if matched_file_id:
            physical = dict(store["physical_files"][matched_file_id])
        else:
            matched_file_id = self._next_file_id(store)
            physical = asdict(
                PhysicalFilePacket(
                    file_id=matched_file_id,
                    display_name=str(requested_name or target_path.name),
                    original_filename=str(source_path.name),
                    absolute_path=str(target_path.resolve()),
                    file_hash=file_hash,
                    file_type=str(doc_type or _detect_file_type(target_path)),
                    status="LINKED" if linked else "ACTIVE",
                    linked=linked,
                    workspace_membership=[],
                    imported_at=utc_now_iso(),
                    updated_at=utc_now_iso(),
                )
            )
            try:
                stat = target_path.stat()
                physical["size"] = int(stat.st_size)
                physical["mtime"] = float(stat.st_mtime)
            except OSError:
                pass
        memberships = set(physical.get("workspace_membership", []))
        if workspace_id:
            memberships.add(workspace_id)
        physical["workspace_membership"] = sorted(memberships)
        physical["status"] = "LINKED" if linked else "ACTIVE"
        physical["linked"] = linked
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][matched_file_id] = physical
        document_id = self._find_existing_instance_document_id(store, matched_file_id, str(workspace_id or ""))
        if not document_id:
            document_id = self.registry.register_document(
                doc_type=str(doc_type or physical.get("file_type") or _detect_file_type(target_path)),
                owner_entity=str(owner_entity or "workspace"),
                owner_id=str(owner_id or workspace_id or "workspace_session"),
                source_file=target_path,
                parsed_fields={},
                confidence=1.0,
                review_required=False,
                workbench_status="STORED",
                operational_reason=str(operational_reason or f"{mode.title()} external file into workstation."),
                display_name=str(physical.get("display_name") or target_path.name),
                file_id=matched_file_id,
                tce_lite={"HOW": {"file_intake_mode": mode}},
            )
            store["document_instances"][document_id] = asdict(
                DocumentInstancePacket(
                    document_id=document_id,
                    file_id=matched_file_id,
                    workspace_id=str(workspace_id or ""),
                    mode="WORKSPACE",
                    status="ACTIVE",
                    active=True,
                    created_at=utc_now_iso(),
                    updated_at=utc_now_iso(),
                )
            )
        else:
            instance = dict(store["document_instances"].get(document_id, {}) or {})
            instance["status"] = "ACTIVE"
            instance["active"] = True
            instance["updated_at"] = utc_now_iso()
            store["document_instances"][document_id] = instance
        store.setdefault("import_sessions", []).append(
            asdict(
                FileImportSessionPacket(
                    import_session_id=f"IMPORT::{matched_file_id}::{len(store.get('import_sessions', [])) + 1}",
                    source_path=resolved_source,
                    import_mode=mode,
                    file_id=matched_file_id,
                    document_id=document_id,
                    created_at=utc_now_iso(),
                )
            )
        )
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_IMPORTED::{matched_file_id}",
                action_type="LINK_EXTERNAL_FILE" if linked else "IMPORT_EXTERNAL_FILE",
                target_file_id=matched_file_id,
                target_workspace_id=str(workspace_id or ""),
                requested_name=str(requested_name or target_path.name),
                requested_at=utc_now_iso(),
                requested_by=requested_by,
                options={"file_path": resolved_source, "import_mode": mode},
            ),
            success=True,
            result_file_id=matched_file_id,
            message="Linked external file without copying." if linked else "Imported external file into the workstation registry.",
            updated_refs={"document_id": document_id, "file_id": matched_file_id, "open_new_tab": True},
        )

    def add_to_workspace(self, *, workspace_id: str = "", file_id: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        memberships = set(physical.get("workspace_membership", []))
        if workspace_id:
            memberships.add(workspace_id)
        physical["workspace_membership"] = sorted(memberships)
        physical["status"] = "ACTIVE"
        physical["archived"] = False
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_ADDED::{physical_id}",
                action_type="ADD_TO_WORKSPACE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_at=utc_now_iso(),
                requested_by=requested_by,
            ),
            success=True,
            result_file_id=physical_id,
            message="Added file to workspace.",
            updated_refs={"workspace_id": workspace_id, "document_id": self.get_preferred_document_id(physical_id, workspace_id=workspace_id)},
        )

    def remove_from_workspace(self, *, workspace_id: str = "", file_id: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        physical["workspace_membership"] = [member for member in list(physical.get("workspace_membership", [])) if member != workspace_id]
        if not physical["workspace_membership"] and not physical.get("archived", False):
            physical["status"] = "REMOVED_FROM_WORKSPACE"
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        for instance in store.get("document_instances", {}).values():
            if instance.get("file_id") == physical_id and instance.get("workspace_id") == workspace_id:
                instance["status"] = "REMOVED_FROM_WORKSPACE"
                instance["updated_at"] = utc_now_iso()
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_REMOVED_FROM_WORKSPACE::{physical_id}",
                action_type="REMOVE_FROM_WORKSPACE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_at=utc_now_iso(),
                requested_by=requested_by,
            ),
            success=True,
            result_file_id=physical_id,
            message="Removed file from workspace membership only.",
            updated_refs={"workspace_id": workspace_id, "close_tab_recommended": True},
        )

    def rename_file(self, *, file_id: str = "", workspace_id: str = "", new_name: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        physical["display_name"] = str(new_name or physical.get("display_name") or physical_id)
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_RENAMED::{physical_id}",
                action_type="RENAME_FILE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_name=str(new_name or ""),
                requested_at=utc_now_iso(),
                requested_by=requested_by,
            ),
            success=True,
            result_file_id=physical_id,
            message="Renamed physical file display label.",
            updated_refs={"tab_label": str(new_name or ""), "document_id": self.get_preferred_document_id(physical_id, workspace_id=workspace_id)},
        )

    def duplicate_file(self, *, file_id: str = "", workspace_id: str = "", new_name: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        source_document_id = str(file_id or "")
        physical_id = self._resolve_physical_file_id(store, source_document_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        source_path = Path(str(physical.get("absolute_path") or ""))
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        target_dir = source_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{source_path.stem}_copy{source_path.suffix}"
        counter = 1
        while target_path.exists():
            counter += 1
            target_path = target_dir / f"{source_path.stem}_copy_{counter}{source_path.suffix}"
        shutil.copy2(source_path, target_path)
        duplicate_result = self.import_external_file(
            workspace_id=workspace_id,
            file_path=str(target_path),
            import_mode="IMPORT",
            requested_by=requested_by,
            requested_name=str(new_name or f"{physical.get('display_name') or source_path.name} Copy"),
            owner_entity="workspace",
            owner_id=str(workspace_id or "workspace_session"),
            doc_type=str(physical.get("file_type") or _detect_file_type(target_path)),
            operational_reason="Duplicated file from workstation explorer.",
            force_new_physical=True,
        )
        duplicate_result["message"] = "Duplicated file into a new physical registry entry."
        duplicate_result["updated_refs"]["source_file_id"] = physical_id
        return duplicate_result

    def archive_file(
        self,
        *,
        file_id: str = "",
        workspace_id: str = "",
        archive_reason: str = "",
        requested_by: str = "operator",
    ) -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        physical["status"] = "ARCHIVED"
        physical["archived"] = True
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        for instance in store.get("document_instances", {}).values():
            if instance.get("file_id") == physical_id:
                instance["status"] = "ARCHIVED"
                instance["active"] = False
                instance["updated_at"] = utc_now_iso()
        store.setdefault("archive_records", []).append(
            asdict(
                ArchiveRecordPacket(
                    archive_id=f"ARCHIVE::{physical_id}::{len(store.get('archive_records', [])) + 1}",
                    file_id=physical_id,
                    archived_at=utc_now_iso(),
                    archive_reason=str(archive_reason or "Archived from workstation."),
                    source_workspace_id=str(workspace_id or ""),
                    restorable=True,
                )
            )
        )
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_ARCHIVED::{physical_id}",
                action_type="ARCHIVE_FILE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_at=utc_now_iso(),
                requested_by=requested_by,
                options={"archive_reason": str(archive_reason or "")},
            ),
            success=True,
            result_file_id=physical_id,
            message="Archived file without deleting it.",
            updated_refs={"document_id": self.get_preferred_document_id(physical_id, workspace_id=workspace_id), "close_tab_recommended": True},
        )

    def delete_file(self, *, file_id: str = "", workspace_id: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        physical["status"] = "DELETED"
        physical["archived"] = False
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        for instance in store.get("document_instances", {}).values():
            if instance.get("file_id") == physical_id:
                instance["status"] = "DELETED"
                instance["active"] = False
                instance["updated_at"] = utc_now_iso()
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_DELETED::{physical_id}",
                action_type="DELETE_FILE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_at=utc_now_iso(),
                requested_by=requested_by,
            ),
            success=True,
            result_file_id=physical_id,
            message="Soft-deleted file from the Portalis lifecycle layer.",
            updated_refs={"document_id": self.get_preferred_document_id(physical_id, workspace_id=workspace_id), "close_tab_recommended": True},
        )

    def restore_file(self, *, file_id: str = "", workspace_id: str = "", requested_by: str = "operator") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store["physical_files"].get(physical_id, {}) or {})
        if not physical:
            raise KeyError(f"File not found: {file_id}")
        memberships = set(physical.get("workspace_membership", []))
        if workspace_id:
            memberships.add(workspace_id)
        physical["workspace_membership"] = sorted(memberships)
        physical["status"] = "LINKED" if physical.get("linked") else "ACTIVE"
        physical["archived"] = False
        physical["updated_at"] = utc_now_iso()
        store["physical_files"][physical_id] = physical
        for instance in store.get("document_instances", {}).values():
            if instance.get("file_id") == physical_id and instance.get("status") in {"ARCHIVED", "DELETED", "REMOVED_FROM_WORKSPACE"}:
                instance["status"] = "ACTIVE"
                instance["updated_at"] = utc_now_iso()
        for record in reversed(store.get("archive_records", [])):
            if record.get("file_id") == physical_id and not record.get("restored_at"):
                record["restored_at"] = utc_now_iso()
                break
        self._save_store(store)
        return self._record_action(
            FileLifecycleActionPacket(
                action_id=f"FILE_RESTORED::{physical_id}",
                action_type="RESTORE_FILE",
                target_file_id=physical_id,
                target_workspace_id=workspace_id,
                requested_at=utc_now_iso(),
                requested_by=requested_by,
            ),
            success=True,
            result_file_id=physical_id,
            message="Restored archived file into active explorer state.",
            updated_refs={"document_id": self.get_preferred_document_id(physical_id, workspace_id=workspace_id)},
        )

    def list_workspace_files(self, *, workspace_id: str = "") -> List[Dict[str, Any]]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        return self._list_files(workspace_id=workspace_id, include_archived=False, linked_only=False)

    def list_archived_files(self, *, workspace_id: str = "") -> List[Dict[str, Any]]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        return self._list_files(workspace_id=workspace_id, include_archived=True, archived_only=True)

    def list_linked_files(self, *, workspace_id: str = "") -> List[Dict[str, Any]]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        return self._list_files(workspace_id=workspace_id, include_archived=False, linked_only=True)

    def get_file(self, file_id: str, *, workspace_id: str = "") -> Dict[str, Any]:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        physical = dict(store.get("physical_files", {}).get(physical_id, {}) or {})
        if not physical:
            return {}
        return self._serialize_explorer_item(store, physical_id, workspace_id=workspace_id)

    def get_preferred_document_id(self, file_id: str, *, workspace_id: str = "") -> str:
        self._sync_registry_documents(default_workspace_id=str(workspace_id or "workspace_session"))
        store = self._load_store()
        physical_id = self._resolve_physical_file_id(store, file_id)
        return self._find_existing_instance_document_id(store, physical_id, workspace_id) or self._find_existing_instance_document_id(store, physical_id, "") or ""

    def get_last_action_result(self) -> Dict[str, Any]:
        store = self._load_store()
        return dict(store.get("last_action_result", {}) or {})

    def list_archive_records(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        return list(store.get("archive_records", []) or [])

    def _list_files(
        self,
        *,
        workspace_id: str = "",
        include_archived: bool = False,
        archived_only: bool = False,
        linked_only: bool = False,
    ) -> List[Dict[str, Any]]:
        store = self._load_store()
        items: List[Dict[str, Any]] = []
        for physical_id, entry in store.get("physical_files", {}).items():
            physical = dict(entry or {})
            archived = bool(physical.get("archived"))
            linked = bool(physical.get("linked"))
            memberships = list(physical.get("workspace_membership", []) or [])
            in_workspace = not workspace_id or workspace_id in memberships
            if archived_only and not archived:
                continue
            if linked_only and not linked:
                continue
            if not include_archived and archived:
                continue
            if not archived_only and workspace_id and not in_workspace:
                continue
            items.append(self._serialize_explorer_item(store, physical_id, workspace_id=workspace_id))
        items.sort(key=lambda item: (str(item.get("display_name") or "").lower(), str(item.get("file_id") or "")))
        return items

    def _serialize_explorer_item(self, store: Dict[str, Any], physical_id: str, *, workspace_id: str = "") -> Dict[str, Any]:
        physical = dict(store.get("physical_files", {}).get(physical_id, {}) or {})
        instances = self._collect_instances_for_file(store, physical_id, workspace_id=workspace_id)
        default_document_id = ""
        if instances:
            default_document_id = str(instances[0].get("document_id") or "")
        return asdict(
            FileExplorerItemPacket(
                file_id=physical_id,
                display_name=str(physical.get("display_name") or physical_id),
                source_path=str(physical.get("absolute_path") or ""),
                file_type=str(physical.get("file_type") or "DOCUMENT"),
                status=str(physical.get("status") or "ACTIVE"),
                workspace_membership=list(physical.get("workspace_membership") or []),
                archived=bool(physical.get("archived")),
                linked=bool(physical.get("linked")),
                favorite=bool(physical.get("favorite")),
                opened_in_tabs=bool(default_document_id),
                created_at=str(physical.get("imported_at") or ""),
                updated_at=str(physical.get("updated_at") or ""),
                original_filename=str(physical.get("original_filename") or ""),
                absolute_path=str(physical.get("absolute_path") or ""),
                file_hash=str(physical.get("file_hash") or ""),
                instances=instances,
                default_document_id=default_document_id,
                instance_count=len(instances),
            )
        )

    def _collect_instances_for_file(self, store: Dict[str, Any], physical_id: str, *, workspace_id: str = "") -> List[Dict[str, Any]]:
        instances: List[Dict[str, Any]] = []
        for document_id, entry in store.get("document_instances", {}).items():
            instance = dict(entry or {})
            if instance.get("file_id") != physical_id:
                continue
            if workspace_id and instance.get("workspace_id") not in {"", workspace_id}:
                continue
            document_entry = self.registry.get_document(document_id) or {}
            instances.append(
                {
                    "document_id": document_id,
                    "workspace_id": str(instance.get("workspace_id") or ""),
                    "task_workspace_id": str(instance.get("task_workspace_id") or ""),
                    "mode": str(instance.get("mode") or "WORKSPACE"),
                    "status": str(instance.get("status") or "ACTIVE"),
                    "active": bool(instance.get("active")),
                    "label": str(document_entry.get("display_name") or document_id),
                }
            )
        instances.sort(key=lambda item: (not bool(item.get("active")), str(item.get("mode") or ""), str(item.get("document_id") or "")))
        return instances

    def _resolve_physical_file_id(self, store: Dict[str, Any], file_id: str) -> str:
        candidate = str(file_id or "")
        if candidate in store.get("physical_files", {}):
            return candidate
        document_entry = self.registry.get_document(candidate) or {}
        if document_entry.get("file_id"):
            return str(document_entry.get("file_id") or "")
        instance = dict(store.get("document_instances", {}).get(candidate, {}) or {})
        return str(instance.get("file_id") or candidate)

    def _find_existing_instance_document_id(self, store: Dict[str, Any], physical_id: str, workspace_id: str) -> str:
        preferred = ""
        fallback = ""
        for document_id, entry in store.get("document_instances", {}).items():
            instance = dict(entry or {})
            if instance.get("file_id") != physical_id:
                continue
            if workspace_id and instance.get("workspace_id") == workspace_id:
                preferred = document_id
                break
            if not fallback:
                fallback = document_id
        return preferred or fallback

    def _find_matching_physical_file(self, store: Dict[str, Any], absolute_path: str, file_hash: str, path: Path) -> str:
        normalized_path = str(Path(absolute_path).resolve())
        stat = path.stat()
        for file_id, entry in store.get("physical_files", {}).items():
            existing = dict(entry or {})
            if str(existing.get("absolute_path") or "") == normalized_path:
                return file_id
            if file_hash and str(existing.get("file_hash") or "") == file_hash:
                return file_id
            existing_name = str(existing.get("original_filename") or "")
            existing_size = int(existing.get("size") or 0)
            existing_mtime = float(existing.get("mtime") or 0.0)
            if existing_name == path.name and existing_size == int(stat.st_size) and int(existing_mtime) == int(stat.st_mtime):
                return file_id
        return ""

    def _sync_registry_documents(self, *, default_workspace_id: str = "") -> None:
        store = self._load_store()
        changed = False
        for document in self.registry.list_documents():
            document_id = str(document.get("document_id") or "")
            if not document_id:
                continue
            physical_id = str(document.get("file_id") or "")
            source_path = Path(str(document.get("source_file") or ""))
            resolved_path = ""
            if str(source_path):
                try:
                    resolved_path = str(source_path.resolve())
                except OSError:
                    resolved_path = str(source_path)
            if not physical_id:
                physical_id = self._find_matching_physical_file(store, resolved_path, self._compute_hash_if_exists(source_path), source_path if source_path.exists() else Path(resolved_path or "."))
            if not physical_id:
                physical_id = self._next_file_id(store)
                stat = source_path.stat() if source_path.exists() else None
                store["physical_files"][physical_id] = asdict(
                    PhysicalFilePacket(
                        file_id=physical_id,
                        display_name=str(document.get("display_name") or source_path.name or document_id),
                        original_filename=str(source_path.name or document_id),
                        absolute_path=resolved_path,
                        file_hash=self._compute_hash_if_exists(source_path),
                        file_type=str(document.get("doc_type") or _detect_file_type(source_path) if str(source_path) else "DOCUMENT"),
                        status="ACTIVE",
                        linked=False,
                        imported_at=str(document.get("created_at") or utc_now_iso()),
                        updated_at=utc_now_iso(),
                    )
                )
                if stat:
                    store["physical_files"][physical_id]["size"] = int(stat.st_size)
                    store["physical_files"][physical_id]["mtime"] = float(stat.st_mtime)
                changed = True
            physical = dict(store["physical_files"].get(physical_id, {}) or {})
            if default_workspace_id and default_workspace_id not in list(physical.get("workspace_membership", []) or []):
                memberships = set(physical.get("workspace_membership", []))
                memberships.add(default_workspace_id)
                physical["workspace_membership"] = sorted(memberships)
                physical["updated_at"] = utc_now_iso()
                store["physical_files"][physical_id] = physical
                changed = True
            if document.get("file_id") != physical_id:
                document["file_id"] = physical_id
                self._rewrite_registry_document(document_id, document)
            instance = dict(store.get("document_instances", {}).get(document_id, {}) or {})
            if not instance:
                store["document_instances"][document_id] = asdict(
                    DocumentInstancePacket(
                        document_id=document_id,
                        file_id=physical_id,
                        workspace_id=str(default_workspace_id or ""),
                        mode="WORKSPACE",
                        status=str(physical.get("status") or "ACTIVE"),
                        active=False,
                        created_at=str(document.get("created_at") or utc_now_iso()),
                        updated_at=utc_now_iso(),
                    )
                )
                changed = True
            elif instance.get("file_id") != physical_id:
                instance["file_id"] = physical_id
                instance["updated_at"] = utc_now_iso()
                store["document_instances"][document_id] = instance
                changed = True
        if changed:
            self._save_store(store)

    def _rewrite_registry_document(self, document_id: str, updated_document: Dict[str, Any]) -> None:
        registry_state = self.registry._load_registry()
        documents = list(registry_state.get("documents", []) or [])
        for index, entry in enumerate(documents):
            if str(entry.get("document_id") or "") == document_id:
                documents[index] = updated_document
                break
        registry_state["documents"] = documents
        self.registry._save_registry(registry_state)

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {
                "physical_files": {},
                "document_instances": {},
                "archive_records": [],
                "import_sessions": [],
                "last_action_result": {},
                "action_history": [],
            }
        with open(self.store_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            data = {}
        data.setdefault("physical_files", {})
        data.setdefault("document_instances", {})
        data.setdefault("archive_records", [])
        data.setdefault("import_sessions", [])
        data.setdefault("last_action_result", {})
        data.setdefault("action_history", [])
        return data

    def _save_store(self, store: Dict[str, Any]) -> None:
        with open(self.store_path, "w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2, ensure_ascii=False)

    def _record_action(
        self,
        action: FileLifecycleActionPacket,
        *,
        success: bool,
        result_file_id: str,
        message: str,
        warnings: List[str] | None = None,
        updated_refs: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        result = asdict(
            FileLifecycleResultPacket(
                action_id=action.action_id,
                success=success,
                result_file_id=result_file_id,
                message=message,
                warnings=list(warnings or []),
                updated_refs=dict(updated_refs or {}),
                completed_at=utc_now_iso(),
            )
        )
        store = self._load_store()
        store["last_action_result"] = result
        store.setdefault("action_history", []).append({"action": asdict(action), "result": result})
        self._save_store(store)
        return result

    def _next_file_id(self, store: Dict[str, Any]) -> str:
        existing = list(store.get("physical_files", {}).keys())
        counter = len(existing) + 1
        candidate = f"FILE_{counter:06d}"
        while candidate in store.get("physical_files", {}):
            counter += 1
            candidate = f"FILE_{counter:06d}"
        return candidate

    def _compute_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _compute_hash_if_exists(self, path: Path) -> str:
        try:
            if path.exists() and path.is_file():
                return self._compute_hash(path)
        except OSError:
            return ""
        return ""
