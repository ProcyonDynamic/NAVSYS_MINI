from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .archive.document_registry import DocumentRegistry
from .storage import utc_now_iso


TEXT_PREVIEW_SUFFIXES = {".txt", ".json", ".csv", ".log", ".xml", ".html", ".md"}
IMAGE_PREVIEW_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
PDF_PREVIEW_SUFFIXES = {".pdf"}
WORKBENCH_STATUSES = {"STORED", "IN_WORKBENCH", "READY_FOR_REVIEW", "MANUAL_HOLD", "COMPLETE"}


@dataclass(slots=True)
class DocumentOpenPacket:
    document_id: str
    document_type: str
    source_path: str
    display_name: str
    linked_entity: str
    linked_entity_id: str
    created_at: str = ""
    updated_at: str = ""
    preview_available: bool = False
    notes: str = ""
    status: str = "STORED"
    manual_tags: List[str] = field(default_factory=list)
    source_exists: bool = False
    preview_kind: str = "none"
    open_url: str = ""
    preview_text: str = ""


@dataclass(slots=True)
class DocumentWorkbenchPacket:
    selected_document_id: str = ""
    document_count: int = 0
    filters: Dict[str, Any] = field(default_factory=dict)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    selected_document: Dict[str, Any] | None = None
    updated_at: str = ""


def build_document_workbench(
    portalis_root: str | Path,
    *,
    selected_document_id: str = "",
    filter_document_type: str = "",
    filter_status: str = "",
    search_text: str = "",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    document_entries = list(registry.list_documents())
    filter_document_type = str(filter_document_type or "").strip().lower()
    filter_status = str(filter_status or "").strip().upper()
    search_text = str(search_text or "").strip().lower()

    workbench_rows: List[Dict[str, Any]] = []
    for entry in reversed(document_entries):
        row = _build_document_open_packet(entry, portalis_root=root)
        if filter_document_type and str(row["document_type"]).lower() != filter_document_type:
            continue
        if filter_status and str(row["status"]).upper() != filter_status:
            continue
        if search_text and not _matches_search(row, search_text):
            continue
        workbench_rows.append(row)

    selected_document = next((row for row in workbench_rows if row.get("document_id") == selected_document_id), None)
    if selected_document is None and selected_document_id:
        entry = registry.get_document(selected_document_id)
        if entry:
            selected_document = _build_document_open_packet(entry, portalis_root=root)

    return asdict(
        DocumentWorkbenchPacket(
            selected_document_id=selected_document_id,
            document_count=len(workbench_rows),
            filters={
                "document_type": filter_document_type,
                "status": filter_status,
                "search_text": search_text,
            },
            documents=workbench_rows,
            selected_document=selected_document,
            updated_at=utc_now_iso(),
        )
    )


def open_document_in_workbench(
    portalis_root: str | Path,
    *,
    document_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")

    now = utc_now_iso()
    history = list(entry.get("workbench_history", []) or [])
    history.append(
        {
            "action": "OPEN_DOCUMENT",
            "operator_name": operator_name or "operator",
            "acted_at": now,
        }
    )
    current_status = str(entry.get("workbench_status") or "STORED").strip().upper()
    next_status = "IN_WORKBENCH" if current_status == "STORED" else current_status
    tce_lite = _merge_tce(entry.get("tce_lite") or {}, _build_workbench_tce_delta(entry, opened_at=now, updated_at=now))
    updated = registry.update_document_workbench(
        document_id,
        workbench_status=next_status,
        workbench_history=history,
        workbench_opened_at=now,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def update_document_workbench(
    portalis_root: str | Path,
    *,
    document_id: str,
    workbench_notes: str = "",
    workbench_status: str = "",
    workbench_tags: str | List[str] | None = None,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")

    normalized_status = str(workbench_status or entry.get("workbench_status") or "STORED").strip().upper()
    if normalized_status not in WORKBENCH_STATUSES:
        normalized_status = "STORED"
    normalized_tags = _normalize_tags(workbench_tags if workbench_tags is not None else entry.get("workbench_tags", []))
    now = utc_now_iso()
    history = list(entry.get("workbench_history", []) or [])
    history.append(
        {
            "action": "UPDATE_WORKBENCH",
            "operator_name": operator_name or "operator",
            "acted_at": now,
            "status": normalized_status,
            "tags": normalized_tags,
        }
    )
    opened_at = str(entry.get("workbench_opened_at") or now)
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            notes=workbench_notes,
            status=normalized_status,
            tags=normalized_tags,
            opened_at=opened_at,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_notes=workbench_notes,
        workbench_status=normalized_status,
        workbench_tags=normalized_tags,
        workbench_history=history,
        workbench_opened_at=opened_at,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def resolve_document_source_path(portalis_root: str | Path, document_entry: Dict[str, Any]) -> Path | None:
    root = Path(portalis_root).resolve()
    source_text = str(document_entry.get("source_file") or "").strip()
    if not source_text:
        return None
    source_path = Path(source_text)
    if not source_path.is_absolute():
        source_path = root / source_path
    source_path = source_path.resolve()
    try:
        source_path.relative_to(root)
    except ValueError:
        return None
    return source_path


def _build_document_open_packet(document_entry: Dict[str, Any], *, portalis_root: Path) -> Dict[str, Any]:
    source_path = resolve_document_source_path(portalis_root, document_entry)
    source_exists = bool(source_path and source_path.exists())
    preview_kind = _preview_kind(source_path) if source_exists else "none"
    display_name = source_path.name if source_path else str(document_entry.get("document_id") or "document")
    preview_text = _read_preview_text(source_path) if preview_kind == "text" else ""
    return asdict(
        DocumentOpenPacket(
            document_id=str(document_entry.get("document_id") or ""),
            document_type=str(document_entry.get("doc_type") or ""),
            source_path=str(source_path or document_entry.get("source_file") or ""),
            display_name=display_name,
            linked_entity=str(document_entry.get("owner_entity") or ""),
            linked_entity_id=str(document_entry.get("owner_id") or ""),
            created_at=str(document_entry.get("created_at") or ""),
            updated_at=str(document_entry.get("workbench_updated_at") or document_entry.get("resolved_at") or document_entry.get("created_at") or ""),
            preview_available=preview_kind in {"pdf", "image", "text"},
            notes=str(document_entry.get("workbench_notes") or ""),
            status=str(document_entry.get("workbench_status") or "STORED"),
            manual_tags=_normalize_tags(document_entry.get("workbench_tags", [])),
            source_exists=source_exists,
            preview_kind=preview_kind,
            open_url=f"/portalis/document/{document_entry.get('document_id')}/source" if source_exists else "",
            preview_text=preview_text,
        )
    )


def _build_workbench_tce_delta(
    document_entry: Dict[str, Any],
    *,
    notes: str = "",
    status: str = "",
    tags: List[str] | None = None,
    opened_at: str = "",
    updated_at: str = "",
) -> Dict[str, Any]:
    source_summary = {
        "document_type": str(document_entry.get("doc_type") or ""),
        "linked_entity": str(document_entry.get("owner_entity") or ""),
        "linked_entity_id": str(document_entry.get("owner_id") or ""),
        "status": status or str(document_entry.get("workbench_status") or "STORED"),
        "tags": list(tags or document_entry.get("workbench_tags", []) or []),
    }
    return {
        "HOW": {
            "workbench_summary": source_summary,
        },
        "WHY": {
            "workbench_reason": {
                "manual_first_workspace": True,
                "notes_present": bool(notes),
            }
        },
        "WHEN": {
            "document_opened_at": opened_at or str(document_entry.get("workbench_opened_at") or ""),
            "workbench_updated_at": updated_at or str(document_entry.get("workbench_updated_at") or ""),
        },
    }


def _merge_tce(base_tce: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    merged = {
        "WHAT": dict(base_tce.get("WHAT", {}) or {}),
        "WHO": dict(base_tce.get("WHO", {}) or {}),
        "WHEN": dict(base_tce.get("WHEN", {}) or {}),
        "WHERE": dict(base_tce.get("WHERE", {}) or {}),
        "HOW": dict(base_tce.get("HOW", {}) or {}),
        "WHY": dict(base_tce.get("WHY", {}) or {}),
    }
    for key in ("WHAT", "WHO", "WHEN", "WHERE", "HOW", "WHY"):
        merged[key].update(dict(delta.get(key, {}) or {}))
    return merged


def _normalize_tags(value: str | List[str] | None) -> List[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    normalized: List[str] = []
    for item in raw_items:
        tag = str(item or "").strip()
        if tag and tag not in normalized:
            normalized.append(tag)
    return normalized


def _matches_search(row: Dict[str, Any], search_text: str) -> bool:
    haystack = " ".join(
        [
            str(row.get("document_id") or ""),
            str(row.get("document_type") or ""),
            str(row.get("display_name") or ""),
            str(row.get("linked_entity") or ""),
            str(row.get("linked_entity_id") or ""),
            str(row.get("notes") or ""),
            " ".join(list(row.get("manual_tags", []) or [])),
        ]
    ).lower()
    return search_text in haystack


def _preview_kind(source_path: Path | None) -> str:
    if source_path is None:
        return "none"
    suffix = source_path.suffix.lower()
    if suffix in PDF_PREVIEW_SUFFIXES:
        return "pdf"
    if suffix in IMAGE_PREVIEW_SUFFIXES:
        return "image"
    if suffix in TEXT_PREVIEW_SUFFIXES:
        return "text"
    return "none"


def _read_preview_text(source_path: Path | None) -> str:
    if source_path is None:
        return ""
    try:
        return source_path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""
