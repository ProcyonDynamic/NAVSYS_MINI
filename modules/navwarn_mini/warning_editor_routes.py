from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path

from flask import Blueprint, render_template, request

from .warning_editor_service import (
    apply_warning_override_to_payload,
    build_warning_editor_payload,
    rebuild_plot_objects_from_editor_payload,
)
from .warning_override_store import save_warning_override


warning_editor_bp = Blueprint("warning_editor", __name__)

DEFAULT_OUTPUT_ROOT = str(Path(__file__).resolve().parents[2])


def _default_form_data() -> dict:
    return {
        "raw_text": "",
        "navarea": "",
        "warning_id": "",
        "title": "",
        "source_kind": "MANUAL",
        "operator_name": "",
        "ship_lat": "",
        "ship_lon": "",
        "route_csv_path": "",
        "output_root": DEFAULT_OUTPUT_ROOT,
        "geom_type": "",
        "verts_text": "",
        "plot_policy_id": "",
        "plot_enabled": "",
        "text_enabled": "",
        "label_text": "",
        "point_symbol_kind": "",
        "color_no": "",
        "line_type": "",
        "line_width": "",
        "operator_note": "",
    }


def _get_form_data(src) -> dict:
    form = _default_form_data()
    for key in form:
        form[key] = (src.get(key, form[key]) or "").strip()
    return form


def _to_float_or_none(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return float(value)


def _to_int_or_none(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return int(value)


def _parse_checkbox_flag(value: str):
    value = (value or "").strip().lower()
    if not value:
        return None
    return value in ("1", "true", "yes", "on")


def _parse_verts_text(verts_text: str) -> list[dict]:
    verts: list[dict] = []
    for idx, raw_line in enumerate((verts_text or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            raise ValueError(f"Bad vertex row {idx}: expected lat,lon")
        try:
            lat = float(parts[0])
            lon = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"Bad vertex row {idx}: invalid number") from exc
        verts.append({"lat": lat, "lon": lon})
    return verts


def _verts_to_text(verts: list[dict]) -> str:
    rows: list[str] = []
    for item in verts or []:
        if not isinstance(item, dict):
            continue
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        rows.append(f"{lat},{lon}")
    return "\n".join(rows)


def _build_override_data(form_data: dict) -> dict:
    geometry_enabled = bool(form_data.get("geom_type") or form_data.get("verts_text"))
    plot_enabled = any(
        form_data.get(key)
        for key in ("plot_policy_id", "plot_enabled", "point_symbol_kind", "color_no", "line_type", "line_width")
    )
    text_enabled = any(
        form_data.get(key)
        for key in ("text_enabled", "label_text")
    )

    geometry_override = {
        "enabled": geometry_enabled,
        "geom_type": form_data.get("geom_type") or None,
        "verts": _parse_verts_text(form_data.get("verts_text", "")) if form_data.get("verts_text") else None,
    }
    plot_override = {
        "enabled": plot_enabled,
        "plot_policy_id": form_data.get("plot_policy_id") or None,
        "plot_enabled": _parse_checkbox_flag(form_data.get("plot_enabled", "")),
        "point_symbol_kind": form_data.get("point_symbol_kind") or None,
        "color_no": _to_int_or_none(form_data.get("color_no", "")),
        "line_type": _to_int_or_none(form_data.get("line_type", "")),
        "line_width": _to_int_or_none(form_data.get("line_width", "")),
    }
    text_override = {
        "enabled": text_enabled,
        "text_enabled": _parse_checkbox_flag(form_data.get("text_enabled", "")),
        "label_text": form_data.get("label_text") or None,
    }
    notes = {
        "operator_note": form_data.get("operator_note") or None,
    }

    return {
        "warning_id": form_data.get("warning_id", ""),
        "navarea": form_data.get("navarea", ""),
        "saved_utc": "",
        "operator_name": form_data.get("operator_name") or None,
        "geometry_override": geometry_override,
        "plot_override": plot_override,
        "text_override": text_override,
        "notes": notes,
    }


def _load_payload_from_form(form_data: dict) -> dict:
    return build_warning_editor_payload(
        raw_text=form_data.get("raw_text", ""),
        navarea=form_data.get("navarea", ""),
        output_root=form_data.get("output_root", DEFAULT_OUTPUT_ROOT),
        warning_id=form_data.get("warning_id", ""),
        title=form_data.get("title", ""),
        source_kind=form_data.get("source_kind", "MANUAL"),
        operator_name=form_data.get("operator_name", ""),
        ship_lat=_to_float_or_none(form_data.get("ship_lat", "")),
        ship_lon=_to_float_or_none(form_data.get("ship_lon", "")),
        route_csv_path=form_data.get("route_csv_path", "") or None,
    )


def _apply_override_fields_to_form(form_data: dict, payload: dict) -> dict:
    result = deepcopy(form_data)
    geometry = payload.get("geometry") if isinstance(payload.get("geometry"), dict) else {}
    plot = payload.get("plot") if isinstance(payload.get("plot"), dict) else {}
    override = payload.get("override") if isinstance(payload.get("override"), dict) else {}
    override_fields = override.get("fields") if isinstance(override.get("fields"), dict) else {}
    notes = override_fields.get("notes") if isinstance(override_fields.get("notes"), dict) else {}

    result["geom_type"] = str(geometry.get("geom_type") or result.get("geom_type", ""))
    result["verts_text"] = _verts_to_text(geometry.get("verts") or [])
    result["plot_policy_id"] = str(plot.get("plot_policy_id") or result.get("plot_policy_id", ""))
    result["plot_enabled"] = "true" if plot.get("plot_enabled") is True else ("false" if plot.get("plot_enabled") is False else result.get("plot_enabled", ""))
    result["text_enabled"] = "true" if plot.get("text_enabled") is True else ("false" if plot.get("text_enabled") is False else result.get("text_enabled", ""))
    result["label_text"] = str(plot.get("label_text") or result.get("label_text", ""))
    result["point_symbol_kind"] = str(plot.get("point_symbol_kind") or result.get("point_symbol_kind", ""))
    result["color_no"] = "" if plot.get("color_no") is None else str(plot.get("color_no"))
    result["line_type"] = "" if plot.get("line_type") is None else str(plot.get("line_type"))
    result["line_width"] = "" if plot.get("line_width") is None else str(plot.get("line_width"))
    result["operator_note"] = str(notes.get("operator_note") or result.get("operator_note", ""))
    return result


def _plot_preview_summary(payload: dict) -> list[dict]:
    plot = payload.get("plot") if isinstance(payload.get("plot"), dict) else {}
    items = []
    for obj in plot.get("plot_objects") or []:
        if not isinstance(obj, dict):
            continue
        items.append(
            {
                "object_kind": obj.get("object_kind"),
                "geom_type": obj.get("geom_type"),
                "vertex_count": len(obj.get("vertices") or []),
                "text": obj.get("text"),
                "point_symbol_kind": obj.get("point_symbol_kind"),
                "color_no": obj.get("color_no"),
                "line_type": obj.get("line_type"),
                "line_width": obj.get("line_width"),
            }
        )
    return items


def _render_editor(*, form_data: dict, payload=None, errors=None, messages=None):
    payload = payload or None
    return render_template(
        "navwarn_editor.html",
        utc_now=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        form=form_data,
        payload=payload,
        errors=errors or [],
        messages=messages or [],
        plot_preview=_plot_preview_summary(payload) if payload else [],
    )


@warning_editor_bp.get("/navwarn/editor")
def navwarn_editor():
    form_data = _get_form_data(request.args)
    payload = None
    errors: list[str] = []

    if request.args.get("autoload", "").strip() == "1" and form_data.get("raw_text"):
        try:
            payload = _load_payload_from_form(form_data)
            if payload.get("override", {}).get("has_override"):
                payload = apply_warning_override_to_payload(payload, payload["override"]["fields"])
            form_data = _apply_override_fields_to_form(form_data, payload)
        except Exception as exc:
            errors.append(str(exc))

    return _render_editor(form_data=form_data, payload=payload, errors=errors)


@warning_editor_bp.post("/navwarn/editor/load")
def navwarn_editor_load():
    form_data = _get_form_data(request.form)
    errors: list[str] = []
    payload = None

    try:
        payload = _load_payload_from_form(form_data)
        if payload.get("override", {}).get("has_override"):
            payload = apply_warning_override_to_payload(payload, payload["override"]["fields"])
        form_data = _apply_override_fields_to_form(form_data, payload)
    except Exception as exc:
        errors.append(str(exc))

    return _render_editor(form_data=form_data, payload=payload, errors=errors)


@warning_editor_bp.post("/navwarn/editor/save_override")
def navwarn_editor_save_override():
    form_data = _get_form_data(request.form)
    errors: list[str] = []
    messages: list[str] = []
    payload = None

    try:
        override_data = _build_override_data(form_data)
        override_path = save_warning_override(
            output_root=form_data.get("output_root", DEFAULT_OUTPUT_ROOT),
            navarea=form_data.get("navarea", ""),
            warning_id=form_data.get("warning_id", ""),
            override_data=override_data,
        )
        messages.append(f"Override saved: {override_path}")
        payload = _load_payload_from_form(form_data)
        payload = apply_warning_override_to_payload(payload, override_data)
        form_data = _apply_override_fields_to_form(form_data, payload)
    except ValueError as exc:
        errors.append(str(exc))
    except Exception as exc:
        errors.append(str(exc))

    return _render_editor(form_data=form_data, payload=payload, errors=errors, messages=messages)


@warning_editor_bp.post("/navwarn/editor/rebuild")
def navwarn_editor_rebuild():
    form_data = _get_form_data(request.form)
    errors: list[str] = []
    messages: list[str] = []
    payload = None

    try:
        override_data = _build_override_data(form_data)
        payload = _load_payload_from_form(form_data)
        payload = apply_warning_override_to_payload(payload, override_data)
        payload["plot"]["plot_objects"] = rebuild_plot_objects_from_editor_payload(payload)
        messages.append("Preview rebuilt without saving.")
        form_data = _apply_override_fields_to_form(form_data, payload)
    except ValueError as exc:
        errors.append(str(exc))
    except Exception as exc:
        errors.append(str(exc))

    return _render_editor(form_data=form_data, payload=payload, errors=errors, messages=messages)
