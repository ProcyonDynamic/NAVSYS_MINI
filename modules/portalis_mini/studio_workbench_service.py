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
ANCHOR_TYPES = {"FIELD_BOX", "HIGHLIGHT", "NOTE", "REGION", "HIGHLIGHT_REGION", "NOTE_REGION", "WARNING_REGION", "TEXT_REGION"}
WORKBENCH_TOOL_MODES = {"SELECT", "ADD_FIELD_BOX", "ADD_HIGHLIGHT", "ADD_NOTE", "ADD_REGION"}
ANNOTATION_TYPES = {"NOTE", "FIELD_OBSERVATION", "WARNING", "REVIEW_HINT", "TODO"}
ANNOTATION_STATUSES = {"ACTIVE", "REVIEWED", "RESOLVED", "ARCHIVED"}
SCRATCHPAD_STATUSES = {"DRAFT", "REVIEWED", "FLAGGED"}
WORKBENCH_CENTER_MODES = {"PREVIEW", "ANNOTATE", "SCRATCHPAD", "INSPECT", "GRID", "RECONSTRUCT"}
WORKBENCH_BOTTOM_TABS = {"SCRATCHPAD", "TCE", "AUDIT", "ALERTS", "REVIEW", "RECONSTRUCTION"}
WORKBENCH_INSPECTOR_MODES = {"DOCUMENT", "SELECTION", "ANNOTATION"}


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
    review_required: bool = False
    review_status: str = ""
    review_reasons: List[str] = field(default_factory=list)
    unresolved_field_count: int = 0
    active_alert_count: int = 0
    open_incident_count: int = 0
    tce_lite: Dict[str, Any] = field(default_factory=dict)
    control_room_context: Dict[str, Any] = field(default_factory=dict)
    workbench_history: List[Dict[str, Any]] = field(default_factory=list)
    anchors: List[Dict[str, Any]] = field(default_factory=list)
    anchor_history: List[Dict[str, Any]] = field(default_factory=list)
    anchor_count: int = 0
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    annotation_history: List[Dict[str, Any]] = field(default_factory=list)
    annotation_count: int = 0
    scratchpad_fields: List[Dict[str, Any]] = field(default_factory=list)
    scratchpad_history: List[Dict[str, Any]] = field(default_factory=list)
    scratchpad_count: int = 0
    reconstruction_grid: Dict[str, Any] = field(default_factory=dict)
    reconstruction_regions: List[Dict[str, Any]] = field(default_factory=list)
    reconstruction_history: List[Dict[str, Any]] = field(default_factory=list)
    reconstruction_ready: bool = False


@dataclass(slots=True)
class ReconstructionCellPacket:
    cell_id: str
    document_id: str
    page_number: int = 1
    row: int = 1
    col: int = 1
    row_span: int = 1
    col_span: int = 1
    content_type: str = "EMPTY"
    text_value: str = ""
    style_hint: str = ""
    linked_field_name: str = ""
    linked_anchor_id: str = ""
    editable_flag: bool = True
    merged_into: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class ReconstructionBlockPacket:
    block_id: str
    document_id: str
    page_number: int = 1
    member_cells: List[str] = field(default_factory=list)
    label: str = ""
    block_type: str = "MERGED_BLOCK"
    merged_state: str = "MERGED"
    note: str = ""
    linked_anchor_id: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class ReconstructionRegionPacket:
    region_id: str
    document_id: str
    page_number: int = 1
    region_type: str = "TEXT_BLOCK"
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    label: str = ""
    text_value: str = ""
    linked_field_name: str = ""
    editable_flag: bool = True


@dataclass(slots=True)
class ReconstructionGridPacket:
    document_id: str
    page_number: int = 1
    grid_rows: int = 24
    grid_cols: int = 18
    cell_size: str = "dense"
    density: str = "high"
    background_reference: str = ""
    editable_surface: bool = True
    merged_regions: List[Dict[str, Any]] = field(default_factory=list)
    cells: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class DocumentAnchorPacket:
    anchor_id: str
    document_id: str
    page_number: int = 1
    anchor_type: str = "FIELD_BOX"
    x1: float = 10.0
    y1: float = 10.0
    x2: float = 30.0
    y2: float = 20.0
    field_name: str = ""
    label: str = ""
    note: str = ""
    linked_annotation_id: str = ""
    linked_scratchpad_id: str = ""
    linked_entity_field: str = ""
    confidence: float | None = None
    created_at: str = ""
    updated_at: str = ""
    status: str = "ACTIVE"


@dataclass(slots=True)
class AnchorRegionPacket:
    anchor_id: str
    document_id: str
    page_number: int = 1
    anchor_type: str = "FIELD_BOX"
    x1: float = 10.0
    y1: float = 10.0
    x2: float = 30.0
    y2: float = 20.0
    label: str = ""
    linked_annotation_id: str = ""
    linked_scratchpad_id: str = ""
    linked_entity_field: str = ""
    confidence: float | None = None
    status: str = "ACTIVE"


@dataclass(slots=True)
class AnchorLinkPacket:
    anchor_id: str
    document_id: str
    linked_annotation_id: str = ""
    linked_scratchpad_id: str = ""
    linked_entity_field: str = ""
    linked_at: str = ""


@dataclass(slots=True)
class AnchorActionPacket:
    document_id: str
    anchor_id: str
    anchor_action: str
    operator_name: str = "operator"
    anchor_note: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class WorkbenchAnnotationPacket:
    annotation_id: str
    document_id: str
    annotation_type: str = "NOTE"
    label: str = ""
    note: str = ""
    page_number: int = 1
    region_hint: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "ACTIVE"


@dataclass(slots=True)
class FieldScratchpadPacket:
    scratchpad_id: str
    document_id: str
    field_name: str = ""
    candidate_value: str = ""
    linked_entity_field: str = ""
    confidence_note: str = ""
    source_hint: str = ""
    operator_note: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "DRAFT"


@dataclass(slots=True)
class WorkbenchAnnotationActionPacket:
    document_id: str
    object_id: str
    action_type: str
    operator_name: str = "operator"
    action_note: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class DocumentWorkbenchPacket:
    selected_document_id: str = ""
    selected_anchor_id: str = ""
    selected_cell_id: str = ""
    selected_block_id: str = ""
    selected_page: int = 1
    active_tool_mode: str = "SELECT"
    active_center_mode: str = "PREVIEW"
    active_bottom_tab: str = "SCRATCHPAD"
    inspector_mode: str = "DOCUMENT"
    document_count: int = 0
    filters: Dict[str, Any] = field(default_factory=dict)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    selected_document: Dict[str, Any] | None = None
    selected_anchor: Dict[str, Any] | None = None
    selected_cell: Dict[str, Any] | None = None
    selected_block: Dict[str, Any] | None = None
    anchors: List[Dict[str, Any]] = field(default_factory=list)
    document_type_options: List[str] = field(default_factory=list)
    status_options: List[str] = field(default_factory=list)
    tool_mode_options: List[str] = field(default_factory=list)
    center_mode_options: List[str] = field(default_factory=list)
    bottom_tab_options: List[str] = field(default_factory=list)
    inspector_mode_options: List[str] = field(default_factory=list)
    menu_categories: List[str] = field(default_factory=list)
    action_strip: List[str] = field(default_factory=list)
    pane_state: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


@dataclass(slots=True)
class DocumentWorkbenchStatePacket:
    selected_document_id: str = ""
    selected_anchor_id: str = ""
    selected_cell_id: str = ""
    selected_block_id: str = ""
    selected_page: int = 1
    active_tool_mode: str = "SELECT"
    active_center_mode: str = "PREVIEW"
    active_bottom_tab: str = "SCRATCHPAD"
    inspector_mode: str = "DOCUMENT"
    reconstruction_mode: str = "PREVIEW"
    filter_state: Dict[str, Any] = field(default_factory=dict)
    pane_state: Dict[str, Any] = field(default_factory=dict)
    document_selected_at: str = ""
    anchor_selected_at: str = ""


@dataclass(slots=True)
class CellActionPacket:
    document_id: str
    cell_id: str
    action_type: str
    operator_name: str = "operator"
    action_note: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class BlockActionPacket:
    document_id: str
    block_id: str
    action_type: str
    operator_name: str = "operator"
    action_note: str = ""
    acted_at: str = ""


@dataclass(slots=True)
class WorkbenchPaneStatePacket:
    left_pane_visible: bool = True
    right_pane_visible: bool = True
    bottom_pane_visible: bool = True
    center_workspace_dominant: bool = True


@dataclass(slots=True)
class WorkbenchActionPacket:
    action_id: str
    label: str
    menu_group: str
    active: bool = False


def build_document_workbench(
    portalis_root: str | Path,
    *,
    selected_document_id: str = "",
    selected_anchor_id: str = "",
    selected_cell_id: str = "",
    selected_block_id: str = "",
    selected_page: int = 1,
    active_tool_mode: str = "SELECT",
    active_center_mode: str = "PREVIEW",
    active_bottom_tab: str = "SCRATCHPAD",
    inspector_mode: str = "DOCUMENT",
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
    active_tool_mode = str(active_tool_mode or "SELECT").strip().upper()
    if active_tool_mode not in WORKBENCH_TOOL_MODES:
        active_tool_mode = "SELECT"
    active_center_mode = str(active_center_mode or "PREVIEW").strip().upper()
    if active_center_mode not in WORKBENCH_CENTER_MODES:
        active_center_mode = "PREVIEW"
    active_bottom_tab = str(active_bottom_tab or "SCRATCHPAD").strip().upper()
    if active_bottom_tab not in WORKBENCH_BOTTOM_TABS:
        active_bottom_tab = "SCRATCHPAD"
    inspector_mode = str(inspector_mode or "DOCUMENT").strip().upper()
    if inspector_mode not in WORKBENCH_INSPECTOR_MODES:
        inspector_mode = "DOCUMENT"
    try:
        selected_page = max(1, int(selected_page or 1))
    except (TypeError, ValueError):
        selected_page = 1

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
    anchors = list((selected_document or {}).get("anchors", []) or [])
    selected_anchor = next((anchor for anchor in anchors if anchor.get("anchor_id") == selected_anchor_id), None)
    if selected_anchor is None and selected_anchor_id and selected_document:
        selected_anchor = _find_anchor(selected_document, selected_anchor_id)
    reconstruction_grid = dict((selected_document or {}).get("reconstruction_grid", {}) or {})
    reconstruction_cells = list(reconstruction_grid.get("cells", []) or [])
    reconstruction_blocks = list(reconstruction_grid.get("blocks", []) or [])
    selected_cell = next((cell for cell in reconstruction_cells if cell.get("cell_id") == selected_cell_id), None)
    selected_block = next((block for block in reconstruction_blocks if block.get("block_id") == selected_block_id), None)
    if selected_document:
        selected_document["tce_lite"] = _merge_tce(
            dict(selected_document.get("tce_lite", {}) or {}),
            _build_workbench_tce_delta(
                selected_document,
                notes=str(selected_document.get("notes") or ""),
                status=str(selected_document.get("status") or ""),
                tags=list(selected_document.get("manual_tags", []) or []),
                anchors=anchors,
                selected_anchor=selected_anchor,
                annotations=list(selected_document.get("annotations", []) or []),
                scratchpad=list(selected_document.get("scratchpad_fields", []) or []),
                selected_at=str((selected_document.get("tce_lite", {}) or {}).get("WHEN", {}).get("document_selected_at") or selected_document.get("updated_at") or ""),
                updated_at=str(selected_document.get("updated_at") or ""),
                reconstruction_grid=dict(selected_document.get("reconstruction_grid", {}) or {}),
                selected_cell=selected_cell,
                selected_block=selected_block,
            ),
        )
        selected_document["anchor_link_options"] = _build_anchor_link_options(selected_document)

    return asdict(
        DocumentWorkbenchPacket(
            selected_document_id=selected_document_id,
            selected_anchor_id=selected_anchor_id,
            selected_cell_id=selected_cell_id,
            selected_block_id=selected_block_id,
            selected_page=selected_page,
            active_tool_mode=active_tool_mode,
            active_center_mode=active_center_mode,
            active_bottom_tab=active_bottom_tab,
            inspector_mode=inspector_mode,
            document_count=len(workbench_rows),
            filters={
                "document_type": filter_document_type,
                "status": filter_status,
                "search_text": search_text,
            },
            documents=workbench_rows,
            selected_document=selected_document,
            selected_anchor=selected_anchor,
            selected_cell=selected_cell,
            selected_block=selected_block,
            anchors=anchors,
            document_type_options=sorted({str((entry.get("doc_type") or "")).strip().lower() for entry in document_entries if str((entry.get("doc_type") or "")).strip()}),
            status_options=sorted(WORKBENCH_STATUSES),
            tool_mode_options=sorted(WORKBENCH_TOOL_MODES),
            center_mode_options=sorted(WORKBENCH_CENTER_MODES),
            bottom_tab_options=sorted(WORKBENCH_BOTTOM_TABS),
            inspector_mode_options=sorted(WORKBENCH_INSPECTOR_MODES),
            menu_categories=["File", "View", "Document", "Edit", "Workbench", "Tools", "Help"],
            action_strip=["Open", "Refresh", "Preview", "Annotate", "Scratchpad", "Inspector", "Context", "Grid", "Reconstruct", "Save"],
            pane_state=asdict(
                WorkbenchPaneStatePacket(
                    left_pane_visible=True,
                    right_pane_visible=True,
                    bottom_pane_visible=True,
                    center_workspace_dominant=True,
                )
            ),
            state=asdict(
                DocumentWorkbenchStatePacket(
                    selected_document_id=selected_document_id,
                    selected_anchor_id=selected_anchor_id,
                    selected_cell_id=selected_cell_id,
                    selected_block_id=selected_block_id,
                    selected_page=selected_page,
                    active_tool_mode=active_tool_mode,
                    active_center_mode=active_center_mode,
                    active_bottom_tab=active_bottom_tab,
                    inspector_mode=inspector_mode,
                    reconstruction_mode=active_center_mode if active_center_mode in {"GRID", "RECONSTRUCT"} else "PREVIEW",
                    filter_state={
                        "document_type": filter_document_type,
                        "status": filter_status,
                        "search_text": search_text,
                    },
                    pane_state=asdict(
                        WorkbenchPaneStatePacket(
                            left_pane_visible=True,
                            right_pane_visible=True,
                            bottom_pane_visible=True,
                            center_workspace_dominant=True,
                        )
                    ),
                    document_selected_at=str((selected_document or {}).get("tce_lite", {}).get("WHEN", {}).get("document_selected_at") or (selected_document or {}).get("tce_lite", {}).get("WHEN", {}).get("document_opened_at") or ""),
                    anchor_selected_at=str((selected_anchor or {}).get("updated_at") or ""),
                )
            ),
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


def add_workbench_annotation(
    portalis_root: str | Path,
    *,
    document_id: str,
    annotation_type: str = "NOTE",
    label: str = "",
    note: str = "",
    page_number: int = 1,
    region_hint: str = "",
    status: str = "ACTIVE",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")

    now = utc_now_iso()
    annotations = list(entry.get("workbench_annotations", []) or [])
    annotation = asdict(
        WorkbenchAnnotationPacket(
            annotation_id=_annotation_id(document_id, len(annotations) + 1),
            document_id=document_id,
            annotation_type=_normalize_annotation_type(annotation_type),
            label=str(label or "").strip(),
            note=str(note or "").strip(),
            page_number=_normalize_page(page_number),
            region_hint=str(region_hint or "").strip(),
            created_at=now,
            updated_at=now,
            status=_normalize_annotation_status(status),
        )
    )
    annotations.append(annotation)
    annotation_history = list(entry.get("workbench_annotation_history", []) or [])
    annotation_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=annotation["annotation_id"],
                action_type="ADD_ANNOTATION",
                operator_name=operator_name or "operator",
                action_note=annotation.get("note") or annotation.get("label") or "",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            annotations=annotations,
            selected_annotation=annotation,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_annotations=annotations,
        workbench_annotation_history=annotation_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def update_workbench_annotation(
    portalis_root: str | Path,
    *,
    document_id: str,
    annotation_id: str,
    annotation_type: str = "",
    label: str = "",
    note: str = "",
    page_number: int | None = None,
    region_hint: str = "",
    status: str = "",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    annotations = list(entry.get("workbench_annotations", []) or [])
    updated_annotation = None
    for index, annotation in enumerate(annotations):
        if str(annotation.get("annotation_id") or "") != annotation_id:
            continue
        new_annotation = dict(annotation)
        if annotation_type:
            new_annotation["annotation_type"] = _normalize_annotation_type(annotation_type)
        if label or label == "":
            new_annotation["label"] = str(label or "").strip()
        if note or note == "":
            new_annotation["note"] = str(note or "").strip()
        if page_number is not None:
            new_annotation["page_number"] = _normalize_page(page_number)
        if region_hint or region_hint == "":
            new_annotation["region_hint"] = str(region_hint or "").strip()
        if status:
            new_annotation["status"] = _normalize_annotation_status(status)
        new_annotation["updated_at"] = now
        annotations[index] = new_annotation
        updated_annotation = new_annotation
        break
    if updated_annotation is None:
        raise KeyError(f"Annotation not found: {annotation_id}")
    annotation_history = list(entry.get("workbench_annotation_history", []) or [])
    annotation_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=annotation_id,
                action_type="UPDATE_ANNOTATION",
                operator_name=operator_name or "operator",
                action_note=str(note or label or ""),
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            annotations=annotations,
            selected_annotation=updated_annotation,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_annotations=annotations,
        workbench_annotation_history=annotation_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def delete_workbench_annotation(
    portalis_root: str | Path,
    *,
    document_id: str,
    annotation_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    annotations = list(entry.get("workbench_annotations", []) or [])
    remaining = [dict(annotation) for annotation in annotations if str(annotation.get("annotation_id") or "") != annotation_id]
    if len(remaining) == len(annotations):
        raise KeyError(f"Annotation not found: {annotation_id}")
    annotation_history = list(entry.get("workbench_annotation_history", []) or [])
    annotation_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=annotation_id,
                action_type="DELETE_ANNOTATION",
                operator_name=operator_name or "operator",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            annotations=remaining,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_annotations=remaining,
        workbench_annotation_history=annotation_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def add_workbench_scratchpad_field(
    portalis_root: str | Path,
    *,
    document_id: str,
    field_name: str = "",
    candidate_value: str = "",
    linked_entity_field: str = "",
    confidence_note: str = "",
    source_hint: str = "",
    operator_note: str = "",
    status: str = "DRAFT",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    scratchpad = list(entry.get("workbench_scratchpad", []) or [])
    scratchpad_row = asdict(
        FieldScratchpadPacket(
            scratchpad_id=_scratchpad_id(document_id, len(scratchpad) + 1),
            document_id=document_id,
            field_name=str(field_name or "").strip(),
            candidate_value=str(candidate_value or "").strip(),
            linked_entity_field=str(linked_entity_field or "").strip(),
            confidence_note=str(confidence_note or "").strip(),
            source_hint=str(source_hint or "").strip(),
            operator_note=str(operator_note or "").strip(),
            created_at=now,
            updated_at=now,
            status=_normalize_scratchpad_status(status),
        )
    )
    scratchpad.append(scratchpad_row)
    scratchpad_history = list(entry.get("workbench_scratchpad_history", []) or [])
    scratchpad_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=scratchpad_row["scratchpad_id"],
                action_type="ADD_SCRATCHPAD_FIELD",
                operator_name=operator_name or "operator",
                action_note=scratchpad_row.get("field_name") or scratchpad_row.get("candidate_value") or "",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            scratchpad=scratchpad,
            selected_scratchpad=scratchpad_row,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_scratchpad=scratchpad,
        workbench_scratchpad_history=scratchpad_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def update_workbench_scratchpad_field(
    portalis_root: str | Path,
    *,
    document_id: str,
    scratchpad_id: str,
    field_name: str = "",
    candidate_value: str = "",
    linked_entity_field: str = "",
    confidence_note: str = "",
    source_hint: str = "",
    operator_note: str = "",
    status: str = "",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    scratchpad = list(entry.get("workbench_scratchpad", []) or [])
    updated_scratchpad = None
    for index, row in enumerate(scratchpad):
        if str(row.get("scratchpad_id") or "") != scratchpad_id:
            continue
        new_row = dict(row)
        if field_name or field_name == "":
            new_row["field_name"] = str(field_name or "").strip()
        if candidate_value or candidate_value == "":
            new_row["candidate_value"] = str(candidate_value or "").strip()
        if linked_entity_field or linked_entity_field == "":
            new_row["linked_entity_field"] = str(linked_entity_field or "").strip()
        if confidence_note or confidence_note == "":
            new_row["confidence_note"] = str(confidence_note or "").strip()
        if source_hint or source_hint == "":
            new_row["source_hint"] = str(source_hint or "").strip()
        if operator_note or operator_note == "":
            new_row["operator_note"] = str(operator_note or "").strip()
        if status:
            new_row["status"] = _normalize_scratchpad_status(status)
        new_row["updated_at"] = now
        scratchpad[index] = new_row
        updated_scratchpad = new_row
        break
    if updated_scratchpad is None:
        raise KeyError(f"Scratchpad field not found: {scratchpad_id}")
    scratchpad_history = list(entry.get("workbench_scratchpad_history", []) or [])
    scratchpad_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=scratchpad_id,
                action_type="UPDATE_SCRATCHPAD_FIELD",
                operator_name=operator_name or "operator",
                action_note=str(updated_scratchpad.get("field_name") or updated_scratchpad.get("candidate_value") or ""),
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            scratchpad=scratchpad,
            selected_scratchpad=updated_scratchpad,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_scratchpad=scratchpad,
        workbench_scratchpad_history=scratchpad_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def delete_workbench_scratchpad_field(
    portalis_root: str | Path,
    *,
    document_id: str,
    scratchpad_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    scratchpad = list(entry.get("workbench_scratchpad", []) or [])
    remaining = [dict(row) for row in scratchpad if str(row.get("scratchpad_id") or "") != scratchpad_id]
    if len(remaining) == len(scratchpad):
        raise KeyError(f"Scratchpad field not found: {scratchpad_id}")
    scratchpad_history = list(entry.get("workbench_scratchpad_history", []) or [])
    scratchpad_history.append(
        asdict(
            WorkbenchAnnotationActionPacket(
                document_id=document_id,
                object_id=scratchpad_id,
                action_type="DELETE_SCRATCHPAD_FIELD",
                operator_name=operator_name or "operator",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            scratchpad=remaining,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_scratchpad=remaining,
        workbench_scratchpad_history=scratchpad_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def mark_workbench_scratchpad_reviewed(
    portalis_root: str | Path,
    *,
    document_id: str,
    scratchpad_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    return update_workbench_scratchpad_field(
        portalis_root,
        document_id=document_id,
        scratchpad_id=scratchpad_id,
        status="REVIEWED",
        operator_name=operator_name,
    )


def select_reconstruction_cell(
    portalis_root: str | Path,
    *,
    document_id: str,
    cell_id: str,
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    for cell in list(packet.get("reconstruction_grid", {}).get("cells", []) or []):
        if str(cell.get("cell_id") or "") == cell_id:
            return cell
    raise KeyError(f"Cell not found: {cell_id}")


def select_reconstruction_block(
    portalis_root: str | Path,
    *,
    document_id: str,
    block_id: str,
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    for block in list(packet.get("reconstruction_grid", {}).get("blocks", []) or []):
        if str(block.get("block_id") or "") == block_id:
            return block
    raise KeyError(f"Block not found: {block_id}")


def update_reconstruction_cell(
    portalis_root: str | Path,
    *,
    document_id: str,
    cell_id: str,
    text_value: str = "",
    content_type: str = "",
    linked_field_name: str = "",
    linked_anchor_id: str = "",
    editable_flag: bool | str | None = None,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    cells = [_normalize_reconstruction_cell(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("cells", []) or [])]
    blocks = [_normalize_reconstruction_block(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("blocks", []) or [])]
    history = list(entry.get("workbench_reconstruction_history", []) or [])
    now = utc_now_iso()
    updated_cell = None
    for index, row in enumerate(cells):
        if str(row.get("cell_id") or "") != cell_id:
            continue
        new_row = dict(row)
        if text_value or text_value == "":
            new_row["text_value"] = str(text_value or "")
        if content_type:
            new_row["content_type"] = str(content_type)
        if linked_field_name or linked_field_name == "":
            new_row["linked_field_name"] = str(linked_field_name or "")
        if linked_anchor_id or linked_anchor_id == "":
            new_row["linked_anchor_id"] = str(linked_anchor_id or "")
        if editable_flag is not None:
            new_row["editable_flag"] = str(editable_flag).strip().lower() not in {"false", "0", "off"}
        new_row["updated_at"] = now
        cells[index] = new_row
        updated_cell = new_row
        break
    if updated_cell is None:
        raise KeyError(f"Cell not found: {cell_id}")
    history.append(asdict(CellActionPacket(document_id=document_id, cell_id=cell_id, action_type="EDIT_CELL_TEXT", operator_name=operator_name or "operator", action_note=str(updated_cell.get("text_value") or ""), acted_at=now)))
    tce_lite = _merge_tce(entry.get("tce_lite") or {}, _build_workbench_tce_delta(entry, updated_at=now, reconstruction_grid={"cells": cells, "blocks": blocks}, selected_cell=updated_cell))
    updated = registry.update_document_workbench(
        document_id,
        workbench_reconstruction_cells=cells,
        workbench_reconstruction_blocks=blocks,
        workbench_reconstruction_history=history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def clear_reconstruction_cell(
    portalis_root: str | Path,
    *,
    document_id: str,
    cell_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    return update_reconstruction_cell(
        portalis_root,
        document_id=document_id,
        cell_id=cell_id,
        text_value="",
        content_type="EMPTY",
        operator_name=operator_name,
    )


def merge_reconstruction_cells(
    portalis_root: str | Path,
    *,
    document_id: str,
    lead_cell_id: str,
    row_span: int = 1,
    col_span: int = 1,
    label: str = "",
    note: str = "",
    linked_anchor_id: str = "",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    cells = [_normalize_reconstruction_cell(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("cells", []) or [])]
    blocks = [_normalize_reconstruction_block(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("blocks", []) or [])]
    history = list(entry.get("workbench_reconstruction_history", []) or [])
    now = utc_now_iso()
    lead = next((row for row in cells if row.get("cell_id") == lead_cell_id), None)
    if lead is None:
        raise KeyError(f"Cell not found: {lead_cell_id}")
    row_span = max(1, int(row_span or 1))
    col_span = max(1, int(col_span or 1))
    member_cells = []
    for row in cells:
        if int(row.get("row") or 0) >= int(lead.get("row") or 1) and int(row.get("row") or 0) < int(lead.get("row") or 1) + row_span and int(row.get("col") or 0) >= int(lead.get("col") or 1) and int(row.get("col") or 0) < int(lead.get("col") or 1) + col_span:
            member_cells.append(str(row.get("cell_id") or ""))
    block_id = f"BLOCK::{document_id}::{len(blocks)+1:03d}"
    for index, row in enumerate(cells):
        if row["cell_id"] == lead_cell_id:
            cells[index]["row_span"] = row_span
            cells[index]["col_span"] = col_span
            cells[index]["updated_at"] = now
        elif row["cell_id"] in member_cells:
            cells[index]["merged_into"] = lead_cell_id
            cells[index]["updated_at"] = now
    block = asdict(
        ReconstructionBlockPacket(
            block_id=block_id,
            document_id=document_id,
            page_number=int(lead.get("page_number") or 1),
            member_cells=member_cells,
            label=str(label or lead.get("text_value") or lead_cell_id),
            block_type="MERGED_BLOCK",
            merged_state="MERGED",
            note=str(note or ""),
            linked_anchor_id=str(linked_anchor_id or lead.get("linked_anchor_id") or ""),
            created_at=now,
            updated_at=now,
        )
    )
    block["row_span_hint"] = row_span
    block["col_span_hint"] = col_span
    blocks.append(block)
    history.append(asdict(BlockActionPacket(document_id=document_id, block_id=block_id, action_type="MERGE_CELLS", operator_name=operator_name or "operator", action_note=str(label or ""), acted_at=now)))
    tce_lite = _merge_tce(entry.get("tce_lite") or {}, _build_workbench_tce_delta(entry, updated_at=now, reconstruction_grid={"cells": cells, "blocks": blocks}, selected_block=block, selected_cell=lead))
    updated = registry.update_document_workbench(
        document_id,
        workbench_reconstruction_cells=cells,
        workbench_reconstruction_blocks=blocks,
        workbench_reconstruction_history=history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def split_reconstruction_block(
    portalis_root: str | Path,
    *,
    document_id: str,
    block_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    cells = [_normalize_reconstruction_cell(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("cells", []) or [])]
    blocks = [_normalize_reconstruction_block(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("blocks", []) or [])]
    history = list(entry.get("workbench_reconstruction_history", []) or [])
    now = utc_now_iso()
    block = next((row for row in blocks if row.get("block_id") == block_id), None)
    if block is None:
        raise KeyError(f"Block not found: {block_id}")
    member_cells = set(block.get("member_cells", []) or [])
    lead_cell_id = next(iter(member_cells), "")
    for index, row in enumerate(cells):
        if row["cell_id"] == lead_cell_id:
            cells[index]["row_span"] = 1
            cells[index]["col_span"] = 1
            cells[index]["updated_at"] = now
        if row["cell_id"] in member_cells:
            cells[index]["merged_into"] = ""
            cells[index]["updated_at"] = now
    blocks = [row for row in blocks if row.get("block_id") != block_id]
    history.append(asdict(BlockActionPacket(document_id=document_id, block_id=block_id, action_type="SPLIT_BLOCK", operator_name=operator_name or "operator", acted_at=now)))
    tce_lite = _merge_tce(entry.get("tce_lite") or {}, _build_workbench_tce_delta(entry, updated_at=now, reconstruction_grid={"cells": cells, "blocks": blocks}))
    updated = registry.update_document_workbench(
        document_id,
        workbench_reconstruction_cells=cells,
        workbench_reconstruction_blocks=blocks,
        workbench_reconstruction_history=history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def update_reconstruction_block(
    portalis_root: str | Path,
    *,
    document_id: str,
    block_id: str,
    label: str = "",
    note: str = "",
    linked_anchor_id: str = "",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    packet = _build_document_open_packet(entry, portalis_root=root)
    cells = [_normalize_reconstruction_cell(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("cells", []) or [])]
    blocks = [_normalize_reconstruction_block(document_id, row) for row in list(packet.get("reconstruction_grid", {}).get("blocks", []) or [])]
    history = list(entry.get("workbench_reconstruction_history", []) or [])
    now = utc_now_iso()
    updated_block = None
    for index, row in enumerate(blocks):
        if row.get("block_id") != block_id:
            continue
        new_row = dict(row)
        if label or label == "":
            new_row["label"] = str(label or "")
        if note or note == "":
            new_row["note"] = str(note or "")
        if linked_anchor_id or linked_anchor_id == "":
            new_row["linked_anchor_id"] = str(linked_anchor_id or "")
        new_row["updated_at"] = now
        blocks[index] = new_row
        updated_block = new_row
        break
    if updated_block is None:
        raise KeyError(f"Block not found: {block_id}")
    history.append(asdict(BlockActionPacket(document_id=document_id, block_id=block_id, action_type="LABEL_BLOCK", operator_name=operator_name or "operator", action_note=str(label or ""), acted_at=now)))
    tce_lite = _merge_tce(entry.get("tce_lite") or {}, _build_workbench_tce_delta(entry, updated_at=now, reconstruction_grid={"cells": cells, "blocks": blocks}, selected_block=updated_block))
    updated = registry.update_document_workbench(
        document_id,
        workbench_reconstruction_cells=cells,
        workbench_reconstruction_blocks=blocks,
        workbench_reconstruction_history=history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def add_document_anchor(
    portalis_root: str | Path,
    *,
    document_id: str,
    anchor_type: str = "FIELD_BOX",
    page_number: int = 1,
    x1: float = 10.0,
    y1: float = 10.0,
    x2: float = 30.0,
    y2: float = 20.0,
    field_name: str = "",
    label: str = "",
    note: str = "",
    linked_annotation_id: str = "",
    linked_scratchpad_id: str = "",
    linked_entity_field: str = "",
    confidence: float | None = None,
    status: str = "ACTIVE",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")

    now = utc_now_iso()
    anchors = list(entry.get("workbench_anchors", []) or [])
    anchor = asdict(
        DocumentAnchorPacket(
            anchor_id=_anchor_id(document_id, len(anchors) + 1),
            document_id=document_id,
            page_number=_normalize_page(page_number),
            anchor_type=_normalize_anchor_type(anchor_type),
            x1=min(_clamp_coord(x1), _clamp_coord(x2)),
            y1=min(_clamp_coord(y1), _clamp_coord(y2)),
            x2=max(_clamp_coord(x1), _clamp_coord(x2)),
            y2=max(_clamp_coord(y1), _clamp_coord(y2)),
            field_name=str(field_name or "").strip(),
            label=str(label or "").strip(),
            note=str(note or "").strip(),
            linked_annotation_id=str(linked_annotation_id or "").strip(),
            linked_scratchpad_id=str(linked_scratchpad_id or "").strip(),
            linked_entity_field=str(linked_entity_field or "").strip(),
            confidence=_normalize_confidence(confidence),
            created_at=now,
            updated_at=now,
            status=str(status or "ACTIVE").strip().upper() or "ACTIVE",
        )
    )
    anchors.append(anchor)
    anchor_history = list(entry.get("workbench_anchor_history", []) or [])
    anchor_history.append(
        asdict(
            AnchorActionPacket(
                document_id=document_id,
                anchor_id=anchor["anchor_id"],
                anchor_action="ADD_ANCHOR",
                operator_name=operator_name or "operator",
                anchor_note=anchor.get("note") or anchor.get("label") or "",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            anchors=anchors,
            selected_anchor=anchor,
            selected_at=now,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_anchors=anchors,
        workbench_anchor_history=anchor_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def update_document_anchor(
    portalis_root: str | Path,
    *,
    document_id: str,
    anchor_id: str,
    anchor_type: str = "",
    page_number: int | None = None,
    x1: float | None = None,
    y1: float | None = None,
    x2: float | None = None,
    y2: float | None = None,
    field_name: str = "",
    label: str = "",
    note: str = "",
    linked_annotation_id: str = "",
    linked_scratchpad_id: str = "",
    linked_entity_field: str = "",
    confidence: float | None = None,
    status: str = "",
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    anchors = list(entry.get("workbench_anchors", []) or [])
    updated_anchor = None
    for index, anchor in enumerate(anchors):
        if str(anchor.get("anchor_id") or "") != anchor_id:
            continue
        new_anchor = dict(anchor)
        if anchor_type:
            new_anchor["anchor_type"] = _normalize_anchor_type(anchor_type)
        if page_number is not None:
            new_anchor["page_number"] = _normalize_page(page_number)
        left = _clamp_coord(x1 if x1 is not None else new_anchor.get("x1", 10.0))
        top = _clamp_coord(y1 if y1 is not None else new_anchor.get("y1", 10.0))
        right = _clamp_coord(x2 if x2 is not None else new_anchor.get("x2", 30.0))
        bottom = _clamp_coord(y2 if y2 is not None else new_anchor.get("y2", 20.0))
        new_anchor["x1"] = min(left, right)
        new_anchor["y1"] = min(top, bottom)
        new_anchor["x2"] = max(left, right)
        new_anchor["y2"] = max(top, bottom)
        if field_name or field_name == "":
            new_anchor["field_name"] = str(field_name or "").strip()
        if label or label == "":
            new_anchor["label"] = str(label or "").strip()
        if note or note == "":
            new_anchor["note"] = str(note or "").strip()
        if linked_annotation_id or linked_annotation_id == "":
            new_anchor["linked_annotation_id"] = str(linked_annotation_id or "").strip()
        if linked_scratchpad_id or linked_scratchpad_id == "":
            new_anchor["linked_scratchpad_id"] = str(linked_scratchpad_id or "").strip()
        if linked_entity_field or linked_entity_field == "":
            new_anchor["linked_entity_field"] = str(linked_entity_field or "").strip()
        if confidence is not None or str(new_anchor.get("confidence") or ""):
            new_anchor["confidence"] = _normalize_confidence(confidence if confidence is not None else new_anchor.get("confidence"))
        if status or status == "":
            new_anchor["status"] = str(status or new_anchor.get("status") or "ACTIVE").strip().upper() or "ACTIVE"
        new_anchor["updated_at"] = now
        anchors[index] = new_anchor
        updated_anchor = new_anchor
        break
    if updated_anchor is None:
        raise KeyError(f"Anchor not found: {anchor_id}")
    anchor_history = list(entry.get("workbench_anchor_history", []) or [])
    anchor_history.append(
        asdict(
            AnchorActionPacket(
                document_id=document_id,
                anchor_id=anchor_id,
                anchor_action="UPDATE_ANCHOR",
                operator_name=operator_name or "operator",
                anchor_note=str(note or label or ""),
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            anchors=anchors,
            selected_anchor=updated_anchor,
            selected_at=now,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_anchors=anchors,
        workbench_anchor_history=anchor_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def delete_document_anchor(
    portalis_root: str | Path,
    *,
    document_id: str,
    anchor_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    now = utc_now_iso()
    anchors = list(entry.get("workbench_anchors", []) or [])
    remaining = [dict(anchor) for anchor in anchors if str(anchor.get("anchor_id") or "") != anchor_id]
    if len(remaining) == len(anchors):
        raise KeyError(f"Anchor not found: {anchor_id}")
    anchor_history = list(entry.get("workbench_anchor_history", []) or [])
    anchor_history.append(
        asdict(
            AnchorActionPacket(
                document_id=document_id,
                anchor_id=anchor_id,
                anchor_action="DELETE_ANCHOR",
                operator_name=operator_name or "operator",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            anchors=remaining,
            selected_anchor=None,
            selected_at=now,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_anchors=remaining,
        workbench_anchor_history=anchor_history,
        workbench_updated_at=now,
        tce_lite=tce_lite,
    )
    return _build_document_open_packet(updated, portalis_root=root)


def select_document_anchor(
    portalis_root: str | Path,
    *,
    document_id: str,
    anchor_id: str,
    operator_name: str = "operator",
) -> Dict[str, Any]:
    root = Path(portalis_root)
    registry = DocumentRegistry(root)
    entry = registry.get_document(document_id)
    if not entry:
        raise KeyError(f"Document not found: {document_id}")
    anchor = _find_anchor(entry, anchor_id)
    if not anchor:
        raise KeyError(f"Anchor not found: {anchor_id}")
    now = utc_now_iso()
    anchor_history = list(entry.get("workbench_anchor_history", []) or [])
    anchor_history.append(
        asdict(
            AnchorActionPacket(
                document_id=document_id,
                anchor_id=anchor_id,
                anchor_action="SELECT_ANCHOR",
                operator_name=operator_name or "operator",
                acted_at=now,
            )
        )
    )
    tce_lite = _merge_tce(
        entry.get("tce_lite") or {},
        _build_workbench_tce_delta(
            entry,
            anchors=list(entry.get("workbench_anchors", []) or []),
            selected_anchor=anchor,
            selected_at=now,
            updated_at=now,
        ),
    )
    updated = registry.update_document_workbench(
        document_id,
        workbench_anchor_history=anchor_history,
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
    control_room_context = _build_control_room_context(document_entry)
    anchors = [_normalize_anchor_packet(document_entry, anchor) for anchor in list(document_entry.get("workbench_anchors", []) or [])]
    annotations = [_normalize_annotation_packet(document_entry, annotation) for annotation in list(document_entry.get("workbench_annotations", []) or [])]
    scratchpad_fields = [_normalize_scratchpad_packet(document_entry, row) for row in list(document_entry.get("workbench_scratchpad", []) or [])]
    reconstruction_grid = _build_reconstruction_grid(
        document_entry,
        preview_kind=preview_kind,
        preview_text=preview_text,
        anchors=anchors,
        annotations=annotations,
        scratchpad_fields=scratchpad_fields,
    )
    tce_lite = _merge_tce(
        dict(document_entry.get("tce_lite", {}) or {}),
        _build_workbench_tce_delta(
            document_entry,
            anchors=anchors,
            annotations=annotations,
            scratchpad=scratchpad_fields,
            updated_at=str(document_entry.get("workbench_updated_at") or document_entry.get("created_at") or ""),
            selected_at=str(document_entry.get("workbench_opened_at") or ""),
            reconstruction_grid=reconstruction_grid,
        ),
    )
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
            review_required=bool(document_entry.get("review_required")),
            review_status=str(document_entry.get("review_status") or ""),
            review_reasons=list(document_entry.get("review_reasons", []) or []),
            unresolved_field_count=len(dict(document_entry.get("unresolved_fields", {}) or {})),
            active_alert_count=len(list(control_room_context.get("active_alerts", []) or [])),
            open_incident_count=len(list(control_room_context.get("open_incidents", []) or [])),
            tce_lite=tce_lite,
            control_room_context=control_room_context,
            workbench_history=list(document_entry.get("workbench_history", []) or []),
            anchors=anchors,
            anchor_history=list(document_entry.get("workbench_anchor_history", []) or []),
            anchor_count=len(anchors),
            annotations=annotations,
            annotation_history=list(document_entry.get("workbench_annotation_history", []) or []),
            annotation_count=len(annotations),
            scratchpad_fields=scratchpad_fields,
            scratchpad_history=list(document_entry.get("workbench_scratchpad_history", []) or []),
            scratchpad_count=len(scratchpad_fields),
            reconstruction_grid=reconstruction_grid,
            reconstruction_regions=list(reconstruction_grid.get("regions", []) or []),
            reconstruction_history=list(document_entry.get("workbench_reconstruction_history", []) or []),
            reconstruction_ready=bool(reconstruction_grid.get("cells")),
        )
    )


def _build_workbench_tce_delta(
    document_entry: Dict[str, Any],
    *,
    notes: str = "",
    status: str = "",
    tags: List[str] | None = None,
    anchors: List[Dict[str, Any]] | None = None,
    selected_anchor: Dict[str, Any] | None = None,
    annotations: List[Dict[str, Any]] | None = None,
    selected_annotation: Dict[str, Any] | None = None,
    scratchpad: List[Dict[str, Any]] | None = None,
    selected_scratchpad: Dict[str, Any] | None = None,
    reconstruction_grid: Dict[str, Any] | None = None,
    selected_cell: Dict[str, Any] | None = None,
    selected_block: Dict[str, Any] | None = None,
    selected_at: str = "",
    opened_at: str = "",
    updated_at: str = "",
) -> Dict[str, Any]:
    anchors = list(anchors if anchors is not None else document_entry.get("workbench_anchors", []) or [])
    annotations = list(annotations if annotations is not None else document_entry.get("workbench_annotations", []) or [])
    scratchpad = list(scratchpad if scratchpad is not None else document_entry.get("workbench_scratchpad", []) or [])
    latest_annotation = dict(selected_annotation or (annotations[-1] if annotations else {}) or {})
    latest_scratchpad = dict(selected_scratchpad or (scratchpad[-1] if scratchpad else {}) or {})
    source_summary = {
        "document_type": str(document_entry.get("doc_type") or ""),
        "linked_entity": str(document_entry.get("owner_entity") or ""),
        "linked_entity_id": str(document_entry.get("owner_id") or ""),
        "status": status or str(document_entry.get("workbench_status") or "STORED"),
        "tags": list(tags or document_entry.get("workbench_tags", []) or []),
    }
    editor_summary = {
        "selected_document_id": str(document_entry.get("document_id") or ""),
        "active_tool_mode": "SELECT",
        "anchor_count": len(anchors),
        "selected_anchor_id": str((selected_anchor or {}).get("anchor_id") or ""),
    }
    anchor_summary = {}
    if selected_anchor:
        anchor_summary = {
            "anchor_id": str(selected_anchor.get("anchor_id") or ""),
            "anchor_type": str(selected_anchor.get("anchor_type") or ""),
            "field_name": str(selected_anchor.get("field_name") or ""),
            "label": str(selected_anchor.get("label") or ""),
            "status": str(selected_anchor.get("status") or "ACTIVE"),
            "linked_annotation_id": str(selected_anchor.get("linked_annotation_id") or ""),
            "linked_scratchpad_id": str(selected_anchor.get("linked_scratchpad_id") or ""),
            "linked_entity_field": str(selected_anchor.get("linked_entity_field") or ""),
        }
    annotation_summary = {
        "annotation_count": len(annotations),
        "selected_annotation_id": str((selected_annotation or {}).get("annotation_id") or ""),
        "active_annotations": len([row for row in annotations if str((row or {}).get("status") or "ACTIVE") == "ACTIVE"]),
    }
    scratchpad_summary = {
        "scratchpad_count": len(scratchpad),
        "selected_scratchpad_id": str((selected_scratchpad or {}).get("scratchpad_id") or ""),
        "reviewed_entries": len([row for row in scratchpad if str((row or {}).get("status") or "") == "REVIEWED"]),
    }
    reconstruction_grid = dict(reconstruction_grid or {})
    reconstruction_summary = {
        "grid_rows": int(reconstruction_grid.get("grid_rows") or 0),
        "grid_cols": int(reconstruction_grid.get("grid_cols") or 0),
        "region_count": len(list(reconstruction_grid.get("regions", []) or [])),
        "block_count": len(list(reconstruction_grid.get("blocks", []) or [])),
        "editable_surface": bool(reconstruction_grid.get("editable_surface")),
    }
    workbench_layout_summary = {
        "application_shell": "KICAD_STYLE",
        "center_workspace_dominant": True,
        "bottom_tabs": sorted(WORKBENCH_BOTTOM_TABS),
    }
    return {
        "HOW": {
            "workbench_summary": source_summary,
            "workbench_layout_summary": workbench_layout_summary,
            "editor_summary": editor_summary,
            "anchor_summary": anchor_summary,
            "region_edit_summary": {
                "selected_anchor_id": str((selected_anchor or {}).get("anchor_id") or ""),
                "linked_annotation_id": str((selected_anchor or {}).get("linked_annotation_id") or ""),
                "linked_scratchpad_id": str((selected_anchor or {}).get("linked_scratchpad_id") or ""),
            },
            "reconstruction_edit_summary": {
                "selected_cell_id": str((selected_cell or {}).get("cell_id") or ""),
                "selected_block_id": str((selected_block or {}).get("block_id") or ""),
                "selected_anchor_id": str((selected_anchor or {}).get("anchor_id") or ""),
                "selected_cell": bool(selected_cell),
                "selected_block": bool(selected_block),
            },
            "block_summary": {
                "block_id": str((selected_block or {}).get("block_id") or ""),
                "label": str((selected_block or {}).get("label") or ""),
                "member_cells": list((selected_block or {}).get("member_cells", []) or []),
                "merged_state": str((selected_block or {}).get("merged_state") or ""),
            },
            "annotation_summary": annotation_summary,
            "scratchpad_summary": scratchpad_summary,
            "reconstruction_summary": reconstruction_summary,
        },
        "WHY": {
            "workbench_reason": {
                "manual_first_workspace": True,
                "notes_present": bool(notes),
            },
            "reconstruction_reason": {
                "grid_backed_foundation": True,
                "document_engineering_surface": True,
            },
            "editor_reason": {
                "manual_anchor_editing": True,
                "selected_anchor": bool(selected_anchor),
            },
            "anchor_reason": {
                "manual_region_editing": True,
                "linked_region_context": bool((selected_anchor or {}).get("linked_annotation_id") or (selected_anchor or {}).get("linked_scratchpad_id")),
            },
            "block_reason": {
                "manual_structural_editing": True,
                "manual_block_structuring": True,
                "selected_block": bool(selected_block),
            },
            "annotation_reason": {
                "manual_annotation_capture": True,
                "selected_annotation": bool(selected_annotation),
                "selected_scratchpad": bool(selected_scratchpad),
            },
        },
        "WHEN": {
            "document_opened_at": opened_at or str(document_entry.get("workbench_opened_at") or ""),
            "workbench_updated_at": updated_at or str(document_entry.get("workbench_updated_at") or ""),
            "workbench_state_updated_at": updated_at or str(document_entry.get("workbench_updated_at") or ""),
            "document_selected_at": selected_at or str(document_entry.get("workbench_opened_at") or ""),
            "anchor_created_at": str((selected_anchor or {}).get("created_at") or ""),
            "anchor_updated_at": str((selected_anchor or {}).get("updated_at") or ""),
            "region_linked_at": str((selected_anchor or {}).get("updated_at") or ""),
            "annotation_created_at": str(latest_annotation.get("created_at") or ""),
            "scratchpad_updated_at": str(latest_scratchpad.get("updated_at") or ""),
            "cell_updated_at": str((selected_cell or {}).get("updated_at") or ""),
            "block_merged_at": str((selected_block or {}).get("updated_at") or ""),
            "block_split_at": str((selected_block or {}).get("updated_at") or ""),
            "reconstruction_started_at": updated_at or str(document_entry.get("workbench_opened_at") or ""),
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


def _build_control_room_context(document_entry: Dict[str, Any]) -> Dict[str, Any]:
    unresolved_fields = dict(document_entry.get("unresolved_fields", {}) or {})
    local_alerts = dict(document_entry.get("local_alerts", {}) or {})
    incident_threads = dict(document_entry.get("incident_threads", {}) or {})
    external_bridge_exports = dict(document_entry.get("external_bridge_exports", {}) or {})
    dropzone_handshakes = dict(document_entry.get("dropzone_handshakes", {}) or {})
    compare_ledger = list(document_entry.get("compare_ledger", []) or [])

    active_alerts = []
    for field_name, payload in local_alerts.items():
        row = dict(payload or {})
        if str(row.get("alert_state") or "") in {"ACTIVE", "REOPENED", "ACKNOWLEDGED"}:
            active_alerts.append(
                {
                    "field_name": field_name,
                    "severity": str(row.get("severity") or "INFO"),
                    "state": str(row.get("alert_state") or "ACTIVE"),
                    "reason": str(row.get("alert_reason") or row.get("message") or ""),
                    "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
                }
            )

    open_incidents = []
    for field_name, payload in incident_threads.items():
        row = dict(payload or {})
        if str(row.get("incident_state") or "") in {"OPEN", "REOPENED", "ACKNOWLEDGED", "PINNED"}:
            open_incidents.append(
                {
                    "field_name": field_name,
                    "severity": str(row.get("severity") or "INFO"),
                    "state": str(row.get("incident_state") or "OPEN"),
                    "reason": str(row.get("incident_reason") or ""),
                    "occurrence_count": int(row.get("occurrence_count") or 0),
                    "last_alert_at": str(row.get("last_alert_at") or row.get("updated_at") or ""),
                }
            )

    export_links = []
    for field_name, payload in external_bridge_exports.items():
        row = dict(payload or {})
        export_links.append(
            {
                "field_name": field_name,
                "target_hint": str(row.get("target_hint") or ""),
                "export_type": str(row.get("export_type") or ""),
                "severity": str(row.get("severity") or "NONE"),
                "state": str(row.get("latest_result_state") or row.get("result_state") or "EXPORT_READY"),
            }
        )

    handshake_links = []
    for field_name, payload in dropzone_handshakes.items():
        row = dict(payload or {})
        handshake_links.append(
            {
                "field_name": field_name,
                "handshake_state": str(row.get("handshake_state") or "DROPZONE_STAGED"),
                "staged_at": str(row.get("staged_at") or ""),
                "last_checked_at": str(row.get("last_checked_at") or ""),
            }
        )

    return {
        "review_required": bool(document_entry.get("review_required")),
        "review_status": str(document_entry.get("review_status") or ""),
        "review_reasons": list(document_entry.get("review_reasons", []) or []),
        "unresolved_fields": sorted(unresolved_fields.keys()),
        "active_alerts": active_alerts,
        "open_incidents": open_incidents,
        "export_links": export_links,
        "dropzone_links": handshake_links,
        "compare_ledger_count": len(compare_ledger),
        "last_compare_event": dict(compare_ledger[-1] or {}) if compare_ledger else {},
    }


def _anchor_id(document_id: str, index: int) -> str:
    return f"ANCHOR::{document_id}::{index:04d}"


def _normalize_anchor_type(value: str) -> str:
    normalized = str(value or "FIELD_BOX").strip().upper()
    if normalized not in ANCHOR_TYPES:
        return "FIELD_BOX"
    return normalized


def _normalize_page(value: int | str | None) -> int:
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _clamp_coord(value: float | int | str | None) -> float:
    try:
        number = float(value if value is not None else 0.0)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(100.0, number)), 2)


def _normalize_confidence(value: float | int | str | None) -> float | None:
    if value in {"", None}:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _normalize_anchor_packet(document_entry: Dict[str, Any], anchor: Dict[str, Any]) -> Dict[str, Any]:
    normalized = asdict(
        DocumentAnchorPacket(
            anchor_id=str(anchor.get("anchor_id") or _anchor_id(str(document_entry.get("document_id") or ""), 1)),
            document_id=str(anchor.get("document_id") or document_entry.get("document_id") or ""),
            page_number=_normalize_page(anchor.get("page_number")),
            anchor_type=_normalize_anchor_type(str(anchor.get("anchor_type") or "FIELD_BOX")),
            x1=_clamp_coord(anchor.get("x1")),
            y1=_clamp_coord(anchor.get("y1")),
            x2=_clamp_coord(anchor.get("x2")),
            y2=_clamp_coord(anchor.get("y2")),
            field_name=str(anchor.get("field_name") or ""),
            label=str(anchor.get("label") or ""),
            note=str(anchor.get("note") or ""),
            linked_annotation_id=str(anchor.get("linked_annotation_id") or ""),
            linked_scratchpad_id=str(anchor.get("linked_scratchpad_id") or ""),
            linked_entity_field=str(anchor.get("linked_entity_field") or ""),
            confidence=_normalize_confidence(anchor.get("confidence")),
            created_at=str(anchor.get("created_at") or ""),
            updated_at=str(anchor.get("updated_at") or anchor.get("created_at") or ""),
            status=str(anchor.get("status") or "ACTIVE").strip().upper() or "ACTIVE",
        )
    )
    normalized["width"] = round(max(1.0, normalized["x2"] - normalized["x1"]), 2)
    normalized["height"] = round(max(1.0, normalized["y2"] - normalized["y1"]), 2)
    return normalized


def _normalize_annotation_packet(document_entry: Dict[str, Any], annotation: Dict[str, Any]) -> Dict[str, Any]:
    return asdict(
        WorkbenchAnnotationPacket(
            annotation_id=str(annotation.get("annotation_id") or _annotation_id(str(document_entry.get("document_id") or ""), 1)),
            document_id=str(annotation.get("document_id") or document_entry.get("document_id") or ""),
            annotation_type=_normalize_annotation_type(annotation.get("annotation_type")),
            label=str(annotation.get("label") or ""),
            note=str(annotation.get("note") or ""),
            page_number=_normalize_page(annotation.get("page_number")),
            region_hint=str(annotation.get("region_hint") or ""),
            created_at=str(annotation.get("created_at") or ""),
            updated_at=str(annotation.get("updated_at") or annotation.get("created_at") or ""),
            status=_normalize_annotation_status(annotation.get("status")),
        )
    )


def _normalize_scratchpad_packet(document_entry: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    return asdict(
        FieldScratchpadPacket(
            scratchpad_id=str(row.get("scratchpad_id") or _scratchpad_id(str(document_entry.get("document_id") or ""), 1)),
            document_id=str(row.get("document_id") or document_entry.get("document_id") or ""),
            field_name=str(row.get("field_name") or ""),
            candidate_value=str(row.get("candidate_value") or ""),
            linked_entity_field=str(row.get("linked_entity_field") or ""),
            confidence_note=str(row.get("confidence_note") or ""),
            source_hint=str(row.get("source_hint") or ""),
            operator_note=str(row.get("operator_note") or ""),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or row.get("created_at") or ""),
            status=_normalize_scratchpad_status(row.get("status")),
        )
    )


def _find_anchor(document_entry: Dict[str, Any], anchor_id: str) -> Dict[str, Any] | None:
    for anchor in list(document_entry.get("workbench_anchors", []) or []):
        normalized = _normalize_anchor_packet(document_entry, dict(anchor or {}))
        if normalized.get("anchor_id") == anchor_id:
            return normalized
    return None


def _annotation_id(document_id: str, index: int) -> str:
    return f"ANNOTATION::{document_id}::{index:04d}"


def _scratchpad_id(document_id: str, index: int) -> str:
    return f"SCRATCHPAD::{document_id}::{index:04d}"


def _normalize_annotation_type(value: Any) -> str:
    normalized = str(value or "NOTE").strip().upper()
    if normalized not in ANNOTATION_TYPES:
        return "NOTE"
    return normalized


def _normalize_annotation_status(value: Any) -> str:
    normalized = str(value or "ACTIVE").strip().upper()
    if normalized not in ANNOTATION_STATUSES:
        return "ACTIVE"
    return normalized


def _normalize_scratchpad_status(value: Any) -> str:
    normalized = str(value or "DRAFT").strip().upper()
    if normalized not in SCRATCHPAD_STATUSES:
        return "DRAFT"
    return normalized


def _build_reconstruction_grid(
    document_entry: Dict[str, Any],
    *,
    preview_kind: str,
    preview_text: str,
    anchors: List[Dict[str, Any]],
    annotations: List[Dict[str, Any]],
    scratchpad_fields: List[Dict[str, Any]],
) -> Dict[str, Any]:
    document_id = str(document_entry.get("document_id") or "")
    doc_type = str(document_entry.get("doc_type") or "").strip().lower()
    grid_rows = 24
    grid_cols = 18
    if doc_type in {"crew_list", "spreadsheet", "csv"}:
        grid_rows = 28
        grid_cols = 24
    elif preview_kind == "text":
        grid_rows = 20
        grid_cols = 16

    persisted_cells = list(document_entry.get("workbench_reconstruction_cells", []) or [])
    persisted_blocks = list(document_entry.get("workbench_reconstruction_blocks", []) or [])
    cells: List[Dict[str, Any]] = []
    preview_lines = [line.strip() for line in preview_text.splitlines() if line.strip()][:10]
    if persisted_cells:
        cells = [_normalize_reconstruction_cell(document_id, cell) for cell in persisted_cells]
    else:
        for index, line in enumerate(preview_lines, start=1):
            cells.append(
                asdict(
                    ReconstructionCellPacket(
                        cell_id=f"CELL::{document_id}::{index:03d}",
                        document_id=document_id,
                        page_number=1,
                        row=index,
                        col=1,
                        row_span=1,
                        col_span=max(2, min(grid_cols, 8)),
                        content_type="TEXT_BLOCK",
                        text_value=line[:180],
                        style_hint="preview_text",
                        editable_flag=True,
                        created_at=utc_now_iso(),
                        updated_at=utc_now_iso(),
                    )
                )
            )

    regions: List[Dict[str, Any]] = []
    for index, anchor in enumerate(anchors[:12], start=1):
        regions.append(
            asdict(
                ReconstructionRegionPacket(
                    region_id=f"REGION::{document_id}::{index:03d}",
                    document_id=document_id,
                    page_number=int(anchor.get("page_number") or 1),
                    region_type=str(anchor.get("anchor_type") or "REGION"),
                    x=float(anchor.get("x1") or 0.0),
                    y=float(anchor.get("y1") or 0.0),
                    width=float(anchor.get("width") or 0.0),
                    height=float(anchor.get("height") or 0.0),
                    label=str(anchor.get("label") or anchor.get("field_name") or anchor.get("anchor_id") or ""),
                    text_value=str(anchor.get("note") or ""),
                    linked_field_name=str(anchor.get("field_name") or ""),
                    editable_flag=True,
                )
            )
        )

    for index, row in enumerate(scratchpad_fields[:8], start=1):
        cells.append(
            asdict(
                ReconstructionCellPacket(
                    cell_id=f"SCRATCH::{document_id}::{index:03d}",
                    document_id=document_id,
                    page_number=1,
                    row=min(grid_rows, index + 10),
                    col=2,
                    row_span=1,
                    col_span=max(3, min(grid_cols - 1, 6)),
                    content_type="FIELD_HINT",
                    text_value=str(row.get("candidate_value") or row.get("field_name") or ""),
                    style_hint="scratchpad_candidate",
                    linked_field_name=str(row.get("field_name") or ""),
                    editable_flag=True,
                )
            )
        )

    merged_regions = [
        {
            "region_id": region["region_id"],
            "row_span_hint": max(1, int(round((float(region.get("height") or 0.0) / 100.0) * grid_rows)) or 1),
            "col_span_hint": max(1, int(round((float(region.get("width") or 0.0) / 100.0) * grid_cols)) or 1),
        }
        for region in regions
    ]
    blocks = [_normalize_reconstruction_block(document_id, block) for block in persisted_blocks]
    merged_regions.extend(
        [
            {
                "region_id": block["block_id"],
                "row_span_hint": max(1, int(block.get("row_span_hint") or 1)),
                "col_span_hint": max(1, int(block.get("col_span_hint") or 1)),
            }
            for block in blocks
        ]
    )

    return asdict(
        ReconstructionGridPacket(
            document_id=document_id,
            page_number=1,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            cell_size="dense",
            density="high",
            background_reference=str(document_entry.get("source_file") or ""),
            editable_surface=True,
            merged_regions=merged_regions,
            cells=cells,
            blocks=blocks,
            regions=regions + [
                asdict(
                    ReconstructionRegionPacket(
                        region_id=f"ANNOTATION::{document_id}::{index:03d}",
                        document_id=document_id,
                        page_number=int(annotation.get("page_number") or 1),
                        region_type="ANNOTATION",
                        x=0.0,
                        y=0.0,
                        width=0.0,
                        height=0.0,
                        label=str(annotation.get("label") or annotation.get("annotation_type") or ""),
                        text_value=str(annotation.get("note") or annotation.get("region_hint") or ""),
                        linked_field_name="",
                        editable_flag=True,
                    )
                )
                for index, annotation in enumerate(annotations[:8], start=1)
            ],
        )
    )


def _build_anchor_link_options(document_entry: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    annotations = [
        {
            "annotation_id": str(item.get("annotation_id") or ""),
            "label": str(item.get("label") or item.get("annotation_type") or item.get("annotation_id") or ""),
        }
        for item in list(document_entry.get("annotations", []) or document_entry.get("workbench_annotations", []) or [])
    ]
    scratchpad = [
        {
            "scratchpad_id": str(item.get("scratchpad_id") or ""),
            "label": str(item.get("field_name") or item.get("candidate_value") or item.get("scratchpad_id") or ""),
        }
        for item in list(document_entry.get("scratchpad_fields", []) or document_entry.get("workbench_scratchpad", []) or [])
    ]
    return {
        "annotations": [item for item in annotations if item["annotation_id"]],
        "scratchpad": [item for item in scratchpad if item["scratchpad_id"]],
    }


def _normalize_reconstruction_cell(document_id: str, cell: Dict[str, Any]) -> Dict[str, Any]:
    return asdict(
        ReconstructionCellPacket(
            cell_id=str(cell.get("cell_id") or f"CELL::{document_id}::000"),
            document_id=str(cell.get("document_id") or document_id),
            page_number=_normalize_page(cell.get("page_number")),
            row=max(1, int(cell.get("row") or 1)),
            col=max(1, int(cell.get("col") or 1)),
            row_span=max(1, int(cell.get("row_span") or 1)),
            col_span=max(1, int(cell.get("col_span") or 1)),
            text_value=str(cell.get("text_value") or ""),
            content_type=str(cell.get("content_type") or "EMPTY"),
            style_hint=str(cell.get("style_hint") or ""),
            linked_field_name=str(cell.get("linked_field_name") or ""),
            linked_anchor_id=str(cell.get("linked_anchor_id") or ""),
            editable_flag=bool(cell.get("editable_flag", True)),
            merged_into=str(cell.get("merged_into") or ""),
            created_at=str(cell.get("created_at") or ""),
            updated_at=str(cell.get("updated_at") or cell.get("created_at") or ""),
        )
    )


def _normalize_reconstruction_block(document_id: str, block: Dict[str, Any]) -> Dict[str, Any]:
    normalized = asdict(
        ReconstructionBlockPacket(
            block_id=str(block.get("block_id") or f"BLOCK::{document_id}::000"),
            document_id=str(block.get("document_id") or document_id),
            page_number=_normalize_page(block.get("page_number")),
            member_cells=[str(item) for item in list(block.get("member_cells", []) or []) if str(item or "").strip()],
            label=str(block.get("label") or ""),
            block_type=str(block.get("block_type") or "MERGED_BLOCK"),
            merged_state=str(block.get("merged_state") or "MERGED"),
            note=str(block.get("note") or ""),
            linked_anchor_id=str(block.get("linked_anchor_id") or ""),
            created_at=str(block.get("created_at") or ""),
            updated_at=str(block.get("updated_at") or block.get("created_at") or ""),
        )
    )
    normalized["row_span_hint"] = max(1, int(block.get("row_span_hint") or 1))
    normalized["col_span_hint"] = max(1, int(block.get("col_span_hint") or 1))
    return normalized
