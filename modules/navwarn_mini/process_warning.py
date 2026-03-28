from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .message_envelope import MessageEnvelope
from .models import (
    WarningDraft,
    Geometry,
    LatLon,
    Validity,
    ShipPosition,
    SourceRef,
)
from .distance import classify_warning

from .route_distance import (
    load_jrc_route_csv,
    min_distance_vertices_to_route_waypoints,
)
from .interpreter import interpret_warning
from .warning_state_service import (
    StateContext,
    handle_duplicate,
    handle_reference,
    handle_cancellation,
)
from .warning_output_service import persist_operational_warning_output
from .warning_geometry_service import resolve_warning_geometry
from .warning_vault_service import match_warning_profile

from .warning_pattern_service import match_warning_pattern
from .warning_geometry_hint_service import build_geometry_hints
from .warning_auditor_service import audit_warning_result

from .warning_plot_builder_service import build_plot_objects
from .warning_text_payload_service import build_plot_text_payload
from .warning_plot_policy_service import (
    resolve_plot_policy_for_profile,
    build_effective_plot_decision,
)

from .voyage_userchart_service import derive_route_id

class WarningState:
    ACTIVE = "ACTIVE"
    CANCELLED_EXPLICIT = "CANCELLED_EXPLICIT"
    OMMITTED_BY_CUMULATIVE = "OMITTED_BY_CUMULATIVE"
    DUPLICATE = "DUPLICATE"
    REFERENCE_CUMULATIVE = "REFERENCE_CUMULATIVE"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _yyyymmdd_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _load_existing_warning_ids(csv_path: Path) -> set[str]:
    ids: set[str] = set()

    if not csv_path.exists():
        return ids

    try:
        import csv

        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                wid = row.get("Warning_ID", "")
                wid = " ".join(wid.upper().split())
                if wid:
                    ids.add(wid)

    except Exception:
        return set()

    return ids


def _safe_name(value: str) -> str:
    value = value.strip().upper()
    value = value.replace("NAVAREA ", "")
    value = value.replace("/", "_")
    value = value.replace(" ", "_")
    return value

def _interpret_stage(
    *,
    raw_text: str,
    warning_id: str,
    navarea: str,
    source_kind: str,
    title: str,
    run_id: str,
    created_utc: str,
    source_title: str,
    source_url: str,
    operator_name: str,
    output_root: str,
):
    src_ref = None
    if source_title or source_url:
        src_ref = SourceRef(
            title=source_title,
            url=source_url,
            retrieved_utc=created_utc,
        )

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

    print("[INTERP DEBUG] warning_id:", warning_id)
    print("[INTERP DEBUG] interp.warning_type:", interp.warning_type)
    print("[INTERP DEBUG] is_reference_message:", interp.is_reference_message)
    print("[INTERP DEBUG] is_cancellation:", interp.is_cancellation)
    print("[INTERP DEBUG] key_phrases:", interp.key_phrases)
    if getattr(interp, "format_fingerprint", None) is not None:
        print("[INTERP DEBUG] fingerprint:", interp.format_fingerprint)

    profile_match = match_warning_profile(
        raw_text=raw_text,
        interp_warning_type=interp.warning_type,
    )

    plot_policy_match = resolve_plot_policy_for_profile(
        output_root=output_root,
        profile=profile_match.profile,
    )

    print("[DEBUG] plot_policy_match.matched:", plot_policy_match.matched)
    print("[DEBUG] plot_policy_id:", plot_policy_match.policy_id)
    print("[DEBUG] plot_policy_reasons:", plot_policy_match.reasons)

    pattern_match = match_warning_pattern(
        raw_text=raw_text,
        profile_id=profile_match.profile.internal_id if profile_match.profile else None,
    )

    return src_ref, draft_struct, interp, profile_match, plot_policy_match, pattern_match

def _state_stage(
    *,
    daily_ns01_csv: Path,
    warning_id: str,
    navarea: str,
    created_utc: str,
    active_table_csv: Path,
    interp,
    raw_text: str,
):
    existing_ids = _load_existing_warning_ids(daily_ns01_csv)

    normalized_warning_id = " ".join(warning_id.upper().split())
    is_duplicate = normalized_warning_id in existing_ids

    dup_decision = handle_duplicate(
        is_duplicate=is_duplicate,
        warning_id=warning_id,
    )

    print("[DUPLICATE DEBUG]", {
        "warning_id": warning_id,
        "is_duplicate": is_duplicate,
        "daily_ns01_csv": str(daily_ns01_csv),
    })

    if dup_decision.handled and False:
        print("[DUPLICATE DEBUG] early return:", dup_decision.response)
        return True, dup_decision.response, None

    state_ctx = StateContext(
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        active_table_csv=active_table_csv,
    )

    if interp.is_reference_message:
        ref_decision = handle_reference(
            ctx=state_ctx,
            raw_text=raw_text,
        )
        return True, ref_decision.response, state_ctx

    if interp.is_cancellation:
        cancel_decision = handle_cancellation(
            ctx=state_ctx,
            cancellation_targets=interp.cancellation_targets,
        )
        return True, cancel_decision.response, state_ctx

    return False, None, state_ctx

def process_warning_text(
    *,
    raw_text: str,
    navarea: str,
    ship_lat: Optional[float],
    ship_lon: Optional[float],
    output_root: str,
    warning_id: str = "",
    title: str = "",
    source_kind: str = "MANUAL",
    source_title: str = "",
    source_url: str = "",
    operator_name: str = "",
    vessel_name: str = "",
    plotted: str = "NO",
    validity_start_utc: Optional[str] = None,
    validity_end_utc: Optional[str] = None,
    validity_ufn: bool = True,
    route_csv_path: Optional[str] = None,
    chart_mode: str = "UPDATE_EXISTING",
    forced_route_id: str = "",
) -> dict:
    
    """
    End-to-end NavWarn Mini pipeline.

    Effective distance rule:
      effective_distance_nm = min(ship_distance_nm, route_distance_nm)
    using whichever values are available.

    Returns:
    {
        "ok": bool,
        "run_id": str,
        "warning_id": str,
        "geom_type": str,
        "vertex_count": int,
        "ship_distance_nm": float | None,
        "route_distance_nm": float | None,
        "distance_nm": float | None,   # effective distance
        "band": str | None,
        "plot_csv_path": str | None,
        "daily_ns01_csv_path": str,
        "daily_ns01_txt_path": str,
        "errors": list[str],
    }
    """
    run_id = _utc_run_id()
    envelope = MessageEnvelope(
        raw_text=raw_text,
        source=source_kind,
    )

    created_utc = _utc_now_iso()
    yyyymmdd = _yyyymmdd_utc()
    
    root = Path(output_root)

    plots_dir = root / "NAVWARN" / "plots"
    reports_dir = root / "NAVWARN" / "reports"
    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    daily_ns01_csv = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.csv"
    daily_ns01_txt = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.txt"

    active_table_csv = root / "NAVWARN" / "active_warning_table.csv"

    route_id = (forced_route_id or derive_route_id(route_csv_path, run_id)).strip().upper()
    chart_mode = (chart_mode or ("UPDATE_EXISTING" if route_csv_path else "CREATE_NEW")).strip().upper()    

    # ----------------------------------------------
    # Structural interpretation
    # ----------------------------------------------

    src_ref, draft_struct, interp, profile_match, plot_policy_match, pattern_match = _interpret_stage(
        raw_text=raw_text,
        warning_id=warning_id,
        navarea=navarea,
        source_kind=source_kind,
        title=title,
        run_id=run_id,
        created_utc=created_utc,
        source_title=source_title,
        source_url=source_url,
        operator_name=operator_name,
        output_root=output_root,
    )



    # ----------------------------------------------
    # Duplicate detection
    # ----------------------------------------------

    handled, response, state_ctx = _state_stage(
        daily_ns01_csv=daily_ns01_csv,
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        active_table_csv=active_table_csv,
        interp=interp,
        raw_text=raw_text,
    )
    if handled:
        return response


    # --- PRIMARY: use interpreter geometry ---
    # --- PRIMARY: use interpreter geometry ---
    geom_result = None

    if interp.geometry and interp.geometry.vertices:
        verts = [
            (v.lat, v.lon)
            for v in interp.geometry.vertices
        ]
        geom_type = interp.geometry.geom_type
        offshore_objects = []

        print("[PRIMARY] using interpreter geometry", {
            "verts_len": len(verts),
            "geom_type": geom_type,
            "offshore_object_count": len(offshore_objects),
        })

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

        print("[FALLBACK] using extractor geometry", {
            "verts_len": len(verts),
            "geom_type": geom_type,
            "offshore_object_count": len(offshore_objects),
        })    
    if offshore_objects and not verts:
        print("[INFO] Offshore-only warning -deriving verts from offshore_objects")

        verts = [
            (
                o.geometry.vertices[0].lat,
                o.geometry.vertices[0].lon,
            )
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
            from .warning_plot_policy_registry import get_plot_policy

            fallback_policy = get_plot_policy(
                output_root=output_root,
                policy_id=fallback_policy_id,
            )

            if fallback_policy is not None:
                plot_policy_match.matched = True
                plot_policy_match.policy_id = fallback_policy_id
                plot_policy_match.policy = fallback_policy
                plot_policy_match.reasons.append(
                    f"Applied fallback policy: {fallback_policy_id}"
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


    if not verts:
        print("[WARN] resolve_warning_geometry produced no verts - trying interpreter fallback")

        if interp.geometry and interp.geometry.vertices:
            verts = [
                (v.lat, v.lon)
                for v in interp.geometry.vertices
            ]
            geom_type = interp.geometry.geom_type
            print("[RECOVERY] interpreter fallback used", {
                "verts_len": len(verts),
                "geom_type": geom_type,
            })

        if offshore_objects and not verts:
            verts = [
                (
                    o.geometry.vertices[0].lat,
                    o.geometry.vertices[0].lon,
                )
                for o in offshore_objects
                if getattr(o, "geometry", None) is not None
                and getattr(o.geometry, "vertices", None)
                and len(o.geometry.vertices) > 0
            ]

            if verts:
                geom_type = "POINT"
                print("[RECOVERY] offshore_objects fallback used", {
                    "verts_len": len(verts),
                    "geom_type": geom_type,
                })

        if not verts:
            return {
                "ok": False,
                "run_id": run_id,
                "warning_id": warning_id,
                "geom_type": geom_type,
                "vertex_count": 0,
                "ship_distance_nm": None,
                "route_distance_nm": None,
                "distance_nm": None,
                "band": None,
                "plot_csv_path": None,
                "daily_ns01_csv_path": str(daily_ns01_csv),
                "daily_ns01_txt_path": str(daily_ns01_txt),
                "errors": ["No usable coordinates extracted from warning content."],
                "offshore_object_count": len(offshore_objects),
                "offshore_objects": [
                    {
                        "platform_id": o.platform_id,
                        "platform_name": o.platform_name,
                        "platform_type": o.platform_type,
                        "match_status": o.match_status,
                        "identity_confidence": o.identity_confidence,
                        "tce_thread_id": o.tce_thread_id,
                        "lat": o.geometry.vertices[0].lat if o.geometry.vertices else None,
                        "lon": o.geometry.vertices[0].lon if o.geometry.vertices else None,
                    }
                    for o in offshore_objects
                ],
            }


    vertices = [LatLon(lat=a, lon=b) for (a, b) in verts]

    # 2) Build draft
    src_ref = None
    if source_title or source_url:
        src_ref = SourceRef(
            title=source_title,
            url=source_url,
            retrieved_utc=created_utc,
        )

    if not warning_id.strip():
        warning_id = f"NAVAREA {navarea} {run_id}"
    if not title.strip():
        title = warning_id

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
            geom_type=geom_type,
            vertices=vertices,
            closed=False,
        ),
        operator_name=operator_name,
        operator_watch="",
        operator_notes="",
    )

    # 3) Ship position
    ship_position = None
    if ship_lat is not None and ship_lon is not None:
        ship_position = ShipPosition(
            lat=ship_lat,
            lon=ship_lon,
            time_utc=created_utc,
        )

    # 4) Classify using ship position first
    classified = classify_warning(
        draft=draft,
        processed_utc=created_utc,
        ship_position=ship_position,
    )

    print("[DEBUG CLASSIFIED]", {
        "status:": classified.status,
        "geom_type:": classified.geometry.geom_type,
        "vertex_count": len(classified.geometry.vertices),
        "distance_nm": classified.distance_nm,
        "band:": classified.band,
    })

    if classified.status != "OK":
        return {
            "ok": False,
            "run_id": run_id,
            "warning_id": warning_id,
            "geom_type": geom_type,
            "vertex_count": len(vertices),
            "ship_distance_nm": classified.distance_nm,
            "route_distance_nm": None,
            "distance_nm": classified.distance_nm,
            "band": classified.band,
            "plot_csv_path": None,
            "daily_ns01_csv_path": str(daily_ns01_csv),
            "daily_ns01_txt_path": str(daily_ns01_txt),
            "errors": classified.errors,
        }

    ship_distance_nm = classified.distance_nm
    route_distance_nm = None

    # 5) Optional route distance
    if route_csv_path:
        try:
            route_waypoints = load_jrc_route_csv(route_csv_path)
            route_distance_nm = min_distance_vertices_to_route_waypoints(
                [(v.lat, v.lon) for v in classified.geometry.vertices],
                route_waypoints,
            )
        except Exception as e:
            # non-fatal
            route_distance_nm = None

    # 6) Effective distance = nearest of available distances
    available = [d for d in (ship_distance_nm, route_distance_nm) if d is not None]
    effective_distance_nm = min(available) if available else None

    # 7) Effective band from effective distance
    if effective_distance_nm is None:
        effective_band = "RED"
    else:
        effective_band = "RED" if effective_distance_nm <= 50.0 else "AMBER"

    # overwrite effective values for downstream use
    classified = classified.__class__(
        run_id=classified.run_id,
        processed_utc=classified.processed_utc,
        navarea=classified.navarea,
        source_kind=classified.source_kind,
        source_ref=classified.source_ref,
        warning_id=classified.warning_id,
        title=classified.title,
        body=classified.body,
        validity=classified.validity,
        geometry=classified.geometry,
        ship_position=classified.ship_position,
        distance_nm=effective_distance_nm,
        band=effective_band,
        status=classified.status,
        errors=classified.errors,
    )
    
    plot_objects = []

    if plot_policy_match.matched and plot_policy_match.policy is not None:
        decision = build_effective_plot_decision(
            policy=plot_policy_match.policy,
            geom_type=geom_type,
            band=effective_band,
            offshore_object_count=len(offshore_objects),
        )

        print("[DEBUG] decision:", decision)
        print("[DEBUG] decision.enable_plot:", getattr(decision, "enable_plot", None))
        print("[DEBUG] geom_type:", geom_type),
        print("[DEBUG] verts_count:", len(verts))

        if not getattr(decision, "enable_plot", True):
            print("[INFO] Plot disabled by policy")
        else:
            text_payload = build_plot_text_payload(
                warning_id=warning_id,
                raw_text=raw_text,
                interp_warning_type=interp.warning_type,
                key_phrases=interp.key_phrases,
            )

            plot_build = build_plot_objects(
                warning_id=warning_id,
                navarea=navarea,
                verts=verts,
                geom_type=geom_type,
                offshore_objects=offshore_objects,
                decision=decision,
                text_payload=text_payload,
            )
                
            print("[DEBUG] plot_build:", plot_build)
            print("[DEBUG] plot_object_count:", len(plot_build.objects) if hasattr(plot_build, "objects") else "NO_OBJECTS_ATTR")

            plot_objects = plot_build.objects

    if not plot_objects and verts:
        print("[FORCED FALLBACK] No plot objects — forcing default build")

        from .warning_plot_policy_registry import get_plot_policy

        fallback_policy_id = None
        if offshore_objects:
            fallback_policy_id = "plot_offshore_points"
        elif geom_type == "AREA":
            fallback_policy_id = "plot_operational_area"
        elif geom_type == "LINE":
            fallback_policy_id = "plot_operational_line"
        elif geom_type == "POINT":
            fallback_policy_id = "plot_operational_point"

        if fallback_policy_id is not None:
            fallback_policy = get_plot_policy(
                output_root=output_root,
                policy_id=fallback_policy_id,
            )

            if fallback_policy is not None:
                decision = build_effective_plot_decision(
                    policy=fallback_policy,
                    geom_type=geom_type,
                    band=effective_band,
                    offshore_object_count=len(offshore_objects),
                )

                text_payload = build_plot_text_payload(
                    warning_id=warning_id,
                    raw_text=raw_text,
                    interp_warning_type=interp.warning_type,
                    key_phrases=interp.key_phrases,
                )

                plot_build = build_plot_objects(
                    warning_id=warning_id,
                    navarea=navarea,
                    verts=verts,
                    geom_type=geom_type,
                    offshore_objects=offshore_objects,
                    decision=decision,
                    text_payload=text_payload,
                )

                plot_objects = plot_build.objects
                


    print("[FALLBACK] plot object count:", len(plot_objects))
    print("[DEBUG FINAL] plot_objects count before persist:", len(plot_objects))
    print("[DEBUG FINAL] route_id:", route_id)

    output_result = persist_operational_warning_output(
        classified=classified,
        plot_objects=plot_objects,
        output_root=output_root,
        daily_ns01_csv=daily_ns01_csv,
        daily_ns01_txt=daily_ns01_txt,
        active_table_csv=active_table_csv,
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        run_id=run_id,
        operator_name=operator_name,
        vessel_name=vessel_name,
        plotted=plotted,
        route_id=route_id,
        chart_mode=chart_mode,
    )

    print("[DEBUG FINAL] output_result:", output_result)
    print("[DEBUG FINAL] output_result.plot_csv_path:", getattr(output_result,"plot_csv_path", None))

    print("[FINAL RETURN DEBUG]", {
        "warning_id": classified.warning_id,
        "geom_type": classified.geometry.geom_type,
        "vertex_count": len(classified.geometry.vertices),
        "ship_distance_nm": ship_distance_nm,
        "band": effective_band,
        "plot_csv_path": output_result.plot_csv_path,
    })

    return {
        "ok": True,
        "run_id": run_id,
        "warning_id": classified.warning_id,
        "geom_type": classified.geometry.geom_type,
        "vertex_count": len(classified.geometry.vertices),
        "ship_distance_nm": ship_distance_nm,
        "route_distance_nm": route_distance_nm,
        "distance_nm": effective_distance_nm,
        "band": effective_band,
        "plot_csv_path": output_result.plot_csv_path,
        "daily_ns01_csv_path": output_result.daily_ns01_csv_path,
        "ns01_txt": output_result.daily_ns01_txt_path,
        "route_id": output_result.route_id,
        "chart_mode": output_result.chart_mode,
        "plotted_warning_ids": output_result.plotted_warning_ids,
        "archived_section_csv_path": output_result.archived_section_csv_path,


        # UI compatibility keys
        "plot_csv": output_result.plot_csv_path,
        "ns01_csv": output_result.daily_ns01_csv_path,
        "ns01_txt": output_result.daily_ns01_txt_path,
        "route_id": output_result.route_id,
        "chart_mode": output_result.chart_mode,
        "profile_id": profile_match.profile.internal_id if profile_match.profile else None,
        "profile_score": profile_match.score,
        "profile_reasons": profile_match.reasons,
        "plot_policy_id": plot_policy_match.policy_id,
        "pattern_id": pattern_match.pattern.pattern_id if pattern_match.pattern else None,
        "pattern_score": pattern_match.score,
        "pattern_reasons": pattern_match.reasons,
        "expected_geometry_types": geometry_hint_result.expected_geometry_types,
        "geometry_hints": geometry_hint_result.geometry_hints,
        "geometry_consistency": geometry_hint_result.geometry_consistency,
        "audit_status": audit_result.audit_status,
        "audit_flags": audit_result.audit_flags,
        "audit_notes": audit_result.audit_notes,
        "jrc_precheck_ok": output_result.jrc_precheck_ok,
        "jrc_precheck_errors": output_result.jrc_precheck_errors,
        "jrc_precheck_warnings": output_result.jrc_precheck_warnings,
        "jrc_filecheck_ok": output_result.jrc_filecheck_ok,
        "jrc_filecheck_errors": output_result.jrc_filecheck_errors,
        "jrc_filecheck_warnings": output_result.jrc_filecheck_warnings,
        
    }