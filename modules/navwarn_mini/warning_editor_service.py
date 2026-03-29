from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from .distance import classify_warning
from .interpreter import interpret_warning
from .models import Geometry, LatLon, OffshoreObject, ShipPosition, SourceRef, Validity, WarningDraft
from .route_distance import load_jrc_route_csv, min_distance_vertices_to_route_waypoints
from .warning_auditor_service import audit_warning_result
from .warning_editor_models import WarningEditorPayload
from .warning_geometry_hint_service import build_geometry_hints
from .warning_geometry_service import resolve_warning_geometry
from .warning_override_store import build_override_path, load_warning_override
from .warning_pattern_service import match_warning_pattern
from .warning_plot_builder_service import PlotObject, build_plot_objects
from .warning_plot_decision_models import EffectivePlotDecision
from .warning_plot_policy_registry import get_plot_policy
from .warning_plot_policy_service import build_effective_plot_decision, resolve_plot_policy_for_profile
from .warning_text_payload_service import build_plot_text_payload
from .warning_vault_service import match_warning_profile


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _serialize_latlon(vertices: list[tuple[float, float]]) -> list[dict[str, float]]:
    return [{"lat": lat, "lon": lon} for lat, lon in vertices]


def _deserialize_latlon(items: list[dict[str, Any]]) -> list[tuple[float, float]]:
    verts: list[tuple[float, float]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        try:
            verts.append((float(item["lat"]), float(item["lon"])))
        except Exception:
            continue
    return verts


def _build_src_ref(source_title: str, source_url: str, created_utc: str) -> SourceRef | None:
    if source_title or source_url:
        return SourceRef(
            title=source_title,
            url=source_url,
            retrieved_utc=created_utc,
        )
    return None


def _serialize_format_fingerprint(fingerprint) -> dict[str, Any] | None:
    if fingerprint is None:
        return None
    return {
        "has_header": getattr(fingerprint, "has_header", False),
        "has_time_block": getattr(fingerprint, "has_time_block", False),
        "has_reference_block": getattr(fingerprint, "has_reference_block", False),
        "has_cancellation_block": getattr(fingerprint, "has_cancellation_block", False),
        "has_geometry_block": getattr(fingerprint, "has_geometry_block", False),
        "has_description_block": getattr(fingerprint, "has_description_block", False),
        "has_admin_block": getattr(fingerprint, "has_admin_block", False),
        "coord_count": getattr(fingerprint, "coord_count", 0),
        "geometry_phrase": getattr(fingerprint, "geometry_phrase", ""),
        "has_list_labels": getattr(fingerprint, "has_list_labels", False),
        "looks_like_offshore_list": getattr(fingerprint, "looks_like_offshore_list", False),
        "looks_like_single_point_notice": getattr(fingerprint, "looks_like_single_point_notice", False),
        "has_cancel_this_msg_clause": getattr(fingerprint, "has_cancel_this_msg_clause", False),
        "has_explicit_cancel_targets": getattr(fingerprint, "has_explicit_cancel_targets", False),
    }


def _serialize_offshore_object(obj: OffshoreObject) -> dict[str, Any]:
    vertices = []
    if getattr(obj, "geometry", None) is not None:
        vertices = [
            {"lat": v.lat, "lon": v.lon}
            for v in getattr(obj.geometry, "vertices", []) or []
        ]
    return {
        "platform_id": obj.platform_id,
        "platform_name": obj.platform_name,
        "platform_type": obj.platform_type,
        "match_status": obj.match_status,
        "identity_confidence": obj.identity_confidence,
        "tce_thread_id": obj.tce_thread_id,
        "source_warning_id": obj.source_warning_id,
        "source_navarea": obj.source_navarea,
        "geometry": {
            "geom_type": getattr(obj.geometry, "geom_type", None),
            "verts": vertices,
        },
    }


def _deserialize_offshore_object(data: dict[str, Any], warning_id: str, navarea: str) -> OffshoreObject | None:
    if not isinstance(data, dict):
        return None

    geometry_data = data.get("geometry") if isinstance(data.get("geometry"), dict) else {}
    verts = [
        LatLon(lat=lat, lon=lon)
        for lat, lon in _deserialize_latlon(geometry_data.get("verts") or [])
    ]

    return OffshoreObject(
        platform_id=data.get("platform_id"),
        platform_name=data.get("platform_name"),
        platform_type=data.get("platform_type"),
        match_status=str(data.get("match_status", "")),
        identity_confidence=float(data.get("identity_confidence", 0.0) or 0.0),
        tce_thread_id=data.get("tce_thread_id"),
        geometry=Geometry(
            geom_type=str(geometry_data.get("geom_type") or "POINT"),
            vertices=verts,
            closed=False,
        ),
        source_warning_id=str(data.get("source_warning_id") or warning_id),
        source_navarea=str(data.get("source_navarea") or navarea),
    )


def _serialize_plot_object(obj: PlotObject) -> dict[str, Any]:
    return {
        "object_kind": obj.object_kind,
        "geom_type": obj.geom_type,
        "vertices": _serialize_latlon(list(obj.vertices)),
        "styled_vertices": [
            {
                "lat": lat,
                "lon": lon,
                "line_type": line_type,
                "width": width,
                "color_no": color_no,
            }
            for lat, lon, line_type, width, color_no in obj.styled_vertices
        ],
        "text": obj.text,
        "point_symbol_kind": obj.point_symbol_kind,
        "color_no": obj.color_no,
        "line_type": obj.line_type,
        "line_width": obj.line_width,
        "hatch_enabled": obj.hatch_enabled,
        "hatch_spacing_nm": obj.hatch_spacing_nm,
        "source_warning_id": obj.source_warning_id,
        "source_navarea": obj.source_navarea,
        "metadata": deepcopy(obj.metadata),
    }


def _serialize_decision(decision: EffectivePlotDecision | None) -> dict[str, Any]:
    if decision is None:
        return {}
    return {
        "policy_id": decision.policy_id,
        "enable_plot": decision.enable_plot,
        "enable_text": decision.enable_text,
        "render_family": decision.render_family,
        "object_mode": decision.object_mode,
        "effective_color_no": decision.effective_color_no,
        "hatch_enabled": decision.hatch_enabled,
        "hatch_spacing_nm": decision.hatch_spacing_nm,
        "label_mode": decision.label_mode,
        "label_offset_mode": decision.label_offset_mode,
        "point_symbol_kind": decision.point_symbol_kind,
        "main_line_type": decision.main_line_type,
        "main_width": decision.main_width,
        "suppress_body_text_for_points": decision.suppress_body_text_for_points,
        "collapse_to_boundary_only": decision.collapse_to_boundary_only,
        "split_multi_object_output": decision.split_multi_object_output,
        "reasons": list(decision.reasons),
    }


def _resolve_geometry(
    *,
    raw_text: str,
    warning_id: str,
    navarea: str,
    created_utc: str,
    interp,
    output_root: str,
    plot_policy_match,
) -> tuple[list[tuple[float, float]], str | None, list[OffshoreObject]]:
    if interp.geometry and interp.geometry.vertices:
        verts = [(v.lat, v.lon) for v in interp.geometry.vertices]
        geom_type = interp.geometry.geom_type
        offshore_objects: list[OffshoreObject] = []
    else:
        geom_result = resolve_warning_geometry(
            raw_text=raw_text,
            warning_id=warning_id,
            navarea=navarea,
            created_utc=created_utc,
            interp_warning_type=interp.warning_type,
            interp_geometry_blocks=interp.structure.geometry_blocks,
            output_root=output_root,
        )
        verts = geom_result.verts
        geom_type = geom_result.geom_type
        offshore_objects = geom_result.offshore_objects

    if offshore_objects and not verts:
        verts = [
            (o.geometry.vertices[0].lat, o.geometry.vertices[0].lon)
            for o in offshore_objects
            if getattr(o, "geometry", None) is not None
            and getattr(o.geometry, "vertices", None)
            and len(o.geometry.vertices) > 0
        ]
        if verts:
            geom_type = "POINT"

    if not plot_policy_match.matched:
        fallback_policy_id = None
        if offshore_objects:
            fallback_policy_id = "plot_offshore_points"
        elif geom_type == "AREA":
            fallback_policy_id = "plot_operational_area"
        elif geom_type == "LINE":
            fallback_policy_id = "plot_operational_line"
        elif geom_type == "POINT":
            fallback_policy_id = "plot_operational_point"

        if fallback_policy_id:
            fallback_policy = get_plot_policy(output_root=output_root, policy_id=fallback_policy_id)
            if fallback_policy is not None:
                plot_policy_match.matched = True
                plot_policy_match.policy_id = fallback_policy_id
                plot_policy_match.policy = fallback_policy
                plot_policy_match.reasons.append(f"Applied fallback policy: {fallback_policy_id}")

    return verts, geom_type, offshore_objects


def _decision_from_payload(payload: dict[str, Any]) -> EffectivePlotDecision:
    plot = payload.get("plot") if isinstance(payload.get("plot"), dict) else {}
    decision_data = plot.get("decision") if isinstance(plot.get("decision"), dict) else {}
    geom = payload.get("geometry") if isinstance(payload.get("geometry"), dict) else {}
    classification = payload.get("classification") if isinstance(payload.get("classification"), dict) else {}
    context = payload.get("_editor_context") if isinstance(payload.get("_editor_context"), dict) else {}

    policy_id = str(plot.get("plot_policy_id") or decision_data.get("policy_id") or "")
    output_root = str(context.get("output_root") or "")
    geom_type = str(geom.get("geom_type") or "POINT")
    band = classification.get("effective_band")
    offshore_count = len(geom.get("offshore_objects") or [])

    decision: EffectivePlotDecision | None = None
    if policy_id and output_root:
        policy = get_plot_policy(output_root=output_root, policy_id=policy_id)
        if policy is not None:
            decision = build_effective_plot_decision(
                policy=policy,
                geom_type=geom_type,
                band=band,
                offshore_object_count=offshore_count,
            )

    if decision is None:
        decision = EffectivePlotDecision(
            policy_id=str(decision_data.get("policy_id") or policy_id or "editor_payload"),
            enable_plot=bool(plot.get("plot_enabled", decision_data.get("enable_plot", True))),
            enable_text=bool(plot.get("text_enabled", decision_data.get("enable_text", True))),
            render_family=str(decision_data.get("render_family", "GENERIC")),
            object_mode=str(decision_data.get("object_mode", "AUTO")),
            effective_color_no=decision_data.get("effective_color_no"),
            hatch_enabled=bool(decision_data.get("hatch_enabled", False)),
            hatch_spacing_nm=decision_data.get("hatch_spacing_nm"),
            label_mode=str(decision_data.get("label_mode", "GENERAL")),
            label_offset_mode=str(decision_data.get("label_offset_mode", "AUTO")),
            point_symbol_kind=str(decision_data.get("point_symbol_kind", "X")),
            main_line_type=decision_data.get("main_line_type"),
            main_width=decision_data.get("main_width"),
            suppress_body_text_for_points=bool(decision_data.get("suppress_body_text_for_points", False)),
            collapse_to_boundary_only=bool(decision_data.get("collapse_to_boundary_only", False)),
            split_multi_object_output=bool(decision_data.get("split_multi_object_output", False)),
            reasons=list(decision_data.get("reasons") or []),
        )

    return replace(
        decision,
        enable_plot=bool(plot.get("plot_enabled", decision.enable_plot)),
        enable_text=bool(plot.get("text_enabled", decision.enable_text)),
        point_symbol_kind=str(plot.get("point_symbol_kind") or decision.point_symbol_kind),
        effective_color_no=plot.get("color_no", decision.effective_color_no),
        main_line_type=plot.get("line_type", decision.main_line_type),
        main_width=plot.get("line_width", decision.main_width),
    )


def build_warning_editor_payload(
    *,
    raw_text: str,
    navarea: str,
    output_root: str,
    warning_id: str = "",
    title: str = "",
    source_kind: str = "MANUAL",
    source_title: str = "",
    source_url: str = "",
    operator_name: str = "",
    ship_lat: float | None = None,
    ship_lon: float | None = None,
    validity_start_utc: str | None = None,
    validity_end_utc: str | None = None,
    validity_ufn: bool = True,
    route_csv_path: str | None = None,
) -> dict:
    run_id = _utc_run_id()
    created_utc = _utc_now_iso()
    src_ref = _build_src_ref(source_title, source_url, created_utc)

    draft_struct, interp = interpret_warning(
        warning_id=warning_id,
        navarea=navarea,
        source_kind=source_kind,
        title=title,
        body=raw_text,
        run_id=run_id,
        created_utc=created_utc,
        source_ref=src_ref,
        operator_name=operator_name,
        operator_watch="",
        operator_notes="",
    )

    profile_match = match_warning_profile(
        raw_text=raw_text,
        interp_warning_type=interp.warning_type,
    )
    plot_policy_match = resolve_plot_policy_for_profile(
        output_root=output_root,
        profile=profile_match.profile,
    )
    pattern_match = match_warning_pattern(
        raw_text=raw_text,
        profile_id=profile_match.profile.internal_id if profile_match.profile else None,
    )

    verts, geom_type, offshore_objects = _resolve_geometry(
        raw_text=raw_text,
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        interp=interp,
        output_root=output_root,
        plot_policy_match=plot_policy_match,
    )

    geometry_hint_result = build_geometry_hints(
        profile_match=profile_match,
        pattern_match=pattern_match,
        actual_geom_type=geom_type,
    )
    audit_result = audit_warning_result(
        profile_match=profile_match,
        pattern_match=pattern_match,
        geometry_hint_result=geometry_hint_result,
        actual_geom_type=geom_type,
        vertex_count=len(verts),
        is_reference_message=interp.is_reference_message,
        is_cancellation=interp.is_cancellation,
        offshore_object_count=len(offshore_objects),
    )

    if not warning_id.strip():
        warning_id = f"NAVAREA {navarea} {run_id}"
    if not title.strip():
        title = warning_id

    ship_position = None
    if ship_lat is not None and ship_lon is not None:
        ship_position = ShipPosition(lat=ship_lat, lon=ship_lon, time_utc=created_utc)

    classification = {
        "ship_distance_nm": None,
        "route_distance_nm": None,
        "effective_distance_nm": None,
        "effective_band": None,
        "status": None,
        "errors": [],
    }
    classified = None

    if verts:
        draft = WarningDraft(
            run_id=run_id,
            created_utc=created_utc,
            navarea=navarea,
            source_kind=source_kind,
            source_ref=src_ref,
            warning_id=warning_id,
            title=title,
            body=raw_text.strip(),
            validity=Validity(
                start_utc=validity_start_utc,
                end_utc=validity_end_utc,
                ufn=validity_ufn,
            ),
            geometry=Geometry(
                geom_type=str(geom_type or "POINT"),
                vertices=[LatLon(lat=lat, lon=lon) for lat, lon in verts],
                closed=False,
            ),
            operator_name=operator_name,
            operator_watch="",
            operator_notes="",
        )

        classified = classify_warning(
            draft=draft,
            processed_utc=created_utc,
            ship_position=ship_position,
        )

        ship_distance_nm = classified.distance_nm
        route_distance_nm = None
        if route_csv_path and classified.status == "OK":
            try:
                route_waypoints = load_jrc_route_csv(route_csv_path)
                route_distance_nm = min_distance_vertices_to_route_waypoints(
                    [(v.lat, v.lon) for v in classified.geometry.vertices],
                    route_waypoints,
                )
            except Exception:
                route_distance_nm = None

        available = [d for d in (ship_distance_nm, route_distance_nm) if d is not None]
        effective_distance_nm = min(available) if available else None
        effective_band = "RED" if effective_distance_nm is None or effective_distance_nm <= 50.0 else "AMBER"

        classified = replace(
            classified,
            distance_nm=effective_distance_nm,
            band=effective_band,
        )
        classification = {
            "ship_distance_nm": ship_distance_nm,
            "route_distance_nm": route_distance_nm,
            "effective_distance_nm": effective_distance_nm,
            "effective_band": effective_band,
            "status": classified.status,
            "errors": list(classified.errors),
        }
    else:
        classification = {
            "ship_distance_nm": None,
            "route_distance_nm": None,
            "effective_distance_nm": None,
            "effective_band": None,
            "status": "FAILED",
            "errors": ["No usable coordinates extracted from warning content."],
        }

    decision = None
    plot_objects: list[PlotObject] = []
    label_text = warning_id

    if classified is not None and classified.status == "OK" and plot_policy_match.matched and plot_policy_match.policy is not None:
        decision = build_effective_plot_decision(
            policy=plot_policy_match.policy,
            geom_type=str(geom_type or "POINT"),
            band=classification["effective_band"],
            offshore_object_count=len(offshore_objects),
        )
        text_payload = build_plot_text_payload(
            warning_id=warning_id,
            raw_text=raw_text,
            interp_warning_type=interp.warning_type,
            key_phrases=interp.key_phrases,
        )
        label_text = " ".join((text_payload.short_text or "").upper().split())
        if decision.enable_plot:
            plot_objects = build_plot_objects(
                warning_id=warning_id,
                navarea=navarea,
                verts=verts,
                geom_type=str(geom_type or "POINT"),
                offshore_objects=offshore_objects,
                decision=decision,
                text_payload=text_payload,
            ).objects

        if not plot_objects and verts:
            fallback_policy_id = None
            if offshore_objects:
                fallback_policy_id = "plot_offshore_points"
            elif geom_type == "AREA":
                fallback_policy_id = "plot_operational_area"
            elif geom_type == "LINE":
                fallback_policy_id = "plot_operational_line"
            elif geom_type == "POINT":
                fallback_policy_id = "plot_operational_point"

            if fallback_policy_id:
                fallback_policy = get_plot_policy(output_root=output_root, policy_id=fallback_policy_id)
                if fallback_policy is not None:
                    decision = build_effective_plot_decision(
                        policy=fallback_policy,
                        geom_type=str(geom_type or "POINT"),
                        band=classification["effective_band"],
                        offshore_object_count=len(offshore_objects),
                    )
                    plot_policy_match.policy_id = fallback_policy_id
                    plot_policy_match.reasons = list(plot_policy_match.reasons) + [f"Applied fallback policy: {fallback_policy_id}"]
                    plot_objects = build_plot_objects(
                        warning_id=warning_id,
                        navarea=navarea,
                        verts=verts,
                        geom_type=str(geom_type or "POINT"),
                        offshore_objects=offshore_objects,
                        decision=decision,
                        text_payload=text_payload,
                    ).objects

    override_data = load_warning_override(output_root, navarea, warning_id)

    payload = WarningEditorPayload(
        warning_id=warning_id,
        navarea=navarea,
        run_id=run_id,
        raw_text=raw_text,
        source_kind=source_kind,
        created_utc=created_utc,
        interp={
            "warning_type": interp.warning_type,
            "is_reference_message": bool(interp.is_reference_message),
            "is_cancellation": bool(interp.is_cancellation),
            "key_phrases": list(interp.key_phrases or []),
            "cancellation_targets": list(interp.cancellation_targets or []),
            "format_fingerprint": _serialize_format_fingerprint(getattr(interp, "format_fingerprint", None)),
        },
        profile={
            "profile_id": profile_match.profile.internal_id if profile_match.profile else None,
            "score": profile_match.score,
            "reasons": list(profile_match.reasons),
        },
        pattern={
            "pattern_id": pattern_match.pattern.pattern_id if pattern_match.pattern else None,
            "score": pattern_match.score,
            "reasons": list(pattern_match.reasons),
        },
        geometry={
            "geom_type": geom_type,
            "verts": _serialize_latlon(verts),
            "offshore_objects": [_serialize_offshore_object(obj) for obj in offshore_objects],
            "geometry_hints": list(geometry_hint_result.geometry_hints),
            "expected_geometry_types": list(geometry_hint_result.expected_geometry_types),
            "geometry_consistency": geometry_hint_result.geometry_consistency,
        },
        classification=classification,
        plot={
            "plot_policy_id": plot_policy_match.policy_id,
            "plot_policy_reasons": list(plot_policy_match.reasons),
            "plot_enabled": bool(getattr(decision, "enable_plot", False)),
            "text_enabled": bool(getattr(decision, "enable_text", False)),
            "plot_objects": [_serialize_plot_object(obj) for obj in plot_objects],
            "label_text": label_text,
            "point_symbol_kind": getattr(decision, "point_symbol_kind", None),
            "color_no": getattr(decision, "effective_color_no", None),
            "line_type": getattr(decision, "main_line_type", None),
            "line_width": getattr(decision, "main_width", None),
            "decision": _serialize_decision(decision),
        },
        audit={
            "audit_status": audit_result.audit_status,
            "audit_flags": list(audit_result.audit_flags),
            "audit_notes": list(audit_result.audit_notes),
        },
        override={
            "has_override": override_data is not None,
            "override_path": str(build_override_path(output_root, navarea, warning_id)),
            "fields": deepcopy(override_data or {}),
        },
        extras={
            "_editor_context": {
                "output_root": output_root,
                "title": title,
                "source_title": source_title,
                "source_url": source_url,
                "operator_name": operator_name,
                "ship_lat": ship_lat,
                "ship_lon": ship_lon,
                "validity_start_utc": validity_start_utc,
                "validity_end_utc": validity_end_utc,
                "validity_ufn": validity_ufn,
                "route_csv_path": route_csv_path,
                "interp_warning_type": interp.warning_type,
                "key_phrases": list(interp.key_phrases or []),
                "draft_warning_id": getattr(draft_struct, "warning_id", ""),
            }
        },
    )
    return payload.to_dict()


def rebuild_plot_objects_from_editor_payload(payload: dict) -> list[dict]:
    payload_copy = deepcopy(payload or {})
    geometry = payload_copy.get("geometry") if isinstance(payload_copy.get("geometry"), dict) else {}
    plot = payload_copy.get("plot") if isinstance(payload_copy.get("plot"), dict) else {}
    interp = payload_copy.get("interp") if isinstance(payload_copy.get("interp"), dict) else {}

    verts = _deserialize_latlon(geometry.get("verts") or [])
    offshore_objects = []
    for item in geometry.get("offshore_objects") or []:
        offshore_obj = _deserialize_offshore_object(item, payload_copy.get("warning_id", ""), payload_copy.get("navarea", ""))
        if offshore_obj is not None:
            offshore_objects.append(offshore_obj)

    if not verts:
        return []

    decision = _decision_from_payload(payload_copy)
    label_text = str(plot.get("label_text") or "").strip()
    text_payload = build_plot_text_payload(
        warning_id=str(payload_copy.get("warning_id", "")),
        raw_text=str(payload_copy.get("raw_text", "")),
        interp_warning_type=str(interp.get("warning_type") or ""),
        key_phrases=list(interp.get("key_phrases") or []),
    )
    if label_text:
        text_payload = replace(text_payload, short_text=label_text)

    plot_objects = build_plot_objects(
        warning_id=str(payload_copy.get("warning_id", "")),
        navarea=str(payload_copy.get("navarea", "")),
        verts=verts,
        geom_type=str(geometry.get("geom_type") or "POINT"),
        offshore_objects=offshore_objects,
        decision=decision,
        text_payload=text_payload,
    ).objects

    edited_objects: list[dict[str, Any]] = []
    for obj in plot_objects:
        if plot.get("point_symbol_kind") and obj.object_kind == "POINT":
            obj.point_symbol_kind = str(plot["point_symbol_kind"])
        if plot.get("color_no") is not None and obj.object_kind != "TEXT":
            obj.color_no = plot.get("color_no")
        if plot.get("line_type") is not None and obj.object_kind != "TEXT":
            obj.line_type = plot.get("line_type")
        if plot.get("line_width") is not None and obj.object_kind != "TEXT":
            obj.line_width = plot.get("line_width")
        edited_objects.append(_serialize_plot_object(obj))
    return edited_objects


def apply_warning_override_to_payload(payload: dict, override_data: dict) -> dict:
    result = deepcopy(payload or {})
    override_copy = deepcopy(override_data or {})

    geometry_override = override_copy.get("geometry_override") if isinstance(override_copy.get("geometry_override"), dict) else {}
    plot_override = override_copy.get("plot_override") if isinstance(override_copy.get("plot_override"), dict) else {}
    text_override = override_copy.get("text_override") if isinstance(override_copy.get("text_override"), dict) else {}
    notes = override_copy.get("notes") if isinstance(override_copy.get("notes"), dict) else {}

    geometry = result.setdefault("geometry", {})
    plot = result.setdefault("plot", {})
    override_section = result.setdefault("override", {})

    if geometry_override.get("enabled"):
        if geometry_override.get("geom_type") is not None:
            geometry["geom_type"] = geometry_override.get("geom_type")
        if geometry_override.get("verts") is not None:
            geometry["verts"] = deepcopy(geometry_override.get("verts"))

    if plot_override.get("enabled"):
        if plot_override.get("plot_policy_id") is not None:
            plot["plot_policy_id"] = plot_override.get("plot_policy_id")
        if plot_override.get("plot_enabled") is not None:
            plot["plot_enabled"] = bool(plot_override.get("plot_enabled"))
        if plot_override.get("point_symbol_kind") is not None:
            plot["point_symbol_kind"] = plot_override.get("point_symbol_kind")
        if plot_override.get("color_no") is not None:
            plot["color_no"] = plot_override.get("color_no")
        if plot_override.get("line_type") is not None:
            plot["line_type"] = plot_override.get("line_type")
        if plot_override.get("line_width") is not None:
            plot["line_width"] = plot_override.get("line_width")

    if text_override.get("enabled"):
        if text_override.get("text_enabled") is not None:
            plot["text_enabled"] = bool(text_override.get("text_enabled"))
        if text_override.get("label_text") is not None:
            plot["label_text"] = str(text_override.get("label_text"))

    if notes.get("operator_note") is not None:
        override_section["operator_note"] = notes.get("operator_note")

    override_section["has_override"] = True
    override_section["fields"] = override_copy
    plot["plot_objects"] = rebuild_plot_objects_from_editor_payload(result)
    return result


def load_and_apply_warning_override(*, payload: dict, output_root: str, navarea: str, warning_id: str) -> dict:
    override_data = load_warning_override(output_root, navarea, warning_id)
    if not override_data:
        return deepcopy(payload)
    return apply_warning_override_to_payload(payload, override_data)
