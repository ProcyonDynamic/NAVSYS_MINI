from __future__ import annotations

import sys
import traceback
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

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
    apply_notification_action,
    apply_reminder_action,
    apply_transport_action,
    apply_triage_action,
    apply_watch_action,
    refresh_control_room_state,
)
from modules.portalis_mini.studio_workbench_service import (
    build_document_workbench,
    open_document_in_workbench,
    resolve_document_source_path,
    update_document_workbench,
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

    def build_ctx(
        state_obj,
        *,
        selected_crew_id_value="",
        selected_port_name_value="",
        selected_review_document_id_value="",
        review_filter_mode_value="all",
        selected_workbench_document_id_value="",
        workbench_filter_document_type_value="",
        workbench_filter_status_value="",
        workbench_search_text_value="",
    ):
        crew_items = list_crew(portalis_root)
        certificate_items = list_certificates(portalis_root)
        port_items = list_ports(portalis_root)
        control_room = refresh_control_room_state(portalis_root)
        review_items = control_room["review_items"]
        document_entries = registry.list_documents()
        workbench_packet = build_document_workbench(
            portalis_root,
            selected_document_id=selected_workbench_document_id_value,
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
        dashboard_summary_value = control_room["dashboard_summary"]
        dashboard_tce_delta_value = control_room["dashboard_tce_delta"]

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
            "selected_workbench_document": workbench_packet.get("selected_document"),
            "workbench_filter_document_type": workbench_filter_document_type_value,
            "workbench_filter_status": workbench_filter_status_value,
            "workbench_search_text": workbench_search_text_value,
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
            "dashboard_summary": dashboard_summary_value,
            "dashboard_tce_delta": dashboard_tce_delta_value,
            "last_import_document_id": state_obj.document_registry.last_import_document_id,
            "last_import_manifest_path": state_obj.document_registry.last_import_manifest_path,
        }

    state = load_portalis_state(str(state_path))
    selected_crew_id = request.args.get("crew_id", "").strip() or (state.crew_registry.selected_crew_id or "")
    selected_port_name = request.args.get("port_name", "").strip() or (state.port_requirements.selected_port_name or state.voyage.arrival_port or "")
    selected_review_document_id = request.args.get("review_document_id", "").strip() or (state.review_queue.last_document_id or "")
    selected_workbench_document_id = request.args.get("workbench_document_id", "").strip()
    review_filter_mode = request.args.get("review_filter", "").strip() or "all"
    workbench_filter_document_type = request.args.get("workbench_document_type", "").strip()
    workbench_filter_status = request.args.get("workbench_status", "").strip().upper()
    workbench_search_text = request.args.get("workbench_search", "").strip()
    ctx = build_ctx(
        state,
        selected_crew_id_value=selected_crew_id,
        selected_port_name_value=selected_port_name,
        selected_review_document_id_value=selected_review_document_id,
        review_filter_mode_value=review_filter_mode,
        selected_workbench_document_id_value=selected_workbench_document_id,
        workbench_filter_document_type_value=workbench_filter_document_type,
        workbench_filter_status_value=workbench_filter_status,
        workbench_search_text_value=workbench_search_text,
    )

    if request.method == "POST":
        try:
            action = request.form.get("action", "").strip()

            if action == "open_workbench_document":
                workbench_document_id = request.form.get("workbench_document_id", "").strip()
                queue_operator_name = request.form.get("workbench_operator_name", "").strip() or "operator"
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
                ctx = build_ctx(
                    state,
                    selected_crew_id_value=selected_crew_id,
                    selected_port_name_value=selected_port_name,
                    selected_review_document_id_value=selected_review_document_id,
                    review_filter_mode_value=review_filter_mode,
                    selected_workbench_document_id_value=selected_workbench_document_id,
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
