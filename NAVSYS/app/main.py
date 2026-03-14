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

from modules.navwarn_mini.bulletin_splitter import split_navarea_bulletin
from modules.navwarn_mini.txt_ingester_helper import split_txt_blocks

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

from flask import Flask, render_template, request

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
from modules.portalis_mini.service import (
    update_vessel_from_form,
    update_voyage_from_form,
    update_documents_from_form,
)

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

def _safe_filename(s: str) -> str:
    return (
        (s or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    


USB_ROOT = Path(r"D:\NAVSYS_USB")
TEMPLATES_DIR = USB_ROOT / "NAVSYS" / "ui" / "templates"
STATIC_DIR = USB_ROOT / "NAVSYS" / "ui" / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float_or_none(s: str):
    s = (s or "").strip()
    if not s:
        return None
    return float(s)


@app.route("/")
def home():
    return render_template("home.html", usb_root=str(USB_ROOT), utc_now=utc_now_iso())


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
        },
        "preview_geom": "",
        "preview_vertices": "",
        "result": None,
        "errors": [],
        "results": [],
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
        }
        ctx["form"] = form

        txt_file = request.files.get("warning_txt")
        if txt_file and txt_file.filename and txt_file.filename.lower().endswith(".txt"):
            uploaded_text = txt_file.read().decode("utf-8", errors="replace")
            if uploaded_text.strip():
                form["raw_text"] = uploaded_text.strip()
        
        try:
            if action == "preview":
                blocks = split_navarea_bulletin(form["raw_text"])
                preview_text = blocks[0]["raw_text"] if blocks else form["raw_text"]

                verts, geom = extract_vertices_and_geom(preview_text)
                ctx["preview_geom"] = geom
                ctx["preview_vertices"] = preview_vertices_dm(verts)

                
            elif action == "process":
                blocks = split_navarea_bulletin(form["raw_text"])

                # Fallback: if no NAVAREA headers found, treat whole text as one warning
                if not blocks:
                    blocks = [{
                    "warning_id": form["warning_id"],
                    "raw_text": form["raw_text"],
                }]

                results = []
                all_errors = []

                for block in blocks:
                    res = process_warning_text(
                        raw_text=block["raw_text"],
                        navarea=form["navarea"] or "IV",
                        ship_lat=_to_float_or_none(form["ship_lat"]),
                        ship_lon=_to_float_or_none(form["ship_lon"]),
                        output_root=str(USB_ROOT),
                        warning_id=block["warning_id"] or form["warning_id"],
                        title=form["title"],
                        source_kind=form["source_kind"],
                        route_csv_path=form["route_csv_path"] or None,
                    )
                    results.append(res)

                    if not res.get("ok", False):
                        all_errors.extend(res.get("errors", []))

                ctx["results"] = results
                ctx["result"] = results[0] if results else None
                ctx["errors"] = all_errors

                preview_text = blocks[0]["raw_text"] if blocks else form["raw_text"]
                verts, geom = extract_vertices_and_geom(preview_text)
                ctx["preview_geom"] = geom
                ctx["preview_vertices"] = preview_vertices_dm(verts)

                if not res.get("ok", False):
                    ctx["errors"] = res.get("errors", [])

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

    state = load_portalis_state(str(state_path))
    crew = list_crew(portalis_root)
    certificates = list_certificates(portalis_root)

    selected_crew_id = request.args.get("crew_id", "").strip()
    selected_crew = None
    if selected_crew_id:
        try:
            selected_crew = load_crew_record(portalis_root, selected_crew_id)
        except Exception:
            selected_crew = None

    selected_port_name = request.args.get("port_name", "").strip() or state.voyage.arrival_port.strip()

    selected_port = None
    if selected_port_name:
        selected_port = load_port_requirement(portalis_root, selected_port_name)

    required_cert_results = []
    if selected_port:
        required_cert_results = check_required_certificates(
            selected_port["certificate_requirements"],
            certificates,
        )

    ctx = {
        "usb_root": str(USB_ROOT),
        "utc_now": utc_now_iso(),
        "state": state,
        "crew": crew,
        "selected_crew": selected_crew,
        "selected_crew_id": selected_crew_id,
        "ports": list_ports(portalis_root),
        "selected_port": selected_port,
        "selected_port_name": selected_port_name,
        "saved": False,
        "errors": [],
        "generated_paths": [],
        "generated_preview": "",
        "certificates": certificates,
        "cert_check": required_cert_results,
        "port_form": {
            "port_name": selected_port["port_name"] if selected_port else selected_port_name,
            "country": selected_port["country"] if selected_port else "",
            "required_docs": list_to_textarea(selected_port["required_docs"]) if selected_port else "",
            "non_standard_forms": list_to_textarea(selected_port["non_standard_forms"]) if selected_port else "",
            "certificate_requirements": list_to_textarea(selected_port["certificate_requirements"]) if selected_port else "",
            "notes": selected_port["notes"] if selected_port else "",
        },
    }

    if request.method == "POST":
        try:
            action = request.form.get("action", "").strip()

            if action == "save_portalis":
                form = request.form.to_dict(flat=True)
                state = update_vessel_from_form(state, form)
                state = update_voyage_from_form(state, form)
                state = update_documents_from_form(state, request.form)
                save_portalis_state(state, str(state_path))
                ctx["state"] = state
                ctx["saved"] = True

            elif action == "create_crew":
                name = request.form.get("crew_name", "").strip()
                rank = request.form.get("crew_rank", "").strip()
                if name:
                    new_id = create_crew(portalis_root, name, rank)
                    crew = list_crew(portalis_root)
                    selected_crew_id = new_id
                    selected_crew = load_crew_record(portalis_root, new_id)

                    ctx["crew"] = crew
                    ctx["selected_crew"] = selected_crew
                    ctx["selected_crew_id"] = selected_crew_id
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

                crew = list_crew(portalis_root)
                selected_crew_id = crew_id
                selected_crew = load_crew_record(portalis_root, crew_id)

                ctx["crew"] = crew
                ctx["selected_crew"] = selected_crew
                ctx["selected_crew_id"] = selected_crew_id
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
                selected_port = load_port_requirement(portalis_root, port_name)

                ctx["ports"] = list_ports(portalis_root)
                ctx["selected_port"] = selected_port
                ctx["selected_port_name"] = selected_port_name
                ctx["port_form"] = {
                    "port_name": selected_port["port_name"],
                    "country": selected_port["country"],
                    "required_docs": list_to_textarea(selected_port["required_docs"]),
                    "non_standard_forms": list_to_textarea(selected_port["non_standard_forms"]),
                    "certificate_requirements": list_to_textarea(selected_port["certificate_requirements"]),
                    "notes": selected_port["notes"],
                }
                ctx["cert_check"] = check_required_certificates(
                    selected_port["certificate_requirements"],
                    ctx["certificates"],
                )
                ctx["saved"] = True

            elif action == "generate_crew_list":
                text = generate_crew_list_txt(portalis_root, state)
                filename = f"crew_list_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "crew_lists", filename, text)
                ctx["generated_paths"] = [out_path]
                ctx["generated_preview"] = text
                ctx["saved"] = True

            elif action == "generate_health_decl":
                text = generate_health_declaration_txt(portalis_root, state)
                filename = f"health_decl_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "health", filename, text)
                ctx["generated_paths"] = [out_path]
                ctx["generated_preview"] = text
                ctx["saved"] = True

            elif action == "generate_port_checklist":
                text = generate_port_checklist_txt(portalis_root, state)
                filename = f"port_checklist_{_safe_filename(state.voyage.arrival_port or 'port')}.txt"
                out_path = save_generated_text(portalis_root, "checklists", filename, text)
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

                ctx["certificates"] = list_certificates(portalis_root)

                if ctx["selected_port"]:
                    ctx["cert_check"] = check_required_certificates(
                        ctx["selected_port"]["certificate_requirements"],
                        ctx["certificates"],
                    )

                ctx["saved"] = True

        except Exception as e:
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