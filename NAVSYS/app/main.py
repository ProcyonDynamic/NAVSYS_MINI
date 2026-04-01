from __future__ import annotations

import sys
import traceback
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import sys
from pathlib import Path

# Force project root onto sys.path so "modules.*" imports work
PROJECT_ROOT = Path(__file__).resolve().parents[2] # D:\NAVSYS_USB
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.navwarn_mini.warning_splitter_service import split_bulletin_to_envelopes
from modules.navwarn_mini.txt_ingester_helper import split_txt_blocks

from modules.portalis_mini.portcall_assistant.excel_arrival_loader import load_arrival_database
from modules.portalis_mini.portcall_assistant.ship_pdf_loader import load_ship_particulars
from modules.portalis_mini.portcall_assistant.certificate_pdf_loader import load_certificate as load_certificate_pdf
from modules.portalis_mini.portcall_assistant.apply_context import (
    apply_ship_to_state,
    import_crew_rows,
    import_certificates,
)

from modules.navwarn_mini.route_navarea_service import (
    detect_navareas_from_route_csv,
    build_chart_slots,
)

from modules.navwarn_mini.planner_cumulative_service import build_planner_cumulative_snapshot

from modules.navwarn_mini.planner_apply_service import apply_planner_mode

from modules.navwarn_mini.planner_slot_summary_service import build_slot_summary

def get_usb_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

USB_ROOT = get_usb_root()

if str(USB_ROOT) not in sys.path:
    sys.path.insert(0, str(USB_ROOT))

def log_startup_error(exc: Exception) -> None:
    try:
        p = USB_ROOT / "navsys_startup_error.txt"
        p.write_text(
            f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
    except Exception:
        pass

def log_startup_paths():
    import sys
    from pathlib import Path

    try:
        p = Path(sys.executable).parent / "navsys_startup_paths.txt"
        p.write_text(
            f"USB_ROOT={USB_ROOT}\n"
            f"TEMPLATES_DIR={TEMPLATES_DIR}\n"
            f"STATIC_DIR={STATIC_DIR}\n"
            f"templates_exists={TEMPLATES_DIR.exists()}\n"
            f"static_exists={STATIC_DIR.exists()}\n",
            encoding="utf-8",
        )
    except Exception as e:
        Path("navsys_startup_error.txt").write_text(str(e))

import webbrowser
from datetime import datetime, timezone

from flask import Flask, abort, render_template, request, send_file

from modules.portalis_mini.crew_service import (
    list_crew,
    create_crew,
    load_crew_record,
    add_document_to_crew,
)

from modules.portalis_mini.port_requirements import (
    list_ports,
    load_port_requirement,
    save_port_requirement,
)
from modules.portalis_mini.text_lists import textarea_to_list, list_to_textarea

from modules.portalis_mini.storage import load_portalis_state, save_portalis_state
from modules.portalis_mini.storage import (
    append_generated_output,
    build_portalis_state_snapshot,
)
from modules.portalis_mini.service import (
    update_vessel_from_form,
    update_voyage_from_form,
    update_documents_from_form,
)
from modules.portalis_mini.import_models import ImportRequest
from modules.portalis_mini.import_service import import_declared_document
from modules.portalis_mini.archive.document_registry import DocumentRegistry
from modules.portalis_mini.review_resolution_service import (
    ReviewResolutionCoupler,
    ReviewResolutionService,
)
from modules.portalis_mini.review_dashboard_service import (
    apply_alert_action,
    apply_assignment_action,
    apply_external_bridge_action,
    apply_incident_action,
    apply_intake_action,
    apply_dropzone_action,
    apply_notification_action,
    apply_reminder_action,
    apply_transport_action,
    apply_triage_action,
    apply_watch_action,
    refresh_control_room_state,
)
from modules.portalis_mini.navsys_shell_service import (
    build_navsys_shell_state,
    build_navsys_shell_tce_delta,
)
from modules.portalis_mini.workspace_persistence_service import WorkspacePersistenceService
from modules.portalis_mini.workspace_layout_service import WorkspaceLayoutService
from modules.portalis_mini.file_lifecycle_service import FileLifecycleService
from modules.portalis_mini.task_workspace_service import TaskWorkspaceService
from modules.portalis_mini.task_template_service import TaskTemplateService
from modules.portalis_mini.review_layer_service import ReviewLayerService
from modules.portalis_mini.studio_workbench_service import (
    add_document_anchor,
    add_workbench_annotation,
    add_workbench_scratchpad_field,
    build_document_workbench,
    clear_reconstruction_cell,
    delete_document_anchor,
    delete_workbench_annotation,
    delete_workbench_scratchpad_field,
    merge_reconstruction_cells,
    open_document_in_workbench,
    resolve_document_source_path,
    select_reconstruction_block,
    select_reconstruction_cell,
    select_document_anchor,
    split_reconstruction_block,
    update_reconstruction_block,
    update_reconstruction_cell,
    update_document_anchor,
    update_document_workbench,
    update_workbench_annotation,
    update_workbench_scratchpad_field,
)
try:
    from NAVSYS.app.portalis_import_routes import portalis_import_bp
except ModuleNotFoundError:
    from portalis_import_routes import portalis_import_bp

from modules.portalis_mini.document_generator import (
    generate_crew_list_txt,
    generate_health_declaration_txt,
    generate_port_checklist_txt,
    save_generated_text,
)

from modules.astranav_mini.models import SightInput
from modules.astranav_mini.skyfield_engine import compute_zn_hc_skyfield
from modules.astranav_mini.compass_error import compute_compass_or_gyro_error
from modules.astranav_mini.report_nsc01 import render_nsc01_compass_error_txt
from modules.astranav_mini.lop import compute_lop
from modules.astranav_mini.report_nsc02 import render_nsc02_lop_txt

from modules.navwarn_mini.process_warning import process_warning_text
from modules.navwarn_mini.extract_warning import extract_vertices_and_geom
from modules.navwarn_mini.coord_preview import preview_vertices_dm

from modules.portalis_mini.crew_service import list_crew, create_crew

from modules.portalis_mini.port_requirements import (
    list_ports,
    load_port_requirement,
    save_port_requirement,
)
from modules.portalis_mini.text_lists import textarea_to_list, list_to_textarea

from modules.portalis_mini.certificate_registry import (
    list_certificates,
    load_certificate,
    save_certificate,
)


from modules.portalis_mini.certificate_checks import check_required_certificates

from modules.navwarn_mini.active_warning_table import load_active_warning_table
from modules.navwarn_mini.warning_editor_routes import warning_editor_bp

def _safe_filename(s: str) -> str:
    return (
        (s or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def _build_review_field_rows(review_item, document_entry):
    if not review_item:
        return []

    parsed_fields = dict(getattr(review_item, "parsed_fields", {}) or {})
    final_fields = dict(getattr(review_item, "final_fields", {}) or {})
    accepted_fields = dict(getattr(review_item, "accepted_fields", {}) or {})

    doc_field_evidence = dict((document_entry or {}).get("field_evidence", {}))
    item_field_evidence = dict(getattr(review_item, "field_evidence", {}) or {})
    field_evidence = item_field_evidence or doc_field_evidence

    doc_field_validation = dict((document_entry or {}).get("field_validation", {}))
    item_field_validation = dict(getattr(review_item, "field_validation", {}) or {})
    field_validation = item_field_validation or doc_field_validation
    doc_field_conflicts = dict((document_entry or {}).get("field_conflicts", {}))
    item_field_conflicts = dict(getattr(review_item, "field_conflicts", {}) or {})
    field_conflicts = item_field_conflicts or doc_field_conflicts
    doc_field_confidence = dict((document_entry or {}).get("field_confidence", {}))
    item_field_confidence = dict(getattr(review_item, "field_confidence", {}) or {})
    field_confidence = item_field_confidence or doc_field_confidence
    doc_candidate_bundles = dict((document_entry or {}).get("candidate_bundles", {}))
    item_candidate_bundles = dict(getattr(review_item, "candidate_bundles", {}) or {})
    candidate_bundles = item_candidate_bundles or doc_candidate_bundles
    accepted_candidate_refs = dict(getattr(review_item, "accepted_candidate_refs", {}) or (document_entry or {}).get("accepted_candidate_refs", {}))
    operator_overrides = dict(getattr(review_item, "operator_overrides", {}) or (document_entry or {}).get("operator_overrides", {}))
    field_statuses = dict(getattr(review_item, "field_statuses", {}) or (document_entry or {}).get("field_statuses", {}))
    unresolved_fields = dict(getattr(review_item, "unresolved_fields", {}) or (document_entry or {}).get("unresolved_fields", {}))
    field_policy = dict(getattr(review_item, "field_policy", {}) or (document_entry or {}).get("field_policy", {}))
    prioritized_field_queue = list(getattr(review_item, "prioritized_field_queue", []) or (document_entry or {}).get("prioritized_field_queue", []))
    escalation_policy = dict(getattr(review_item, "escalation_policy", {}) or (document_entry or {}).get("escalation_policy", {}))
    triage_state = dict(getattr(review_item, "triage_state", {}) or (document_entry or {}).get("triage_state", {}))
    routing_hints = dict(getattr(review_item, "routing_hints", {}) or (document_entry or {}).get("routing_hints", {}))
    assignment_state = dict(getattr(review_item, "assignment_state", {}) or (document_entry or {}).get("assignment_state", {}))
    sla_policy = dict(getattr(review_item, "sla_policy", {}) or (document_entry or {}).get("sla_policy", {}))
    watch_state = dict(getattr(review_item, "watch_state", {}) or (document_entry or {}).get("watch_state", {}))
    reminder_stage = dict(getattr(review_item, "reminder_stage", {}) or (document_entry or {}).get("reminder_stage", {}))
    notification_prep = dict(getattr(review_item, "notification_prep", {}) or (document_entry or {}).get("notification_prep", {}))
    notification_ledger = dict(getattr(review_item, "notification_ledger", {}) or (document_entry or {}).get("notification_ledger", {}))
    delivery_attempts = dict(getattr(review_item, "delivery_attempts", {}) or (document_entry or {}).get("delivery_attempts", {}))
    transport_requests = dict(getattr(review_item, "transport_requests", {}) or (document_entry or {}).get("transport_requests", {}))
    transport_results = dict(getattr(review_item, "transport_results", {}) or (document_entry or {}).get("transport_results", {}))
    local_alerts = dict(getattr(review_item, "local_alerts", {}) or (document_entry or {}).get("local_alerts", {}))
    incident_threads = dict(getattr(review_item, "incident_threads", {}) or (document_entry or {}).get("incident_threads", {}))
    external_bridge_exports = dict(getattr(review_item, "external_bridge_exports", {}) or (document_entry or {}).get("external_bridge_exports", {}))
    external_bridge_results = dict(getattr(review_item, "external_bridge_results", {}) or (document_entry or {}).get("external_bridge_results", {}))
    intake_contracts = dict(getattr(review_item, "intake_contracts", {}) or (document_entry or {}).get("intake_contracts", {}))
    intake_acks = dict(getattr(review_item, "intake_acks", {}) or (document_entry or {}).get("intake_acks", {}))
    dropzone_handshakes = dict(getattr(review_item, "dropzone_handshakes", {}) or (document_entry or {}).get("dropzone_handshakes", {}))
    dropzone_receipts = dict(getattr(review_item, "dropzone_receipts", {}) or (document_entry or {}).get("dropzone_receipts", {}))
    dropzone_reconciliation = dict(getattr(review_item, "dropzone_reconciliation", {}) or (document_entry or {}).get("dropzone_reconciliation", {}))
    dropzone_recovery = dict(getattr(review_item, "dropzone_recovery", {}) or (document_entry or {}).get("dropzone_recovery", {}))

    queue_map = {item.get("field_name"): item for item in prioritized_field_queue if item.get("field_name")}
    ordered_field_names = [item.get("field_name") for item in prioritized_field_queue if item.get("field_name")]

    field_names = []
    for source in (parsed_fields, final_fields, accepted_fields, field_evidence, field_validation, field_conflicts, field_confidence, candidate_bundles):
        for key in source.keys():
            if key not in field_names:
                field_names.append(key)
    for key in ordered_field_names:
        if key in field_names:
            field_names.remove(key)
    field_names = ordered_field_names + field_names

    rows = []
    for field_name in field_names:
        evidence = dict(field_evidence.get(field_name, {}) or {})
        validation = dict(field_validation.get(field_name, {}) or {})
        conflict = dict(field_conflicts.get(field_name, {}) or {})
        confidence = dict(field_confidence.get(field_name, {}) or {})
        bundle = dict(candidate_bundles.get(field_name, {}) or {})
        policy = dict(field_policy.get(field_name, {}) or {})
        queue_item = dict(queue_map.get(field_name, {}) or {})
        escalation = dict(escalation_policy.get(field_name, {}) or {})
        routing_hint = dict(routing_hints.get(field_name, {}) or {})
        sla = dict(sla_policy.get(field_name, {}) or {})
        warnings = []
        warnings.extend(list(evidence.get("warnings", []) or []))
        warnings.extend(list(validation.get("validator_messages", []) or []))
        warnings.extend(list(conflict.get("warning_flags", []) or []))
        warnings.extend(list(confidence.get("warning_flags", []) or []))
        rows.append(
            {
                "field_name": field_name,
                "parsed_value": parsed_fields.get(field_name, ""),
                "final_value": final_fields.get(field_name, parsed_fields.get(field_name, "")),
                "accepted_value": accepted_fields.get(field_name, ""),
                "evidence": evidence,
                "validation": validation,
                "conflict": conflict,
                "confidence": confidence,
                "candidate_bundle": bundle,
                "accepted_candidate_id": accepted_candidate_refs.get(field_name, ""),
                "operator_override": operator_overrides.get(field_name, ""),
                "field_status": str((field_statuses.get(field_name) or {}).get("status") or "PENDING"),
                "unresolved": dict(unresolved_fields.get(field_name, {}) or {}),
                "policy": policy,
                "queue_item": queue_item,
                "escalation": escalation,
                "triage_state": dict(triage_state.get(field_name, {}) or {}),
                "routing_hint": routing_hint,
                "assignment_state": dict(assignment_state.get(field_name, {}) or {}),
                "sla": sla,
                "watch_state": dict(watch_state.get(field_name, {}) or {}),
                "reminder_stage": dict(reminder_stage.get(field_name, {}) or {}),
                "notification_prep": dict(notification_prep.get(field_name, {}) or {}),
                "notification_ledger": dict(notification_ledger.get(field_name, {}) or {}),
                "delivery_attempts": list(delivery_attempts.get(field_name, []) or []),
                "transport_request": dict(transport_requests.get(field_name, {}) or {}),
                "transport_results": list(transport_results.get(field_name, []) or []),
                "local_alert": dict(local_alerts.get(field_name, {}) or {}),
                "incident_thread": dict(incident_threads.get(field_name, {}) or {}),
                "external_bridge_export": dict(external_bridge_exports.get(field_name, {}) or {}),
                "external_bridge_result": dict(external_bridge_results.get(field_name, {}) or {}),
                "intake_contract": dict(intake_contracts.get(field_name, {}) or {}),
                "intake_ack": dict(intake_acks.get(field_name, {}) or {}),
                "dropzone_handshake": dict(dropzone_handshakes.get(field_name, {}) or {}),
                "dropzone_receipt": dict(dropzone_receipts.get(field_name, {}) or {}),
                "dropzone_reconciliation": dict(dropzone_reconciliation.get(field_name, {}) or {}),
                "dropzone_recovery": dict(dropzone_recovery.get(field_name, {}) or {}),
                "warnings": warnings,
            }
        )

    return rows


def _filter_review_field_rows(rows, mode: str):
    mode = (mode or "").strip().lower()
    if mode == "unresolved":
        return [row for row in rows if row.get("field_status") == "UNRESOLVED" or row.get("unresolved")]
    if mode == "attention":
        return [row for row in rows if str((row.get("policy") or {}).get("attention_state") or "") == "ATTENTION"]
    if mode == "conflicted":
        return [row for row in rows if str((row.get("conflict") or {}).get("conflict_level") or "") in {"MEDIUM", "HIGH"}]
    if mode == "low_confidence":
        return [row for row in rows if str((row.get("confidence") or {}).get("confidence_band") or "") in {"LOW", "UNKNOWN"}]
    return rows
    

BASE_DIR = Path(__file__).resolve().parent.parent
USB_ROOT = BASE_DIR.parent
TEMPLATES_DIR = BASE_DIR / "ui" / "templates"
STATIC_DIR = BASE_DIR / "ui" / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.register_blueprint(warning_editor_bp)
app.register_blueprint(portalis_import_bp)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float_or_none(s: str):
    s = (s or "").strip()
    if not s:
        return None
    return float(s)

def _split_navwarn_blocks(raw_text: str) -> tuple[list[dict], list[str]]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return [], []

    split_result = split_bulletin_to_envelopes(
        raw_text=raw_text,
        source="MANUAL",
    )

    blocks = []
    for env in split_result.envelopes:
        blocks.append({
            "warning_id": (env.warning_id or "").strip(),
            "navarea": (env.navarea or "").strip(),
            "raw_text": (env.raw_text or "").strip(),
        })

    if not blocks:
        fallback_blocks = split_txt_blocks(raw_text)
        if fallback_blocks:
            blocks = []
            for block_text in fallback_blocks:
                first_line = block_text.splitlines()[0].strip() if block_text.splitlines() else ""
                blocks.append({
                    "warning_id": first_line,
                    "navarea": "",
                    "raw_text": block_text.strip(),
                })

    return blocks, list(split_result.errors)

def _attach_slot_summary_state(slots: list[dict], usb_root: Path) -> list[dict]:
    enriched = []

    for slot in slots:
        route_id = (slot.get("route_id") or "").strip().upper()
        navarea = (slot.get("navarea") or "").strip().upper()

        summary = build_slot_summary(
            output_root=str(usb_root),
            route_id=route_id,
            navarea=navarea,
        )

        merged = dict(slot)
        merged["summary"] = summary
        enriched.append(merged)

    return enriched

def _attach_slot_cumulative_state(slots: list[dict], usb_root: Path) -> list[dict]:
    enriched = []

    for slot in slots:
        navarea = (slot.get("navarea") or "").strip().upper()

        snapshot = build_planner_cumulative_snapshot(
            output_root=str(usb_root),
            navarea=navarea,
        )

        merged = dict(slot)
        merged["cumulative"] = snapshot
        enriched.append(merged)

    return enriched

def _decorate_overview_rows(ids: list[str], status: str) -> list[dict]:
    rows = []
    normalized_status = (status or "").strip().upper()

    for wid in ids or []:
        wid = " ".join((wid or "").split())
        if not wid:
            continue

        if normalized_status == "ACTIVE":
            css_class = "status-active"
            label = "ACTIVE"
        elif normalized_status == "NEW":
            css_class = "status-new"
            label = "NEW"
        elif normalized_status == "DROPPED":
            css_class = "status-dropped"
            label = "DROPPED"
        elif normalized_status == "CANCELLED":
            css_class = "status-cancelled"
            label = "CANCELLED"
        else:
            css_class = "status-neutral"
            label = normalized_status or "INFO"

        rows.append({
            "warning_id": wid,
            "status": normalized_status,
            "css_class": css_class,
            "label": label,
        })

    return rows

@app.route("/")
def home():
    return render_template("home.html", usb_root=str(USB_ROOT), utc_now=utc_now_iso())


@app.route("/portalis/document/<document_id>/source")
def portalis_document_source(document_id: str):
    portalis_root = USB_ROOT / "data" / "PORTALIS"
    registry = DocumentRegistry(portalis_root)
    document_entry = registry.get_document(document_id)
    if not document_entry:
        abort(404)
    source_path = resolve_document_source_path(portalis_root, document_entry)
    if source_path is None or not source_path.exists():
        abort(404)
    return send_file(source_path)


@app.route("/navwarn", methods=["GET", "POST"])
def navwarn():
    ctx = {
        "usb_root": str(USB_ROOT),
        "utc_now": utc_now_iso(),
        "form": {
            "navarea": "",
            "warning_id": "",
            "title": "",
            "ship_lat": "",
            "ship_lon": "",
            "route_csv_path": str(USB_ROOT / "data" / "ROUTE" / "route.csv"),
            "source_kind": "MANUAL",
            "raw_text": "",
            "chart_mode": "UPDATE_EXISTING",
            "target_navarea": "",
        },
        "preview_geom": "",
        "preview_vertices": "",
        "result": None,
        "errors": [],
        "results": [],
        "route_detect": None,
        "chart_slots": [],
    }

    if request.method == "POST":
        
        
        action = request.form.get("action", "").strip()

        form = {
            "navarea": request.form.get("navarea", "").strip().upper(),
            "warning_id": request.form.get("warning_id", "").strip(),
            "title": request.form.get("title", "").strip(),
            "ship_lat": request.form.get("ship_lat", "").strip(),
            "ship_lon": request.form.get("ship_lon", "").strip(),
            "route_csv_path": request.form.get("route_csv_path", "").strip(),
            "source_kind": request.form.get("source_kind", "").strip().upper() or "MANUAL",
            "raw_text": request.form.get("raw_text", "").strip(),
            "chart_mode": request.form.get("chart_mode", "").strip().upper() or "UPDATE_EXISTING",
            "target_navarea": request.form.get("target_navarea", "").strip().upper(),
        }
        
        ctx["form"] = form

        txt_file = request.files.get("warning_txt")
        if txt_file and txt_file.filename and txt_file.filename.lower().endswith(".txt"):
            uploaded_text = txt_file.read().decode("utf-8", errors="replace")
            if uploaded_text.strip():
                form["raw_text"] = uploaded_text.strip()
        
        try:
            
            if action in (
                "slot_apply_effective",
                "slot_apply_new",
                "slot_rebuild_state",
                "slot_apply_selected",
                "slot_rebuild_selected",
            ):
                detect_result = detect_navareas_from_route_csv(
                    form["route_csv_path"],
                ) if form["route_csv_path"] else None

                ctx["route_detect"] = detect_result
                if detect_result and detect_result.get("ok"):
                    slots = build_chart_slots(
                        output_root=str(USB_ROOT),
                        route_id=detect_result["route_id"],
                        navareas=detect_result["navareas"],
                    )
                    slots = _attach_slot_cumulative_state(slots, USB_ROOT)
                    ctx["chart_slots"] = _attach_slot_summary_state(slots, USB_ROOT)
                    
                selected_navarea = request.form.get("slot_navarea", "").strip().upper()
                selected_route_id = (
                    detect_result["route_id"]
                    if detect_result and detect_result.get("ok")
                    else ""
                )

                selected_warning_ids = request.form.getlist("selected_warning_ids")

                if action == "slot_apply_effective":
                    planner_mode = "APPLY_EFFECTIVE_ACTIVE"
                elif action == "slot_apply_new":
                    planner_mode = "APPLY_NEW_ONLY"
                elif action == "slot_rebuild_state":
                    planner_mode = "REBUILD_FROM_STATE"
                elif action == "slot_apply_selected":
                    planner_mode = "APPLY_SELECTED"
                else:
                    planner_mode = "REBUILD_SELECTED"
                    
                apply_result = apply_planner_mode(
                    output_root=str(USB_ROOT),
                    route_id=selected_route_id,
                    navarea=selected_navarea,
                    mode=planner_mode,
                    selected_warning_ids=selected_warning_ids,
                )
                
                planner_audit_rows = []
                
                for wid in apply_result.applied_warning_ids:
                    
                    planner_audit_rows.append({
                        "warning_id": wid,
                        "source": apply_result.fallback_sources.get(wid, "UNKNOWN"),
                    })

                ctx["result"] = {
                    "ok": apply_result.ok,
                    "warning_id": f"{planner_mode}:{selected_navarea}",
                    "geom_type": "PLANNER",
                    "vertex_count": 0,
                    "ship_distance_nm": None,
                    "route_distance_nm": None,
                    "distance_nm": None,
                    "band": None,
                    "plot_csv_path": apply_result.chart_csv_path,
                    "daily_ns01_csv_path": "",
                    "daily_ns01_txt_path": "",
                    "route_id": apply_result.route_id,
                    "chart_mode": planner_mode,
                    "plotted_warning_ids": apply_result.applied_warning_ids,
                    "fallback_sources": apply_result.fallback_sources,
                    "planner_audit_rows": planner_audit_rows,
                    "errors": list(apply_result.errors) + [
                        f"MISSING_ARCHIVE: {wid}" for wid in apply_result.missing_warning_ids
                    ],
                }

                ctx["results"] = [ctx["result"]]

                ctx["errors"] = list(apply_result.errors) + [
                    f"missing archived section: {wid}" for wid in apply_result.missing_warning_ids
                ]
            
            if action in ("slot_create", "slot_update"):
                detect_result = detect_navareas_from_route_csv(
                    form["route_csv_path"],
                ) if form["route_csv_path"] else None

                ctx["route_detect"] = detect_result
                
                if detect_result and detect_result.get("ok"):
                    slots = build_chart_slots(
                        output_root=str(USB_ROOT),
                        route_id=detect_result["route_id"],
                        navareas=detect_result["navareas"],
                    )
                    slots = _attach_slot_cumulative_state(slots, USB_ROOT)
                    ctx["chart_slots"] = _attach_slot_summary_state(slots, USB_ROOT)
                    
                selected_navarea = request.form.get("slot_navarea", "").strip().upper()
                if selected_navarea:
                    form["target_navarea"] = selected_navarea

                form["chart_mode"] = (
                    "CREATE_NEW" if action == "slot_create" else "UPDATE_EXISTING"
                )

                blocks, split_errors = _split_navwarn_blocks(form["raw_text"])

                if not blocks:
                    blocks = [{
                        "warning_id": form["warning_id"],
                        "navarea": form["target_navarea"] or form["navarea"],
                        "raw_text": form["raw_text"],
                    }]

                results = []
                all_errors = list(split_errors)

                for block in blocks:
                    block_navarea = (
                        form["target_navarea"]
                        or block.get("navarea")
                        or form["navarea"]
                        or "IV"
                    ).strip().upper()

                    res = process_warning_text(
                        raw_text=block["raw_text"],
                        navarea=block_navarea,
                        ship_lat=_to_float_or_none(form["ship_lat"]),
                        ship_lon=_to_float_or_none(form["ship_lon"]),
                        output_root=str(USB_ROOT),
                        warning_id=block["warning_id"] or form["warning_id"],
                        title=form["title"],
                        source_kind=form["source_kind"],
                        route_csv_path=form["route_csv_path"] or None,
                        chart_mode=form["chart_mode"],
                        forced_route_id=(detect_result["route_id"] if detect_result and detect_result.get("ok") else ""),
                    )
                    results.append(res)

                    if not res.get("ok", False):
                        all_errors.extend(res.get("errors", []))

                ctx["results"] = results
                ctx["result"] = results[0] if results else None
                ctx["errors"] = all_errors

                if ctx["result"]:
                    if "plot_csv" not in ctx["result"]:
                        ctx["result"]["plot_csv"] = ctx["result"].get("plot_csv_path", "")
                    if "ns01_csv" not in ctx["result"]:
                        ctx["result"]["ns01_csv"] = ctx["result"].get("daily_ns01_csv_path", "")
                    if "ns01_txt" not in ctx["result"]:
                        ctx["result"]["ns01_txt"] = ctx["result"].get("daily_ns01_txt_path", "")

                for r in ctx["results"]:
                    if "plot_csv" not in r:
                        r["plot_csv"] = r.get("plot_csv_path", "")
                    if "ns01_csv" not in r:
                        r["ns01_csv"] = r.get("daily_ns01_csv_path", "")
                    if "ns01_txt" not in r:
                        r["ns01_txt"] = r.get("daily_ns01_txt_path", "")

                preview_text = blocks[0]["raw_text"] if blocks else form["raw_text"]
                verts, geom = extract_vertices_and_geom(preview_text)
                ctx["preview_geom"] = geom
                ctx["preview_vertices"] = preview_vertices_dm(verts)
            
            if action == "detect_route_navareas":
                detect_result = detect_navareas_from_route_csv(
                    form["route_csv_path"],
                )
                ctx["route_detect"] = detect_result

                if detect_result.get("ok"):
                    slots = build_chart_slots(
                        output_root=str(USB_ROOT),
                        route_id=detect_result["route_id"],
                        navareas=detect_result["navareas"],
                    )
                    slots = _attach_slot_cumulative_state(slots, USB_ROOT)
                    ctx["chart_slots"] = _attach_slot_summary_state(slots, USB_ROOT)
                                        
                else:
                    ctx["errors"] = detect_result.get("errors", [])
            
            if action == "preview":
                blocks, split_errors = _split_navwarn_blocks(form["raw_text"])
                preview_text = blocks[0]["raw_text"] if blocks else form["raw_text"]

                verts, geom = extract_vertices_and_geom(preview_text)
                ctx["preview_geom"] = geom
                ctx["preview_vertices"] = preview_vertices_dm(verts)
                ctx["errors"] = split_errors
                
            elif action == "process":
                blocks, split_errors = _split_navwarn_blocks(form["raw_text"])

                detect_result = detect_navareas_from_route_csv(
                    form["route_csv_path"],
                ) if form["route_csv_path"] else None

                ctx["route_detect"] = detect_result
                
                if detect_result and detect_result.get("ok"):
                    slots = build_chart_slots(
                        output_root=str(USB_ROOT),
                        route_id=detect_result["route_id"],
                        navareas=detect_result["navareas"],
                    )
                    ctx["chart_slots"] = _attach_slot_cumulative_state(slots, USB_ROOT)
                    

                if not blocks:
                    blocks = [{
                        "warning_id": form["warning_id"],
                        "navarea": form["navarea"],
                        "raw_text": form["raw_text"],
                    }]

                results = []
                all_errors = list(split_errors)

                for block in blocks:
                    
                    block_navarea = (
                        form["target_navarea"]
                        or block.get("navarea")
                        or form["navarea"]
                        or "IV"
                    ).strip().upper()
                    
                    res = process_warning_text(
                        raw_text=block["raw_text"],
                        navarea=block_navarea,
                        ship_lat=_to_float_or_none(form["ship_lat"]),
                        ship_lon=_to_float_or_none(form["ship_lon"]),
                        output_root=str(USB_ROOT),
                        warning_id=block["warning_id"] or form["warning_id"],
                        title=form["title"],
                        source_kind=form["source_kind"],
                        route_csv_path=form["route_csv_path"] or None,
                        chart_mode=form["chart_mode"],
                        forced_route_id=(detect_result["route_id"] if detect_result and detect_result.get("ok") else ""),
                    )
                    results.append(res)

                    if not res.get("ok", False):
                        all_errors.extend(res.get("errors", []))

                ctx["results"] = results
                ctx["result"] = results[0] if results else None

                if ctx["result"]:
                    if "plot_csv" not in ctx["result"]:
                        ctx["result"]["plot_csv"] = ctx["result"].get("plot_csv_path", "")
                    if "ns01_csv" not in ctx["result"]:
                        ctx["result"]["ns01_csv"] = ctx["result"].get("daily_ns01_csv_path", "")
                    if "ns01_txt" not in ctx["result"]:
                        ctx["result"]["ns01_txt"] = ctx["result"].get("daily_ns01_txt_path", "")

                for r in ctx["results"]:
                    if "plot_csv" not in r:
                        r["plot_csv"] = r.get("plot_csv_path", "")
                    if "ns01_csv" not in r:
                        r["ns01_csv"] = r.get("daily_ns01_csv_path", "")
                    if "ns01_txt" not in r:
                        r["ns01_txt"] = r.get("daily_ns01_txt_path", "")

                ctx["errors"] = all_errors

                cumulative_results = [
                    r for r in results
                    if (r.get("state") or "") == "REFERENCE_CUMULATIVE"
                ]

                if cumulative_results:
                    latest_cumulative = cumulative_results[-1]

                    cumulative_navarea = ""
                    listed_ids = latest_cumulative.get("listed_ids", [])
                    if listed_ids:
                        first_listed = " ".join((listed_ids[0] or "").split()).upper()
                        parts = first_listed.split()
                        if len(parts) >= 2 and parts[0] == "NAVAREA":
                            cumulative_navarea = parts[1]

                    if not cumulative_navarea:
                        cumulative_navarea = (form["navarea"] or "").strip().upper()

                    cancelled_ids = []
                    try:
                        active_rows = load_active_warning_table(USB_ROOT / "NAVWARN" / "active_warning_table.csv")
                        cancelled_ids = [
                            row.warning_id
                            for row in active_rows
                            if (row.navarea or "").strip().upper() == cumulative_navarea
                            and (row.state or "").strip().upper() == "CANCELLED_EXPLICIT"
                        ]
                    except Exception as e:
                        all_errors.append(f"overview_cancelled_load_failed: {e}")
                    ctx["latest_cumulative_cancelled_ids"] = cancelled_ids

                    ctx["latest_cumulative_warning_id"] = latest_cumulative.get("warning_id", "")
                    ctx["latest_cumulative_listed_ids"] = latest_cumulative.get("listed_ids", [])
                    ctx["latest_cumulative_kept_ids"] = latest_cumulative.get("kept_ids", [])
                    ctx["latest_cumulative_omitted_ids"] = latest_cumulative.get("omitted_ids", [])
                    ctx["latest_cumulative_newer_preserved_ids"] = latest_cumulative.get("newer_preserved_ids", [])
                    ctx["latest_cumulative_active_session_ok"] = latest_cumulative.get("active_session_ok", False)
                    ctx["latest_cumulative_active_session_rows_written"] = latest_cumulative.get("active_session_rows_written", 0)
                    ctx["latest_cumulative_listed_count"] = len(ctx["latest_cumulative_listed_ids"])
                    ctx["latest_cumulative_new_count"] = len(ctx["latest_cumulative_newer_preserved_ids"])
                    ctx["latest_cumulative_dropped_count"] = len(ctx["latest_cumulative_omitted_ids"])
                    ctx["latest_cumulative_cancelled_count"] = len(ctx["latest_cumulative_cancelled_ids"])
                    effective_active_ids = []
                    seen_effective = set()

                    cancelled_set = {
                        " ".join((wid or "").split())
                        for wid in ctx["latest_cumulative_cancelled_ids"]
                    }

                    for wid in ctx["latest_cumulative_listed_ids"] + ctx["latest_cumulative_newer_preserved_ids"]:
                        norm_wid = " ".join((wid or "").split())

                        if not norm_wid:
                            continue

                        if norm_wid in cancelled_set:
                            continue

                        if norm_wid not in seen_effective:
                            seen_effective.add(norm_wid)
                            effective_active_ids.append(norm_wid)

                    ctx["latest_cumulative_effective_active_ids"] = effective_active_ids
                    ctx["latest_cumulative_effective_active_count"] = len(effective_active_ids)

                    ctx["latest_cumulative_effective_active_rows"] = _decorate_overview_rows(
                        ctx["latest_cumulative_effective_active_ids"],
                        "ACTIVE",
                    )
                    ctx["latest_cumulative_listed_rows"] = _decorate_overview_rows(
                        ctx["latest_cumulative_listed_ids"],
                        "ACTIVE",
                    )
                    ctx["latest_cumulative_new_rows"] = _decorate_overview_rows(
                        ctx["latest_cumulative_newer_preserved_ids"],
                        "NEW",
                    )
                    ctx["latest_cumulative_dropped_rows"] = _decorate_overview_rows(
                        ctx["latest_cumulative_omitted_ids"],
                        "DROPPED",
                    )
                    ctx["latest_cumulative_cancelled_rows"] = _decorate_overview_rows(
                        ctx["latest_cumulative_cancelled_ids"],
                        "CANCELLED",
                    )

                preview_text = blocks[0]["raw_text"] if blocks else form["raw_text"]
                verts, geom = extract_vertices_and_geom(preview_text)
                ctx["preview_geom"] = geom
                ctx["preview_vertices"] = preview_vertices_dm(verts)

        except Exception as e:
            ctx["errors"] = [str(e)]

    return render_template("navwarn.html", **ctx)


@app.route("/astranav", methods=["GET", "POST"])
def astranav():
    ctx = {
        "usb_root": str(USB_ROOT),
        "utc_now": utc_now_iso(),
        "form": {
            "time_utc": utc_now_iso(),
            "lat": "",
            "lon": "",
            "body_kind": "SUN",
            "body_name": "Sun",
            "instrument_mode": "GYRO_1",
            "instrument_label": "",
            "observed_bearing_deg": "",
            "observed_ho_deg": "",
            "variation_deg": "",
            "deviation_card_csv_path": str(USB_ROOT / "data" / "ASTRANAV" / "deviation_card.csv"),
        },
        "sky": None,
        "nsc01_report": "",
        "nsc02_report": "",
        "errors": [],
    }

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        form = {
            "time_utc": request.form.get("time_utc", "").strip(),
            "lat": request.form.get("lat", "").strip(),
            "lon": request.form.get("lon", "").strip(),
            "body_kind": request.form.get("body_kind", "").strip().upper() or "SUN",
            "body_name": request.form.get("body_name", "").strip() or "Sun",
            "instrument_mode": request.form.get("instrument_mode", "").strip().upper() or "GYRO_1",
            "instrument_label": request.form.get("instrument_label", "").strip(),
            "observed_bearing_deg": request.form.get("observed_bearing_deg", "").strip(),
            "observed_ho_deg": request.form.get("observed_ho_deg", "").strip(),
            "variation_deg": request.form.get("variation_deg", "").strip(),
            "deviation_card_csv_path": request.form.get("deviation_card_csv_path", "").strip(),
        }
        ctx["form"] = form

        try:
            s = SightInput(
                run_id="UI",
                time_utc=form["time_utc"],
                lat=float(form["lat"]),
                lon=float(form["lon"]),
                body_kind=form["body_kind"],
                body_name=form["body_name"],
                instrument_mode=form["instrument_mode"],
                instrument_label=form["instrument_label"],
                observed_bearing_deg=_to_float_or_none(form["observed_bearing_deg"]),
                observed_ho_deg=_to_float_or_none(form["observed_ho_deg"]),
                variation_deg=_to_float_or_none(form["variation_deg"]),
            )

            sky = compute_zn_hc_skyfield(s)
            ctx["sky"] = sky

            if action == "nsc01":
                res = compute_compass_or_gyro_error(
                    s,
                    sky,
                    deviation_card_csv_path=form["deviation_card_csv_path"] or None,
                )
                ctx["nsc01_report"] = render_nsc01_compass_error_txt(
                    form="NSC-01",
                    generated_utc=utc_now_iso(),
                    s=s,
                    sky=sky,
                    res=res,
                )

            elif action == "nsc02":
                res = compute_lop(s, sky)
                ctx["nsc02_report"] = render_nsc02_lop_txt(
                    form="NSC-02",
                    generated_utc=utc_now_iso(),
                    s=s,
                    sky=sky,
                    res=res,
                )

        except Exception as e:
            ctx["errors"] = [str(e)]

    return render_template("astranav.html", **ctx)

@app.route("/portalis", methods=["GET", "POST"])
def portalis():
    state_path = USB_ROOT / "data" / "PORTALIS" / "state.json"
    portalis_root = USB_ROOT / "data" / "PORTALIS"
    registry = DocumentRegistry(portalis_root)
    review_service = ReviewResolutionService(portalis_root)
    workspace_service = WorkspacePersistenceService(portalis_root)
    layout_service = WorkspaceLayoutService(portalis_root)
    file_service = FileLifecycleService(portalis_root)
    task_service = TaskWorkspaceService(portalis_root)
    template_service = TaskTemplateService(portalis_root)
    review_layer_service = ReviewLayerService(portalis_root)

    def infer_nav_submodule(action_name: str, current_value: str) -> str:
        action_name = str(action_name or "").strip().lower()
        if not action_name:
            return current_value or "STUDIO"
        if any(
            action_name.startswith(prefix)
            for prefix in (
                "open_workbench",
                "update_workbench",
                "add_workbench",
                "delete_workbench",
                "select_workbench",
                "clear_workbench",
                "merge_workbench",
                "split_workbench",
            )
        ):
            return "STUDIO"
        if action_name.startswith("apply_"):
            return "CONTROL_ROOM"
        if action_name in {"accept_review_item", "resolve_review_item", "reject_review_item", "select_review_document"}:
            return "REVIEW"
        if action_name.startswith("generate_"):
            return "OUTPUT"
        if action_name in {
            "save_portalis",
            "import_arrival_db",
            "import_crew_passport",
            "create_crew",
            "add_crew_document",
            "save_port_requirements",
            "save_certificate",
        }:
            return "ARCHIVE"
        return current_value or "STUDIO"

    def _as_bool_flag(value: str) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "open", "collapsed"}

    def build_workspace_payload(
        *,
        workspace_name: str,
        ui_mode: str,
        open_document_tabs: list,
        active_document_tab_id: str,
        active_ribbon_tab_value: str,
        left_pane_collapsed_value: bool,
        right_pane_collapsed_value: bool,
        bottom_pane_collapsed_value: bool,
        selected_file_id: str,
        workbench_bottom_tab_value: str,
        workbench_inspector_mode_value: str,
        split_view_enabled_value: bool = False,
        split_view_mode_value: str = "SINGLE",
        split_orientation_value: str = "VERTICAL",
        active_pane_id_value: str = "LEFT",
        left_pane_document_id_value: str = "",
        right_pane_document_id_value: str = "",
        compare_session_value: dict | None = None,
        inspector_follow_mode_value: str = "FOLLOW_ACTIVE_PANE",
        selected_review_item_id_value: str = "",
        review_session_id_value: str = "",
        review_filter_value: str = "all",
        selected_workspace_mode_id_value: str = "STUDIO",
        selected_layout_profile_id_value: str = "DEFAULT",
        selected_panel_configuration_id_value: str = "",
        panel_visibility_state_value: dict | None = None,
    ):
        panel_visibility_state_value = dict(panel_visibility_state_value or {})
        return {
            "workspace_name": workspace_name,
            "ui_mode": ui_mode,
            "open_tabs": list(open_document_tabs or []),
            "tab_order": [str(tab.get("tab_id") or "") for tab in list(open_document_tabs or [])],
            "active_document_tab_id": str(active_document_tab_id or ""),
            "pinned_tabs": [],
            "tab_groups": [{"group_id": "PRIMARY", "label": "Primary View", "tab_ids": [str(tab.get("tab_id") or "") for tab in list(open_document_tabs or [])]}],
            "layout_profile_id": str(selected_layout_profile_id_value or "DEFAULT"),
            "selected_workspace_mode_id": str(selected_workspace_mode_id_value or "STUDIO"),
            "selected_panel_configuration_id": str(selected_panel_configuration_id_value or ""),
            "linked_context_files": [],
            "selected_file_id": str(selected_file_id or ""),
            "active_ribbon_tab": str(active_ribbon_tab_value or ""),
            "left_pane_state": "COLLAPSED" if left_pane_collapsed_value else "VISIBLE",
            "right_pane_state": "COLLAPSED" if right_pane_collapsed_value else workbench_inspector_mode_value,
            "bottom_pane_state": "COLLAPSED" if bottom_pane_collapsed_value else workbench_bottom_tab_value,
            "left_section_state": {
                "WORKSPACES": True,
                "FILE_EXPLORER": True,
                "ARCHIVE": True,
            },
            "favorites": {},
            "autosave_enabled": True,
            "split_view_enabled": bool(split_view_enabled_value),
            "split_view_mode": str(split_view_mode_value or "SINGLE"),
            "active_pane_id": str(active_pane_id_value or "LEFT"),
            "pane_documents": {
                "LEFT": {"document_id": str(left_pane_document_id_value or active_document_tab_id or "")},
                "RIGHT": {"document_id": str(right_pane_document_id_value or "")},
            },
            "compare_session": dict(compare_session_value or {}),
            "inspector_follow_mode": str(inspector_follow_mode_value or "FOLLOW_ACTIVE_PANE"),
            "selected_review_item_id": str(selected_review_item_id_value or ""),
            "review_session_id": str(review_session_id_value or ""),
            "review_filter": str(review_filter_value or "all"),
            "panel_visibility_state": panel_visibility_state_value,
            "layout_profile": {
                "layout_profile_id": str(selected_layout_profile_id_value or "DEFAULT"),
                "workspace_mode_id": str(selected_workspace_mode_id_value or "STUDIO"),
                "panel_configuration_id": str(selected_panel_configuration_id_value or ""),
                "name": "Default Layout",
                "left_width": "92px",
                "right_width": "320px",
                "bottom_height": "180px",
                "left_collapsed": bool(left_pane_collapsed_value),
                "right_collapsed": bool(right_pane_collapsed_value),
                "bottom_collapsed": bool(bottom_pane_collapsed_value),
                "split_view_state": {
                    "enabled": bool(split_view_enabled_value),
                    "mode": str(split_view_mode_value or "SINGLE"),
                    "pane_ids": ["LEFT", "RIGHT"],
                    "active_pane_id": str(active_pane_id_value or "LEFT"),
                    "orientation": str(split_orientation_value or "VERTICAL"),
                    "divider_positions": {"primary": "50%"},
                    "compare_mode": str((compare_session_value or {}).get("compare_type") or ""),
                    "group_ids": ["PRIMARY"],
                },
                "active_split_mode": str(split_view_mode_value or "SINGLE"),
            },
        }

    def apply_workspace_payload(payload: dict):
        open_tabs = list(payload.get("open_tabs", []))
        active_tab_id = str(payload.get("active_document_tab_id") or "")
        active_tab = next((tab for tab in open_tabs if str(tab.get("tab_id") or "") == active_tab_id), {})
        if not active_tab and open_tabs:
            active_tab = dict(open_tabs[0])
        source_lane = str(active_tab.get("source_lane") or "STUDIO").upper()
        active_document_id = str(active_tab.get("document_id") or active_tab.get("tab_id") or "")
        pane_documents = dict(payload.get("pane_documents", {}) or {})
        split_view_state = dict((payload.get("layout_profile", {}) or {}).get("split_view_state", {}) or {})
        return {
            "selected_nav_submodule": "REVIEW" if source_lane == "REVIEW" else "STUDIO",
            "selected_workbench_document_id": active_document_id if source_lane == "STUDIO" else "",
            "selected_review_document_id": active_document_id if source_lane == "REVIEW" else "",
            "active_ribbon_tab": str(payload.get("active_ribbon_tab") or ""),
            "shell_ui_mode": str(payload.get("ui_mode") or ""),
            "left_pane_collapsed": bool((payload.get("layout_profile", {}) or {}).get("left_collapsed", False)),
            "right_pane_collapsed": bool((payload.get("layout_profile", {}) or {}).get("right_collapsed", False)),
            "bottom_pane_collapsed": bool((payload.get("layout_profile", {}) or {}).get("bottom_collapsed", False)),
            "workbench_bottom_tab": str(payload.get("bottom_pane_state") or "SCRATCHPAD"),
            "workbench_inspector_mode": str(payload.get("right_pane_state") or "DOCUMENT"),
            "active_document_tab_id": active_tab_id,
            "split_view_enabled": bool(payload.get("split_view_enabled") or split_view_state.get("enabled")),
            "split_view_mode": str(payload.get("split_view_mode") or split_view_state.get("mode") or "SINGLE"),
            "split_orientation": str(split_view_state.get("orientation") or "VERTICAL"),
            "active_pane_id": str(payload.get("active_pane_id") or split_view_state.get("active_pane_id") or "LEFT"),
            "pane_documents": pane_documents,
            "compare_session": dict(payload.get("compare_session", {}) or {}),
            "inspector_follow_mode": str(payload.get("inspector_follow_mode") or "FOLLOW_ACTIVE_PANE"),
            "selected_review_item_id": str(payload.get("selected_review_item_id") or ""),
            "review_session_id": str(payload.get("review_session_id") or ""),
            "review_filter": str(payload.get("review_filter") or "all"),
            "selected_workspace_mode_id": str(payload.get("selected_workspace_mode_id") or (payload.get("layout_profile", {}) or {}).get("workspace_mode_id") or "STUDIO"),
            "selected_layout_profile_id": str(payload.get("layout_profile_id") or (payload.get("layout_profile", {}) or {}).get("layout_profile_id") or "DEFAULT"),
            "selected_panel_configuration_id": str(payload.get("selected_panel_configuration_id") or (payload.get("layout_profile", {}) or {}).get("panel_configuration_id") or ""),
            "panel_visibility_state": dict(payload.get("panel_visibility_state", {})),
        }

    def task_type_options():
        return [
            "ARRIVAL",
            "DEPARTURE",
            "CREW_CHANGE",
            "INSPECTION",
            "CERTIFICATE_RENEWAL",
            "PORT_PACKAGE",
            "CUSTOMS_IMMIGRATION",
            "FORM_RECONSTRUCTION",
            "VALIDATION_LAB",
        ]

    def template_type_options():
        return [
            "STANDARD_WORKSPACE",
            "TASK_WORKSPACE",
            "OPERATIONAL_WORKFLOW",
            "STUDIO_RECONSTRUCTION",
        ]

    def parse_slot_definitions(raw_text: str):
        slot_defs = []
        for index, raw_line in enumerate(str(raw_text or "").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            label = parts[0] if parts else f"Slot {index}"
            required = (parts[1].upper() if len(parts) > 1 else "REQUIRED") != "OPTIONAL"
            file_types = [value.strip().upper() for value in (parts[2] if len(parts) > 2 else "PDF").split(",") if value.strip()]
            source_role = parts[3].upper() if len(parts) > 3 else "REFERENCE"
            allow_multiple = (parts[4].upper() if len(parts) > 4 else "SINGLE") == "MULTI"
            slot_defs.append(
                {
                    "slot_id": f"{_safe_filename(label).upper()}_SLOT",
                    "label": label,
                    "required": required,
                    "accepted_file_types": file_types,
                    "binding_type": "DOCUMENT",
                    "validation_rules": ["required"] if required else [],
                    "tce_relationship": source_role,
                    "default_usage": label,
                    "allow_multiple": allow_multiple,
                    "source_role": source_role,
                }
            )
        return slot_defs

    def parse_checklist_template(raw_text: str):
        checklist = []
        for raw_line in str(raw_text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            group = parts[0] if len(parts) > 1 else "GENERAL"
            label = parts[-2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else parts[0])
            required_token = parts[-1].upper() if len(parts) > 1 else "REQUIRED"
            checklist.append(
                {
                    "group": group,
                    "label": label,
                    "required": required_token != "OPTIONAL",
                }
            )
        return checklist

    def build_ctx(
        state_obj,
        *,
        selected_crew_id_value="",
        selected_port_name_value="",
        selected_review_document_id_value="",
        review_filter_mode_value="all",
        selected_workbench_document_id_value="",
        selected_workbench_anchor_id_value="",
        selected_workbench_cell_id_value="",
        selected_workbench_block_id_value="",
        workbench_selected_page_value=1,
        workbench_tool_mode_value="SELECT",
        workbench_center_mode_value="PREVIEW",
        workbench_bottom_tab_value="SCRATCHPAD",
        workbench_inspector_mode_value="DOCUMENT",
        workbench_filter_document_type_value="",
        workbench_filter_status_value="",
        workbench_search_text_value="",
        active_menu_value=None,
        active_dropdown_value=None,
        active_dialog_value=None,
        command_palette_open_value=None,
        command_palette_query_value=None,
        selected_command_id_value=None,
        left_pane_collapsed_value=None,
        right_pane_collapsed_value=None,
        bottom_pane_collapsed_value=None,
        active_ribbon_tab_value=None,
        selected_workspace_id_value=None,
        workspace_snapshot_id_value=None,
        workspace_dirty_value=None,
        restore_candidate_workspace_id_value=None,
        restore_candidate_snapshot_id_value=None,
        selected_task_workspace_id_value=None,
        selected_template_id_value=None,
        template_wizard_id_value=None,
        recent_file_action_result_value=None,
        selected_file_action_value=None,
        explorer_active_section_value=None,
        split_view_enabled_value=None,
        split_view_mode_value=None,
        split_orientation_value=None,
        active_pane_id_value=None,
        left_pane_document_id_value=None,
        right_pane_document_id_value=None,
        compare_session_value=None,
        inspector_follow_mode_value=None,
        selected_review_item_id_value=None,
        review_mode_enabled_value=None,
        review_annotation_tool_value=None,
        review_comment_draft_value=None,
        selected_workspace_mode_id_value=None,
        selected_layout_profile_id_value=None,
        selected_panel_configuration_id_value=None,
        layout_editor_enabled_value=None,
        layout_editor_dirty_value=None,
        panel_visibility_state_value=None,
        workspace_mode_switch_pending_value=None,
    ):
        active_menu_effective = active_nav_menu if active_menu_value is None else active_menu_value
        active_dropdown_effective = active_nav_dropdown if active_dropdown_value is None else active_dropdown_value
        active_dialog_effective = active_nav_dialog if active_dialog_value is None else active_dialog_value
        command_palette_open_effective = command_palette_open if command_palette_open_value is None else bool(command_palette_open_value)
        command_palette_query_effective = command_palette_query if command_palette_query_value is None else str(command_palette_query_value or "")
        selected_command_id_effective = selected_command_id if selected_command_id_value is None else str(selected_command_id_value or "")
        left_pane_collapsed_effective = left_pane_collapsed if left_pane_collapsed_value is None else bool(left_pane_collapsed_value)
        right_pane_collapsed_effective = right_pane_collapsed if right_pane_collapsed_value is None else bool(right_pane_collapsed_value)
        bottom_pane_collapsed_effective = bottom_pane_collapsed if bottom_pane_collapsed_value is None else bool(bottom_pane_collapsed_value)
        active_ribbon_tab_effective = active_ribbon_tab if active_ribbon_tab_value is None else str(active_ribbon_tab_value or "")
        selected_workspace_id_effective = selected_workspace_id if selected_workspace_id_value is None else str(selected_workspace_id_value or "")
        workspace_snapshot_id_effective = workspace_snapshot_id if workspace_snapshot_id_value is None else str(workspace_snapshot_id_value or "")
        workspace_dirty_effective = workspace_dirty if workspace_dirty_value is None else bool(workspace_dirty_value)
        restore_candidate_workspace_id_effective = restore_candidate_workspace_id if restore_candidate_workspace_id_value is None else str(restore_candidate_workspace_id_value or "")
        restore_candidate_snapshot_id_effective = restore_candidate_snapshot_id if restore_candidate_snapshot_id_value is None else str(restore_candidate_snapshot_id_value or "")
        selected_task_workspace_id_effective = selected_task_workspace_id if selected_task_workspace_id_value is None else str(selected_task_workspace_id_value or "")
        selected_template_id_effective = selected_template_id if selected_template_id_value is None else str(selected_template_id_value or "")
        template_wizard_id_effective = template_wizard_id if template_wizard_id_value is None else str(template_wizard_id_value or "")
        recent_file_action_result_effective = file_service.get_last_action_result() if recent_file_action_result_value is None else dict(recent_file_action_result_value or {})
        selected_file_action_effective = str(selected_file_action_value or "")
        explorer_active_section_effective = str(explorer_active_section_value or "FILE_EXPLORER")
        split_view_enabled_effective = False if split_view_enabled_value is None else bool(split_view_enabled_value)
        split_view_mode_effective = "SINGLE" if split_view_mode_value is None else str(split_view_mode_value or "SINGLE").upper()
        split_orientation_effective = "VERTICAL" if split_orientation_value is None else str(split_orientation_value or "VERTICAL").upper()
        active_pane_id_effective = "LEFT" if active_pane_id_value is None else str(active_pane_id_value or "LEFT").upper()
        left_pane_document_id_effective = str(left_pane_document_id_value or selected_workbench_document_id_value or selected_review_document_id_value or "")
        right_pane_document_id_effective = str(right_pane_document_id_value or "")
        compare_session_effective = {key: value for key, value in dict(compare_session_value or {}).items() if value not in ("", None, [], {})}
        inspector_follow_mode_effective = "FOLLOW_ACTIVE_PANE" if inspector_follow_mode_value is None else str(inspector_follow_mode_value or "FOLLOW_ACTIVE_PANE")
        selected_review_item_id_effective = selected_review_item_id if selected_review_item_id_value is None else str(selected_review_item_id_value or "")
        review_mode_enabled_effective = (selected_nav_submodule == "REVIEW") if review_mode_enabled_value is None else bool(review_mode_enabled_value)
        review_annotation_tool_effective = "NOTE_MARKER" if review_annotation_tool_value is None else str(review_annotation_tool_value or "NOTE_MARKER").upper()
        review_comment_draft_effective = "" if review_comment_draft_value is None else str(review_comment_draft_value or "")
        default_workspace_mode = {
            "STUDIO": "STUDIO",
            "REVIEW": "REVIEW",
            "CONTROL_ROOM": "BRIDGE_OPS",
            "OUTPUT": "PACKAGE",
            "ARCHIVE": "PACKAGE",
        }.get(selected_nav_submodule, "VALIDATION")
        selected_workspace_mode_id_effective = default_workspace_mode if selected_workspace_mode_id_value is None else str(selected_workspace_mode_id_value or default_workspace_mode or "STUDIO").upper()
        selected_layout_profile_id_effective = "DEFAULT" if selected_layout_profile_id_value is None else str(selected_layout_profile_id_value or "DEFAULT")
        selected_panel_configuration_id_effective = "" if selected_panel_configuration_id_value is None else str(selected_panel_configuration_id_value or "")
        layout_editor_enabled_effective = False if layout_editor_enabled_value is None else bool(layout_editor_enabled_value)
        layout_editor_dirty_effective = False if layout_editor_dirty_value is None else bool(layout_editor_dirty_value)
        panel_visibility_state_effective = {} if panel_visibility_state_value is None else dict(panel_visibility_state_value or {})
        workspace_mode_switch_pending_effective = False if workspace_mode_switch_pending_value is None else bool(workspace_mode_switch_pending_value)

        def build_shell_href(**overrides):
            params = {
                "nav_module": selected_nav_module,
                "nav_submodule": selected_nav_submodule,
                "crew_id": selected_crew_id_value,
                "port_name": selected_port_name_value,
                "review_document_id": selected_review_document_id_value,
                "review_filter": review_filter_mode_value,
                "selected_review_item_id": selected_review_item_id_effective,
                "review_annotation_tool": review_annotation_tool_effective,
                "review_comment_draft": review_comment_draft_effective,
                "workbench_document_id": selected_workbench_document_id_value,
                "workbench_anchor_id": selected_workbench_anchor_id_value,
                "workbench_cell_id": selected_workbench_cell_id_value,
                "workbench_block_id": selected_workbench_block_id_value,
                "workbench_tool": workbench_tool_mode_value,
                "workbench_center": workbench_center_mode_value,
                "workbench_tab": workbench_bottom_tab_value,
                "workbench_inspector": workbench_inspector_mode_value,
                "workbench_document_type": workbench_filter_document_type_value,
                "workbench_status": workbench_filter_status_value,
                "workbench_search": workbench_search_text_value,
                "nav_menu": active_menu_effective,
                "nav_dropdown": active_dropdown_effective,
                "nav_dialog": active_dialog_effective,
                "command_palette": "open" if command_palette_open_effective else "",
                "command_query": command_palette_query_effective,
                "selected_command": selected_command_id_effective,
                "pane_left": "collapsed" if left_pane_collapsed_effective else "",
                "pane_right": "collapsed" if right_pane_collapsed_effective else "",
                "pane_bottom": "collapsed" if bottom_pane_collapsed_effective else "",
                "split_enabled": "true" if split_view_enabled_effective else "",
                "split_mode": split_view_mode_effective if split_view_enabled_effective else "",
                "split_orientation": split_orientation_effective if split_view_enabled_effective else "",
                "active_pane_id": active_pane_id_effective,
                "left_document_id": left_pane_document_id_effective,
                "right_document_id": right_pane_document_id_effective,
                "inspector_follow_mode": inspector_follow_mode_effective,
                "workspace_mode_id": selected_workspace_mode_id_effective,
                "layout_profile_id": selected_layout_profile_id_effective,
                "panel_configuration_id": selected_panel_configuration_id_effective,
                "layout_editor": "open" if layout_editor_enabled_effective else "",
            }
            params.update(overrides)
            clean_params = {key: value for key, value in params.items() if value not in ("", None, False)}
            query = urlencode(clean_params)
            return f"/portalis?{query}" if query else "/portalis"

        crew_items = list_crew(portalis_root)
        certificate_items = list_certificates(portalis_root)
        port_items = list_ports(portalis_root)
        control_room = refresh_control_room_state(portalis_root)
        review_items = control_room["review_items"]
        document_entries = registry.list_documents()
        workbench_packet = build_document_workbench(
            portalis_root,
            selected_document_id=selected_workbench_document_id_value,
            selected_anchor_id=selected_workbench_anchor_id_value,
            selected_cell_id=selected_workbench_cell_id_value,
            selected_block_id=selected_workbench_block_id_value,
            selected_page=workbench_selected_page_value,
            active_tool_mode=workbench_tool_mode_value,
            active_center_mode=workbench_center_mode_value,
            active_bottom_tab=workbench_bottom_tab_value,
            inspector_mode=workbench_inspector_mode_value,
            filter_document_type=workbench_filter_document_type_value,
            filter_status=workbench_filter_status_value,
            search_text=workbench_search_text_value,
        )

        state_obj.crew_registry.selected_crew_id = selected_crew_id_value or None
        state_obj.port_requirements.selected_port_name = selected_port_name_value or None
        build_portalis_state_snapshot(
            state_obj,
            crew_count=len(crew_items),
            certificate_count=len(certificate_items),
            port_count=len(port_items),
            document_count=len(document_entries),
            review_items=review_items,
        )

        selected_crew_value = None
        if selected_crew_id_value:
            try:
                selected_crew_value = load_crew_record(portalis_root, selected_crew_id_value)
            except Exception:
                selected_crew_value = None

        selected_port_value = None
        if selected_port_name_value:
            selected_port_value = load_port_requirement(portalis_root, selected_port_name_value)

        cert_check_value = []
        if selected_port_value:
            cert_check_value = check_required_certificates(
                selected_port_value["certificate_requirements"],
                certificate_items,
            )

        selected_review_item_value = None
        for item in review_items:
            if item.document_id == selected_review_document_id_value:
                selected_review_item_value = item
                break

        selected_review_document_value = None
        if selected_review_document_id_value:
            selected_review_document_value = registry.get_document(selected_review_document_id_value)
        review_field_rows_value = _build_review_field_rows(
            selected_review_item_value,
            selected_review_document_value,
        )
        filtered_review_field_rows_value = _filter_review_field_rows(
            review_field_rows_value,
            review_filter_mode_value,
        )
        global_review_queue_value = control_room["global_review_queue"]
        watch_queue_value = control_room["watch_queue"]
        reminder_queue_value = control_room.get("reminder_queue", [])
        notification_queue_value = control_room.get("notification_queue", [])
        transport_queue_value = control_room.get("transport_queue", [])
        alert_feed_value = control_room.get("alert_feed", [])
        incident_feed_value = control_room.get("incident_feed", [])
        export_queue_value = control_room.get("export_queue", [])
        intake_queue_value = control_room.get("intake_queue", [])
        dropzone_queue_value = control_room.get("dropzone_queue", [])
        dashboard_summary_value = control_room["dashboard_summary"]
        dashboard_tce_delta_value = control_room["dashboard_tce_delta"]
        shell_workspace_summary = {
            "selected_document_id": selected_workbench_document_id_value or selected_review_document_id_value,
            "selected_anchor_id": selected_workbench_anchor_id_value,
            "selected_cell_id": selected_workbench_cell_id_value,
            "selected_block_id": selected_workbench_block_id_value,
            "review_queue_count": len(review_items),
            "workbench_document_count": workbench_packet.get("document_count", 0),
            "active_alert_count": dashboard_summary_value.get("total_active_alerts", 0),
            "open_incident_count": dashboard_summary_value.get("total_open_incidents", 0),
        }
        shell_ui_mode = default_workspace_mode
        workspace_entries = workspace_service.list_workspaces()
        last_session = workspace_service.load_last_session()
        recovery_state = workspace_service.load_recovery_state()
        task_entries = task_service.list_task_workspaces()
        active_task_workspace = task_service.load_task_workspace(selected_task_workspace_id_effective) if selected_task_workspace_id_effective else {}
        if not active_task_workspace:
            active_task_workspace = task_service.get_last_active_task_workspace()
            if active_task_workspace and not selected_task_workspace_id_effective:
                selected_task_workspace_id_effective = str(active_task_workspace.get("task_workspace_id") or "")
        template_entries = template_service.list_templates()
        active_template = template_service.load_template(selected_template_id_effective) if selected_template_id_effective else {}
        if not active_template and template_entries:
            favorite_template = next((item for item in template_entries if item.get("favorite")), {})
            active_template = favorite_template or {}
            if active_template and not selected_template_id_effective:
                selected_template_id_effective = str(active_template.get("template_id") or "")
        active_template_wizard = template_service.load_template_wizard(template_wizard_id_effective) if template_wizard_id_effective else {}
        review_scope_type = "COMPARE_SESSION" if compare_session_effective else ("TASK_WORKSPACE" if selected_task_workspace_id_effective else "DOCUMENT")
        review_scope_id = (
            str(compare_session_effective.get("compare_session_id") or compare_session_effective.get("left_source_id") or compare_session_effective.get("right_source_id") or "")
            if compare_session_effective
            else str(selected_task_workspace_id_effective or selected_workbench_document_id_value or selected_review_document_id_value or "GLOBAL")
        )
        active_review_session = review_layer_service.get_or_create_review_session(
            scope_type=review_scope_type,
            scope_id=review_scope_id,
            task_workspace_id=selected_task_workspace_id_effective,
        )
        review_session_id_effective = str(active_review_session.get("review_session_id") or "")
        review_document_id_effective = str(selected_workbench_document_id_value or selected_review_document_id_value or left_pane_document_id_effective or "")
        review_layer_items = review_layer_service.list_review_items(
            review_session_id=review_session_id_effective,
            document_id=review_document_id_effective,
            status_filter=review_filter_mode_value,
        )
        if not selected_review_item_id_effective and review_layer_items:
            selected_review_item_id_effective = str(review_layer_items[0].get("review_item_id") or "")
        selected_review_layer_item = review_layer_service.get_review_item(selected_review_item_id_effective) if selected_review_item_id_effective else {}
        review_comments = review_layer_service.list_comments(review_item_id=selected_review_item_id_effective) if selected_review_item_id_effective else []
        review_annotations = review_layer_service.list_annotations(
            document_id=review_document_id_effective,
            pane_id=active_pane_id_effective,
            review_session_id=review_session_id_effective,
        )
        review_audit_entries = review_layer_service.list_audit_entries(
            review_session_id=review_session_id_effective,
            document_id=review_document_id_effective,
            related_review_item_id=selected_review_item_id_effective,
        )
        shell_status_summary = {
            "utc_now": utc_now_iso(),
            "crew_total": len(crew_items),
            "document_total": len(document_entries),
            "pending_review_total": len(review_items),
            "selected_port": selected_port_name_value,
        }
        workspace_modes = layout_service.list_workspace_modes()
        saved_layout_profiles = layout_service.list_layout_profiles()
        panel_configurations = layout_service.list_panel_configurations()
        active_workspace_mode_record = layout_service.switch_workspace_mode(selected_workspace_mode_id_effective)
        if not selected_layout_profile_id_effective or selected_layout_profile_id_effective == "DEFAULT":
            selected_layout_profile_id_effective = str(
                active_workspace_mode_record.get("default_layout_profile_id")
                or selected_layout_profile_id_effective
                or "DEFAULT"
            )
        active_layout_profile = layout_service.load_layout_profile(selected_layout_profile_id_effective)
        if not active_layout_profile and saved_layout_profiles:
            active_layout_profile = dict(saved_layout_profiles[0] or {})
            selected_layout_profile_id_effective = str(active_layout_profile.get("layout_profile_id") or selected_layout_profile_id_effective)
        if not selected_panel_configuration_id_effective:
            selected_panel_configuration_id_effective = str(
                active_layout_profile.get("panel_configuration_id")
                or active_workspace_mode_record.get("default_panel_configuration_id")
                or ""
            )
        active_panel_configuration = layout_service.load_panel_configuration(selected_panel_configuration_id_effective)
        if not active_panel_configuration and panel_configurations:
            active_panel_configuration = dict(panel_configurations[0] or {})
            selected_panel_configuration_id_effective = str(active_panel_configuration.get("panel_configuration_id") or selected_panel_configuration_id_effective)
        if not panel_visibility_state_effective:
            panel_visibility_state_effective = {
                "left_sidebar_visible": bool(active_panel_configuration.get("left_sidebar_visible", not left_pane_collapsed_effective)),
                "right_inspector_visible": bool(active_panel_configuration.get("right_inspector_visible", not right_pane_collapsed_effective)),
                "bottom_panel_visible": bool(active_panel_configuration.get("bottom_panel_visible", not bottom_pane_collapsed_effective)),
                "command_palette_enabled": bool(active_panel_configuration.get("command_palette_enabled", True)),
                "review_summary_visible": bool(active_panel_configuration.get("review_summary_visible", True)),
                "task_header_visible": bool(active_panel_configuration.get("task_header_visible", True)),
                "compare_summary_visible": bool(active_panel_configuration.get("compare_summary_visible", bool(compare_session_effective))),
                "active_sections": list(active_panel_configuration.get("active_sections", [])),
            }
        layout_editor_state = layout_service.get_layout_editor_state()
        if layout_editor_enabled_value is None:
            layout_editor_enabled_effective = bool(layout_editor_state.get("enabled"))
        if layout_editor_dirty_value is None:
            layout_editor_dirty_effective = bool(layout_editor_state.get("dirty"))
        if layout_editor_enabled_effective and not layout_editor_state:
            layout_editor_state = {
                "enabled": True,
                "editing_profile_id": selected_layout_profile_id_effective,
                "draft_panel_configuration": dict(panel_visibility_state_effective),
                "draft_dimensions": {
                    "left_width": str(active_layout_profile.get("left_width") or "92px"),
                    "right_width": str(active_layout_profile.get("right_width") or "320px"),
                    "bottom_height": str(active_layout_profile.get("bottom_height") or "180px"),
                },
                "preview_mode": "LIVE",
                "dirty": bool(layout_editor_dirty_effective),
            }
        effective_workspace_id = str(selected_workspace_id_effective or (workspace_entries[0]["workspace_id"] if workspace_entries else ""))
        selected_file_id_effective = selected_workbench_document_id_value or selected_review_document_id_value
        file_entries = file_service.list_workspace_files(workspace_id=effective_workspace_id or selected_nav_submodule)
        archive_entries = file_service.list_archived_files(workspace_id=effective_workspace_id or selected_nav_submodule)
        linked_file_entries = file_service.list_linked_files(workspace_id=effective_workspace_id or selected_nav_submodule)
        selected_file_entry = file_service.get_file(selected_file_id_effective, workspace_id=effective_workspace_id or selected_nav_submodule) if selected_file_id_effective else {}
        open_document_tabs = []
        if workbench_packet.get("selected_document"):
            selected_doc = dict(workbench_packet.get("selected_document") or {})
            selected_doc_file = file_service.get_file(str(selected_doc.get("document_id") or ""), workspace_id=effective_workspace_id or selected_nav_submodule)
            open_document_tabs.append(
                {
                    "tab_id": selected_doc.get("document_id"),
                    "document_id": selected_doc.get("document_id"),
                    "label": selected_doc_file.get("display_name") or selected_doc.get("display_name") or selected_doc.get("document_id"),
                    "source_lane": "STUDIO",
                    "opened_at": selected_doc.get("updated_at") or utc_now_iso(),
                }
            )
        if selected_review_document_value:
            selected_review_file = file_service.get_file(str(selected_review_document_value.get("document_id") or ""), workspace_id=effective_workspace_id or selected_nav_submodule)
            open_document_tabs.append(
                {
                    "tab_id": str(selected_review_document_value.get("document_id") or ""),
                    "document_id": str(selected_review_document_value.get("document_id") or ""),
                    "label": str(selected_review_file.get("display_name") or selected_review_document_value.get("display_name") or selected_review_document_value.get("document_id") or ""),
                    "source_lane": "REVIEW",
                    "opened_at": str(selected_review_document_value.get("updated_at") or utc_now_iso()),
                }
            )
        active_document_tab_id = selected_workbench_document_id_value or selected_review_document_id_value
        if not split_view_enabled_effective and split_view_mode_effective == "SINGLE":
            left_pane_document_id_effective = left_pane_document_id_effective or active_document_tab_id
        if not compare_session_effective and split_view_enabled_effective and right_pane_document_id_effective:
            compare_session_effective = {
                "compare_session_id": "COMPARE_SESSION_ACTIVE",
                "compare_type": "VARIANT_COMPARE" if active_ribbon_tab_effective == "VARIANTS" else "DOCUMENT_COMPARE",
                "left_source_id": left_pane_document_id_effective,
                "right_source_id": right_pane_document_id_effective,
                "summary_state": {
                    "left_label": left_pane_document_id_effective,
                    "right_label": right_pane_document_id_effective,
                    "session_summary": "Side-by-side compare ready.",
                },
            }
        workspace_snapshots = workspace_service.list_snapshots(effective_workspace_id) if effective_workspace_id else []
        selected_object_type = ""
        if selected_review_item_id_effective:
            selected_object_type = "REVIEW_ISSUE"
        elif selected_workbench_anchor_id_value:
            selected_object_type = "FIELD"
        elif selected_workbench_cell_id_value:
            selected_object_type = "CELL"
        elif selected_workbench_block_id_value:
            selected_object_type = "TABLE"
        elif selected_nav_submodule == "REVIEW" and selected_review_document_id_value:
            selected_object_type = "REVIEW_ISSUE"
        elif selected_nav_submodule == "STUDIO" and selected_workbench_document_id_value:
            selected_object_type = "DOCUMENT"
        navsys_shell = build_navsys_shell_state(
            selected_module=selected_nav_module,
            selected_submodule=selected_nav_submodule,
            ui_mode=shell_ui_mode,
            selected_item_id=selected_workbench_document_id_value or selected_review_document_id_value,
            selected_object_id=selected_workbench_anchor_id_value or selected_workbench_cell_id_value or selected_workbench_block_id_value,
            selected_object_type=selected_object_type,
            active_workspace_mode=workbench_center_mode_value if selected_nav_submodule == "STUDIO" else "WORKSPACE",
            left_pane_state="MODULE_RAIL",
            right_pane_state="INSPECTOR",
            bottom_pane_tab=workbench_bottom_tab_value if selected_nav_submodule == "STUDIO" else "CONTEXT",
            layout_mode="COUPLER_WIDE",
            active_menu=active_menu_effective,
            active_dropdown=active_dropdown_effective,
            active_dialog=active_dialog_effective,
            command_palette_open=command_palette_open_effective,
            command_palette_query=command_palette_query_effective,
            selected_command_id=selected_command_id_effective,
            left_pane_collapsed=left_pane_collapsed_effective,
            right_pane_collapsed=right_pane_collapsed_effective,
            bottom_pane_collapsed=bottom_pane_collapsed_effective,
            active_ribbon_tab=active_ribbon_tab_effective,
            open_document_tabs=open_document_tabs,
            active_document_tab_id=active_document_tab_id,
            split_view_enabled=split_view_enabled_effective,
            split_view_mode=split_view_mode_effective,
            split_orientation=split_orientation_effective,
            active_pane_id=active_pane_id_effective,
            pane_documents={
                "LEFT": {"document_id": left_pane_document_id_effective},
                "RIGHT": {"document_id": right_pane_document_id_effective},
            },
            compare_session=compare_session_effective,
            inspector_follow_mode=inspector_follow_mode_effective,
            selected_file_id=selected_file_id_effective,
            selected_file_status=str(selected_file_entry.get("status") or ""),
            selected_file_action=selected_file_action_effective,
            explorer_active_section=explorer_active_section_effective,
            archive_visible=selected_nav_submodule == "ARCHIVE",
            recent_file_action_result=recent_file_action_result_effective,
            pending_file_lifecycle_action={"action_id": selected_file_action_effective} if selected_file_action_effective else {},
            file_entries=file_entries,
            archive_entries=archive_entries,
            linked_file_entries=linked_file_entries,
            selected_workspace_id=effective_workspace_id or selected_nav_submodule,
            workspace_snapshot_id=workspace_snapshot_id_effective,
            workspace_dirty=bool(workspace_dirty_effective),
            restore_candidate_workspace_id=restore_candidate_workspace_id_effective or str(last_session.get("workspace_id") or recovery_state.get("workspace_id") or ""),
            restore_candidate_snapshot_id=restore_candidate_snapshot_id_effective or str(recovery_state.get("snapshot_id") or ""),
            workspace_entries=workspace_entries,
            selected_task_workspace_id=selected_task_workspace_id_effective,
            selected_template_id=selected_template_id_effective,
            selected_template_category=str((active_template or {}).get("category") or ""),
            selected_review_item_id=selected_review_item_id_effective,
            review_mode_enabled=review_mode_enabled_effective,
            review_filter=review_filter_mode_value,
            review_session_id=review_session_id_effective,
            review_pending_count=int(active_review_session.get("pending_count") or 0),
            review_annotation_tool=review_annotation_tool_effective,
            review_comment_draft=review_comment_draft_effective,
            review_signoff_state={
                "signed_off": bool(active_review_session.get("signed_off")),
                "signed_off_at": str(active_review_session.get("signed_off_at") or ""),
                "status": str(active_review_session.get("status") or ""),
            },
            selected_workspace_mode_id=selected_workspace_mode_id_effective,
            selected_layout_profile_id=selected_layout_profile_id_effective,
            selected_panel_configuration_id=selected_panel_configuration_id_effective,
            layout_editor_enabled=layout_editor_enabled_effective,
            layout_editor_dirty=layout_editor_dirty_effective or bool((layout_editor_state or {}).get("dirty")),
            panel_visibility_state=panel_visibility_state_effective,
            saved_layout_profiles=saved_layout_profiles,
            workspace_modes=workspace_modes,
            panel_configurations=panel_configurations,
            layout_editor_state=layout_editor_state,
            workspace_mode_switch_pending=workspace_mode_switch_pending_effective,
            active_layout_profile=active_layout_profile,
            active_panel_configuration=active_panel_configuration,
            template_entries=template_entries,
            active_template=active_template,
            template_wizard=active_template_wizard,
            review_items=review_layer_items,
            annotations=review_annotations,
            review_comments=review_comments,
            review_session=active_review_session,
            review_audit_entries=review_audit_entries,
            task_entries=task_entries,
            active_task_workspace=active_task_workspace,
            task_history_visible=True,
            workspace_summary=shell_workspace_summary,
            status_summary=shell_status_summary,
        )
        navsys_shell["command_palette_toggle_href"] = build_shell_href(
            command_palette="" if command_palette_open_effective else "open",
        )
        navsys_shell["command_palette_close_href"] = build_shell_href(
            command_palette="",
            command_query="",
            selected_command="",
        )
        navsys_shell["restore_layout_href"] = build_shell_href(
            pane_left="",
            pane_right="",
            pane_bottom="",
        )
        navsys_shell["left_pane_toggle_href"] = build_shell_href(
            pane_left="" if left_pane_collapsed_effective else "collapsed",
        )
        navsys_shell["right_pane_toggle_href"] = build_shell_href(
            pane_right="" if right_pane_collapsed_effective else "collapsed",
        )
        navsys_shell["bottom_pane_toggle_href"] = build_shell_href(
            pane_bottom="" if bottom_pane_collapsed_effective else "collapsed",
        )
        navsys_shell["split_view_toggle_href"] = build_shell_href(
            split_enabled="" if split_view_enabled_effective else "true",
            split_mode="TWO_PANE_VERTICAL" if not split_view_enabled_effective else "SINGLE",
            right_document_id=right_pane_document_id_effective if not split_view_enabled_effective else "",
        )
        navsys_shell["split_swap_href"] = build_shell_href(
            split_enabled="true",
            split_mode=split_view_mode_effective if split_view_enabled_effective else "TWO_PANE_VERTICAL",
            left_document_id=right_pane_document_id_effective,
            right_document_id=left_pane_document_id_effective,
            active_pane_id="RIGHT" if active_pane_id_effective == "LEFT" else "LEFT",
        )
        for quick_action in navsys_shell.get("quick_actions", []):
            quick_action["href"] = build_shell_href(**dict(quick_action.get("target_params") or {}))
        for command in (navsys_shell.get("command_palette", {}) or {}).get("commands", []):
            command["href"] = build_shell_href(
                selected_command=command.get("command_id", ""),
                **dict(command.get("target_params") or {}),
            )
        shell_tce = build_navsys_shell_tce_delta(navsys_shell)

        return {
            "usb_root": str(USB_ROOT),
            "utc_now": utc_now_iso(),
            "state": state_obj,
            "crew": crew_items,
            "selected_crew": selected_crew_value,
            "selected_crew_id": selected_crew_id_value,
            "ports": port_items,
            "selected_port": selected_port_value,
            "selected_port_name": selected_port_name_value,
            "saved": False,
            "errors": [],
            "generated_paths": [],
            "generated_preview": "",
            "certificates": certificate_items,
            "cert_check": cert_check_value,
            "port_form": {
                "port_name": selected_port_value["port_name"] if selected_port_value else selected_port_name_value,
                "country": selected_port_value["country"] if selected_port_value else "",
                "required_docs": list_to_textarea(selected_port_value["required_docs"]) if selected_port_value else "",
                "non_standard_forms": list_to_textarea(selected_port_value["non_standard_forms"]) if selected_port_value else "",
                "certificate_requirements": list_to_textarea(selected_port_value["certificate_requirements"]) if selected_port_value else "",
                "notes": selected_port_value["notes"] if selected_port_value else "",
            },
            "document_entries": list(reversed(document_entries[-10:])),
            "workbench_documents": workbench_packet.get("documents", []),
            "selected_workbench_document_id": selected_workbench_document_id_value,
            "selected_workbench_anchor_id": selected_workbench_anchor_id_value,
            "selected_workbench_cell_id": selected_workbench_cell_id_value,
            "selected_workbench_block_id": selected_workbench_block_id_value,
            "selected_workbench_document": workbench_packet.get("selected_document"),
            "selected_workbench_anchor": workbench_packet.get("selected_anchor"),
            "selected_workbench_cell": workbench_packet.get("selected_cell"),
            "selected_workbench_block": workbench_packet.get("selected_block"),
            "workbench_anchors": workbench_packet.get("anchors", []),
            "workbench_selected_page": workbench_packet.get("selected_page", workbench_selected_page_value),
            "workbench_tool_mode": workbench_packet.get("active_tool_mode", workbench_tool_mode_value),
            "workbench_center_mode": workbench_packet.get("active_center_mode", workbench_center_mode_value),
            "workbench_bottom_tab": workbench_packet.get("active_bottom_tab", workbench_bottom_tab_value),
            "workbench_inspector_mode": workbench_packet.get("inspector_mode", workbench_inspector_mode_value),
            "workbench_filter_document_type": workbench_filter_document_type_value,
            "workbench_filter_status": workbench_filter_status_value,
            "workbench_search_text": workbench_search_text_value,
            "workbench_document_type_options": workbench_packet.get("document_type_options", []),
            "workbench_status_options": workbench_packet.get("status_options", []),
            "workbench_tool_mode_options": workbench_packet.get("tool_mode_options", []),
            "workbench_center_mode_options": workbench_packet.get("center_mode_options", []),
            "workbench_bottom_tab_options": workbench_packet.get("bottom_tab_options", []),
            "workbench_inspector_mode_options": workbench_packet.get("inspector_mode_options", []),
            "workbench_menu_categories": workbench_packet.get("menu_categories", []),
            "workbench_action_strip": workbench_packet.get("action_strip", []),
            "workbench_pane_state": workbench_packet.get("pane_state", {}),
            "workbench_state": workbench_packet.get("state", {}),
            "workbench_summary": {
                "document_count": workbench_packet.get("document_count", 0),
                "updated_at": workbench_packet.get("updated_at", ""),
            },
            "review_items": review_items,
            "selected_review_document_id": selected_review_document_id_value,
            "selected_review_item": selected_review_item_value,
            "selected_review_document": selected_review_document_value,
            "review_field_rows": filtered_review_field_rows_value,
            "review_field_rows_all": review_field_rows_value,
            "review_filter_mode": review_filter_mode_value,
            "prioritized_field_queue": list(getattr(selected_review_item_value, "prioritized_field_queue", []) or (selected_review_document_value or {}).get("prioritized_field_queue", [])),
            "global_review_queue": global_review_queue_value,
            "watch_queue": watch_queue_value,
            "reminder_queue": reminder_queue_value,
            "notification_queue": notification_queue_value,
            "transport_queue": transport_queue_value,
            "alert_feed": alert_feed_value,
            "incident_feed": incident_feed_value,
            "export_queue": export_queue_value,
            "intake_queue": intake_queue_value,
            "dropzone_queue": dropzone_queue_value,
            "dashboard_summary": dashboard_summary_value,
            "dashboard_tce_delta": dashboard_tce_delta_value,
            "navsys_shell": navsys_shell,
            "navsys_shell_tce": shell_tce,
            "selected_nav_module": selected_nav_module,
            "selected_nav_submodule": selected_nav_submodule,
            "active_nav_menu": active_menu_effective,
            "active_nav_dropdown": active_dropdown_effective,
            "active_nav_dialog": active_dialog_effective,
            "command_palette_open": command_palette_open_effective,
            "command_palette_query": command_palette_query_effective,
            "selected_command_id": selected_command_id_effective,
            "left_pane_collapsed": left_pane_collapsed_effective,
            "right_pane_collapsed": right_pane_collapsed_effective,
            "bottom_pane_collapsed": bottom_pane_collapsed_effective,
            "active_ribbon_tab": active_ribbon_tab_effective,
            "selected_workspace_id": effective_workspace_id,
            "selected_file_id": selected_file_id_effective,
            "selected_file_entry": selected_file_entry,
            "file_entries": file_entries,
            "archive_entries": archive_entries,
            "linked_file_entries": linked_file_entries,
            "recent_file_action_result": recent_file_action_result_effective,
            "split_view_enabled": split_view_enabled_effective,
            "split_view_mode": split_view_mode_effective,
            "split_orientation": split_orientation_effective,
            "active_pane_id": active_pane_id_effective,
            "left_pane_document_id": left_pane_document_id_effective,
            "right_pane_document_id": right_pane_document_id_effective,
            "compare_session": compare_session_effective,
            "inspector_follow_mode": inspector_follow_mode_effective,
            "workspace_snapshot_id": workspace_snapshot_id_effective,
            "workspace_dirty": bool(workspace_dirty_effective),
            "selected_workspace_mode_id": selected_workspace_mode_id_effective,
            "selected_layout_profile_id": selected_layout_profile_id_effective,
            "selected_panel_configuration_id": selected_panel_configuration_id_effective,
            "active_workspace_mode_record": active_workspace_mode_record,
            "saved_layout_profiles": saved_layout_profiles,
            "panel_configurations": panel_configurations,
            "active_layout_profile": active_layout_profile,
            "active_panel_configuration": active_panel_configuration,
            "panel_visibility_state": panel_visibility_state_effective,
            "layout_editor_enabled": layout_editor_enabled_effective,
            "layout_editor_dirty": layout_editor_dirty_effective or bool((layout_editor_state or {}).get("dirty")),
            "layout_editor_state": layout_editor_state,
            "workspace_modes": workspace_modes,
            "workspace_mode_switch_pending": workspace_mode_switch_pending_effective,
            "workspace_entries": workspace_entries,
            "workspace_snapshots": workspace_snapshots,
            "selected_task_workspace_id": selected_task_workspace_id_effective,
            "task_entries": task_entries,
            "active_task_workspace": active_task_workspace,
            "task_type_options": task_type_options(),
            "selected_template_id": selected_template_id_effective,
            "template_entries": template_entries,
            "active_template": active_template,
            "active_template_wizard": active_template_wizard,
            "selected_review_item_id": selected_review_item_id_effective,
            "selected_review_layer_item": selected_review_layer_item,
            "review_layer_items": review_layer_items,
            "review_annotations": review_annotations,
            "review_comments": review_comments,
            "active_review_session": active_review_session,
            "review_audit_entries": review_audit_entries,
            "review_mode_enabled": review_mode_enabled_effective,
            "review_annotation_tool": review_annotation_tool_effective,
            "review_comment_draft": review_comment_draft_effective,
            "template_type_options": template_type_options(),
            "template_categories": template_service.list_template_categories(),
            "last_session_workspace_id": last_session.get("workspace_id", ""),
            "recovery_workspace_id": recovery_state.get("workspace_id", ""),
            "recovery_snapshot_id": recovery_state.get("snapshot_id", ""),
            "last_import_document_id": state_obj.document_registry.last_import_document_id,
            "last_import_manifest_path": state_obj.document_registry.last_import_manifest_path,
        }

    state = load_portalis_state(str(state_path))
    selected_crew_id = request.args.get("crew_id", "").strip() or (state.crew_registry.selected_crew_id or "")
    selected_port_name = request.args.get("port_name", "").strip() or (state.port_requirements.selected_port_name or state.voyage.arrival_port or "")
    selected_review_document_id = request.args.get("review_document_id", "").strip() or (state.review_queue.last_document_id or "")
    selected_workbench_document_id = request.args.get("workbench_document_id", "").strip()
    selected_workbench_anchor_id = request.args.get("workbench_anchor_id", "").strip()
    selected_workbench_cell_id = request.args.get("workbench_cell_id", "").strip()
    selected_workbench_block_id = request.args.get("workbench_block_id", "").strip()
    workbench_tool_mode = request.args.get("workbench_tool", "").strip().upper() or "SELECT"
    workbench_center_mode = request.args.get("workbench_center", "").strip().upper() or "PREVIEW"
    workbench_bottom_tab = request.args.get("workbench_tab", "").strip().upper() or "SCRATCHPAD"
    workbench_inspector_mode = request.args.get("workbench_inspector", "").strip().upper() or "DOCUMENT"
    try:
        workbench_selected_page = max(1, int(request.args.get("workbench_page", "1").strip() or "1"))
    except ValueError:
        workbench_selected_page = 1
    review_filter_mode = request.args.get("review_filter", "").strip() or "all"
    workbench_filter_document_type = request.args.get("workbench_document_type", "").strip()
    workbench_filter_status = request.args.get("workbench_status", "").strip().upper()
    workbench_search_text = request.args.get("workbench_search", "").strip()
    selected_nav_module = request.args.get("nav_module", "").strip().upper() or "PORTALIS"
    selected_nav_submodule = request.args.get("nav_submodule", "").strip().upper() or "STUDIO"
    active_nav_menu = request.args.get("nav_menu", "").strip().upper()
    active_nav_dropdown = request.args.get("nav_dropdown", "").strip().upper()
    active_nav_dialog = request.args.get("nav_dialog", "").strip().upper()
    command_palette_open = _as_bool_flag(request.args.get("command_palette", ""))
    command_palette_query = request.args.get("command_query", "").strip()
    selected_command_id = request.args.get("selected_command", "").strip().upper()
    active_ribbon_tab = request.args.get("ribbon_tab", "").strip().upper()
    left_pane_collapsed = str(request.args.get("pane_left", "")).strip().lower() == "collapsed"
    right_pane_collapsed = str(request.args.get("pane_right", "")).strip().lower() == "collapsed"
    bottom_pane_collapsed = str(request.args.get("pane_bottom", "")).strip().lower() == "collapsed"
    selected_workspace_id = request.args.get("workspace_id", "").strip()
    workspace_snapshot_id = request.args.get("workspace_snapshot_id", "").strip()
    workspace_dirty = _as_bool_flag(request.args.get("workspace_dirty", ""))
    restore_candidate_workspace_id = request.args.get("restore_workspace_id", "").strip()
    restore_candidate_snapshot_id = request.args.get("restore_snapshot_id", "").strip()
    selected_task_workspace_id = request.args.get("task_workspace_id", "").strip()
    selected_template_id = request.args.get("template_id", "").strip()
    template_wizard_id = request.args.get("template_wizard_id", "").strip()
    selected_review_item_id = request.args.get("selected_review_item_id", "").strip()
    review_annotation_tool = request.args.get("review_annotation_tool", "").strip().upper() or "NOTE_MARKER"
    review_comment_draft = request.args.get("review_comment_draft", "").strip()
    selected_workspace_mode_id = request.args.get("workspace_mode_id", "").strip().upper() or ""
    selected_layout_profile_id = request.args.get("layout_profile_id", "").strip()
    selected_panel_configuration_id = request.args.get("panel_configuration_id", "").strip()
    layout_editor_enabled = _as_bool_flag(request.args.get("layout_editor", ""))
    layout_editor_dirty = _as_bool_flag(request.args.get("layout_editor_dirty", ""))
    workspace_mode_switch_pending = _as_bool_flag(request.args.get("workspace_mode_switch_pending", ""))
    split_view_enabled = _as_bool_flag(request.args.get("split_enabled", ""))
    split_view_mode = request.args.get("split_mode", "").strip().upper() or "SINGLE"
    split_orientation = request.args.get("split_orientation", "").strip().upper() or "VERTICAL"
    active_pane_id = request.args.get("active_pane_id", "").strip().upper() or "LEFT"
    left_pane_document_id = request.args.get("left_document_id", "").strip()
    right_pane_document_id = request.args.get("right_document_id", "").strip()
    compare_session = {
        "compare_session_id": request.args.get("compare_session_id", "").strip(),
        "compare_type": request.args.get("compare_type", "").strip().upper(),
        "left_source_id": request.args.get("compare_left_source_id", "").strip(),
        "right_source_id": request.args.get("compare_right_source_id", "").strip(),
    }
    inspector_follow_mode = request.args.get("inspector_follow_mode", "").strip().upper() or "FOLLOW_ACTIVE_PANE"
    ctx = build_ctx(
        state,
        selected_crew_id_value=selected_crew_id,
        selected_port_name_value=selected_port_name,
        selected_review_document_id_value=selected_review_document_id,
        review_filter_mode_value=review_filter_mode,
        selected_workbench_document_id_value=selected_workbench_document_id,
        selected_workbench_anchor_id_value=selected_workbench_anchor_id,
        selected_workbench_cell_id_value=selected_workbench_cell_id,
        selected_workbench_block_id_value=selected_workbench_block_id,
        workbench_selected_page_value=workbench_selected_page,
        workbench_tool_mode_value=workbench_tool_mode,
        workbench_center_mode_value=workbench_center_mode,
        workbench_bottom_tab_value=workbench_bottom_tab,
        workbench_inspector_mode_value=workbench_inspector_mode,
        workbench_filter_document_type_value=workbench_filter_document_type,
        workbench_filter_status_value=workbench_filter_status,
        workbench_search_text_value=workbench_search_text,
        active_menu_value=active_nav_menu,
        active_dropdown_value=active_nav_dropdown,
        active_dialog_value=active_nav_dialog,
        command_palette_open_value=command_palette_open,
        command_palette_query_value=command_palette_query,
        selected_command_id_value=selected_command_id,
        left_pane_collapsed_value=left_pane_collapsed,
        right_pane_collapsed_value=right_pane_collapsed,
        bottom_pane_collapsed_value=bottom_pane_collapsed,
        active_ribbon_tab_value=active_ribbon_tab,
        selected_workspace_id_value=selected_workspace_id,
        workspace_snapshot_id_value=workspace_snapshot_id,
        workspace_dirty_value=workspace_dirty,
        restore_candidate_workspace_id_value=restore_candidate_workspace_id,
        restore_candidate_snapshot_id_value=restore_candidate_snapshot_id,
        selected_task_workspace_id_value=selected_task_workspace_id,
        selected_template_id_value=selected_template_id,
        template_wizard_id_value=template_wizard_id,
        selected_review_item_id_value=selected_review_item_id,
        review_mode_enabled_value=selected_nav_submodule == "REVIEW",
        review_annotation_tool_value=review_annotation_tool,
        review_comment_draft_value=review_comment_draft,
        selected_workspace_mode_id_value=selected_workspace_mode_id,
        selected_layout_profile_id_value=selected_layout_profile_id,
        selected_panel_configuration_id_value=selected_panel_configuration_id,
        layout_editor_enabled_value=layout_editor_enabled,
        layout_editor_dirty_value=layout_editor_dirty,
        workspace_mode_switch_pending_value=workspace_mode_switch_pending,
        split_view_enabled_value=split_view_enabled,
        split_view_mode_value=split_view_mode,
        split_orientation_value=split_orientation,
        active_pane_id_value=active_pane_id,
        left_pane_document_id_value=left_pane_document_id,
        right_pane_document_id_value=right_pane_document_id,
        compare_session_value=compare_session,
        inspector_follow_mode_value=inspector_follow_mode,
    )

    if request.method == "POST":
        try:
            action = request.form.get("action", "").strip()
            selected_nav_module = request.form.get("nav_module", "").strip().upper() or selected_nav_module
            selected_nav_submodule = request.form.get("nav_submodule", "").strip().upper() or infer_nav_submodule(action, selected_nav_submodule)
            active_nav_menu = request.form.get("nav_menu", "").strip().upper() or active_nav_menu
            active_nav_dropdown = request.form.get("nav_dropdown", "").strip().upper() or active_nav_dropdown
            active_nav_dialog = request.form.get("nav_dialog", "").strip().upper() or active_nav_dialog
            command_palette_open = _as_bool_flag(request.form.get("command_palette", "")) or command_palette_open
            command_palette_query = request.form.get("command_query", "").strip() or command_palette_query
            selected_command_id = request.form.get("selected_command", "").strip().upper() or selected_command_id
            active_ribbon_tab = request.form.get("ribbon_tab", "").strip().upper() or active_ribbon_tab
            left_pane_collapsed = _as_bool_flag(request.form.get("pane_left", "")) or left_pane_collapsed
            right_pane_collapsed = _as_bool_flag(request.form.get("pane_right", "")) or right_pane_collapsed
            bottom_pane_collapsed = _as_bool_flag(request.form.get("pane_bottom", "")) or bottom_pane_collapsed
            selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id
            workspace_snapshot_id = request.form.get("workspace_snapshot_id", "").strip() or workspace_snapshot_id
            workspace_dirty = _as_bool_flag(request.form.get("workspace_dirty", "")) or workspace_dirty
            selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
            selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
            template_wizard_id = request.form.get("template_wizard_id", "").strip() or template_wizard_id
            selected_review_item_id = request.form.get("selected_review_item_id", "").strip() or selected_review_item_id
            review_annotation_tool = request.form.get("review_annotation_tool", "").strip().upper() or review_annotation_tool
            review_comment_draft = request.form.get("review_comment_draft", "").strip() or review_comment_draft
            selected_workspace_mode_id = request.form.get("workspace_mode_id", "").strip().upper() or selected_workspace_mode_id
            selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
            selected_panel_configuration_id = request.form.get("panel_configuration_id", "").strip() or selected_panel_configuration_id
            layout_editor_enabled = _as_bool_flag(request.form.get("layout_editor", "")) or layout_editor_enabled
            layout_editor_dirty = _as_bool_flag(request.form.get("layout_editor_dirty", "")) or layout_editor_dirty
            workspace_mode_switch_pending = _as_bool_flag(request.form.get("workspace_mode_switch_pending", "")) or workspace_mode_switch_pending
            split_view_enabled = _as_bool_flag(request.form.get("split_enabled", "")) or split_view_enabled
            split_view_mode = request.form.get("split_mode", "").strip().upper() or split_view_mode
            split_orientation = request.form.get("split_orientation", "").strip().upper() or split_orientation
            active_pane_id = request.form.get("active_pane_id", "").strip().upper() or active_pane_id
            left_pane_document_id = request.form.get("left_document_id", "").strip() or left_pane_document_id
            right_pane_document_id = request.form.get("right_document_id", "").strip() or right_pane_document_id
            inspector_follow_mode = request.form.get("inspector_follow_mode", "").strip().upper() or inspector_follow_mode
            compare_session = {
                "compare_session_id": request.form.get("compare_session_id", "").strip() or compare_session.get("compare_session_id", ""),
                "compare_type": request.form.get("compare_type", "").strip().upper() or compare_session.get("compare_type", ""),
                "left_source_id": request.form.get("compare_left_source_id", "").strip() or compare_session.get("left_source_id", ""),
                "right_source_id": request.form.get("compare_right_source_id", "").strip() or compare_session.get("right_source_id", ""),
            }
            workbench_center_mode = request.form.get("workbench_center_mode", "").strip().upper() or workbench_center_mode
            workbench_bottom_tab = request.form.get("workbench_bottom_tab", "").strip().upper() or workbench_bottom_tab
            workbench_inspector_mode = request.form.get("workbench_inspector_mode", "").strip().upper() or workbench_inspector_mode
            selected_workbench_cell_id = request.form.get("workbench_cell_id", "").strip() or selected_workbench_cell_id
            selected_workbench_block_id = request.form.get("workbench_block_id", "").strip() or selected_workbench_block_id

            def current_open_tabs():
                tabs = []
                if selected_workbench_document_id:
                    tabs.append(
                        {
                            "tab_id": selected_workbench_document_id,
                            "document_id": selected_workbench_document_id,
                            "label": selected_workbench_document_id,
                            "source_lane": "STUDIO",
                            "opened_at": utc_now_iso(),
                        }
                    )
                if selected_review_document_id:
                    tabs.append(
                        {
                            "tab_id": selected_review_document_id,
                            "document_id": selected_review_document_id,
                            "label": selected_review_document_id,
                            "source_lane": "REVIEW",
                            "opened_at": utc_now_iso(),
                        }
                    )
                return tabs

            def current_workspace_payload():
                return build_workspace_payload(
                    workspace_name=selected_workspace_id or "Workspace",
                    ui_mode={
                        "STUDIO": "STUDIO",
                        "REVIEW": "REVIEW",
                        "CONTROL_ROOM": "BRIDGE_OPS",
                        "OUTPUT": "PACKAGE",
                        "ARCHIVE": "PACKAGE",
                    }.get(selected_nav_submodule, "VALIDATION"),
                    open_document_tabs=current_open_tabs(),
                    active_document_tab_id=selected_workbench_document_id or selected_review_document_id,
                    active_ribbon_tab_value=active_ribbon_tab,
                    left_pane_collapsed_value=left_pane_collapsed,
                    right_pane_collapsed_value=right_pane_collapsed,
                    bottom_pane_collapsed_value=bottom_pane_collapsed,
                    selected_file_id=selected_workbench_document_id or selected_review_document_id,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    split_view_enabled_value=split_view_enabled,
                    split_view_mode_value=split_view_mode,
                    split_orientation_value=split_orientation,
                    active_pane_id_value=active_pane_id,
                    left_pane_document_id_value=left_pane_document_id or selected_workbench_document_id or selected_review_document_id,
                    right_pane_document_id_value=right_pane_document_id,
                    compare_session_value=compare_session,
                    inspector_follow_mode_value=inspector_follow_mode,
                    selected_review_item_id_value=selected_review_item_id,
                    review_session_id_value=request.form.get("review_session_id", "").strip() or request.args.get("review_session_id", "").strip(),
                    review_filter_value=review_filter_mode,
                    selected_workspace_mode_id_value=selected_workspace_mode_id,
                    selected_layout_profile_id_value=selected_layout_profile_id,
                    selected_panel_configuration_id_value=selected_panel_configuration_id,
                    panel_visibility_state_value={
                        "left_sidebar_visible": not left_pane_collapsed,
                        "right_inspector_visible": not right_pane_collapsed,
                        "bottom_panel_visible": not bottom_pane_collapsed,
                        "command_palette_enabled": True,
                        "review_summary_visible": selected_nav_submodule == "REVIEW" or bool(compare_session.get("compare_type")),
                        "task_header_visible": bool(selected_task_workspace_id),
                        "compare_summary_visible": bool(compare_session.get("compare_type")),
                        "active_sections": [],
                    },
                )

            def current_layout_profile_payload():
                return {
                    "workspace_mode_id": selected_workspace_mode_id or "STUDIO",
                    "left_width": request.form.get("left_width", "").strip() or request.args.get("left_width", "").strip() or "92px",
                    "right_width": request.form.get("right_width", "").strip() or request.args.get("right_width", "").strip() or "320px",
                    "bottom_height": request.form.get("bottom_height", "").strip() or request.args.get("bottom_height", "").strip() or "180px",
                    "left_collapsed": bool(left_pane_collapsed),
                    "right_collapsed": bool(right_pane_collapsed),
                    "bottom_collapsed": bool(bottom_pane_collapsed),
                    "split_view_state": {
                        "enabled": bool(split_view_enabled),
                        "mode": str(split_view_mode or "SINGLE"),
                        "pane_ids": ["LEFT", "RIGHT"],
                        "active_pane_id": str(active_pane_id or "LEFT"),
                        "orientation": str(split_orientation or "VERTICAL"),
                        "divider_positions": {"primary": "50%"},
                        "compare_mode": str(compare_session.get("compare_type") or ""),
                        "group_ids": ["PRIMARY"],
                    },
                    "active_split_mode": str(split_view_mode or "SINGLE"),
                    "panel_configuration_id": str(selected_panel_configuration_id or ""),
                }

            def current_panel_configuration_payload():
                return {
                    "left_sidebar_visible": not left_pane_collapsed,
                    "right_inspector_visible": not right_pane_collapsed,
                    "bottom_panel_visible": not bottom_pane_collapsed,
                    "command_palette_enabled": True,
                    "review_summary_visible": bool(selected_nav_submodule == "REVIEW" or compare_session.get("compare_type")),
                    "task_header_visible": bool(selected_task_workspace_id),
                    "compare_summary_visible": bool(compare_session.get("compare_type")),
                    "active_sections": [],
                }

            def current_review_scope():
                if compare_session.get("compare_session_id") or compare_session.get("left_source_id") or compare_session.get("right_source_id"):
                    scope_id = str(compare_session.get("compare_session_id") or compare_session.get("left_source_id") or compare_session.get("right_source_id") or "COMPARE")
                    return "COMPARE_SESSION", scope_id
                if selected_task_workspace_id:
                    return "TASK_WORKSPACE", selected_task_workspace_id
                return "DOCUMENT", (selected_workbench_document_id or selected_review_document_id or left_pane_document_id or "GLOBAL")

            def current_review_session():
                scope_type, scope_id = current_review_scope()
                return review_layer_service.get_or_create_review_session(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    task_workspace_id=selected_task_workspace_id,
                )

            def rebuild_ctx(**overrides):
                params = {
                    "selected_crew_id_value": selected_crew_id,
                    "selected_port_name_value": selected_port_name,
                    "selected_review_document_id_value": selected_review_document_id,
                    "review_filter_mode_value": review_filter_mode,
                    "selected_workbench_document_id_value": selected_workbench_document_id,
                    "selected_workbench_anchor_id_value": selected_workbench_anchor_id,
                    "selected_workbench_cell_id_value": selected_workbench_cell_id,
                    "selected_workbench_block_id_value": selected_workbench_block_id,
                    "workbench_selected_page_value": workbench_selected_page,
                    "workbench_tool_mode_value": workbench_tool_mode,
                    "workbench_center_mode_value": workbench_center_mode,
                    "workbench_bottom_tab_value": workbench_bottom_tab,
                    "workbench_inspector_mode_value": workbench_inspector_mode,
                    "workbench_filter_document_type_value": workbench_filter_document_type,
                    "workbench_filter_status_value": workbench_filter_status,
                    "workbench_search_text_value": workbench_search_text,
                    "active_menu_value": active_nav_menu,
                    "active_dropdown_value": active_nav_dropdown,
                    "active_dialog_value": active_nav_dialog,
                    "command_palette_open_value": command_palette_open,
                    "command_palette_query_value": command_palette_query,
                    "selected_command_id_value": selected_command_id,
                    "left_pane_collapsed_value": left_pane_collapsed,
                    "right_pane_collapsed_value": right_pane_collapsed,
                    "bottom_pane_collapsed_value": bottom_pane_collapsed,
                    "active_ribbon_tab_value": active_ribbon_tab,
                    "selected_workspace_id_value": selected_workspace_id,
                    "workspace_snapshot_id_value": workspace_snapshot_id,
                    "workspace_dirty_value": workspace_dirty,
                    "restore_candidate_workspace_id_value": restore_candidate_workspace_id,
                    "restore_candidate_snapshot_id_value": restore_candidate_snapshot_id,
                    "selected_task_workspace_id_value": selected_task_workspace_id,
                    "selected_template_id_value": selected_template_id,
                    "template_wizard_id_value": template_wizard_id,
                    "selected_review_item_id_value": selected_review_item_id,
                    "review_mode_enabled_value": selected_nav_submodule == "REVIEW",
                    "review_annotation_tool_value": review_annotation_tool,
                    "review_comment_draft_value": review_comment_draft,
                    "selected_workspace_mode_id_value": selected_workspace_mode_id,
                    "selected_layout_profile_id_value": selected_layout_profile_id,
                    "selected_panel_configuration_id_value": selected_panel_configuration_id,
                    "layout_editor_enabled_value": layout_editor_enabled,
                    "layout_editor_dirty_value": layout_editor_dirty,
                    "panel_visibility_state_value": current_panel_configuration_payload(),
                    "workspace_mode_switch_pending_value": workspace_mode_switch_pending,
                    "split_view_enabled_value": split_view_enabled,
                    "split_view_mode_value": split_view_mode,
                    "split_orientation_value": split_orientation,
                    "active_pane_id_value": active_pane_id,
                    "left_pane_document_id_value": left_pane_document_id,
                    "right_pane_document_id_value": right_pane_document_id,
                    "compare_session_value": compare_session,
                    "inspector_follow_mode_value": inspector_follow_mode,
                }
                params.update(overrides)
                return build_ctx(state, **params)

            if action == "switch_workspace_mode":
                selected_workspace_mode_id = request.form.get("workspace_mode_id", "").strip().upper() or selected_workspace_mode_id or "STUDIO"
                mode_record = layout_service.switch_workspace_mode(selected_workspace_mode_id)
                selected_layout_profile_id = str(mode_record.get("default_layout_profile_id") or selected_layout_profile_id or "")
                loaded_profile = layout_service.load_layout_profile(selected_layout_profile_id)
                if loaded_profile:
                    left_pane_collapsed = bool(loaded_profile.get("left_collapsed", left_pane_collapsed))
                    right_pane_collapsed = bool(loaded_profile.get("right_collapsed", right_pane_collapsed))
                    bottom_pane_collapsed = bool(loaded_profile.get("bottom_collapsed", bottom_pane_collapsed))
                    split_view_mode = str(loaded_profile.get("active_split_mode") or split_view_mode or "SINGLE")
                    split_view_enabled = split_view_mode != "SINGLE"
                    selected_panel_configuration_id = str(loaded_profile.get("panel_configuration_id") or selected_panel_configuration_id or "")
                active_ribbon_tab = str(mode_record.get("default_ribbon_tab") or active_ribbon_tab or "HOME")
                workspace_mode_switch_pending = False
                ctx = rebuild_ctx(workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "save_layout_profile":
                layout_name = request.form.get("layout_profile_name", "").strip() or selected_layout_profile_id or "Layout Profile"
                saved_profile = layout_service.save_layout_profile(
                    layout_profile_id=selected_layout_profile_id or "",
                    name=layout_name,
                    payload=current_layout_profile_payload(),
                )
                selected_layout_profile_id = str(saved_profile.get("layout_profile_id") or selected_layout_profile_id)
                workspace_dirty = False
                ctx = rebuild_ctx(workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "save_layout_profile_as":
                layout_name = request.form.get("layout_profile_name", "").strip() or "Layout Copy"
                saved_profile = layout_service.save_layout_profile_as(name=layout_name, payload=current_layout_profile_payload())
                selected_layout_profile_id = str(saved_profile.get("layout_profile_id") or selected_layout_profile_id)
                workspace_dirty = False
                ctx = rebuild_ctx(workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "load_layout_profile":
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                loaded_profile = layout_service.load_layout_profile(selected_layout_profile_id)
                if loaded_profile:
                    selected_workspace_mode_id = str(loaded_profile.get("workspace_mode_id") or selected_workspace_mode_id or "STUDIO")
                    selected_panel_configuration_id = str(loaded_profile.get("panel_configuration_id") or selected_panel_configuration_id or "")
                    left_pane_collapsed = bool(loaded_profile.get("left_collapsed", left_pane_collapsed))
                    right_pane_collapsed = bool(loaded_profile.get("right_collapsed", right_pane_collapsed))
                    bottom_pane_collapsed = bool(loaded_profile.get("bottom_collapsed", bottom_pane_collapsed))
                    split_view_mode = str(loaded_profile.get("active_split_mode") or split_view_mode or "SINGLE")
                    split_view_enabled = split_view_mode != "SINGLE"
                    split_orientation = str((loaded_profile.get("split_view_state") or {}).get("orientation") or split_orientation or "VERTICAL")
                    active_pane_id = str((loaded_profile.get("split_view_state") or {}).get("active_pane_id") or active_pane_id or "LEFT")
                workspace_dirty = False
                ctx = rebuild_ctx(workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "rename_layout_profile":
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                layout_service.rename_layout_profile(
                    layout_profile_id=selected_layout_profile_id,
                    new_name=request.form.get("layout_profile_name", "").strip() or selected_layout_profile_id,
                )
                ctx = rebuild_ctx(workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "duplicate_layout_profile":
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                duplicated_profile = layout_service.duplicate_layout_profile(
                    layout_profile_id=selected_layout_profile_id,
                    new_name=request.form.get("layout_profile_name", "").strip() or "",
                )
                selected_layout_profile_id = str(duplicated_profile.get("layout_profile_id") or selected_layout_profile_id)
                ctx = rebuild_ctx(workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "delete_layout_profile":
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                layout_service.delete_layout_profile(selected_layout_profile_id)
                selected_layout_profile_id = ""
                ctx = rebuild_ctx(workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "save_panel_configuration":
                panel_name = request.form.get("panel_configuration_name", "").strip() or selected_panel_configuration_id or "Panel Configuration"
                saved_config = layout_service.save_panel_configuration(
                    panel_configuration_id=selected_panel_configuration_id or "",
                    name=panel_name,
                    payload=current_panel_configuration_payload(),
                )
                selected_panel_configuration_id = str(saved_config.get("panel_configuration_id") or selected_panel_configuration_id)
                workspace_dirty = False
                ctx = rebuild_ctx(workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "load_panel_configuration":
                selected_panel_configuration_id = request.form.get("panel_configuration_id", "").strip() or selected_panel_configuration_id
                loaded_config = layout_service.load_panel_configuration(selected_panel_configuration_id)
                if loaded_config:
                    left_pane_collapsed = not bool(loaded_config.get("left_sidebar_visible", True))
                    right_pane_collapsed = not bool(loaded_config.get("right_inspector_visible", True))
                    bottom_pane_collapsed = not bool(loaded_config.get("bottom_panel_visible", True))
                workspace_dirty = False
                ctx = rebuild_ctx(workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "enter_layout_editor":
                layout_editor_enabled = True
                layout_editor_dirty = False
                layout_service.enter_layout_editor(
                    editing_profile_id=selected_layout_profile_id,
                    current_state={
                        "draft_panel_configuration": current_panel_configuration_payload(),
                        "draft_dimensions": current_layout_profile_payload(),
                        "preview_mode": "LIVE",
                        "dirty": False,
                    },
                )
                ctx = rebuild_ctx(layout_editor_enabled_value=True, layout_editor_dirty_value=False, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "apply_layout_editor":
                layout_editor_enabled = True
                layout_editor_dirty = True
                left_pane_collapsed = not _as_bool_flag(request.form.get("panel_left_visible", "true"))
                right_pane_collapsed = not _as_bool_flag(request.form.get("panel_right_visible", "true"))
                bottom_pane_collapsed = not _as_bool_flag(request.form.get("panel_bottom_visible", "true"))
                selected_workspace_mode_id = request.form.get("workspace_mode_id", "").strip().upper() or selected_workspace_mode_id
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                selected_panel_configuration_id = request.form.get("panel_configuration_id", "").strip() or selected_panel_configuration_id
                layout_service.apply_layout_editor_draft(
                    draft_state={
                        "enabled": True,
                        "editing_profile_id": selected_layout_profile_id,
                        "draft_panel_configuration": {
                            "left_sidebar_visible": not left_pane_collapsed,
                            "right_inspector_visible": not right_pane_collapsed,
                            "bottom_panel_visible": not bottom_pane_collapsed,
                            "command_palette_enabled": _as_bool_flag(request.form.get("panel_command_palette_enabled", "true")) or True,
                            "review_summary_visible": _as_bool_flag(request.form.get("panel_review_summary_visible", "")),
                            "task_header_visible": _as_bool_flag(request.form.get("panel_task_header_visible", "")),
                            "compare_summary_visible": _as_bool_flag(request.form.get("panel_compare_summary_visible", "")),
                            "active_sections": [],
                        },
                        "draft_dimensions": current_layout_profile_payload(),
                        "preview_mode": request.form.get("layout_preview_mode", "").strip().upper() or "LIVE",
                        "dirty": True,
                    }
                )
                ctx = rebuild_ctx(layout_editor_enabled_value=True, layout_editor_dirty_value=True, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "cancel_layout_editor":
                layout_editor_enabled = False
                layout_editor_dirty = False
                layout_service.cancel_layout_editor()
                ctx = rebuild_ctx(layout_editor_enabled_value=False, layout_editor_dirty_value=False, workspace_dirty_value=workspace_dirty)
                ctx["saved"] = True

            elif action == "set_default_layout_for_mode":
                selected_workspace_mode_id = request.form.get("workspace_mode_id", "").strip().upper() or selected_workspace_mode_id or "STUDIO"
                selected_layout_profile_id = request.form.get("layout_profile_id", "").strip() or selected_layout_profile_id
                layout_service.set_default_layout_for_mode(
                    mode_id=selected_workspace_mode_id,
                    layout_profile_id=selected_layout_profile_id,
                )
                ctx = rebuild_ctx(workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "create_review_item":
                review_session = current_review_session()
                created = review_layer_service.create_review_item(
                    review_session_id=str(review_session.get("review_session_id") or ""),
                    document_id=selected_workbench_document_id or selected_review_document_id or left_pane_document_id or "",
                    document_tab_id=selected_workbench_document_id or selected_review_document_id or "",
                    pane_id=active_pane_id,
                    target_object_id=selected_workbench_anchor_id or selected_workbench_cell_id or selected_workbench_block_id,
                    kind=request.form.get("review_item_kind", "").strip().upper() or "ISSUE",
                    severity=request.form.get("review_item_severity", "").strip().upper() or "MEDIUM",
                    title=request.form.get("review_item_title", "").strip() or "Review item",
                    body=request.form.get("review_item_body", "").strip(),
                    tags=[tag.strip() for tag in request.form.get("review_item_tags", "").split(",") if tag.strip()],
                    created_by=request.form.get("review_actor", "").strip() or "operator",
                    task_workspace_id=selected_task_workspace_id,
                )
                selected_review_item_id = str(created.get("review_item_id") or "")
                review_comment_draft = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value="", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "add_review_comment":
                review_session = current_review_session()
                target_review_item_id = request.form.get("selected_review_item_id", "").strip() or selected_review_item_id
                comment_body = request.form.get("review_comment_body", "").strip()
                if target_review_item_id and comment_body:
                    review_layer_service.add_comment(
                        review_item_id=target_review_item_id,
                        document_id=selected_workbench_document_id or selected_review_document_id or left_pane_document_id or "",
                        target_object_id=selected_workbench_anchor_id or selected_workbench_cell_id or selected_workbench_block_id,
                        body=comment_body,
                        created_by=request.form.get("review_actor", "").strip() or "operator",
                    )
                selected_review_item_id = target_review_item_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value="", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "create_review_annotation":
                review_session = current_review_session()
                review_layer_service.create_annotation(
                    document_id=selected_workbench_document_id or selected_review_document_id or left_pane_document_id or "",
                    pane_id=active_pane_id,
                    target_object_id=selected_workbench_anchor_id or selected_workbench_cell_id or selected_workbench_block_id,
                    annotation_type=request.form.get("review_annotation_tool", "").strip().upper() or review_annotation_tool or "NOTE_MARKER",
                    content=request.form.get("review_annotation_content", "").strip(),
                    style={"tone": request.form.get("review_annotation_style", "").strip() or "default"},
                    review_session_id=str(review_session.get("review_session_id") or ""),
                )
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value=review_comment_draft, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "delete_review_annotation":
                annotation_id = request.form.get("annotation_id", "").strip()
                if annotation_id:
                    review_layer_service.delete_annotation(annotation_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value=review_comment_draft, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action in {"resolve_review_item", "reopen_review_item", "approve_review_item", "reject_review_item"}:
                target_review_item_id = request.form.get("selected_review_item_id", "").strip() or selected_review_item_id
                review_note = request.form.get("review_action_note", "").strip()
                review_actor = request.form.get("review_actor", "").strip() or "operator"
                if target_review_item_id:
                    if action == "resolve_review_item":
                        review_layer_service.resolve_review_item(target_review_item_id, actor=review_actor, note=review_note)
                    elif action == "reopen_review_item":
                        review_layer_service.reopen_review_item(target_review_item_id, actor=review_actor, note=review_note)
                    elif action == "approve_review_item":
                        review_layer_service.approve_review_item(target_review_item_id, actor=review_actor, note=review_note)
                    else:
                        review_layer_service.reject_review_item(target_review_item_id, actor=review_actor, note=review_note)
                selected_review_item_id = target_review_item_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value=review_comment_draft, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "signoff_review_session":
                review_session = current_review_session()
                review_layer_service.signoff_review_session(
                    review_session_id=str(review_session.get("review_session_id") or ""),
                    actor=request.form.get("review_actor", "").strip() or "operator",
                    note=request.form.get("review_action_note", "").strip(),
                )
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value=review_comment_draft, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "select_review_layer_item":
                selected_review_item_id = request.form.get("selected_review_item_id", "").strip() or selected_review_item_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value="VALIDATION", workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value="REVIEW", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_review_item_id_value=selected_review_item_id, review_mode_enabled_value=True, review_annotation_tool_value=review_annotation_tool, review_comment_draft_value=review_comment_draft, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "create_file":
                result = file_service.create_file(
                    workspace_id=selected_workspace_id or selected_nav_submodule,
                    file_name=request.form.get("file_name", "").strip() or "New Workspace File",
                )
                selected_workbench_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or selected_workbench_document_id)
                selected_review_document_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value="", review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="CREATE_FILE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action in {"open_from_disk", "import_external_file", "link_external_file"}:
                requested_path = request.form.get("external_file_path", "").strip()
                requested_name = request.form.get("external_file_name", "").strip()
                import_mode = "LINK" if action == "link_external_file" else "IMPORT"
                result = file_service.import_external_file(
                    workspace_id=selected_workspace_id or selected_nav_submodule,
                    file_path=requested_path,
                    import_mode=import_mode,
                    requested_name=requested_name,
                    owner_entity="workspace",
                    owner_id=str(selected_workspace_id or selected_nav_submodule or "workspace_session"),
                    operational_reason="Opened from external disk intake." if action == "open_from_disk" else "Imported from external disk intake.",
                )
                selected_workbench_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or selected_workbench_document_id)
                selected_review_document_id = ""
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value="", review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab or "FILE", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value=action.upper(), explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "add_file_to_workspace":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.add_to_workspace(workspace_id=selected_workspace_id or selected_nav_submodule, file_id=target_file_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="ADD_TO_WORKSPACE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "open_explorer_file":
                target_file_id = request.form.get("file_id", "").strip()
                target_document_id = request.form.get("document_id", "").strip() or file_service.get_preferred_document_id(target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule)
                selected_workbench_document_id = target_document_id or selected_workbench_document_id
                selected_review_document_id = ""
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value="", review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, selected_file_action_value="OPEN_FILE", explorer_active_section_value=request.form.get("explorer_section", "").strip() or "FILE_EXPLORER", workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "rename_file":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.rename_file(file_id=target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule, new_name=request.form.get("file_name", "").strip())
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="RENAME_FILE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "duplicate_file":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.duplicate_file(file_id=target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule, new_name=request.form.get("file_name", "").strip())
                selected_workbench_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or selected_workbench_document_id)
                selected_review_document_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value="", review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="DUPLICATE_FILE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "remove_file_from_workspace":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.remove_from_workspace(workspace_id=selected_workspace_id or selected_nav_submodule, file_id=target_file_id)
                target_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or file_service.get_preferred_document_id(target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule))
                if selected_workbench_document_id in {target_file_id, target_document_id}:
                    selected_workbench_document_id = ""
                    selected_workbench_anchor_id = ""
                    selected_workbench_cell_id = ""
                    selected_workbench_block_id = ""
                if selected_review_document_id in {target_file_id, target_document_id}:
                    selected_review_document_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="REMOVE_FROM_WORKSPACE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "archive_file":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.archive_file(file_id=target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule, archive_reason=request.form.get("archive_reason", "").strip())
                target_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or file_service.get_preferred_document_id(target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule))
                if selected_workbench_document_id in {target_file_id, target_document_id}:
                    selected_workbench_document_id = ""
                    selected_workbench_anchor_id = ""
                    selected_workbench_cell_id = ""
                    selected_workbench_block_id = ""
                if selected_review_document_id in {target_file_id, target_document_id}:
                    selected_review_document_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="ARCHIVE_FILE", explorer_active_section_value="ARCHIVE", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "delete_file":
                target_file_id = request.form.get("file_id", "").strip() or selected_workbench_document_id or selected_review_document_id
                result = file_service.delete_file(file_id=target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule)
                target_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or file_service.get_preferred_document_id(target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule))
                if selected_workbench_document_id in {target_file_id, target_document_id}:
                    selected_workbench_document_id = ""
                    selected_workbench_anchor_id = ""
                    selected_workbench_cell_id = ""
                    selected_workbench_block_id = ""
                if selected_review_document_id in {target_file_id, target_document_id}:
                    selected_review_document_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="DELETE_FILE", explorer_active_section_value="FILE_EXPLORER", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "restore_file":
                target_file_id = request.form.get("file_id", "").strip()
                result = file_service.restore_file(file_id=target_file_id, workspace_id=selected_workspace_id or selected_nav_submodule)
                if not selected_workbench_document_id:
                    selected_workbench_document_id = str((result.get("updated_refs", {}) or {}).get("document_id") or selected_workbench_document_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, recent_file_action_result_value=result, selected_file_action_value="RESTORE_FILE", explorer_active_section_value="ARCHIVE", workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "start_template_wizard":
                seed_template = template_service.load_template(selected_template_id) if selected_template_id else {}
                active_task = task_service.load_task_workspace(selected_task_workspace_id) if selected_task_workspace_id else {}
                wizard = template_service.start_template_wizard(
                    template_type=request.form.get("template_type", "").strip().upper() or "TASK_WORKSPACE",
                    seed_template=seed_template,
                    seed_task_workspace=active_task,
                    seed_workspace_payload=current_workspace_payload(),
                )
                template_wizard_id = wizard.get("wizard_id", "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "update_template_wizard":
                template_wizard_id = request.form.get("template_wizard_id", "").strip() or template_wizard_id
                wizard_step = int(request.form.get("wizard_step", "1") or "1")
                wizard = template_service.update_template_wizard(
                    wizard_id=template_wizard_id,
                    updates={
                        "current_step": wizard_step,
                        "template_type": request.form.get("wizard_template_type", "").strip().upper() or "TASK_WORKSPACE",
                        "draft_name": request.form.get("wizard_template_name", "").strip(),
                        "draft_category": request.form.get("wizard_template_category", "").strip(),
                        "draft_description": request.form.get("wizard_template_description", "").strip(),
                        "draft_ui_mode": request.form.get("wizard_ui_mode", "").strip().upper() or "STUDIO",
                        "draft_task_type": request.form.get("wizard_task_type", "").strip().upper() or "ARRIVAL",
                        "draft_stage_template": [stage.strip().upper() for stage in request.form.get("wizard_stage_template", "").split(",") if stage.strip()],
                        "draft_slot_definitions": parse_slot_definitions(request.form.get("wizard_slot_definitions", "")),
                        "draft_checklist_template": parse_checklist_template(request.form.get("wizard_checklist_template", "")),
                        "draft_save_options": {
                            "include_layout": _as_bool_flag(request.form.get("wizard_include_layout", "true")) or True,
                            "include_tool_state": _as_bool_flag(request.form.get("wizard_include_tool_state", "true")) or True,
                            "include_validation_rules": _as_bool_flag(request.form.get("wizard_include_validation_rules", "")),
                            "include_slots": _as_bool_flag(request.form.get("wizard_include_slots", "true")) or True,
                            "include_checklist": _as_bool_flag(request.form.get("wizard_include_checklist", "true")) or True,
                            "include_context_bindings": _as_bool_flag(request.form.get("wizard_include_context_bindings", "")),
                            "include_live_values": _as_bool_flag(request.form.get("wizard_include_live_values", "")),
                        },
                        "draft_layout_profile": dict(current_workspace_payload().get("layout_profile", {})),
                    },
                )
                template_wizard_id = wizard.get("wizard_id", template_wizard_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "save_template_from_wizard":
                template_wizard_id = request.form.get("template_wizard_id", "").strip() or template_wizard_id
                saved_template = template_service.save_template_from_wizard(template_wizard_id)
                selected_template_id = saved_template.get("template_id", "")
                template_wizard_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value="", workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "save_current_as_template":
                saved_template = template_service.save_current_as_template(
                    name=request.form.get("template_name", "").strip() or (selected_task_workspace_id or "Current Workspace Template"),
                    category=request.form.get("template_category", "").strip() or "Operational Workflow",
                    template_type=request.form.get("template_type", "").strip().upper() or "TASK_WORKSPACE",
                    task_type=request.form.get("task_type", "").strip().upper() or ((task_service.load_task_workspace(selected_task_workspace_id) or {}).get("task_type") or "ARRIVAL"),
                    workspace_payload=current_workspace_payload(),
                    active_task_workspace=task_service.load_task_workspace(selected_task_workspace_id) if selected_task_workspace_id else {},
                    include_live_values=_as_bool_flag(request.form.get("include_live_values", "")),
                )
                selected_template_id = saved_template.get("template_id", "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "load_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, template_wizard_id_value=template_wizard_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "rename_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                template_service.rename_template(template_id=selected_template_id, new_name=request.form.get("template_name", "").strip())
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "duplicate_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                duplicated_template = template_service.duplicate_template(template_id=selected_template_id, new_name=request.form.get("template_name", "").strip())
                selected_template_id = duplicated_template.get("template_id", selected_template_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "archive_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                template_service.archive_template(selected_template_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "delete_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                template_service.delete_template(selected_template_id)
                selected_template_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value="", workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "toggle_template_favorite":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                template_service.set_template_favorite(template_id=selected_template_id, favorite=_as_bool_flag(request.form.get("favorite", "")))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "create_task_from_template":
                selected_template_id = request.form.get("template_id", "").strip() or selected_template_id
                template = template_service.load_template(selected_template_id)
                slot_assignments = []
                for slot in list(template.get("slot_definitions", []) or []):
                    slot_id = str(slot.get("slot_id") or "")
                    slot_assignments.append(
                        {
                            "slot_id": slot_id,
                            "assigned_source_id": request.form.get(f"slot_{slot_id}_source_id", "").strip(),
                            "assigned_source_type": request.form.get(f"slot_{slot_id}_source_type", "").strip().upper(),
                            "note": request.form.get(f"slot_{slot_id}_note", "").strip(),
                        }
                    )
                created_task = template_service.create_task_from_template(
                    template_id=selected_template_id,
                    task_name=request.form.get("task_name", "").strip() or f"{template.get('name', 'Template')} Run",
                    workspace_id=selected_workspace_id or "workspace_session",
                    resume_target={
                        "nav_submodule": selected_nav_submodule,
                        "document_id": selected_workbench_document_id or selected_review_document_id,
                        "ribbon_tab": active_ribbon_tab or "TASKS",
                    },
                    slot_assignments=slot_assignments,
                    task_service=task_service,
                )
                selected_task_workspace_id = created_task.get("task_workspace_id", "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value="TASKS", selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, selected_template_id_value=selected_template_id, workspace_dirty_value=True)
                ctx["saved"] = True

            if action == "create_task_workspace":
                workspace_id_for_task = selected_workspace_id or "workspace_session"
                created_task = task_service.create_task_workspace(
                    workspace_id=workspace_id_for_task,
                    name=request.form.get("task_name", "").strip() or request.form.get("task_type", "ARRIVAL").strip().replace("_", " ").title(),
                    task_type=request.form.get("task_type", "ARRIVAL").strip().upper() or "ARRIVAL",
                    resume_target={
                        "nav_submodule": selected_nav_submodule,
                        "document_id": selected_workbench_document_id or selected_review_document_id,
                        "ribbon_tab": active_ribbon_tab,
                    },
                )
                selected_task_workspace_id = created_task.get("task_workspace_id", "")
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                    active_ribbon_tab_value=active_ribbon_tab,
                    selected_workspace_id_value=selected_workspace_id,
                    selected_task_workspace_id_value=selected_task_workspace_id,
                    workspace_dirty_value=True,
                )
                ctx["saved"] = True

            elif action == "start_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task = task_service.start_task_workspace(selected_task_workspace_id)
                selected_workspace_id = str(task.get("workspace_id") or selected_workspace_id or "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "load_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task = task_service.load_task_workspace(selected_task_workspace_id)
                selected_workspace_id = str(task.get("workspace_id") or selected_workspace_id or "")
                resume_target = dict(task.get("resume_target", {}) or {})
                target_doc = str(resume_target.get("document_id") or "")
                selected_nav_submodule = str(resume_target.get("nav_submodule") or selected_nav_submodule or "STUDIO").upper()
                active_ribbon_tab = str(resume_target.get("ribbon_tab") or active_ribbon_tab or "TASKS").upper()
                if selected_nav_submodule == "REVIEW":
                    selected_review_document_id = target_doc or selected_review_document_id
                    selected_workbench_document_id = ""
                else:
                    selected_workbench_document_id = target_doc or selected_workbench_document_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "resume_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task = task_service.resume_task_workspace(selected_task_workspace_id)
                selected_workspace_id = str(task.get("workspace_id") or selected_workspace_id or "")
                resume_target = dict(task.get("resume_target", {}) or {})
                selected_nav_submodule = str(resume_target.get("nav_submodule") or selected_nav_submodule or "STUDIO").upper()
                active_ribbon_tab = str(resume_target.get("ribbon_tab") or active_ribbon_tab or "TASKS").upper()
                target_doc = str(resume_target.get("document_id") or "")
                if selected_nav_submodule == "REVIEW":
                    selected_review_document_id = target_doc or selected_review_document_id
                    selected_workbench_document_id = ""
                else:
                    selected_workbench_document_id = target_doc or selected_workbench_document_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "rename_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.rename_task_workspace(task_workspace_id=selected_task_workspace_id, new_name=request.form.get("task_name", "").strip())
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "duplicate_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                duplicated_task = task_service.duplicate_task_workspace(task_workspace_id=selected_task_workspace_id, new_name=request.form.get("task_name", "").strip())
                selected_task_workspace_id = duplicated_task.get("task_workspace_id", selected_task_workspace_id)
                selected_workspace_id = str(duplicated_task.get("workspace_id") or selected_workspace_id or "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "delete_task_workspace":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.delete_task_workspace(selected_task_workspace_id)
                selected_task_workspace_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value="", workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "update_task_checklist_item":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.update_checklist_item(
                    task_workspace_id=selected_task_workspace_id,
                    item_id=request.form.get("task_item_id", "").strip(),
                    status=request.form.get("task_item_status", "").strip().upper() or "TODO",
                    note=request.form.get("task_item_note", "").strip(),
                )
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "change_task_stage":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.change_task_stage(
                    task_workspace_id=selected_task_workspace_id,
                    stage=request.form.get("task_stage", "").strip().upper(),
                )
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "mark_task_complete":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.mark_task_complete(selected_task_workspace_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "save_task_checkpoint":
                selected_task_workspace_id = request.form.get("task_workspace_id", "").strip() or selected_task_workspace_id
                task_service.save_task_checkpoint(
                    task_workspace_id=selected_task_workspace_id,
                    note=request.form.get("task_checkpoint_note", "").strip() or "Checkpoint saved from workstation shell.",
                )
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, selected_task_workspace_id_value=selected_task_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "save_workspace":
                workspace_name = request.form.get("workspace_name", "").strip() or selected_workspace_id or "Workspace"
                payload = current_workspace_payload()
                payload["workspace_name"] = workspace_name
                saved_workspace = workspace_service.save_workspace(
                    workspace_id=selected_workspace_id or f"workspace_{workspace_name.lower().replace(' ', '_')}",
                    name=workspace_name,
                    payload=payload,
                )
                workspace_service.autosave_workspace(workspace_id=saved_workspace["workspace_id"], payload=payload)
                selected_workspace_id = saved_workspace["workspace_id"]
                workspace_dirty = False
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                    active_menu_value=active_nav_menu,
                    active_dropdown_value=active_nav_dropdown,
                    active_dialog_value=active_nav_dialog,
                    command_palette_open_value=command_palette_open,
                    command_palette_query_value=command_palette_query,
                    selected_command_id_value=selected_command_id,
                    left_pane_collapsed_value=left_pane_collapsed,
                    right_pane_collapsed_value=right_pane_collapsed,
                    bottom_pane_collapsed_value=bottom_pane_collapsed,
                    active_ribbon_tab_value=active_ribbon_tab,
                    selected_workspace_id_value=selected_workspace_id,
                    workspace_dirty_value=False,
                )
                ctx["saved"] = True

            elif action == "save_workspace_as":
                workspace_name = request.form.get("workspace_name", "").strip() or "Workspace Copy"
                payload = current_workspace_payload()
                payload["workspace_name"] = workspace_name
                saved_workspace = workspace_service.save_workspace_as(name=workspace_name, payload=payload)
                selected_workspace_id = saved_workspace["workspace_id"]
                workspace_dirty = False
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_menu_value=active_nav_menu, active_dropdown_value=active_nav_dropdown, active_dialog_value=active_nav_dialog, command_palette_open_value=command_palette_open, command_palette_query_value=command_palette_query, selected_command_id_value=selected_command_id, left_pane_collapsed_value=left_pane_collapsed, right_pane_collapsed_value=right_pane_collapsed, bottom_pane_collapsed_value=bottom_pane_collapsed, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "load_workspace":
                selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id
                workspace = workspace_service.load_workspace(selected_workspace_id)
                restored = apply_workspace_payload(dict(workspace.get("shell_state", {}) or {}))
                selected_nav_submodule = restored["selected_nav_submodule"]
                selected_workbench_document_id = restored["selected_workbench_document_id"]
                selected_review_document_id = restored["selected_review_document_id"]
                active_ribbon_tab = restored["active_ribbon_tab"] or active_ribbon_tab
                left_pane_collapsed = restored["left_pane_collapsed"]
                right_pane_collapsed = restored["right_pane_collapsed"]
                bottom_pane_collapsed = restored["bottom_pane_collapsed"]
                workbench_bottom_tab = restored["workbench_bottom_tab"] or workbench_bottom_tab
                workbench_inspector_mode = restored["workbench_inspector_mode"] or workbench_inspector_mode
                split_view_enabled = restored["split_view_enabled"]
                split_view_mode = restored["split_view_mode"] or split_view_mode
                split_orientation = restored["split_orientation"] or split_orientation
                active_pane_id = restored["active_pane_id"] or active_pane_id
                left_pane_document_id = str((restored["pane_documents"].get("LEFT", {}) or {}).get("document_id") or selected_workbench_document_id or selected_review_document_id)
                right_pane_document_id = str((restored["pane_documents"].get("RIGHT", {}) or {}).get("document_id") or "")
                compare_session = dict(restored["compare_session"] or {})
                inspector_follow_mode = restored["inspector_follow_mode"] or inspector_follow_mode
                selected_review_item_id = restored["selected_review_item_id"] or selected_review_item_id
                review_filter_mode = restored["review_filter"] or review_filter_mode
                selected_workspace_mode_id = restored["selected_workspace_mode_id"] or selected_workspace_mode_id
                selected_layout_profile_id = restored["selected_layout_profile_id"] or selected_layout_profile_id
                selected_panel_configuration_id = restored["selected_panel_configuration_id"] or selected_panel_configuration_id
                workspace_dirty = False
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_menu_value=active_nav_menu, active_dropdown_value=active_nav_dropdown, active_dialog_value=active_nav_dialog, command_palette_open_value=command_palette_open, command_palette_query_value=command_palette_query, selected_command_id_value=selected_command_id, left_pane_collapsed_value=left_pane_collapsed, right_pane_collapsed_value=right_pane_collapsed, bottom_pane_collapsed_value=bottom_pane_collapsed, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "rename_workspace":
                selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id
                workspace_service.rename_workspace(workspace_id=selected_workspace_id, new_name=request.form.get("workspace_name", "").strip() or selected_workspace_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, workspace_dirty_value=True)
                ctx["saved"] = True

            elif action == "duplicate_workspace":
                selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id
                duplicated = workspace_service.duplicate_workspace(workspace_id=selected_workspace_id, new_name=request.form.get("workspace_name", "").strip())
                selected_workspace_id = duplicated.get("workspace_id", selected_workspace_id)
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "delete_workspace":
                selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id
                workspace_service.delete_workspace(selected_workspace_id)
                selected_workspace_id = ""
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value="", workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "save_workspace_snapshot":
                selected_workspace_id = request.form.get("workspace_id", "").strip() or selected_workspace_id or "workspace_session"
                payload = current_workspace_payload()
                payload["workspace_name"] = request.form.get("workspace_name", "").strip() or selected_workspace_id
                snapshot = workspace_service.save_snapshot(workspace_id=selected_workspace_id, payload=payload, note=request.form.get("snapshot_note", "").strip())
                workspace_snapshot_id = snapshot.get("snapshot_id", "")
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value=selected_workbench_anchor_id, selected_workbench_cell_id_value=selected_workbench_cell_id, selected_workbench_block_id_value=selected_workbench_block_id, workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, selected_workspace_id_value=selected_workspace_id, workspace_snapshot_id_value=workspace_snapshot_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "restore_workspace_snapshot":
                workspace_snapshot_id = request.form.get("workspace_snapshot_id", "").strip() or workspace_snapshot_id
                snapshot = workspace_service.restore_snapshot(workspace_snapshot_id)
                selected_workspace_id = snapshot.get("workspace_id", selected_workspace_id)
                restored = apply_workspace_payload(dict(snapshot.get("shell_state", {}) or {}))
                selected_nav_submodule = restored["selected_nav_submodule"]
                selected_workbench_document_id = restored["selected_workbench_document_id"]
                selected_review_document_id = restored["selected_review_document_id"]
                active_ribbon_tab = restored["active_ribbon_tab"] or active_ribbon_tab
                left_pane_collapsed = restored["left_pane_collapsed"]
                right_pane_collapsed = restored["right_pane_collapsed"]
                bottom_pane_collapsed = restored["bottom_pane_collapsed"]
                workbench_bottom_tab = restored["workbench_bottom_tab"] or workbench_bottom_tab
                workbench_inspector_mode = restored["workbench_inspector_mode"] or workbench_inspector_mode
                split_view_enabled = restored["split_view_enabled"]
                split_view_mode = restored["split_view_mode"] or split_view_mode
                split_orientation = restored["split_orientation"] or split_orientation
                active_pane_id = restored["active_pane_id"] or active_pane_id
                left_pane_document_id = str((restored["pane_documents"].get("LEFT", {}) or {}).get("document_id") or selected_workbench_document_id or selected_review_document_id)
                right_pane_document_id = str((restored["pane_documents"].get("RIGHT", {}) or {}).get("document_id") or "")
                compare_session = dict(restored["compare_session"] or {})
                inspector_follow_mode = restored["inspector_follow_mode"] or inspector_follow_mode
                selected_review_item_id = restored["selected_review_item_id"] or selected_review_item_id
                review_filter_mode = restored["review_filter"] or review_filter_mode
                selected_workspace_mode_id = restored["selected_workspace_mode_id"] or selected_workspace_mode_id
                selected_layout_profile_id = restored["selected_layout_profile_id"] or selected_layout_profile_id
                selected_panel_configuration_id = restored["selected_panel_configuration_id"] or selected_panel_configuration_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, left_pane_collapsed_value=left_pane_collapsed, right_pane_collapsed_value=right_pane_collapsed, bottom_pane_collapsed_value=bottom_pane_collapsed, selected_workspace_id_value=selected_workspace_id, workspace_snapshot_id_value=workspace_snapshot_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "restore_last_session":
                last_session = workspace_service.load_last_session()
                selected_workspace_id = last_session.get("workspace_id", selected_workspace_id)
                restored = apply_workspace_payload(dict(last_session.get("shell_state", {}) or {}))
                selected_nav_submodule = restored["selected_nav_submodule"]
                selected_workbench_document_id = restored["selected_workbench_document_id"]
                selected_review_document_id = restored["selected_review_document_id"]
                active_ribbon_tab = restored["active_ribbon_tab"] or active_ribbon_tab
                left_pane_collapsed = restored["left_pane_collapsed"]
                right_pane_collapsed = restored["right_pane_collapsed"]
                bottom_pane_collapsed = restored["bottom_pane_collapsed"]
                workbench_bottom_tab = restored["workbench_bottom_tab"] or workbench_bottom_tab
                workbench_inspector_mode = restored["workbench_inspector_mode"] or workbench_inspector_mode
                split_view_enabled = restored["split_view_enabled"]
                split_view_mode = restored["split_view_mode"] or split_view_mode
                split_orientation = restored["split_orientation"] or split_orientation
                active_pane_id = restored["active_pane_id"] or active_pane_id
                left_pane_document_id = str((restored["pane_documents"].get("LEFT", {}) or {}).get("document_id") or selected_workbench_document_id or selected_review_document_id)
                right_pane_document_id = str((restored["pane_documents"].get("RIGHT", {}) or {}).get("document_id") or "")
                compare_session = dict(restored["compare_session"] or {})
                inspector_follow_mode = restored["inspector_follow_mode"] or inspector_follow_mode
                selected_review_item_id = restored["selected_review_item_id"] or selected_review_item_id
                review_filter_mode = restored["review_filter"] or review_filter_mode
                selected_workspace_mode_id = restored["selected_workspace_mode_id"] or selected_workspace_mode_id
                selected_layout_profile_id = restored["selected_layout_profile_id"] or selected_layout_profile_id
                selected_panel_configuration_id = restored["selected_panel_configuration_id"] or selected_panel_configuration_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, left_pane_collapsed_value=left_pane_collapsed, right_pane_collapsed_value=right_pane_collapsed, bottom_pane_collapsed_value=bottom_pane_collapsed, selected_workspace_id_value=selected_workspace_id, workspace_dirty_value=False)
                ctx["saved"] = True

            elif action == "recover_workspace_autosave":
                recovery = workspace_service.load_recovery_state()
                selected_workspace_id = recovery.get("workspace_id", selected_workspace_id)
                workspace_snapshot_id = recovery.get("snapshot_id", workspace_snapshot_id)
                restored = apply_workspace_payload(dict(recovery.get("shell_state", {}) or {}))
                selected_nav_submodule = restored["selected_nav_submodule"]
                selected_workbench_document_id = restored["selected_workbench_document_id"]
                selected_review_document_id = restored["selected_review_document_id"]
                active_ribbon_tab = restored["active_ribbon_tab"] or active_ribbon_tab
                left_pane_collapsed = restored["left_pane_collapsed"]
                right_pane_collapsed = restored["right_pane_collapsed"]
                bottom_pane_collapsed = restored["bottom_pane_collapsed"]
                workbench_bottom_tab = restored["workbench_bottom_tab"] or workbench_bottom_tab
                workbench_inspector_mode = restored["workbench_inspector_mode"] or workbench_inspector_mode
                split_view_enabled = restored["split_view_enabled"]
                split_view_mode = restored["split_view_mode"] or split_view_mode
                split_orientation = restored["split_orientation"] or split_orientation
                active_pane_id = restored["active_pane_id"] or active_pane_id
                left_pane_document_id = str((restored["pane_documents"].get("LEFT", {}) or {}).get("document_id") or selected_workbench_document_id or selected_review_document_id)
                right_pane_document_id = str((restored["pane_documents"].get("RIGHT", {}) or {}).get("document_id") or "")
                compare_session = dict(restored["compare_session"] or {})
                inspector_follow_mode = restored["inspector_follow_mode"] or inspector_follow_mode
                selected_review_item_id = restored["selected_review_item_id"] or selected_review_item_id
                review_filter_mode = restored["review_filter"] or review_filter_mode
                selected_workspace_mode_id = restored["selected_workspace_mode_id"] or selected_workspace_mode_id
                selected_layout_profile_id = restored["selected_layout_profile_id"] or selected_layout_profile_id
                selected_panel_configuration_id = restored["selected_panel_configuration_id"] or selected_panel_configuration_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode, selected_workbench_document_id_value=selected_workbench_document_id, selected_workbench_anchor_id_value="", selected_workbench_cell_id_value="", selected_workbench_block_id_value="", workbench_selected_page_value=workbench_selected_page, workbench_tool_mode_value=workbench_tool_mode, workbench_center_mode_value=workbench_center_mode, workbench_bottom_tab_value=workbench_bottom_tab, workbench_inspector_mode_value=workbench_inspector_mode, workbench_filter_document_type_value=workbench_filter_document_type, workbench_filter_status_value=workbench_filter_status, workbench_search_text_value=workbench_search_text, active_ribbon_tab_value=active_ribbon_tab, left_pane_collapsed_value=left_pane_collapsed, right_pane_collapsed_value=right_pane_collapsed, bottom_pane_collapsed_value=bottom_pane_collapsed, selected_workspace_id_value=selected_workspace_id, workspace_snapshot_id_value=workspace_snapshot_id, workspace_dirty_value=False, restore_candidate_workspace_id_value=selected_workspace_id, restore_candidate_snapshot_id_value=workspace_snapshot_id)
                ctx["saved"] = True

            elif action == "open_workbench_document":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()

                if not workbench_document_id:
                    raise ValueError("workbench_document_id is required")

                open_document_in_workbench(
                    portalis_root,
                    document_id=workbench_document_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_document":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                workbench_notes = request.form.get("workbench_notes", "").strip()
                workbench_status_value = request.form.get("workbench_status_value", "").strip().upper()
                workbench_tags_value = request.form.get("workbench_tags_value", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                selected_workbench_anchor_id = request.form.get("workbench_anchor_id", "").strip()
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()

                if not workbench_document_id:
                    raise ValueError("workbench_document_id is required")

                update_document_workbench(
                    portalis_root,
                    document_id=workbench_document_id,
                    workbench_notes=workbench_notes,
                    workbench_status=workbench_status_value,
                    workbench_tags=workbench_tags_value,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "select_workbench_anchor":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_anchor_id = request.form.get("workbench_anchor_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                if not workbench_document_id or not selected_workbench_anchor_id:
                    raise ValueError("workbench document and anchor are required")
                select_document_anchor(
                    portalis_root,
                    document_id=workbench_document_id,
                    anchor_id=selected_workbench_anchor_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "clear_workbench_selection":
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value="",
                    selected_workbench_cell_id_value="",
                    selected_workbench_block_id_value="",
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "add_workbench_anchor":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                updated_document = add_document_anchor(
                    portalis_root,
                    document_id=workbench_document_id,
                    anchor_type=request.form.get("anchor_type", "").strip() or workbench_tool_mode.replace("ADD_", ""),
                    page_number=request.form.get("anchor_page_number", "1").strip() or "1",
                    x1=request.form.get("anchor_x1", "10").strip() or "10",
                    y1=request.form.get("anchor_y1", "10").strip() or "10",
                    x2=request.form.get("anchor_x2", "30").strip() or "30",
                    y2=request.form.get("anchor_y2", "20").strip() or "20",
                    field_name=request.form.get("anchor_field_name", "").strip(),
                    label=request.form.get("anchor_label", "").strip(),
                    note=request.form.get("anchor_note", "").strip(),
                    linked_annotation_id=request.form.get("anchor_linked_annotation_id", "").strip(),
                    linked_scratchpad_id=request.form.get("anchor_linked_scratchpad_id", "").strip(),
                    linked_entity_field=request.form.get("anchor_linked_entity_field", "").strip(),
                    confidence=request.form.get("anchor_confidence", "").strip() or None,
                    status=request.form.get("anchor_status", "").strip() or "ACTIVE",
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = str((updated_document.get("anchors") or [{}])[-1].get("anchor_id") or "")
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_anchor":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_anchor_id = request.form.get("workbench_anchor_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                update_document_anchor(
                    portalis_root,
                    document_id=workbench_document_id,
                    anchor_id=selected_workbench_anchor_id,
                    anchor_type=request.form.get("anchor_type", "").strip(),
                    page_number=request.form.get("anchor_page_number", "1").strip() or "1",
                    x1=request.form.get("anchor_x1", "").strip() or None,
                    y1=request.form.get("anchor_y1", "").strip() or None,
                    x2=request.form.get("anchor_x2", "").strip() or None,
                    y2=request.form.get("anchor_y2", "").strip() or None,
                    field_name=request.form.get("anchor_field_name", "").strip(),
                    label=request.form.get("anchor_label", "").strip(),
                    note=request.form.get("anchor_note", "").strip(),
                    linked_annotation_id=request.form.get("anchor_linked_annotation_id", "").strip(),
                    linked_scratchpad_id=request.form.get("anchor_linked_scratchpad_id", "").strip(),
                    linked_entity_field=request.form.get("anchor_linked_entity_field", "").strip(),
                    confidence=request.form.get("anchor_confidence", "").strip() or None,
                    status=request.form.get("anchor_status", "").strip(),
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "delete_workbench_anchor":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_anchor_id = request.form.get("workbench_anchor_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                delete_document_anchor(
                    portalis_root,
                    document_id=workbench_document_id,
                    anchor_id=selected_workbench_anchor_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value="",
                    selected_workbench_cell_id_value="",
                    selected_workbench_block_id_value="",
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "add_workbench_annotation":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                add_workbench_annotation(
                    portalis_root,
                    document_id=workbench_document_id,
                    annotation_type=request.form.get("annotation_type", "").strip(),
                    label=request.form.get("annotation_label", "").strip(),
                    note=request.form.get("annotation_note", "").strip(),
                    page_number=request.form.get("annotation_page_number", "1").strip() or "1",
                    region_hint=request.form.get("annotation_region_hint", "").strip(),
                    status=request.form.get("annotation_status", "").strip() or "ACTIVE",
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_annotation":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                annotation_id = request.form.get("annotation_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                update_workbench_annotation(
                    portalis_root,
                    document_id=workbench_document_id,
                    annotation_id=annotation_id,
                    annotation_type=request.form.get("annotation_type", "").strip(),
                    label=request.form.get("annotation_label", "").strip(),
                    note=request.form.get("annotation_note", "").strip(),
                    page_number=request.form.get("annotation_page_number", "1").strip() or "1",
                    region_hint=request.form.get("annotation_region_hint", "").strip(),
                    status=request.form.get("annotation_status", "").strip() or "ACTIVE",
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "delete_workbench_annotation":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                annotation_id = request.form.get("annotation_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                delete_workbench_annotation(
                    portalis_root,
                    document_id=workbench_document_id,
                    annotation_id=annotation_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "add_workbench_scratchpad":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                add_workbench_scratchpad_field(
                    portalis_root,
                    document_id=workbench_document_id,
                    field_name=request.form.get("scratchpad_field_name", "").strip(),
                    candidate_value=request.form.get("scratchpad_candidate_value", "").strip(),
                    linked_entity_field=request.form.get("scratchpad_linked_entity_field", "").strip(),
                    confidence_note=request.form.get("scratchpad_confidence_note", "").strip(),
                    source_hint=request.form.get("scratchpad_source_hint", "").strip(),
                    operator_note=request.form.get("scratchpad_operator_note", "").strip(),
                    status=request.form.get("scratchpad_status", "").strip() or "DRAFT",
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_scratchpad":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                scratchpad_id = request.form.get("scratchpad_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                update_workbench_scratchpad_field(
                    portalis_root,
                    document_id=workbench_document_id,
                    scratchpad_id=scratchpad_id,
                    field_name=request.form.get("scratchpad_field_name", "").strip(),
                    candidate_value=request.form.get("scratchpad_candidate_value", "").strip(),
                    linked_entity_field=request.form.get("scratchpad_linked_entity_field", "").strip(),
                    confidence_note=request.form.get("scratchpad_confidence_note", "").strip(),
                    source_hint=request.form.get("scratchpad_source_hint", "").strip(),
                    operator_note=request.form.get("scratchpad_operator_note", "").strip(),
                    status=request.form.get("scratchpad_status", "").strip() or "DRAFT",
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "delete_workbench_scratchpad":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                scratchpad_id = request.form.get("scratchpad_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                delete_workbench_scratchpad_field(
                    portalis_root,
                    document_id=workbench_document_id,
                    scratchpad_id=scratchpad_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "select_workbench_cell":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_cell_id = request.form.get("workbench_cell_id", "").strip()
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                if not workbench_document_id or not selected_workbench_cell_id:
                    raise ValueError("workbench document and cell are required")
                select_reconstruction_cell(
                    portalis_root,
                    document_id=workbench_document_id,
                    cell_id=selected_workbench_cell_id,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_block_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "select_workbench_block":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_block_id = request.form.get("workbench_block_id", "").strip()
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                if not workbench_document_id or not selected_workbench_block_id:
                    raise ValueError("workbench document and block are required")
                select_reconstruction_block(
                    portalis_root,
                    document_id=workbench_document_id,
                    block_id=selected_workbench_block_id,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_cell":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_cell_id = request.form.get("workbench_cell_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                update_reconstruction_cell(
                    portalis_root,
                    document_id=workbench_document_id,
                    cell_id=selected_workbench_cell_id,
                    text_value=request.form.get("cell_text_value", ""),
                    content_type=request.form.get("cell_content_type", ""),
                    linked_field_name=request.form.get("cell_linked_field_name", ""),
                    linked_anchor_id=request.form.get("cell_linked_anchor_id", ""),
                    editable_flag=request.form.get("cell_editable_flag", "").strip() or None,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_block_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "clear_workbench_cell":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_cell_id = request.form.get("workbench_cell_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                clear_reconstruction_cell(
                    portalis_root,
                    document_id=workbench_document_id,
                    cell_id=selected_workbench_cell_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_block_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "merge_workbench_cells":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_cell_id = request.form.get("workbench_cell_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                updated_document = merge_reconstruction_cells(
                    portalis_root,
                    document_id=workbench_document_id,
                    lead_cell_id=selected_workbench_cell_id,
                    row_span=request.form.get("block_row_span", "1"),
                    col_span=request.form.get("block_col_span", "1"),
                    label=request.form.get("block_label", ""),
                    note=request.form.get("block_note", ""),
                    linked_anchor_id=request.form.get("block_linked_anchor_id", ""),
                    operator_name=queue_operator_name,
                )
                blocks = list(updated_document.get("reconstruction_grid", {}).get("blocks", []) or [])
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = str(blocks[-1].get("block_id") or "") if blocks else ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "split_workbench_block":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_block_id = request.form.get("workbench_block_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                split_reconstruction_block(
                    portalis_root,
                    document_id=workbench_document_id,
                    block_id=selected_workbench_block_id,
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                selected_workbench_block_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "update_workbench_block":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                selected_workbench_block_id = request.form.get("workbench_block_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
                workbench_tool_mode = request.form.get("workbench_tool_mode", "").strip().upper() or "SELECT"
                workbench_filter_document_type = request.form.get("workbench_filter_document_type", "").strip()
                workbench_filter_status = request.form.get("workbench_filter_status", "").strip().upper()
                workbench_search_text = request.form.get("workbench_search_text", "").strip()
                update_reconstruction_block(
                    portalis_root,
                    document_id=workbench_document_id,
                    block_id=selected_workbench_block_id,
                    label=request.form.get("block_label", ""),
                    note=request.form.get("block_note", ""),
                    linked_anchor_id=request.form.get("block_linked_anchor_id", ""),
                    operator_name=queue_operator_name,
                )
                selected_workbench_document_id = workbench_document_id
                selected_workbench_anchor_id = ""
                selected_workbench_cell_id = ""
                workbench_inspector_mode = "SELECTION"
                workbench_bottom_tab = "RECONSTRUCTION"
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
                    selected_workbench_anchor_id_value=selected_workbench_anchor_id,
                    selected_workbench_cell_id_value=selected_workbench_cell_id,
                    selected_workbench_block_id_value=selected_workbench_block_id,
                    workbench_selected_page_value=workbench_selected_page,
                    workbench_tool_mode_value=workbench_tool_mode,
                    workbench_center_mode_value=workbench_center_mode,
                    workbench_bottom_tab_value=workbench_bottom_tab,
                    workbench_inspector_mode_value=workbench_inspector_mode,
                    workbench_filter_document_type_value=workbench_filter_document_type,
                    workbench_filter_status_value=workbench_filter_status,
                    workbench_search_text_value=workbench_search_text,
                )
                ctx["saved"] = True

            elif action == "save_portalis":
                form = request.form.to_dict(flat=True)
                state = update_vessel_from_form(state, form)
                state = update_voyage_from_form(state, form)
                state = update_documents_from_form(state, request.form)
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=state.voyage.arrival_port or selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True

            elif action == "create_crew":
                name = request.form.get("crew_name", "").strip()
                rank = request.form.get("crew_rank", "").strip()
                if name:
                    new_id = create_crew(portalis_root, name, rank)
                    state.crew_registry.last_created_crew_id = new_id
                    state.crew_registry.selected_crew_id = new_id
                    save_portalis_state(state, str(state_path))
                    selected_crew_id = new_id
                    ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                    ctx["saved"] = True

            elif action == "add_crew_document":
                crew_id = request.form.get("crew_id", "").strip()
                if not crew_id:
                    raise ValueError("crew_id is required")

                add_document_to_crew(
                    portalis_root,
                    crew_id,
                    doc_type=request.form.get("doc_type", "").strip(),
                    doc_subtype=request.form.get("doc_subtype", "").strip(),
                    document_number=request.form.get("document_number", "").strip(),
                    country=request.form.get("country", "").strip(),
                    issue_date=request.form.get("issue_date", "").strip(),
                    expiry_date=request.form.get("expiry_date", "").strip(),
                    is_primary=(request.form.get("is_primary") == "on"),
                    status=request.form.get("doc_status", "").strip() or "ACTIVE",
                    source_file=request.form.get("source_file", "").strip(),
                    confidence=request.form.get("confidence", "").strip(),
                    notes=request.form.get("doc_notes", "").strip(),
                )
                selected_crew_id = crew_id
                state.crew_registry.selected_crew_id = crew_id
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True

            elif action == "save_port_requirements":
                port_name = request.form.get("port_name", "").strip()
                if not port_name:
                    raise ValueError("port_name is required")

                save_port_requirement(
                    portalis_root,
                    port_name=port_name,
                    country=request.form.get("port_country", "").strip(),
                    required_docs=textarea_to_list(request.form.get("required_docs_text", "")),
                    non_standard_forms=textarea_to_list(request.form.get("non_standard_forms_text", "")),
                    certificate_requirements=textarea_to_list(request.form.get("certificate_requirements_text", "")),
                    notes=request.form.get("port_notes", "").strip(),
                )
                selected_port_name = port_name
                state.port_requirements.selected_port_name = port_name
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True

            elif action == "generate_crew_list":
                text = generate_crew_list_txt(portalis_root, state)
                filename = f"crew_list_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "crew_lists", filename, text)
                append_generated_output(state, category="crew_lists", output_path=out_path)
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["generated_paths"] = [out_path]
                ctx["generated_preview"] = text
                ctx["saved"] = True

            elif action == "generate_health_decl":
                text = generate_health_declaration_txt(portalis_root, state)
                filename = f"health_decl_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "health", filename, text)
                append_generated_output(state, category="health", output_path=out_path)
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["generated_paths"] = [out_path]
                ctx["generated_preview"] = text
                ctx["saved"] = True

            elif action == "generate_port_checklist":
                text = generate_port_checklist_txt(portalis_root, state)
                filename = f"port_checklist_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "checklists", filename, text)
                append_generated_output(state, category="checklists", output_path=out_path)
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["generated_paths"] = [out_path]
                ctx["generated_preview"] = text
                ctx["saved"] = True

            elif action == "save_certificate":
                save_certificate(
                    portalis_root,
                    name=request.form.get("cert_name"),
                    number=request.form.get("cert_number"),
                    issuer=request.form.get("cert_issuer"),
                    issue_date=request.form.get("cert_issue_date"),
                    expiry_date=request.form.get("cert_expiry_date"),
                    notes=request.form.get("cert_notes"),
                )
                save_portalis_state(state, str(state_path))
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True

            elif action == "import_crew_passport":
                source_path = request.form.get("passport_source_path", "").strip()
                crew_id = request.form.get("passport_crew_id", "").strip() or selected_crew_id

                if not source_path:
                    raise ValueError("passport_source_path is required")
                if not crew_id:
                    raise ValueError("passport_crew_id is required")

                import_result = import_declared_document(
                    ImportRequest(
                        source_path=source_path,
                        document_type="CREW_PASSPORT",
                        declared_entity_kind="crew",
                        declared_entity_id=crew_id,
                        notes="Portalis operator passport import",
                        tags=["portalis_alpha", "passport"],
                    ),
                    portalis_root=portalis_root,
                )

                if not import_result.ok:
                    ctx = build_ctx(state, selected_crew_id_value=crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                    ctx["errors"] = import_result.errors or ["Passport import failed"]
                    return render_template("portalis.html", **ctx)

                documents = registry.list_documents()
                last_document = documents[-1] if documents else {}
                state.document_registry.last_import_document_id = last_document.get("document_id")
                state.document_registry.last_import_manifest_path = import_result.manifest_path
                state.review_queue.last_document_id = last_document.get("document_id")
                state.crew_registry.selected_crew_id = crew_id
                save_portalis_state(state, str(state_path))

                selected_review_document_id = last_document.get("document_id") or ""
                ctx = build_ctx(state, selected_crew_id_value=crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True
                ctx["generated_paths"] = [import_result.manifest_path] if import_result.manifest_path else []

            elif action in {"accept_review_item", "resolve_review_item", "reject_review_item"}:
                review_document_id = request.form.get("review_document_id", "").strip()
                operator_name = request.form.get("review_operator_name", "").strip() or "operator"
                resolution_reason = request.form.get("review_resolution_reason", "").strip()
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")

                review_item = review_service.get_review_item(review_document_id)
                edited_fields = {}
                selected_candidate_ids = {}
                field_actions = {}
                unresolved_reasons = {}
                for key, value in request.form.items():
                    if key.startswith("review_field__"):
                        field_name = key.replace("review_field__", "", 1)
                        edited_fields[field_name] = value.strip()
                    elif key.startswith("review_selected_candidate__"):
                        field_name = key.replace("review_selected_candidate__", "", 1)
                        selected_candidate_ids[field_name] = value.strip()
                    elif key.startswith("review_field_action__"):
                        field_name = key.replace("review_field_action__", "", 1)
                        field_actions[field_name] = value.strip()
                    elif key.startswith("review_unresolved_reason__"):
                        field_name = key.replace("review_unresolved_reason__", "", 1)
                        unresolved_reasons[field_name] = value.strip()

                action_map = {
                    "accept_review_item": "ACCEPT",
                    "resolve_review_item": "RESOLVE",
                    "reject_review_item": "REJECT",
                }
                write_result = review_service.resolve(
                    ReviewResolutionCoupler(
                        review_item=review_item,
                        operator_action=action_map[action],
                        edited_fields=edited_fields,
                        selected_candidate_ids=selected_candidate_ids,
                        field_actions=field_actions,
                        unresolved_reasons=unresolved_reasons,
                        operator_name=operator_name,
                        resolution_reason=resolution_reason,
                    )
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))

                selected_review_document_id = review_document_id
                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id, review_filter_mode_value=review_filter_mode)
                ctx["saved"] = True
                if write_result.crew_record_path:
                    ctx["generated_paths"] = [write_result.crew_record_path]

            elif action == "apply_queue_triage":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                triage_action = request.form.get("queue_triage_action", "").strip().upper()
                triage_note = request.form.get("queue_triage_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not triage_action:
                    raise ValueError("queue_triage_action is required")

                apply_triage_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    triage_action=triage_action,
                    operator_name=queue_operator_name,
                    triage_note=triage_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_queue_assignment":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                assignment_action = request.form.get("queue_assignment_action", "").strip().upper()
                assignment_bucket = request.form.get("queue_assignment_bucket", "").strip().upper()
                assignment_owner = request.form.get("queue_assignment_owner", "").strip().upper()
                assignment_note = request.form.get("queue_assignment_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not assignment_action:
                    raise ValueError("queue_assignment_action is required")

                apply_assignment_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    assignment_action=assignment_action,
                    operator_name=queue_operator_name,
                    assignment_note=assignment_note,
                    assigned_bucket=assignment_bucket,
                    owner_hint=assignment_owner,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_watch_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                watch_action = request.form.get("queue_watch_action", "").strip().upper()
                watch_note = request.form.get("queue_watch_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not watch_action:
                    raise ValueError("queue_watch_action is required")

                apply_watch_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    watch_action=watch_action,
                    operator_name=queue_operator_name,
                    watch_note=watch_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_reminder_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                reminder_action = request.form.get("queue_reminder_action", "").strip().upper()
                reminder_note = request.form.get("queue_reminder_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not reminder_action:
                    raise ValueError("queue_reminder_action is required")

                apply_reminder_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    reminder_action=reminder_action,
                    operator_name=queue_operator_name,
                    reminder_note=reminder_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_notification_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                notification_action = request.form.get("queue_notification_action", "").strip().upper()
                notification_note = request.form.get("queue_notification_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not notification_action:
                    raise ValueError("queue_notification_action is required")

                apply_notification_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    notification_action=notification_action,
                    operator_name=queue_operator_name,
                    notification_note=notification_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_transport_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                transport_action = request.form.get("queue_transport_action", "").strip().upper()
                transport_note = request.form.get("queue_transport_note", "").strip()
                transport_channel = request.form.get("queue_transport_channel", "").strip().upper()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not transport_action:
                    raise ValueError("queue_transport_action is required")

                apply_transport_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    transport_action=transport_action,
                    operator_name=queue_operator_name,
                    transport_note=transport_note,
                    channel_hint=transport_channel,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_alert_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                alert_action = request.form.get("queue_alert_action", "").strip().upper()
                alert_note = request.form.get("queue_alert_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not alert_action:
                    raise ValueError("queue_alert_action is required")

                apply_alert_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    alert_action=alert_action,
                    operator_name=queue_operator_name,
                    alert_note=alert_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_incident_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                incident_action = request.form.get("queue_incident_action", "").strip().upper()
                incident_note = request.form.get("queue_incident_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not incident_action:
                    raise ValueError("queue_incident_action is required")

                apply_incident_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    incident_action=incident_action,
                    operator_name=queue_operator_name,
                    incident_note=incident_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_external_bridge_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                bridge_action = request.form.get("queue_bridge_action", "").strip().upper()
                bridge_note = request.form.get("queue_bridge_note", "").strip()
                bridge_target = request.form.get("queue_bridge_target", "").strip().upper()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not bridge_action:
                    raise ValueError("queue_bridge_action is required")

                apply_external_bridge_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    bridge_action=bridge_action,
                    operator_name=queue_operator_name,
                    bridge_note=bridge_note,
                    target_hint=bridge_target,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_intake_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                intake_action = request.form.get("queue_intake_action", "").strip().upper()
                intake_note = request.form.get("queue_intake_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not intake_action:
                    raise ValueError("queue_intake_action is required")

                apply_intake_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    intake_action=intake_action,
                    operator_name=queue_operator_name,
                    intake_note=intake_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "apply_dropzone_action":
                review_document_id = request.form.get("review_document_id", "").strip()
                field_name = request.form.get("queue_field_name", "").strip()
                handshake_action = request.form.get("queue_dropzone_action", "").strip().upper()
                handshake_note = request.form.get("queue_dropzone_note", "").strip()
                queue_operator_name = request.form.get("queue_operator_name", "").strip() or "operator"
                review_filter_mode = request.form.get("review_filter_mode", "").strip() or review_filter_mode

                if not review_document_id:
                    raise ValueError("review_document_id is required")
                if not field_name:
                    raise ValueError("queue_field_name is required")
                if not handshake_action:
                    raise ValueError("queue_dropzone_action is required")

                apply_dropzone_action(
                    portalis_root,
                    document_id=review_document_id,
                    field_name=field_name,
                    handshake_action=handshake_action,
                    operator_name=queue_operator_name,
                    handshake_note=handshake_note,
                )

                state.review_queue.last_document_id = review_document_id
                save_portalis_state(state, str(state_path))
                selected_review_document_id = review_document_id
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                )
                ctx["saved"] = True

            elif action == "import_arrival_db":
                crew_excel_path = request.form.get("crew_excel_path", "").strip()
                ship_pdf_path = request.form.get("ship_pdf_path", "").strip()
                cert_paths_raw = request.form.get("cert_paths", "").strip()
                cert_paths = [item.strip() for item in cert_paths_raw.split(",") if item.strip()]

                if not crew_excel_path:
                    raise ValueError("crew_excel_path is required")
                if not ship_pdf_path:
                    raise ValueError("ship_pdf_path is required")

                crew_rows = load_arrival_database(crew_excel_path)
                ship_data = load_ship_particulars(ship_pdf_path)
                certs = [load_certificate_pdf(path) for path in cert_paths]

                state = apply_ship_to_state(state, ship_data)
                import_crew_rows(portalis_root, crew_rows)
                import_certificates(portalis_root, certs)
                save_portalis_state(state, str(state_path))

                ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
                ctx["saved"] = True

        except Exception as e:
            ctx = build_ctx(state, selected_crew_id_value=selected_crew_id, selected_port_name_value=selected_port_name, selected_review_document_id_value=selected_review_document_id)
            ctx["errors"] = [str(e)]

    return render_template("portalis.html", **ctx)

@app.route("/reports")
def reports():
    return render_template("reports.html", usb_root=str(USB_ROOT), utc_now=utc_now_iso())


if __name__ == "__main__":
    try:
        log_startup_paths()

        url = "http://127.0.0.1:5000/"
        try:
            webbrowser.open(url)
        except Exception:
            pass

        app.run(host="127.0.0.1", port=5000, debug=False)
    except Exception as e:
        log_startup_error(e)
        raise
