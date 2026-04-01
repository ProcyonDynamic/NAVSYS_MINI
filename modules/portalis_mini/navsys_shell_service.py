from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .storage import utc_now_iso


NAVSYS_MODULES = ["DASHBOARD", "PORTALIS", "NAVWARN", "ASTRANAV", "SYSTEM"]
PORTALIS_SUBMODULES = ["CONTROL_ROOM", "STUDIO", "ARCHIVE", "REVIEW", "OUTPUT"]


@dataclass(slots=True)
class ModuleWorkspaceStatePacket:
    module_id: str
    submodule_id: str
    selected_item_id: str = ""
    selected_object_id: str = ""
    active_workspace_mode: str = "WORKSPACE"
    left_pane_state: str = "BROWSER"
    right_pane_state: str = "INSPECTOR"
    bottom_pane_tab: str = "CONTEXT"
    layout_mode: str = "COUPLER_WIDE"


@dataclass(slots=True)
class UiActionPacket:
    action_id: str
    label: str
    scope: str
    active: bool = False
    enabled: bool = True


@dataclass(slots=True)
class UiDropdownStatePacket:
    dropdown_id: str = ""
    label: str = ""
    menu_group: str = ""
    item_ids: List[str] = field(default_factory=list)
    active: bool = False


@dataclass(slots=True)
class UiDialogStatePacket:
    dialog_id: str = ""
    title: str = ""
    dialog_reason: str = ""
    visible: bool = False
    fields: List[Dict[str, Any]] = field(default_factory=list)
    opened_at: str = ""


@dataclass(slots=True)
class UiCommandPacket:
    command_id: str
    label: str
    scope: str
    command_group: str = ""
    command_reason: str = ""
    enabled: bool = True
    active: bool = False
    target_params: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuickActionPacket:
    action_id: str
    label: str
    scope: str
    action_reason: str = ""
    emphasized: bool = False
    target_params: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CommandPaletteStatePacket:
    open: bool = False
    query: str = ""
    selected_command_id: str = ""
    commands: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class WorkbenchPaneStatePacket:
    left_pane_collapsed: bool = False
    right_pane_collapsed: bool = False
    bottom_pane_collapsed: bool = False
    left_pane_active: bool = True
    right_pane_active: bool = True
    bottom_pane_active: bool = True
    pane_sizes: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class KeyboardActionPacket:
    action_id: str
    shortcut: str
    label: str
    scope: str


@dataclass(slots=True)
class DockingStatePacket:
    active_docked_window: str = ""
    docking_modes: Dict[str, List[str]] = field(default_factory=dict)
    default_dock_mode: str = "FLOAT"


@dataclass(slots=True)
class LayoutProfilePacket:
    profile_id: str = "DEFAULT"
    layout_profile_id: str = "DEFAULT"
    name: str = "Default Layout"
    workspace_mode_id: str = "STUDIO"
    panel_configuration_id: str = ""
    pane_widths: Dict[str, str] = field(default_factory=dict)
    pane_heights: Dict[str, str] = field(default_factory=dict)
    left_width: str = "92px"
    right_width: str = "320px"
    bottom_height: str = "180px"
    left_collapsed: bool = False
    right_collapsed: bool = False
    bottom_collapsed: bool = False
    split_view_state: Dict[str, Any] = field(default_factory=dict)
    active_split_mode: str = "SINGLE"
    created_at: str = ""
    updated_at: str = ""
    restore_available: bool = True


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
class LayoutEditorStatePacket:
    enabled: bool = False
    editing_profile_id: str = ""
    draft_panel_configuration: Dict[str, Any] = field(default_factory=dict)
    draft_dimensions: Dict[str, Any] = field(default_factory=dict)
    preview_mode: str = "LIVE"
    dirty: bool = False
    updated_at: str = ""


@dataclass(slots=True)
class PartialRefreshPacket:
    enabled: bool = True
    client_regions: List[str] = field(default_factory=list)
    refresh_reason: str = ""


@dataclass(slots=True)
class RibbonTabStatePacket:
    ribbon_id: str
    label: str
    tool_groups: List[str] = field(default_factory=list)
    active: bool = False
    recommended: bool = False
    recommended_group: str = ""


@dataclass(slots=True)
class DocumentTabPacket:
    tab_id: str
    document_id: str
    label: str
    source_lane: str = "STUDIO"
    active: bool = False
    closable: bool = True
    pinned: bool = False
    opened_at: str = ""


@dataclass(slots=True)
class DocumentTabStatePacket:
    tabs: List[Dict[str, Any]] = field(default_factory=list)
    active_document_tab_id: str = ""
    tab_order: List[str] = field(default_factory=list)
    pinned_tabs: List[str] = field(default_factory=list)
    tab_groups: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class SidebarSectionPacket:
    section_id: str
    label: str
    icon_hint: str = ""
    expanded: bool = True
    item_count: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class BottomHostTabPacket:
    tab_id: str
    label: str
    active: bool = False
    badge: str = ""


@dataclass(slots=True)
class InspectorModePacket:
    mode_id: str
    label: str
    active: bool = False


@dataclass(slots=True)
class WorkspacePacket:
    workspace_id: str
    label: str
    workspace_type: str = "WORKSPACE"
    active: bool = False
    name: str = ""
    ui_mode: str = "STUDIO"
    open_tabs: List[Dict[str, Any]] = field(default_factory=list)
    tab_order: List[str] = field(default_factory=list)
    active_document_tab_id: str = ""
    pinned_tabs: List[str] = field(default_factory=list)
    tab_groups: List[Dict[str, Any]] = field(default_factory=list)
    layout_profile_id: str = "DEFAULT"
    linked_context_files: List[str] = field(default_factory=list)
    selected_file_id: str = ""
    selected_workspace_id: str = ""
    open_tab_ids: List[str] = field(default_factory=list)
    active_ribbon_tab: str = ""
    left_pane_state: str = ""
    right_pane_state: str = ""
    bottom_pane_state: str = ""
    left_section_state: Dict[str, Any] = field(default_factory=dict)
    favorites: Dict[str, Any] = field(default_factory=dict)
    snapshot_history: List[Dict[str, Any]] = field(default_factory=list)
    autosave_enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class SelectionEventPacket:
    event_id: str = ""
    target_type: str = ""
    target_id: str = ""
    selection_context: Dict[str, Any] = field(default_factory=dict)
    selection_bounds: Dict[str, Any] = field(default_factory=dict)
    selection_page: int = 1
    selection_source_document_id: str = ""
    recommended_ribbon_tab: str = ""
    recommended_ribbon_group: str = ""
    context_actions: List[str] = field(default_factory=list)
    floating_toolbar_tools: List[str] = field(default_factory=list)
    selection_reason: str = ""
    event_scope: str = ""


@dataclass(slots=True)
class ContextMenuStatePacket:
    menu_id: str = ""
    target_type: str = ""
    target_id: str = ""
    visible: bool = False
    sections: List[str] = field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = field(default_factory=list)
    object_actions: List[Dict[str, Any]] = field(default_factory=list)
    favorite_actions: List[Dict[str, Any]] = field(default_factory=list)
    anchor_x: int = 0
    anchor_y: int = 0
    opened_at: str = ""


@dataclass(slots=True)
class FloatingToolbarStatePacket:
    visible: bool = False
    anchor_x: int = 0
    anchor_y: int = 0
    target_type: str = ""
    target_id: str = ""
    tools: List[Dict[str, Any]] = field(default_factory=list)
    collapsed: bool = False
    opened_at: str = ""


@dataclass(slots=True)
class ObjectLayerStatePacket:
    layer_order: List[str] = field(default_factory=list)
    visibility: Dict[str, bool] = field(default_factory=dict)
    lock_state: Dict[str, bool] = field(default_factory=dict)
    opacity: Dict[str, float] = field(default_factory=dict)
    object_refs: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FavoriteToolsPacket:
    pinned_ribbon_actions: List[str] = field(default_factory=list)
    pinned_context_actions: List[str] = field(default_factory=list)
    favorite_workspaces: List[str] = field(default_factory=list)
    favorite_templates: List[str] = field(default_factory=list)


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


@dataclass(slots=True)
class SplitViewStatePacket:
    enabled: bool = False
    mode: str = "SINGLE"
    pane_ids: List[str] = field(default_factory=lambda: ["LEFT", "RIGHT"])
    active_pane_id: str = "LEFT"
    orientation: str = "VERTICAL"
    divider_positions: Dict[str, str] = field(default_factory=lambda: {"primary": "50%"})
    compare_mode: str = ""
    active_group_id: str = "PRIMARY"
    group_ids: List[str] = field(default_factory=lambda: ["PRIMARY"])
    updated_at: str = ""


@dataclass(slots=True)
class PaneContextPacket:
    pane_id: str
    document_tab_id: str = ""
    document_id: str = ""
    focused: bool = False
    selection_state: Dict[str, Any] = field(default_factory=dict)
    inspector_mode: str = "SELECTION"
    recommended_ribbon_tab: str = ""
    canvas_state: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


@dataclass(slots=True)
class CompareSessionPacket:
    compare_session_id: str = ""
    compare_type: str = ""
    left_source_id: str = ""
    right_source_id: str = ""
    variant_ids: List[str] = field(default_factory=list)
    summary_state: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class ModuleMenuPacket:
    menu_id: str
    label: str
    item_ids: List[str] = field(default_factory=list)
    active: bool = False


@dataclass(slots=True)
class NavsysShellStatePacket:
    selected_module: str = "PORTALIS"
    selected_submodule: str = "STUDIO"
    ui_mode: str = "STUDIO"
    selected_item_id: str = ""
    selected_object_id: str = ""
    selected_object_type: str = ""
    selected_workspace_id: str = ""
    selected_file_status: str = ""
    selected_file_action: str = ""
    explorer_active_section: str = "FILE_EXPLORER"
    archive_visible: bool = False
    recent_file_action_result: Dict[str, Any] = field(default_factory=dict)
    pending_file_lifecycle_action: Dict[str, Any] = field(default_factory=dict)
    workspace_snapshot_id: str = ""
    workspace_dirty: bool = False
    restore_candidate_workspace_id: str = ""
    restore_candidate_snapshot_id: str = ""
    selected_task_workspace_id: str = ""
    selected_template_id: str = ""
    selected_template_category: str = ""
    selected_review_item_id: str = ""
    review_mode_enabled: bool = False
    review_filter: str = "all"
    review_session_id: str = ""
    review_pending_count: int = 0
    review_annotation_tool: str = ""
    review_comment_draft: str = ""
    review_signoff_state: Dict[str, Any] = field(default_factory=dict)
    selected_workspace_mode_id: str = "STUDIO"
    selected_layout_profile_id: str = "DEFAULT"
    selected_panel_configuration_id: str = ""
    layout_editor_enabled: bool = False
    layout_editor_dirty: bool = False
    panel_visibility_state: Dict[str, Any] = field(default_factory=dict)
    saved_layout_profiles: List[Dict[str, Any]] = field(default_factory=list)
    workspace_modes: List[Dict[str, Any]] = field(default_factory=list)
    panel_configurations: List[Dict[str, Any]] = field(default_factory=list)
    layout_editor_state: Dict[str, Any] = field(default_factory=dict)
    workspace_mode_switch_pending: bool = False
    template_wizard_step: int = 0
    template_wizard_visible: bool = False
    template_launch_ready: bool = False
    active_task_type: str = ""
    task_stage: str = ""
    task_progress_percent: int = 0
    task_pending_count: int = 0
    task_resume_target: Dict[str, Any] = field(default_factory=dict)
    task_history_visible: bool = True
    slot_assignments: List[Dict[str, Any]] = field(default_factory=list)
    active_workspace_mode: str = "WORKSPACE"
    left_pane_state: str = "MODULE_RAIL"
    right_pane_state: str = "INSPECTOR"
    bottom_pane_tab: str = "CONTEXT"
    layout_mode: str = "COUPLER_WIDE"
    active_menu: str = ""
    active_dropdown: str = ""
    active_dialog: str = ""
    module_options: List[str] = field(default_factory=lambda: list(NAVSYS_MODULES))
    module_subnav: Dict[str, List[str]] = field(default_factory=dict)
    menu_bar: List[Dict[str, Any]] = field(default_factory=list)
    module_actions: List[Dict[str, Any]] = field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = field(default_factory=list)
    dropdown_state: Dict[str, Any] = field(default_factory=dict)
    dialog_state: Dict[str, Any] = field(default_factory=dict)
    command_palette: Dict[str, Any] = field(default_factory=dict)
    pane_state: Dict[str, Any] = field(default_factory=dict)
    keyboard_shortcuts: List[Dict[str, Any]] = field(default_factory=list)
    docking_state: Dict[str, Any] = field(default_factory=dict)
    layout_profile: Dict[str, Any] = field(default_factory=dict)
    partial_refresh: Dict[str, Any] = field(default_factory=dict)
    ribbon_tabs: List[Dict[str, Any]] = field(default_factory=list)
    document_tab_state: Dict[str, Any] = field(default_factory=dict)
    sidebar_sections: List[Dict[str, Any]] = field(default_factory=list)
    bottom_host_tabs: List[Dict[str, Any]] = field(default_factory=list)
    inspector_modes: List[Dict[str, Any]] = field(default_factory=list)
    workspace_registry: List[Dict[str, Any]] = field(default_factory=list)
    task_workspaces: List[Dict[str, Any]] = field(default_factory=list)
    active_task_workspace: Dict[str, Any] = field(default_factory=dict)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    active_template: Dict[str, Any] = field(default_factory=dict)
    template_wizard: Dict[str, Any] = field(default_factory=dict)
    review_items: List[Dict[str, Any]] = field(default_factory=list)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    review_comments: List[Dict[str, Any]] = field(default_factory=list)
    review_session: Dict[str, Any] = field(default_factory=dict)
    review_audit_entries: List[Dict[str, Any]] = field(default_factory=list)
    selection_event: Dict[str, Any] = field(default_factory=dict)
    context_menu_state: Dict[str, Any] = field(default_factory=dict)
    floating_toolbar_state: Dict[str, Any] = field(default_factory=dict)
    object_layer_state: Dict[str, Any] = field(default_factory=dict)
    favorite_tools: Dict[str, Any] = field(default_factory=dict)
    split_view_state: Dict[str, Any] = field(default_factory=dict)
    split_view_enabled: bool = False
    split_view_mode: str = "SINGLE"
    active_pane_id: str = "LEFT"
    pane_contexts: List[Dict[str, Any]] = field(default_factory=list)
    compare_session_id: str = ""
    compare_type: str = ""
    active_compare_sources: Dict[str, str] = field(default_factory=dict)
    inspector_follow_mode: str = "FOLLOW_ACTIVE_PANE"
    workspace_state: Dict[str, Any] = field(default_factory=dict)
    workspace_summary: Dict[str, Any] = field(default_factory=dict)
    status_summary: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


def build_navsys_shell_state(
    *,
    selected_module: str = "PORTALIS",
    selected_submodule: str = "STUDIO",
    ui_mode: str = "STUDIO",
    selected_item_id: str = "",
    selected_object_id: str = "",
    selected_object_type: str = "",
    active_workspace_mode: str = "WORKSPACE",
    left_pane_state: str = "MODULE_RAIL",
    right_pane_state: str = "INSPECTOR",
    bottom_pane_tab: str = "CONTEXT",
    layout_mode: str = "COUPLER_WIDE",
    active_menu: str = "",
    active_dropdown: str = "",
    active_dialog: str = "",
    command_palette_open: bool = False,
    command_palette_query: str = "",
    selected_command_id: str = "",
    left_pane_collapsed: bool = False,
    right_pane_collapsed: bool = False,
    bottom_pane_collapsed: bool = False,
    active_ribbon_tab: str = "",
    open_document_tabs: List[Dict[str, Any]] | None = None,
    active_document_tab_id: str = "",
    split_view_enabled: bool = False,
    split_view_mode: str = "SINGLE",
    split_orientation: str = "VERTICAL",
    active_pane_id: str = "LEFT",
    pane_documents: Dict[str, Any] | None = None,
    compare_session: Dict[str, Any] | None = None,
    inspector_follow_mode: str = "FOLLOW_ACTIVE_PANE",
    selected_file_id: str = "",
    selected_file_status: str = "",
    selected_file_action: str = "",
    explorer_active_section: str = "FILE_EXPLORER",
    archive_visible: bool = False,
    recent_file_action_result: Dict[str, Any] | None = None,
    pending_file_lifecycle_action: Dict[str, Any] | None = None,
    file_entries: List[Dict[str, Any]] | None = None,
    archive_entries: List[Dict[str, Any]] | None = None,
    linked_file_entries: List[Dict[str, Any]] | None = None,
    selected_workspace_id: str = "",
    workspace_snapshot_id: str = "",
    workspace_dirty: bool = False,
    restore_candidate_workspace_id: str = "",
    restore_candidate_snapshot_id: str = "",
    workspace_entries: List[Dict[str, Any]] | None = None,
    selected_task_workspace_id: str = "",
    selected_template_id: str = "",
    selected_template_category: str = "",
    selected_review_item_id: str = "",
    review_mode_enabled: bool = False,
    review_filter: str = "all",
    review_session_id: str = "",
    review_pending_count: int = 0,
    review_annotation_tool: str = "",
    review_comment_draft: str = "",
    review_signoff_state: Dict[str, Any] | None = None,
    selected_workspace_mode_id: str = "STUDIO",
    selected_layout_profile_id: str = "DEFAULT",
    selected_panel_configuration_id: str = "",
    layout_editor_enabled: bool = False,
    layout_editor_dirty: bool = False,
    panel_visibility_state: Dict[str, Any] | None = None,
    saved_layout_profiles: List[Dict[str, Any]] | None = None,
    workspace_modes: List[Dict[str, Any]] | None = None,
    panel_configurations: List[Dict[str, Any]] | None = None,
    layout_editor_state: Dict[str, Any] | None = None,
    workspace_mode_switch_pending: bool = False,
    active_layout_profile: Dict[str, Any] | None = None,
    active_panel_configuration: Dict[str, Any] | None = None,
    template_entries: List[Dict[str, Any]] | None = None,
    active_template: Dict[str, Any] | None = None,
    template_wizard: Dict[str, Any] | None = None,
    review_items: List[Dict[str, Any]] | None = None,
    annotations: List[Dict[str, Any]] | None = None,
    review_comments: List[Dict[str, Any]] | None = None,
    review_session: Dict[str, Any] | None = None,
    review_audit_entries: List[Dict[str, Any]] | None = None,
    task_entries: List[Dict[str, Any]] | None = None,
    active_task_workspace: Dict[str, Any] | None = None,
    task_history_visible: bool = True,
    workspace_summary: Dict[str, Any] | None = None,
    status_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    module_id = _normalize_module(selected_module)
    submodule_id = _normalize_submodule(module_id, selected_submodule)
    selected_item = str(selected_item_id or "")
    selected_object = str(selected_object_id or "")
    selection_state = _derive_selection_state(
        selected_submodule=submodule_id,
        selected_item_id=selected_item,
        selected_object_id=selected_object,
        selected_object_type=selected_object_type,
    )
    normalized_split_mode = str(split_view_mode or "SINGLE").upper()
    split_is_enabled = bool(split_view_enabled) and normalized_split_mode != "SINGLE"
    pane_documents = dict(pane_documents or {})
    active_pane = str(active_pane_id or "LEFT").upper()
    if active_pane not in {"LEFT", "RIGHT"}:
        active_pane = "LEFT"
    left_document_id = str(
        pane_documents.get("LEFT", {}).get("document_id")
        or selected_item
        or active_document_tab_id
        or ""
    )
    right_document_id = str(
        pane_documents.get("RIGHT", {}).get("document_id")
        or ""
    )
    compare_session_packet = _build_compare_session(
        compare_session=dict(compare_session or {}),
        left_document_id=left_document_id,
        right_document_id=right_document_id,
    )
    pane_contexts = _build_pane_contexts(
        split_view_enabled=split_is_enabled,
        active_pane_id=active_pane,
        left_document_id=left_document_id,
        right_document_id=right_document_id,
        selection_state=selection_state,
    )
    workspace_state = asdict(
        ModuleWorkspaceStatePacket(
            module_id=module_id,
            submodule_id=submodule_id,
            selected_item_id=selected_item,
            selected_object_id=selected_object,
            active_workspace_mode=str(active_workspace_mode or "WORKSPACE"),
            left_pane_state="COLLAPSED" if left_pane_collapsed else str(left_pane_state or "BROWSER"),
            right_pane_state="COLLAPSED" if right_pane_collapsed else str(right_pane_state or "INSPECTOR"),
            bottom_pane_tab="HIDDEN" if bottom_pane_collapsed else str(bottom_pane_tab or "CONTEXT"),
            layout_mode=str(layout_mode or "COUPLER_WIDE"),
        )
    )
    pane_state = asdict(
        WorkbenchPaneStatePacket(
            left_pane_collapsed=bool(left_pane_collapsed),
            right_pane_collapsed=bool(right_pane_collapsed),
            bottom_pane_collapsed=bool(bottom_pane_collapsed),
            left_pane_active=not bool(left_pane_collapsed),
            right_pane_active=not bool(right_pane_collapsed),
            bottom_pane_active=not bool(bottom_pane_collapsed),
            pane_sizes={
                "left": "92px" if not left_pane_collapsed else "18px",
                "right": "320px" if not right_pane_collapsed else "0px",
                "bottom": "180px" if not bottom_pane_collapsed else "0px",
            },
        )
    )
    active_layout_profile = dict(active_layout_profile or {})
    active_panel_configuration = dict(active_panel_configuration or {})
    effective_panel_configuration_id = str(
        selected_panel_configuration_id
        or active_panel_configuration.get("panel_configuration_id")
        or active_layout_profile.get("panel_configuration_id")
        or ""
    )
    effective_panel_visibility = dict(
        panel_visibility_state
        or {
            "left_sidebar_visible": not bool(left_pane_collapsed),
            "right_inspector_visible": not bool(right_pane_collapsed),
            "bottom_panel_visible": not bool(bottom_pane_collapsed),
            "command_palette_enabled": True,
            "review_summary_visible": True,
            "task_header_visible": True,
            "compare_summary_visible": bool(compare_session_packet.compare_type),
        }
    )
    packet = NavsysShellStatePacket(
        selected_module=module_id,
        selected_submodule=submodule_id,
        ui_mode=_normalize_ui_mode(ui_mode, submodule_id),
        selected_item_id=selected_item,
        selected_object_id=selected_object,
        selected_object_type=selection_state["selected_object_type"],
        selected_workspace_id=str(selected_workspace_id or ""),
        selected_file_status=str(selected_file_status or ""),
        selected_file_action=str(selected_file_action or ""),
        explorer_active_section=str(explorer_active_section or "FILE_EXPLORER"),
        archive_visible=bool(archive_visible),
        recent_file_action_result=dict(recent_file_action_result or {}),
        pending_file_lifecycle_action=dict(pending_file_lifecycle_action or {}),
        workspace_snapshot_id=str(workspace_snapshot_id or ""),
        workspace_dirty=bool(workspace_dirty),
        restore_candidate_workspace_id=str(restore_candidate_workspace_id or ""),
        restore_candidate_snapshot_id=str(restore_candidate_snapshot_id or ""),
        selected_task_workspace_id=str(selected_task_workspace_id or ""),
        selected_template_id=str(selected_template_id or ""),
        selected_template_category=str(selected_template_category or (active_template or {}).get("category") or ""),
        selected_review_item_id=str(selected_review_item_id or ""),
        review_mode_enabled=bool(review_mode_enabled),
        review_filter=str(review_filter or "all"),
        review_session_id=str(review_session_id or (review_session or {}).get("review_session_id") or ""),
        review_pending_count=int(review_pending_count or (review_session or {}).get("pending_count") or 0),
        review_annotation_tool=str(review_annotation_tool or ""),
        review_comment_draft=str(review_comment_draft or ""),
        review_signoff_state=dict(review_signoff_state or {
            "signed_off": bool((review_session or {}).get("signed_off")),
            "signed_off_at": str((review_session or {}).get("signed_off_at") or ""),
            "status": str((review_session or {}).get("status") or ""),
        }),
        selected_workspace_mode_id=str(selected_workspace_mode_id or "STUDIO"),
        selected_layout_profile_id=str(selected_layout_profile_id or active_layout_profile.get("layout_profile_id") or "DEFAULT"),
        selected_panel_configuration_id=effective_panel_configuration_id,
        layout_editor_enabled=bool(layout_editor_enabled),
        layout_editor_dirty=bool(layout_editor_dirty),
        panel_visibility_state=effective_panel_visibility,
        saved_layout_profiles=list(saved_layout_profiles or []),
        workspace_modes=list(workspace_modes or []),
        panel_configurations=list(panel_configurations or []),
        layout_editor_state=dict(layout_editor_state or {}),
        workspace_mode_switch_pending=bool(workspace_mode_switch_pending),
        template_wizard_step=int((template_wizard or {}).get("current_step") or 0),
        template_wizard_visible=bool(template_wizard),
        template_launch_ready=bool((template_wizard or {}).get("review_ready") or False),
        active_task_type=str((active_task_workspace or {}).get("task_type") or ""),
        task_stage=str((active_task_workspace or {}).get("workflow_stage") or ""),
        task_progress_percent=int((active_task_workspace or {}).get("progress_percent") or 0),
        task_pending_count=len(list((active_task_workspace or {}).get("pending_items") or [])),
        task_resume_target=dict((active_task_workspace or {}).get("resume_target") or {}),
        task_history_visible=bool(task_history_visible),
        slot_assignments=list((active_task_workspace or {}).get("slot_assignments") or []),
        active_workspace_mode=str(active_workspace_mode or "WORKSPACE"),
        left_pane_state=str(left_pane_state or "MODULE_RAIL"),
        right_pane_state=str(right_pane_state or "INSPECTOR"),
        bottom_pane_tab=str(bottom_pane_tab or "CONTEXT"),
        layout_mode=str(layout_mode or "COUPLER_WIDE"),
        active_menu=str(active_menu or ""),
        active_dropdown=str(active_dropdown or ""),
        active_dialog=str(active_dialog or ""),
        module_subnav={
            "DASHBOARD": ["OVERVIEW"],
            "PORTALIS": list(PORTALIS_SUBMODULES),
            "NAVWARN": ["PLANNER"],
            "ASTRANAV": ["WORKSPACE"],
            "SYSTEM": ["STATUS"],
        },
        menu_bar=_build_menu_bar(module_id, submodule_id, active_menu),
        module_actions=[
            asdict(UiActionPacket(action_id="OPEN", label="Open", scope=module_id)),
            asdict(UiActionPacket(action_id="REFRESH", label="Refresh", scope=module_id)),
            asdict(UiActionPacket(action_id="WORKSPACE", label="Workspace", scope=module_id, active=True)),
            asdict(UiActionPacket(action_id="CONTEXT", label="Context", scope=module_id)),
        ],
        quick_actions=[
            asdict(action)
            for action in _build_quick_actions(
                module_id,
                submodule_id,
                active_workspace_mode,
                selected_item,
                selected_object,
            )
        ],
        dropdown_state=asdict(_build_dropdown_state(module_id, submodule_id, active_dropdown)),
        dialog_state=asdict(_build_dialog_state(module_id, submodule_id, active_dialog)),
        command_palette=asdict(
            _build_command_palette_state(
                module_id,
                submodule_id,
                active_workspace_mode,
                selected_item,
                selected_object,
                command_palette_open=command_palette_open,
                command_palette_query=command_palette_query,
                selected_command_id=selected_command_id,
            )
        ),
        pane_state=pane_state,
        keyboard_shortcuts=[
            asdict(KeyboardActionPacket("OPEN_COMMAND_PALETTE", "Ctrl+K", "Open Command Palette", module_id)),
            asdict(KeyboardActionPacket("OPEN_COMMAND_PALETTE_ALT", "Ctrl+P", "Open Command Palette", module_id)),
            asdict(KeyboardActionPacket("CLOSE_ACTIVE_OVERLAY", "Esc", "Close Palette Or Dialog", module_id)),
            asdict(KeyboardActionPacket("FOCUS_LEFT_PANE", "Alt+1", "Focus Left Pane", module_id)),
            asdict(KeyboardActionPacket("FOCUS_CENTER_PANE", "Alt+2", "Focus Center Pane", module_id)),
            asdict(KeyboardActionPacket("FOCUS_RIGHT_PANE", "Alt+3", "Focus Right Pane", module_id)),
            asdict(KeyboardActionPacket("FOCUS_BOTTOM_PANE", "Alt+4", "Focus Bottom Pane", module_id)),
        ],
        docking_state=asdict(
            DockingStatePacket(
                active_docked_window="COMMAND_PALETTE" if command_palette_open else "",
                docking_modes={
                    "COMMAND_PALETTE": ["FLOAT", "RIGHT", "BOTTOM"],
                    "DIALOG": ["FLOAT", "RIGHT", "BOTTOM"],
                },
                default_dock_mode="FLOAT",
            )
        ),
        layout_profile=asdict(
            LayoutProfilePacket(
                profile_id=str(active_layout_profile.get("layout_profile_id") or selected_layout_profile_id or "DEFAULT"),
                layout_profile_id=str(active_layout_profile.get("layout_profile_id") or selected_layout_profile_id or "DEFAULT"),
                name=str(active_layout_profile.get("name") or "Default Layout"),
                workspace_mode_id=str(active_layout_profile.get("workspace_mode_id") or selected_workspace_mode_id or "STUDIO"),
                panel_configuration_id=effective_panel_configuration_id,
                pane_widths={
                    "left": str(active_layout_profile.get("left_width") or pane_state["pane_sizes"]["left"]),
                    "right": str(active_layout_profile.get("right_width") or pane_state["pane_sizes"]["right"]),
                },
                pane_heights={
                    "bottom": str(active_layout_profile.get("bottom_height") or pane_state["pane_sizes"]["bottom"]),
                },
                left_width=str(active_layout_profile.get("left_width") or pane_state["pane_sizes"]["left"]),
                right_width=str(active_layout_profile.get("right_width") or pane_state["pane_sizes"]["right"]),
                bottom_height=str(active_layout_profile.get("bottom_height") or pane_state["pane_sizes"]["bottom"]),
                left_collapsed=bool(active_layout_profile.get("left_collapsed", left_pane_collapsed)),
                right_collapsed=bool(active_layout_profile.get("right_collapsed", right_pane_collapsed)),
                bottom_collapsed=bool(active_layout_profile.get("bottom_collapsed", bottom_pane_collapsed)),
                split_view_state=dict(
                    active_layout_profile.get("split_view_state")
                    or asdict(
                        SplitViewStatePacket(
                            enabled=split_is_enabled,
                            mode=normalized_split_mode,
                            active_pane_id=active_pane,
                            orientation=str(split_orientation or "VERTICAL").upper(),
                            compare_mode=str(compare_session_packet.compare_type or ""),
                            updated_at=utc_now_iso(),
                        )
                    )
                ),
                active_split_mode=str(active_layout_profile.get("active_split_mode") or normalized_split_mode),
                created_at=str(active_layout_profile.get("created_at") or ""),
                updated_at=utc_now_iso(),
                restore_available=True,
            )
        ),
        partial_refresh=asdict(
            PartialRefreshPacket(
                enabled=True,
                client_regions=["COMMAND_PALETTE", "LEFT_PANE", "RIGHT_PANE", "BOTTOM_PANE", "RIBBON", "DOCUMENT_TABS"],
                refresh_reason="Client-side palette, docking, pane state, and document-tab updates reduce full shell redraw friction.",
            )
        ),
        ribbon_tabs=[
            asdict(tab)
            for tab in _build_ribbon_tabs(
                module_id,
                submodule_id,
                active_ribbon_tab,
                selection_state["recommended_ribbon_tab"],
                selection_state["recommended_ribbon_group"],
            )
        ],
        document_tab_state=asdict(
            _build_document_tab_state(
                tabs=list(open_document_tabs or []),
                active_document_tab_id=str(active_document_tab_id or selected_item),
            )
        ),
        sidebar_sections=[
            asdict(section)
            for section in _build_sidebar_sections(
                selected_submodule=submodule_id,
                selected_file_id=str(selected_file_id or selected_item),
                selected_workspace_id=str(selected_workspace_id or submodule_id),
                open_document_tabs=list(open_document_tabs or []),
                file_entries=list(file_entries or []),
                archive_entries=list(archive_entries or []),
                linked_file_entries=list(linked_file_entries or []),
                workspace_entries=list(workspace_entries or []),
                template_entries=list(template_entries or []),
                selected_template_id=str(selected_template_id or ""),
                review_items=list(review_items or []),
                selected_review_item_id=str(selected_review_item_id or ""),
                task_entries=list(task_entries or []),
                selected_task_workspace_id=str(selected_task_workspace_id or ""),
                task_checklist_items=list((active_task_workspace or {}).get("checklist") or []),
                workspace_summary=dict(workspace_summary or {}),
                status_summary=dict(status_summary or {}),
            )
        ],
        bottom_host_tabs=[
            asdict(tab)
            for tab in _build_bottom_host_tabs(
                selected_submodule=submodule_id,
                active_bottom_tab=str(bottom_pane_tab or "CONTEXT"),
            )
        ],
        inspector_modes=[
            asdict(mode)
            for mode in _build_inspector_modes(
                right_pane_collapsed=bool(right_pane_collapsed),
                preferred_mode=selection_state["inspector_mode"],
            )
        ],
        workspace_registry=[
            asdict(packet)
            for packet in _build_workspace_registry(
                selected_submodule=submodule_id,
                selected_file_id=str(selected_file_id or selected_item),
                selected_workspace_id=str(selected_workspace_id or submodule_id),
                open_document_tabs=list(open_document_tabs or []),
                workspace_entries=list(workspace_entries or []),
            )
        ],
        task_workspaces=list(task_entries or []),
        active_task_workspace=dict(active_task_workspace or {}),
        templates=list(template_entries or []),
        active_template=dict(active_template or {}),
        template_wizard=dict(template_wizard or {}),
        review_items=list(review_items or []),
        annotations=list(annotations or []),
        review_comments=list(review_comments or []),
        review_session=dict(review_session or {}),
        review_audit_entries=list(review_audit_entries or []),
        selection_event=asdict(
            SelectionEventPacket(
                event_id="OBJECT_SELECTED" if selected_object else ("DOCUMENT_TAB_ACTIVATED" if active_document_tab_id else ""),
                target_type=selection_state["selected_object_type"],
                target_id=selected_object or str(active_document_tab_id or selected_item),
                selection_context=selection_state["selection_context"],
                selection_bounds=selection_state["selection_bounds"],
                selection_page=selection_state["selection_page"],
                selection_source_document_id=selection_state["selection_source_document_id"],
                recommended_ribbon_tab=selection_state["recommended_ribbon_tab"],
                recommended_ribbon_group=selection_state["recommended_ribbon_group"],
                context_actions=selection_state["context_actions"],
                floating_toolbar_tools=selection_state["floating_toolbar_tools"],
                selection_reason="Selection updates shell state first, then drives inspector, ribbon emphasis, context actions, and floating quick tools.",
                event_scope=submodule_id,
            )
        ),
        context_menu_state=asdict(_build_context_menu_state(selection_state)),
        floating_toolbar_state=asdict(_build_floating_toolbar_state(selection_state)),
        object_layer_state=asdict(
            ObjectLayerStatePacket(
                layer_order=["BASE_DOCUMENT", "ANNOTATIONS", "ANCHORS", "RECONSTRUCTION"],
                visibility={
                    "BASE_DOCUMENT": True,
                    "ANNOTATIONS": True,
                    "ANCHORS": True,
                    "RECONSTRUCTION": submodule_id == "STUDIO",
                },
                lock_state={
                    "BASE_DOCUMENT": False,
                    "ANNOTATIONS": False,
                    "ANCHORS": False,
                    "RECONSTRUCTION": False,
                },
                opacity={
                    "BASE_DOCUMENT": 1.0,
                    "ANNOTATIONS": 0.92,
                    "ANCHORS": 0.96,
                    "RECONSTRUCTION": 0.88,
                },
                object_refs=[selected_object] if selected_object else ([selected_item] if selected_item else []),
            )
        ),
        favorite_tools=asdict(
            FavoriteToolsPacket(
                pinned_ribbon_actions=["OPEN_RECENT", "PANE_VISIBILITY", "WORKBENCH", "REVIEW"],
                pinned_context_actions=["COMMAND_PALETTE", "TOGGLE_RIGHT_PANE", "TOGGLE_BOTTOM_PANE"],
                favorite_workspaces=["STUDIO_DESK", "CONTROL_ROOM_DESK"],
                favorite_templates=[],
            )
        ),
        split_view_state=asdict(
            SplitViewStatePacket(
                enabled=split_is_enabled,
                mode=normalized_split_mode,
                active_pane_id=active_pane,
                orientation=str(split_orientation or "VERTICAL").upper(),
                compare_mode=str(compare_session_packet.compare_type or ""),
                updated_at=utc_now_iso(),
            )
        ),
        split_view_enabled=split_is_enabled,
        split_view_mode=normalized_split_mode,
        active_pane_id=active_pane,
        pane_contexts=[asdict(context) for context in pane_contexts],
        compare_session_id=str(compare_session_packet.compare_session_id or ""),
        compare_type=str(compare_session_packet.compare_type or ""),
        active_compare_sources={
            "LEFT": str(compare_session_packet.left_source_id or left_document_id),
            "RIGHT": str(compare_session_packet.right_source_id or right_document_id),
        },
        inspector_follow_mode=str(inspector_follow_mode or "FOLLOW_ACTIVE_PANE"),
        workspace_state=workspace_state,
        workspace_summary=dict(workspace_summary or {}),
        status_summary=dict(status_summary or {}),
        updated_at=utc_now_iso(),
    )
    return asdict(packet)


def build_navsys_shell_tce_delta(shell_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "HOW": {
            "shell_summary": {
                "selected_module": str(shell_state.get("selected_module") or "PORTALIS"),
                "selected_submodule": str(shell_state.get("selected_submodule") or "STUDIO"),
                "layout_mode": str(shell_state.get("layout_mode") or "COUPLER_WIDE"),
            },
            "menu_summary": {
                "active_menu": str(shell_state.get("active_menu") or ""),
                "active_dropdown": str((shell_state.get("dropdown_state") or {}).get("dropdown_id") or ""),
            },
            "dialog_summary": {
                "active_dialog": str(shell_state.get("active_dialog") or ""),
                "dialog_visible": bool((shell_state.get("dialog_state") or {}).get("visible")),
            },
            "command_summary": {
                "command_palette_open": bool((shell_state.get("command_palette") or {}).get("open")),
                "selected_command_id": str((shell_state.get("command_palette") or {}).get("selected_command_id") or ""),
            },
            "quick_action_summary": {
                "quick_action_count": len(list(shell_state.get("quick_actions") or [])),
                "selected_object_id": str(shell_state.get("selected_object_id") or ""),
            },
            "selection_summary": {
                "selected_object_type": str(shell_state.get("selected_object_type") or ""),
                "recommended_ribbon_tab": str((shell_state.get("selection_event") or {}).get("recommended_ribbon_tab") or ""),
                "inspector_mode": next((mode.get("mode_id") for mode in list(shell_state.get("inspector_modes") or []) if mode.get("active")), ""),
            },
            "layout_summary": dict(shell_state.get("layout_profile") or {}),
            "keyboard_summary": {
                "shortcut_count": len(list(shell_state.get("keyboard_shortcuts") or [])),
                "command_palette_shortcuts": ["Ctrl+K", "Ctrl+P"],
            },
            "ribbon_summary": {
                "active_ribbon_tab": next(
                    (tab.get("ribbon_id") for tab in list(shell_state.get("ribbon_tabs") or []) if tab.get("active")),
                    "",
                ),
            },
            "document_tab_summary": {
                "open_document_tabs": len(list((shell_state.get("document_tab_state") or {}).get("tabs") or [])),
                "active_document_tab_id": str((shell_state.get("document_tab_state") or {}).get("active_document_tab_id") or ""),
            },
            "workspace_persistence_summary": {
                "selected_workspace_id": str(shell_state.get("selected_workspace_id") or ""),
                "workspace_dirty": bool(shell_state.get("workspace_dirty")),
                "snapshot_count": len(list(next((item.get("snapshot_history", []) for item in list(shell_state.get("workspace_registry") or []) if item.get("active")), []))),
            },
            "task_summary": {
                "selected_task_workspace_id": str(shell_state.get("selected_task_workspace_id") or ""),
                "active_task_type": str(shell_state.get("active_task_type") or ""),
                "task_stage": str(shell_state.get("task_stage") or ""),
                "task_progress_percent": int(shell_state.get("task_progress_percent") or 0),
                "task_pending_count": int(shell_state.get("task_pending_count") or 0),
            },
            "template_summary": {
                "selected_template_id": str(shell_state.get("selected_template_id") or ""),
                "selected_template_category": str(shell_state.get("selected_template_category") or ""),
                "template_wizard_visible": bool(shell_state.get("template_wizard_visible")),
                "template_launch_ready": bool(shell_state.get("template_launch_ready")),
            },
            "review_summary": {
                "selected_review_item_id": str(shell_state.get("selected_review_item_id") or ""),
                "review_session_id": str(shell_state.get("review_session_id") or ""),
                "review_pending_count": int(shell_state.get("review_pending_count") or 0),
                "review_mode_enabled": bool(shell_state.get("review_mode_enabled")),
                "review_signoff_state": dict(shell_state.get("review_signoff_state") or {}),
            },
            "context_menu_summary": {
                "menu_id": str((shell_state.get("context_menu_state") or {}).get("menu_id") or ""),
                "target_type": str((shell_state.get("context_menu_state") or {}).get("target_type") or ""),
            },
            "dock_manager_summary": {
                "left_pane_state": str((shell_state.get("workspace_state") or {}).get("left_pane_state") or ""),
                "right_pane_state": str((shell_state.get("workspace_state") or {}).get("right_pane_state") or ""),
                "bottom_pane_tab": str((shell_state.get("workspace_state") or {}).get("bottom_pane_tab") or ""),
            },
            "workspace_summary": dict(shell_state.get("workspace_summary") or {}),
        },
        "WHY": {
            "workspace_mode_reason": {
                "persistent_shell": True,
                "module_navigation": True,
                "pane_driven_application": True,
            },
            "dialog_reason": {
                "advanced_actions_grouped": True,
                "main_panes_kept_clear": True,
            },
            "command_reason": {
                "selection_driven_actions": True,
                "faster_operator_access": True,
            },
            "layout_reason": {
                "persistent_sizes": True,
                "dockable_windows": True,
                "lower_reload_friction": True,
            },
        },
        "WHEN": {
            "workspace_state_updated_at": str(shell_state.get("updated_at") or ""),
            "dialog_opened_at": str((shell_state.get("dialog_state") or {}).get("opened_at") or shell_state.get("updated_at") or ""),
            "command_executed_at": str(shell_state.get("updated_at") or ""),
            "layout_updated_at": str(shell_state.get("updated_at") or ""),
            "document_tab_opened_at": str(
                next(
                    (
                        tab.get("opened_at")
                        for tab in list((shell_state.get("document_tab_state") or {}).get("tabs") or [])
                        if tab.get("active")
                    ),
                    shell_state.get("updated_at") or "",
                )
            ),
        },
    }


def _normalize_module(value: str) -> str:
    module_id = str(value or "PORTALIS").strip().upper()
    if module_id not in NAVSYS_MODULES:
        return "PORTALIS"
    return module_id


def _normalize_submodule(module_id: str, value: str) -> str:
    submodule_id = str(value or "").strip().upper()
    options = {
        "DASHBOARD": ["OVERVIEW"],
        "PORTALIS": PORTALIS_SUBMODULES,
        "NAVWARN": ["PLANNER"],
        "ASTRANAV": ["WORKSPACE"],
        "SYSTEM": ["STATUS"],
    }.get(module_id, ["OVERVIEW"])
    if submodule_id not in options:
        return options[0]
    return submodule_id


def _normalize_ui_mode(value: str, submodule_id: str) -> str:
    allowed = {"STUDIO", "VALIDATION", "PACKAGE", "TASK_EXECUTION", "REVIEW", "BRIDGE_OPS"}
    ui_mode = str(value or "").strip().upper()
    if ui_mode in allowed:
        return ui_mode
    if submodule_id == "STUDIO":
        return "STUDIO"
    if submodule_id == "REVIEW":
        return "REVIEW"
    if submodule_id == "CONTROL_ROOM":
        return "BRIDGE_OPS"
    return "PACKAGE"


def _build_menu_bar(module_id: str, submodule_id: str, active_menu: str) -> List[Dict[str, Any]]:
    menu_groups = {
        "FILE": ["OPEN_RECENT", "OPEN_ARCHIVE", "OPEN_LINKED_DOCUMENT", "OPEN_SOURCE_FILE"],
        "VIEW": ["PANE_VISIBILITY", "LAYOUT_TOGGLES", "INSPECTOR", "CONTEXT", "GRID", "PREVIEW"],
        "MODULE": [submodule_id, "SWITCH"],
        "DOCUMENT": ["PREVIEW", "ARCHIVE", "REVIEW"],
        "EDIT": ["ANNOTATE", "SCRATCHPAD", "RECONSTRUCT"],
        "TOOLS": ["FILTERS", "MAPPING", "BRIDGE"],
        "WORKSPACES": ["SAVE_WORKSPACE", "LOAD_WORKSPACE", "SAVE_SNAPSHOT", "RESTORE_SESSION"],
        "TASKS": ["NEW_TASK_WORKSPACE", "RESUME_TASK_WORKSPACE", "MARK_TASK_COMPLETE", "SAVE_TASK_CHECKPOINT"],
        "WINDOW": ["DIALOGS", "PANES"],
        "HELP": ["ABOUT", "STATUS"],
    }
    return [
        asdict(
            ModuleMenuPacket(
                menu_id=menu_id,
                label=menu_id.title(),
                item_ids=item_ids,
                active=str(active_menu or "").upper() == menu_id,
            )
        )
        for menu_id, item_ids in menu_groups.items()
    ]


def _build_dropdown_state(module_id: str, submodule_id: str, active_dropdown: str) -> UiDropdownStatePacket:
    dropdown_id = str(active_dropdown or "").strip().upper()
    dropdown_map = {
        "FILE": ("Open", "FILE", ["OPEN_RECENT", "OPEN_ARCHIVE", "OPEN_LINKED_DOCUMENT", "OPEN_SOURCE_FILE"]),
        "VIEW": ("View", "VIEW", ["LEFT_PANE", "RIGHT_PANE", "BOTTOM_PANE", "GRID", "PREVIEW", "INSPECTOR", "CONTEXT"]),
        "DOCUMENT": ("Document", "DOCUMENT", ["OPEN_SOURCE", "PREVIEW", "PROPERTIES", "HISTORY"]),
        "OBJECT": ("Object", "EDIT", ["SELECTED_ACTIONS", "LINKS", "DELETE", "LABEL"]),
        "QUEUE": ("Queue", "CONTROL_ROOM", ["QUEUE", "ALERTS", "INCIDENTS", "WATCH", "BRIDGE"]),
        "STUDIO": ("Studio", "STUDIO", ["OPEN", "PREVIEW", "ANNOTATE", "SCRATCHPAD", "RECONSTRUCT", "MAP"]),
        "WORKSPACES": ("Workspaces", "WORKSPACES", ["NEW_WORKSPACE", "SAVE_WORKSPACE", "SAVE_WORKSPACE_AS", "LOAD_WORKSPACE", "SAVE_SNAPSHOT", "RESTORE_LAST_SESSION", "RECOVER_AUTOSAVE"]),
        "TASKS": ("Tasks", "TASKS", ["NEW_TASK_WORKSPACE", "START_TASK_WORKSPACE", "LOAD_TASK_WORKSPACE", "RESUME_TASK_WORKSPACE", "MARK_TASK_COMPLETE", "SAVE_TASK_CHECKPOINT"]),
    }
    if dropdown_id not in dropdown_map:
        return UiDropdownStatePacket()
    label, menu_group, item_ids = dropdown_map[dropdown_id]
    return UiDropdownStatePacket(
        dropdown_id=dropdown_id,
        label=label,
        menu_group=menu_group,
        item_ids=item_ids,
        active=True,
    )


def _build_ribbon_tabs(
    module_id: str,
    submodule_id: str,
    active_ribbon_tab: str,
    recommended_ribbon_tab: str,
    recommended_ribbon_group: str,
) -> List[RibbonTabStatePacket]:
    default_ribbon = str(active_ribbon_tab or "").strip().upper()
    if not default_ribbon:
        default_ribbon = "STUDIO" if submodule_id == "STUDIO" else "HOME"
    ribbon_map = {
        "HOME": ["Open", "Recent", "Selection"],
        "LAYOUT": ["Pane Visibility", "Inspector", "Context", "Preview", "Grid"],
        "DATA": ["Archive", "Open Linked", "Scratchpad", "Mappings"],
        "TCE": ["TCE", "Audit", "Context"],
        "DYNAMICS": ["Alerts", "Incidents", "Watch", "Reminder"],
        "STUDIO": ["Workbench", "Annotate", "Reconstruct", "Properties"],
        "INSERT": ["Annotation", "Anchor", "Cell", "Block"],
        "VARIANTS": ["Profiles", "Layouts", "Views"],
        "QTR": ["Mapping", "Bridge", "Output"],
        "WORKSPACES": ["Save", "Load", "Restore", "Snapshot"],
        "TASKS": ["Task Status", "Checklist", "Resume"],
        "TEMPLATES": ["Template Save", "Template Load", "Wizard"],
        "HELP": ["Guide", "Status", "About"],
    }
    return [
        RibbonTabStatePacket(
            ribbon_id=ribbon_id,
            label=ribbon_id.title(),
            tool_groups=tool_groups,
            active=ribbon_id == default_ribbon,
            recommended=ribbon_id == str(recommended_ribbon_tab or "").strip().upper() and ribbon_id != default_ribbon,
            recommended_group=recommended_ribbon_group if ribbon_id == str(recommended_ribbon_tab or "").strip().upper() else "",
        )
        for ribbon_id, tool_groups in ribbon_map.items()
    ]


def _build_document_tab_state(*, tabs: List[Dict[str, Any]], active_document_tab_id: str) -> DocumentTabStatePacket:
    normalized_tabs: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    active_id = str(active_document_tab_id or "")
    for raw_tab in tabs:
        tab_id = str(raw_tab.get("tab_id") or raw_tab.get("document_id") or "").strip()
        if not tab_id or tab_id in seen_ids:
            continue
        seen_ids.add(tab_id)
        packet = DocumentTabPacket(
            tab_id=tab_id,
            document_id=str(raw_tab.get("document_id") or tab_id),
            label=str(raw_tab.get("label") or raw_tab.get("document_id") or tab_id),
            source_lane=str(raw_tab.get("source_lane") or "STUDIO"),
            active=tab_id == active_id,
            closable=bool(raw_tab.get("closable", True)),
            pinned=bool(raw_tab.get("pinned", False)),
            opened_at=str(raw_tab.get("opened_at") or utc_now_iso()),
        )
        normalized_tabs.append(asdict(packet))
    if not active_id and normalized_tabs:
        normalized_tabs[0]["active"] = True
        active_id = str(normalized_tabs[0]["tab_id"])
    return DocumentTabStatePacket(
        tabs=normalized_tabs,
        active_document_tab_id=active_id,
        tab_order=[str(tab.get("tab_id") or "") for tab in normalized_tabs],
        pinned_tabs=[str(tab.get("tab_id") or "") for tab in normalized_tabs if tab.get("pinned")],
        tab_groups=[{"group_id": "PRIMARY", "label": "Primary View", "tab_ids": [str(tab.get("tab_id") or "") for tab in normalized_tabs]}],
    )


def _build_sidebar_sections(
    *,
    selected_submodule: str,
    selected_file_id: str,
    selected_workspace_id: str,
    open_document_tabs: List[Dict[str, Any]],
    file_entries: List[Dict[str, Any]],
    archive_entries: List[Dict[str, Any]],
    linked_file_entries: List[Dict[str, Any]],
    workspace_entries: List[Dict[str, Any]],
    template_entries: List[Dict[str, Any]],
    selected_template_id: str,
    review_items: List[Dict[str, Any]],
    selected_review_item_id: str,
    task_entries: List[Dict[str, Any]],
    selected_task_workspace_id: str,
    task_checklist_items: List[Dict[str, Any]],
    workspace_summary: Dict[str, Any],
    status_summary: Dict[str, Any],
) -> List[SidebarSectionPacket]:
    open_items = [
        {
            "item_id": str(entry.get("file_id") or ""),
            "label": str(entry.get("display_name") or entry.get("file_id") or "Document"),
            "active": (
                str(entry.get("file_id") or "") == selected_file_id
                or any(str(instance.get("document_id") or "") == selected_file_id for instance in list(entry.get("instances") or []))
            ),
            "file_type": str(entry.get("file_type") or ""),
            "status": str(entry.get("status") or "ACTIVE"),
            "workspace_membership": list(entry.get("workspace_membership") or []),
            "opened_in_tabs": bool(entry.get("opened_in_tabs")),
            "default_document_id": str(entry.get("default_document_id") or ""),
            "instance_count": int(entry.get("instance_count") or 0),
            "instances": list(entry.get("instances") or []),
            "source_path": str(entry.get("source_path") or ""),
            "linked": bool(entry.get("linked")),
            "archived": bool(entry.get("archived")),
        }
        for entry in file_entries
    ]
    workspace_items = [
        {
            "item_id": str(entry.get("workspace_id") or ""),
            "label": str(entry.get("name") or entry.get("workspace_id") or "Workspace"),
            "active": str(entry.get("workspace_id") or "") == selected_workspace_id,
            "snapshot_count": len(list(entry.get("snapshot_history", []) or [])),
        }
        for entry in workspace_entries
    ] or [
        {"item_id": "STUDIO", "label": "Studio Workspace", "active": selected_workspace_id == "STUDIO", "snapshot_count": 0},
        {"item_id": "CONTROL_ROOM", "label": "Control Room Workspace", "active": selected_workspace_id == "CONTROL_ROOM", "snapshot_count": 0},
    ]
    task_items = [
        {
            "item_id": str(entry.get("task_workspace_id") or ""),
            "label": str(entry.get("name") or entry.get("task_workspace_id") or "Task Workspace"),
            "active": str(entry.get("task_workspace_id") or "") == selected_task_workspace_id,
            "progress": int(entry.get("progress_percent") or 0),
            "pending_count": len(list(entry.get("pending_items") or [])),
        }
        for entry in task_entries
    ] or [{"item_id": "NO_TASK", "label": "No active task workspaces", "active": False, "progress": 0, "pending_count": 0}]
    template_items = [
        {
            "item_id": str(entry.get("template_id") or ""),
            "label": str(entry.get("name") or entry.get("template_id") or "Template"),
            "active": str(entry.get("template_id") or "") == selected_template_id,
            "category": str(entry.get("category") or ""),
            "task_type": str(entry.get("task_type") or ""),
            "slot_count": len(list(entry.get("slot_definitions") or [])),
            "favorite": bool(entry.get("favorite")),
        }
        for entry in template_entries
    ] or [{"item_id": "NO_TEMPLATE", "label": "No templates saved", "active": False, "category": "", "task_type": "", "slot_count": 0, "favorite": False}]
    review_sidebar_items = [
        {
            "item_id": str(entry.get("review_item_id") or ""),
            "label": str(entry.get("title") or entry.get("review_item_id") or "Review Item"),
            "active": str(entry.get("review_item_id") or "") == selected_review_item_id,
            "status": str(entry.get("status") or "OPEN"),
            "severity": str(entry.get("severity") or "MEDIUM"),
            "pane_id": str(entry.get("pane_id") or ""),
        }
        for entry in review_items
    ] or [{"item_id": "REVIEW_EMPTY", "label": "No review items", "active": False, "status": "", "severity": "", "pane_id": ""}]
    linked_items = [
        {
            "item_id": str(entry.get("file_id") or ""),
            "label": str(entry.get("display_name") or entry.get("file_id") or "Linked File"),
            "active": (
                str(entry.get("file_id") or "") == selected_file_id
                or any(str(instance.get("document_id") or "") == selected_file_id for instance in list(entry.get("instances") or []))
            ),
            "file_type": str(entry.get("file_type") or ""),
            "status": str(entry.get("status") or "LINKED"),
            "default_document_id": str(entry.get("default_document_id") or ""),
            "instance_count": int(entry.get("instance_count") or 0),
            "instances": list(entry.get("instances") or []),
            "source_path": str(entry.get("source_path") or ""),
        }
        for entry in linked_file_entries
    ] or [{"item_id": "LINKED_NONE", "label": "No linked files in focus", "active": False, "file_type": "", "status": ""}]
    archive_items = [
        {
            "item_id": str(entry.get("file_id") or ""),
            "label": str(entry.get("display_name") or entry.get("file_id") or "Archived File"),
            "active": (
                str(entry.get("file_id") or "") == selected_file_id
                or any(str(instance.get("document_id") or "") == selected_file_id for instance in list(entry.get("instances") or []))
            ),
            "file_type": str(entry.get("file_type") or ""),
            "status": str(entry.get("status") or "ARCHIVED"),
            "default_document_id": str(entry.get("default_document_id") or ""),
            "instance_count": int(entry.get("instance_count") or 0),
            "instances": list(entry.get("instances") or []),
            "source_path": str(entry.get("source_path") or ""),
        }
        for entry in archive_entries
    ] or [{"item_id": "ARCHIVE_EMPTY", "label": "No archived files", "active": False, "file_type": "", "status": "ARCHIVED"}]
    return [
        SidebarSectionPacket("WORKSPACES", "Workspaces", "DESK", True, len(workspace_items), workspace_items),
        SidebarSectionPacket("TASK_WORKSPACES", "Task Workspaces", "TASK", True, len(task_items), task_items),
        SidebarSectionPacket("TEMPLATES", "Templates", "TPL", True, len(template_items), template_items),
        SidebarSectionPacket("REVIEW_ITEMS", "Review Items", "RVW", True, len(review_sidebar_items), review_sidebar_items),
        SidebarSectionPacket("FILE_EXPLORER", "File Explorer", "FILE", True, len(open_items), open_items or [{"item_id": "NO_FILE", "label": "No active files in this workspace", "active": False, "file_type": "", "status": ""}]),
        SidebarSectionPacket("LINKED_FILES", "Linked Files", "LINK", False, len(linked_items), linked_items),
        SidebarSectionPacket("ARCHIVE", "Archive", "ARCH", selected_submodule == "ARCHIVE", len(archive_items), archive_items),
        SidebarSectionPacket("VARIANTS", "Variants", "VAR", False, 1, [{"item_id": "VARIANT_HOST", "label": "Variant host scaffold", "active": False}]),
        SidebarSectionPacket("CONTEXT_FILES", "Context Files", "CTX", False, 1, [{"item_id": "CONTEXT_NONE", "label": "No context files pinned", "active": False}]),
        SidebarSectionPacket("TASK_CHECKLIST", "Task Checklist", "CHK", True, len(task_checklist_items), task_checklist_items or [{"item_id": "CHECKLIST_EMPTY", "label": "No active task checklist", "active": False}]),
    ]


def _build_bottom_host_tabs(*, selected_submodule: str, active_bottom_tab: str) -> List[BottomHostTabPacket]:
    tab_ids = [
        ("STATUS", "Status"),
        ("REVIEW", "Review"),
        ("LOG", "Log"),
        ("OUTPUT", "Output"),
        ("TASK_PROGRESS", "Task Progress"),
        ("SNAPSHOT_HISTORY", "Snapshot History"),
    ]
    normalized_active = str(active_bottom_tab or "").strip().upper()
    if not normalized_active:
        normalized_active = "REVIEW" if selected_submodule == "REVIEW" else "STATUS"
    if normalized_active not in {tab_id for tab_id, _label in tab_ids}:
        normalized_active = "REVIEW" if selected_submodule == "REVIEW" else "STATUS"
    return [
        BottomHostTabPacket(tab_id=tab_id, label=label, active=tab_id == normalized_active)
        for tab_id, label in tab_ids
    ]


def _build_inspector_modes(*, right_pane_collapsed: bool, preferred_mode: str) -> List[InspectorModePacket]:
    active_mode = str(preferred_mode or "SELECTION").strip().upper()
    if active_mode not in {"SELECTION", "VALIDATION", "TCE", "RELATIONS", "FILE_LIFECYCLE"}:
        active_mode = "SELECTION"
    return [
        InspectorModePacket("SELECTION", "Selection Inspector", active_mode == "SELECTION"),
        InspectorModePacket("VALIDATION", "Validation Inspector", active_mode == "VALIDATION"),
        InspectorModePacket("TCE", "TCE Inspector", active_mode == "TCE"),
        InspectorModePacket("RELATIONS", "Relations Inspector", active_mode == "RELATIONS"),
        InspectorModePacket("FILE_LIFECYCLE", "File Lifecycle Inspector", active_mode == "FILE_LIFECYCLE"),
    ]


def _build_workspace_registry(
    *,
    selected_submodule: str,
    selected_file_id: str,
    selected_workspace_id: str,
    open_document_tabs: List[Dict[str, Any]],
    workspace_entries: List[Dict[str, Any]],
) -> List[WorkspacePacket]:
    if workspace_entries:
        packets: List[WorkspacePacket] = []
        for entry in workspace_entries:
            workspace_id = str(entry.get("workspace_id") or "")
            packets.append(
                WorkspacePacket(
                    workspace_id=workspace_id,
                    label=str(entry.get("name") or workspace_id or "Workspace"),
                    name=str(entry.get("name") or workspace_id or "Workspace"),
                    workspace_type=str(entry.get("workspace_type") or "WORKSPACE"),
                    active=workspace_id == selected_workspace_id,
                    ui_mode=str(entry.get("ui_mode") or "STUDIO"),
                    open_tabs=list(entry.get("open_tabs", [])),
                    tab_order=list(entry.get("tab_order", [])),
                    active_document_tab_id=str(entry.get("active_document_tab_id") or ""),
                    pinned_tabs=list(entry.get("pinned_tabs", [])),
                    tab_groups=list(entry.get("tab_groups", [])),
                    layout_profile_id=str(entry.get("layout_profile_id") or "DEFAULT"),
                    linked_context_files=list(entry.get("linked_context_files", [])),
                    selected_file_id=str(entry.get("selected_file_id") or selected_file_id),
                    selected_workspace_id=str(selected_workspace_id or ""),
                    open_tab_ids=[str(item.get("tab_id") or "") for item in list(entry.get("open_tabs", []))],
                    active_ribbon_tab=str(entry.get("active_ribbon_tab") or ""),
                    left_pane_state=str(entry.get("left_pane_state") or ""),
                    right_pane_state=str(entry.get("right_pane_state") or ""),
                    bottom_pane_state=str(entry.get("bottom_pane_state") or ""),
                    left_section_state=dict(entry.get("left_section_state", {})),
                    favorites=dict(entry.get("favorites", {})),
                    snapshot_history=list(entry.get("snapshot_history", [])),
                    autosave_enabled=bool(entry.get("autosave_enabled", True)),
                    created_at=str(entry.get("created_at") or ""),
                    updated_at=str(entry.get("updated_at") or ""),
                )
            )
        return packets
    workspaces = [
        WorkspacePacket(
            workspace_id="STUDIO",
            label="Studio Workspace",
            name="Studio Workspace",
            workspace_type="WORKSPACE",
            active=selected_workspace_id in {"", "STUDIO"} and selected_submodule == "STUDIO",
            selected_file_id=selected_file_id,
            selected_workspace_id=selected_workspace_id,
            open_tab_ids=[str(tab.get("tab_id") or "") for tab in open_document_tabs],
            open_tabs=list(open_document_tabs),
            tab_order=[str(tab.get("tab_id") or "") for tab in open_document_tabs],
            active_document_tab_id=selected_file_id,
        ),
        WorkspacePacket(
            workspace_id="CONTROL_ROOM",
            label="Control Room Workspace",
            name="Control Room Workspace",
            workspace_type="WORKSPACE",
            active=selected_submodule == "CONTROL_ROOM",
            selected_file_id=selected_file_id,
            selected_workspace_id=selected_workspace_id,
            open_tab_ids=[str(tab.get("tab_id") or "") for tab in open_document_tabs],
            open_tabs=list(open_document_tabs),
            tab_order=[str(tab.get("tab_id") or "") for tab in open_document_tabs],
            active_document_tab_id=selected_file_id,
        ),
    ]
    return workspaces


def _derive_selection_state(
    *,
    selected_submodule: str,
    selected_item_id: str,
    selected_object_id: str,
    selected_object_type: str,
) -> Dict[str, Any]:
    normalized_type = str(selected_object_type or "").strip().upper()
    if not normalized_type:
        if str(selected_object_id).startswith("ANCHOR"):
            normalized_type = "FIELD"
        elif str(selected_object_id).startswith("CELL"):
            normalized_type = "CELL"
        elif str(selected_object_id).startswith("BLOCK"):
            normalized_type = "TABLE"
        elif selected_submodule == "REVIEW" and selected_item_id:
            normalized_type = "REVIEW_ISSUE"
        elif selected_item_id:
            normalized_type = "DOCUMENT"
        else:
            normalized_type = "EMPTY_PAGE"

    ribbon_map = {
        "TEXT": ("HOME", "Font"),
        "CELL": ("DATA", "Formula"),
        "TABLE": ("LAYOUT", "Field Map"),
        "IMAGE": ("STUDIO", "Layer"),
        "FIELD": ("LAYOUT", "Field Map"),
        "DYNAMIC_FIELD": ("DYNAMICS", "Dynamic Fields"),
        "TCE_REGION": ("TCE", "Context"),
        "REVIEW_ISSUE": ("REVIEW", "Comments"),
        "EMPTY_PAGE": ("STUDIO", "Canvas"),
        "FILE_EXPLORER_ITEM": ("FILE", "Open"),
        "WORKSPACE_ITEM": ("WORKSPACES", "Workspace"),
        "TEMPLATE_ITEM": ("TEMPLATES", "Template"),
        "DOCUMENT": ("STUDIO", "Workbench"),
    }
    inspector_map = {
        "TEXT": "SELECTION",
        "CELL": "SELECTION",
        "TABLE": "SELECTION",
        "IMAGE": "SELECTION",
        "FIELD": "RELATIONS",
        "DYNAMIC_FIELD": "RELATIONS",
        "TCE_REGION": "TCE",
        "REVIEW_ISSUE": "VALIDATION",
        "FILE_EXPLORER_ITEM": "FILE_LIFECYCLE",
        "WORKSPACE_ITEM": "FILE_LIFECYCLE",
        "TEMPLATE_ITEM": "FILE_LIFECYCLE",
        "EMPTY_PAGE": "SELECTION",
        "DOCUMENT": "SELECTION",
    }
    toolbar_map = {
        "TEXT": ["BOLD", "ITALIC", "UNDERLINE", "FONT_COLOR", "HIGHLIGHT", "DELETE"],
        "CELL": ["EDIT", "FORMULA", "FILL", "BORDER", "MERGE", "DELETE"],
        "TABLE": ["EDIT", "FORMULA", "FILL", "BORDER", "SPLIT", "DELETE"],
        "IMAGE": ["MOVE", "RESIZE", "FRONT", "BACK", "WATERMARK", "DELETE"],
        "FIELD": ["EDIT", "LINK", "VALIDATION", "CLONE", "DELETE"],
        "DYNAMIC_FIELD": ["EDIT", "LINK", "VALIDATION", "CLONE", "DELETE"],
        "TCE_REGION": ["INFER", "VALIDATE", "APPROVE", "REJECT"],
        "REVIEW_ISSUE": ["COMMENT", "APPROVE", "REJECT", "RESTORE"],
        "DOCUMENT": ["OPEN", "PREVIEW", "PROPERTIES", "LINK"],
        "EMPTY_PAGE": ["INSERT_TEXT", "INSERT_TABLE", "INSERT_IMAGE", "GRID"],
    }
    context_map = {
        "TEXT": ["EDIT_TEXT", "BOLD", "ITALIC", "DELETE"],
        "CELL": ["EDIT_VALUE", "FORMULA", "MERGE_CELLS", "DELETE"],
        "TABLE": ["FORMAT_CELL", "SPLIT_CELLS", "VALIDATION_RULES", "DELETE"],
        "IMAGE": ["MOVE", "RESIZE", "OCR_ANALYZE_REGION", "DELETE"],
        "FIELD": ["EDIT_FIELD", "MAP_TO_SOURCE", "VIEW_FIELD_LINEAGE", "DELETE"],
        "DYNAMIC_FIELD": ["EDIT_DYNAMIC_FIELD", "REFRESH_SOURCE", "VALIDATION", "DELETE"],
        "TCE_REGION": ["INFER_MISSING_DATA", "VALIDATE_AGAINST_CONTEXT", "REQUIRE_APPROVAL", "REJECT_SUGGESTION"],
        "EMPTY_PAGE": ["INSERT_TEXT", "INSERT_TABLE", "INSERT_IMAGE", "GRID_SETTINGS"],
        "FILE_EXPLORER_ITEM": ["OPEN", "OPEN_IN_NEW_TAB", "DUPLICATE", "DELETE"],
        "WORKSPACE_ITEM": ["LOAD", "RENAME", "DUPLICATE", "DELETE"],
        "TEMPLATE_ITEM": ["NEW_TASK_FROM_TEMPLATE", "EDIT_TEMPLATE", "EXPORT_TEMPLATE", "ARCHIVE"],
        "REVIEW_ISSUE": ["COMMENTS", "APPROVAL", "REJECT", "VIEW_HISTORY"],
        "DOCUMENT": ["OPEN_LINKED_DOCUMENT", "OPEN_SOURCE_FILE", "PREVIEW", "HISTORY"],
    }
    recommended_ribbon_tab, recommended_ribbon_group = ribbon_map.get(normalized_type, ("HOME", "Selection"))
    return {
        "selected_object_type": normalized_type,
        "selection_context": {"submodule": selected_submodule, "active_document_id": selected_item_id},
        "selection_bounds": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},
        "selection_page": 1,
        "selection_source_document_id": selected_item_id,
        "inspector_mode": inspector_map.get(normalized_type, "SELECTION"),
        "recommended_ribbon_tab": recommended_ribbon_tab,
        "recommended_ribbon_group": recommended_ribbon_group,
        "context_actions": context_map.get(normalized_type, ["OPEN", "DELETE"]),
        "floating_toolbar_tools": toolbar_map.get(normalized_type, ["OPEN", "DELETE"]),
    }


def _build_compare_session(
    *,
    compare_session: Dict[str, Any],
    left_document_id: str,
    right_document_id: str,
) -> CompareSessionPacket:
    compare_type = str(compare_session.get("compare_type") or ("DOCUMENT_COMPARE" if left_document_id and right_document_id else ""))
    return CompareSessionPacket(
        compare_session_id=str(compare_session.get("compare_session_id") or ("COMPARE_SESSION_ACTIVE" if compare_type else "")),
        compare_type=compare_type,
        left_source_id=str(compare_session.get("left_source_id") or left_document_id),
        right_source_id=str(compare_session.get("right_source_id") or right_document_id),
        variant_ids=list(compare_session.get("variant_ids") or []),
        summary_state=dict(compare_session.get("summary_state") or {
            "active": bool(compare_type),
            "left_label": left_document_id,
            "right_label": right_document_id,
            "session_summary": "Side-by-side compare ready." if compare_type else "Single-pane workspace.",
        }),
        created_at=str(compare_session.get("created_at") or utc_now_iso()),
        updated_at=str(compare_session.get("updated_at") or utc_now_iso()),
    )


def _build_pane_contexts(
    *,
    split_view_enabled: bool,
    active_pane_id: str,
    left_document_id: str,
    right_document_id: str,
    selection_state: Dict[str, Any],
) -> List[PaneContextPacket]:
    pane_packets: List[PaneContextPacket] = []
    pane_documents = {"LEFT": left_document_id, "RIGHT": right_document_id}
    for pane_id in ["LEFT", "RIGHT"]:
        document_id = str(pane_documents.get(pane_id) or "")
        if pane_id == "RIGHT" and not split_view_enabled and not document_id:
            document_id = ""
        pane_selection = dict(selection_state if pane_id == active_pane_id else {})
        pane_packets.append(
            PaneContextPacket(
                pane_id=pane_id,
                document_tab_id=document_id,
                document_id=document_id,
                focused=pane_id == active_pane_id,
                selection_state=pane_selection,
                inspector_mode=str(pane_selection.get("inspector_mode") or "SELECTION"),
                recommended_ribbon_tab=str(pane_selection.get("recommended_ribbon_tab") or ""),
                canvas_state={
                    "visible": pane_id == "LEFT" or split_view_enabled,
                    "compare_ready": split_view_enabled,
                    "status": "READY" if document_id else "EMPTY",
                },
                updated_at=utc_now_iso(),
            )
        )
    return pane_packets


def _action_packet(action_id: str, label: str, *, enabled: bool = True) -> Dict[str, Any]:
    return {"action_id": action_id, "label": label, "enabled": enabled}


def _build_context_menu_state(selection_state: Dict[str, Any]) -> ContextMenuStatePacket:
    target_type = str(selection_state.get("selected_object_type") or "")
    target_id = str(selection_state.get("selection_source_document_id") or "")
    quick_actions = {
        "TEXT": [_action_packet("EDIT_TEXT", "Edit text"), _action_packet("CLONE", "Clone"), _action_packet("DELETE", "Delete")],
        "CELL": [_action_packet("EDIT_VALUE", "Edit value"), _action_packet("FORMULA", "Formula"), _action_packet("DELETE", "Delete")],
        "TABLE": [_action_packet("EDIT_VALUE", "Edit value"), _action_packet("MERGE_CELLS", "Merge cells"), _action_packet("DELETE", "Delete")],
        "IMAGE": [_action_packet("MOVE", "Move"), _action_packet("RESIZE", "Resize"), _action_packet("DELETE", "Delete")],
        "FIELD": [_action_packet("EDIT_FIELD", "Edit field"), _action_packet("MAP_TO_SOURCE", "Map to source"), _action_packet("DELETE", "Delete")],
        "DYNAMIC_FIELD": [_action_packet("EDIT_DYNAMIC_FIELD", "Edit dynamic field"), _action_packet("REFRESH_SOURCE", "Refresh source"), _action_packet("DELETE", "Delete")],
        "TCE_REGION": [_action_packet("INFER", "Infer"), _action_packet("VALIDATE", "Validate"), _action_packet("REJECT", "Reject")],
        "EMPTY_PAGE": [_action_packet("INSERT_TEXT", "Insert text"), _action_packet("INSERT_TABLE", "Insert table"), _action_packet("INSERT_IMAGE", "Insert image")],
        "FILE_EXPLORER_ITEM": [_action_packet("OPEN", "Open"), _action_packet("OPEN_IN_NEW_TAB", "Open in new tab"), _action_packet("DELETE", "Delete")],
        "WORKSPACE_ITEM": [_action_packet("LOAD", "Load"), _action_packet("PIN", "Pin"), _action_packet("DELETE", "Delete")],
        "TEMPLATE_ITEM": [_action_packet("NEW_TASK_FROM_TEMPLATE", "New task from template"), _action_packet("EDIT_TEMPLATE", "Edit template"), _action_packet("DELETE", "Delete")],
        "REVIEW_ISSUE": [_action_packet("COMMENTS", "Comments"), _action_packet("APPROVAL", "Approval"), _action_packet("REJECT", "Reject")],
        "DOCUMENT": [_action_packet("OPEN", "Open"), _action_packet("PREVIEW", "Preview"), _action_packet("PROPERTIES", "Properties")],
    }.get(target_type, [_action_packet("OPEN", "Open"), _action_packet("DELETE", "Delete")])
    object_action_ids = {
        "TEXT": ["BOLD", "ITALIC", "UNDERLINE", "FONT_COLOR", "HIGHLIGHT", "ALIGNMENT", "PARAGRAPH_SETTINGS", "ROTATE", "SAVE_STYLE_PRESET", "LOCK_OBJECT"],
        "CELL": ["FORMAT_CELL", "BORDERS", "FILL_COLOR", "MERGE_CELLS", "SPLIT_CELLS", "INSERT_ROW", "INSERT_COLUMN", "DELETE_ROW", "DELETE_COLUMN", "VALIDATION_RULES", "CONVERT_TO_LINKED_FIELD"],
        "TABLE": ["FORMAT_CELL", "BORDERS", "FILL_COLOR", "MERGE_CELLS", "SPLIT_CELLS", "INSERT_ROW", "INSERT_COLUMN", "DELETE_ROW", "DELETE_COLUMN", "VALIDATION_RULES", "CONVERT_TO_LINKED_FIELD"],
        "IMAGE": ["ROTATE", "CROP", "TRANSPARENCY", "SEND_TO_FRONT", "SEND_TO_BACK", "MAKE_WATERMARK", "LOCK_LAYER", "OCR_ANALYZE_REGION", "CONVERT_TO_ANCHOR_REGION"],
        "FIELD": ["RENAME", "LINK_DATA_SOURCE", "SET_DYNAMIC_VALUE", "SET_VALIDATION", "ADD_RELATION", "CLONE_FIELD", "CREATE_REPEATING_FIELD", "ADD_CHILD_FIELD", "VIEW_FIELD_LINEAGE", "SHOW_LINKED_SOURCES"],
        "DYNAMIC_FIELD": ["VIEW_PARENT_CHILD_LINKS", "SET_UPDATE_BEHAVIOR", "VALIDATION", "CONVERT_ADAPT"],
        "TCE_REGION": ["SCAN_DISCREPANCY", "VIEW_CONTEXT_TREE", "OPEN_CONTEXTLOAF", "ADD_SUPPORTING_FILE", "REQUIRE_APPROVAL", "APPROVE_INFERRED_VALUE"],
        "EMPTY_PAGE": ["INSERT_CHECKBOX", "INSERT_ANNOTATION", "INSERT_CREW_LIST", "INSERT_GRAPH", "ADD_PAGE", "CLONE_PAGE", "PAGE_LAYOUT", "PRINT_SETTINGS", "WATERMARK", "GRID_SETTINGS"],
        "FILE_EXPLORER_ITEM": ["DUPLICATE", "RENAME", "LINK_TO_ACTIVE_DOCUMENT", "ADD_AS_CONTEXT_SOURCE", "ADD_TO_TCE", "CONVERT_VARIANT", "EXPORT", "MOVE_TO_ARCHIVE", "RESTORE_PREVIOUS_VERSION"],
        "WORKSPACE_ITEM": ["RENAME", "DUPLICATE", "SET_DEFAULT"],
        "TEMPLATE_ITEM": ["DUPLICATE", "RENAME", "EXPORT_TEMPLATE", "IMPORT_TEMPLATE", "PIN", "SET_DEFAULT", "ARCHIVE"],
        "REVIEW_ISSUE": ["MARKUP", "FLAGS", "SIGN_OFF", "COMPARE_REVISIONS", "AUDIT_TRAIL"],
        "DOCUMENT": ["OPEN_LINKED_DOCUMENT", "OPEN_SOURCE_FILE", "VIEW_HISTORY", "ARCHIVE"],
    }.get(target_type, [])
    return ContextMenuStatePacket(
        menu_id=f"{target_type}_MENU" if target_type else "",
        target_type=target_type,
        target_id=target_id,
        visible=False,
        sections=["QUICK_ACTIONS", "OBJECT_TOOLS", "FAVORITES"],
        quick_actions=quick_actions,
        object_actions=[_action_packet(action_id, action_id.replace("_", " ").title(), enabled=False) for action_id in object_action_ids],
        favorite_actions=[_action_packet("PIN_TO_FAVORITES", "Pin to favorites", enabled=False), _action_packet("PIN_TO_QUICK_TOOLS", "Pin to quick tools", enabled=False)],
        anchor_x=0,
        anchor_y=0,
        opened_at=utc_now_iso(),
    )


def _build_floating_toolbar_state(selection_state: Dict[str, Any]) -> FloatingToolbarStatePacket:
    target_type = str(selection_state.get("selected_object_type") or "")
    target_id = str(selection_state.get("selection_source_document_id") or "")
    visible_types = {"TEXT", "CELL", "TABLE", "IMAGE", "FIELD", "DYNAMIC_FIELD", "TCE_REGION"}
    return FloatingToolbarStatePacket(
        visible=target_type in visible_types,
        anchor_x=0,
        anchor_y=0,
        target_type=target_type,
        target_id=target_id,
        tools=[_action_packet(tool_id, tool_id.replace("_", " ").title()) for tool_id in list(selection_state.get("floating_toolbar_tools") or [])],
        collapsed=False,
        opened_at=utc_now_iso(),
    )


def _build_dialog_state(module_id: str, submodule_id: str, active_dialog: str) -> UiDialogStatePacket:
    dialog_id = str(active_dialog or "").strip().upper()
    dialog_map = {
        "FILTERS": ("Filter Options", "Advanced queue/workbench filtering", [{"label": "Document Type"}, {"label": "Status"}, {"label": "Search Text"}]),
        "WORKBENCH_SETTINGS": ("Workbench Settings", "Studio surface and pane preferences", [{"label": "Center Mode"}, {"label": "Inspector Mode"}, {"label": "Bottom Tab"}]),
        "EXPORT_SETTINGS": ("Export Settings", "Bridge/export target and operator preferences", [{"label": "Target Hint"}, {"label": "Export Reason"}, {"label": "Operator Note"}]),
        "OBJECT_PROPERTIES": ("Object Properties", "Selected object details and advanced actions", [{"label": "Selected Object"}, {"label": "Linked Context"}, {"label": "Action Scope"}]),
    }
    if dialog_id not in dialog_map:
        return UiDialogStatePacket()
    title, reason, fields = dialog_map[dialog_id]
    packet = UiDialogStatePacket(
        dialog_id=dialog_id,
        title=title,
        dialog_reason=reason,
        visible=True,
        fields=fields,
        opened_at=utc_now_iso(),
    )
    return packet


def _build_command_palette_state(
    module_id: str,
    submodule_id: str,
    active_workspace_mode: str,
    selected_item_id: str,
    selected_object_id: str,
    *,
    command_palette_open: bool,
    command_palette_query: str,
    selected_command_id: str,
) -> CommandPaletteStatePacket:
    commands = _build_commands(
        module_id,
        submodule_id,
        active_workspace_mode,
        selected_item_id,
        selected_object_id,
    )
    query = str(command_palette_query or "").strip().lower()
    filtered = [
        command
        for command in commands
        if not query
        or query in command.label.lower()
        or query in command.command_group.lower()
        or query in command.command_reason.lower()
    ]
    return CommandPaletteStatePacket(
        open=bool(command_palette_open),
        query=str(command_palette_query or ""),
        selected_command_id=str(selected_command_id or ""),
        commands=[asdict(command) for command in filtered[:14]],
    )


def _build_commands(
    module_id: str,
    submodule_id: str,
    active_workspace_mode: str,
    selected_item_id: str,
    selected_object_id: str,
) -> List[UiCommandPacket]:
    commands: List[UiCommandPacket] = [
        UiCommandPacket(
            command_id="SWITCH_PORTALIS_STUDIO",
            label="Switch To Studio",
            scope="PORTALIS",
            command_group="Module",
            command_reason="Open the Studio workbench lane",
            target_params={"nav_module": "PORTALIS", "nav_submodule": "STUDIO"},
            active=module_id == "PORTALIS" and submodule_id == "STUDIO",
        ),
        UiCommandPacket(
            command_id="SWITCH_PORTALIS_CONTROL_ROOM",
            label="Show Control Room",
            scope="PORTALIS",
            command_group="Module",
            command_reason="Open alerts, incidents, and queues",
            target_params={"nav_module": "PORTALIS", "nav_submodule": "CONTROL_ROOM"},
            active=module_id == "PORTALIS" and submodule_id == "CONTROL_ROOM",
        ),
        UiCommandPacket(
            command_id="OPEN_COMMAND_FILTERS",
            label="Open Filter Options",
            scope=module_id,
            command_group="Dialog",
            command_reason="Show advanced filtering controls",
            target_params={"nav_dialog": "FILTERS"},
        ),
        UiCommandPacket(
            command_id="TOGGLE_INSPECTOR",
            label="Toggle Inspector Pane",
            scope=module_id,
            command_group="Window",
            command_reason="Collapse or restore the right inspector pane",
            target_params={"toggle_pane": "right"},
        ),
        UiCommandPacket(
            command_id="TOGGLE_BOTTOM_CONTEXT",
            label="Toggle Bottom Context Pane",
            scope=module_id,
            command_group="Window",
            command_reason="Collapse or restore the bottom context pane",
            target_params={"toggle_pane": "bottom"},
        ),
    ]
    if module_id == "PORTALIS" and submodule_id == "STUDIO":
        commands.extend(
            [
                UiCommandPacket(
                    command_id="OPEN_WORKBENCH_SETTINGS",
                    label="Open Workbench Settings",
                    scope="STUDIO",
                    command_group="Studio",
                    command_reason="Tune workspace panes and modes",
                    target_params={"nav_dialog": "WORKBENCH_SETTINGS"},
                ),
                UiCommandPacket(
                    command_id="SHOW_STUDIO_ACTIONS",
                    label="Show Studio Actions",
                    scope="STUDIO",
                    command_group="Studio",
                    command_reason="Open grouped Studio commands",
                    target_params={"nav_menu": "EDIT", "nav_dropdown": "STUDIO"},
                ),
                UiCommandPacket(
                    command_id="PREVIEW_DOCUMENT",
                    label="Switch To Preview Mode",
                    scope="STUDIO",
                    command_group="Studio",
                    command_reason="Focus the center pane on document preview",
                    target_params={"workbench_center": "PREVIEW"},
                    enabled=bool(selected_item_id),
                ),
                UiCommandPacket(
                    command_id="SHOW_RECONSTRUCTION",
                    label="Switch To Reconstruction Mode",
                    scope="STUDIO",
                    command_group="Studio",
                    command_reason="Focus the center pane on reconstruction editing",
                    target_params={"workbench_center": "RECONSTRUCT"},
                    enabled=bool(selected_item_id),
                ),
                UiCommandPacket(
                    command_id="SELECT_OBJECT_PROPERTIES",
                    label="Open Selected Object Properties",
                    scope="STUDIO",
                    command_group="Selection",
                    command_reason="Inspect the current anchor, cell, or block",
                    target_params={"nav_dialog": "OBJECT_PROPERTIES"},
                    enabled=bool(selected_object_id),
                ),
            ]
        )
    if module_id == "PORTALIS" and submodule_id == "CONTROL_ROOM":
        commands.extend(
            [
                UiCommandPacket(
                    command_id="SHOW_QUEUE_ACTIONS",
                    label="Show Queue Actions",
                    scope="CONTROL_ROOM",
                    command_group="Control Room",
                    command_reason="Open grouped queue, alert, and bridge actions",
                    target_params={"nav_menu": "MODULE", "nav_dropdown": "QUEUE"},
                ),
                UiCommandPacket(
                    command_id="OPEN_EXPORT_SETTINGS",
                    label="Open Export Settings",
                    scope="CONTROL_ROOM",
                    command_group="Control Room",
                    command_reason="Adjust bridge/export options",
                    target_params={"nav_dialog": "EXPORT_SETTINGS"},
                ),
            ]
        )
    return commands


def _build_quick_actions(
    module_id: str,
    submodule_id: str,
    active_workspace_mode: str,
    selected_item_id: str,
    selected_object_id: str,
) -> List[QuickActionPacket]:
    actions: List[QuickActionPacket] = [
        QuickActionPacket(
            action_id="COMMAND_PALETTE",
            label="Command Palette",
            scope=module_id,
            action_reason="Search actions without hunting through menus",
            emphasized=True,
            target_params={"command_palette": "open"},
        ),
        QuickActionPacket(
            action_id="TOGGLE_LEFT_PANE",
            label="Toggle Rail",
            scope=module_id,
            action_reason="Collapse or restore the left module rail",
            target_params={"toggle_pane": "left"},
        ),
        QuickActionPacket(
            action_id="TOGGLE_RIGHT_PANE",
            label="Toggle Inspector",
            scope=module_id,
            action_reason="Collapse or restore the inspector pane",
            target_params={"toggle_pane": "right"},
        ),
        QuickActionPacket(
            action_id="TOGGLE_BOTTOM_PANE",
            label="Toggle Context",
            scope=module_id,
            action_reason="Collapse or restore the bottom context pane",
            target_params={"toggle_pane": "bottom"},
        ),
    ]
    if module_id == "PORTALIS" and submodule_id == "STUDIO":
        actions.extend(
            [
                QuickActionPacket(
                    action_id="STUDIO_RECONSTRUCT",
                    label="Reconstruct",
                    scope="STUDIO",
                    action_reason="Jump to reconstruction editing",
                    emphasized=active_workspace_mode == "RECONSTRUCT",
                    target_params={"workbench_center": "RECONSTRUCT"},
                ),
                QuickActionPacket(
                    action_id="STUDIO_OBJECT",
                    label="Object Actions",
                    scope="STUDIO",
                    action_reason="Show actions for the current selected object",
                    target_params={"nav_dropdown": "OBJECT", "nav_menu": "EDIT"},
                ),
                QuickActionPacket(
                    action_id="STUDIO_REVIEW",
                    label="Review Detail",
                    scope="STUDIO",
                    action_reason="Jump from the selected workbench document into review detail",
                    target_params={"nav_submodule": "REVIEW"},
                    emphasized=bool(selected_item_id),
                ),
                QuickActionPacket(
                    action_id="STUDIO_CONTROL_ROOM",
                    label="Control Room",
                    scope="STUDIO",
                    action_reason="Jump from Studio into the control-room lane",
                    target_params={"nav_submodule": "CONTROL_ROOM"},
                    emphasized=bool(selected_item_id),
                ),
            ]
        )
    if module_id == "PORTALIS" and submodule_id == "CONTROL_ROOM":
        actions.extend(
            [
                QuickActionPacket(
                    action_id="CONTROL_ROOM_QUEUE",
                    label="Queue Actions",
                    scope="CONTROL_ROOM",
                    action_reason="Open the grouped control-room actions",
                    emphasized=True,
                    target_params={"nav_dropdown": "QUEUE", "nav_menu": "MODULE"},
                ),
                QuickActionPacket(
                    action_id="CONTROL_ROOM_BRIDGE",
                    label="Bridge Options",
                    scope="CONTROL_ROOM",
                    action_reason="Open export and bridge settings",
                    target_params={"nav_dialog": "EXPORT_SETTINGS"},
                ),
                QuickActionPacket(
                    action_id="CONTROL_ROOM_REVIEW",
                    label="Open Review",
                    scope="CONTROL_ROOM",
                    action_reason="Jump into the selected review document workspace",
                    target_params={"nav_submodule": "REVIEW"},
                    emphasized=bool(selected_item_id),
                ),
                QuickActionPacket(
                    action_id="CONTROL_ROOM_STUDIO",
                    label="Open Studio",
                    scope="CONTROL_ROOM",
                    action_reason="Jump into Studio with the same selected document",
                    target_params={"nav_submodule": "STUDIO", "workbench_document_id": selected_item_id},
                    emphasized=bool(selected_item_id),
                ),
            ]
        )
    return actions
