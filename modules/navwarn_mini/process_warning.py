from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import re


from .vertex_text_builder import build_vertex_texts_for_platform
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
from .build_line_aggregate import build_line_aggregate
from .route_distance import (
    load_jrc_route_csv,
    min_distance_vertices_to_route_waypoints,
)
from .interpreter import interpret_warning
from .active_warning_table import (
    ActiveWarningRecord,
    upsert_warning_record,
    mark_cancelled_targets,
)
from .warning_state_service import (
    StateContext,
    handle_duplicate,
    handle_reference,
    handle_cancellation,
)
from .warning_output_service import persist_operational_warning_output
from .warning_geometry_service import resolve_warning_geometry
from .warning_vault_service import match_warning_profile


class WarningState:
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    DUPLICATE = "DUPLICATE"
    REFERENCE = "REFERENCE"

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
    sessions_dir = root / "NAVWARN" / "active_sessions"

    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    daily_ns01_csv = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.csv"
    daily_ns01_txt = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.txt"
    plot_csv = plots_dir / f"jrc_userchart_{run_id}.csv"

    active_table_csv = root / "NAVWARN" / "active_warning_table.csv"
    active_session_csv = sessions_dir / "jrc_active_session.csv"


    
    # ----------------------------------------------
    # Structural interpretation
    # ----------------------------------------------

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

    profile_match = match_warning_profile(
        raw_text=raw_text,
        interp_warning_type=interp.warning_type,
    )


    # ----------------------------------------------
    # Duplicate detection
    # ----------------------------------------------

    existing_ids = _load_existing_warning_ids(daily_ns01_csv)

    normalized_warning_id = " ".join(warning_id.upper().split())
    is_duplicate = normalized_warning_id in existing_ids

    dup_decision = handle_duplicate(
        is_duplicate=is_duplicate,
        warning_id=warning_id,
    )
    if dup_decision.handled:
        return dup_decision.response

    state_ctx = StateContext(
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        active_table_csv=active_table_csv,
        active_session_csv=active_session_csv,
    )

    
    
    # ----------------------------------------------
    # Semantic branching
    # ----------------------------------------------

    if interp.is_reference_message:
        ref_decision = handle_reference(
            ctx=state_ctx,
            cancellation_targets=interp.cancellation_targets,
        )
        return ref_decision.response


    if interp.is_cancellation:
        cancel_decision = handle_cancellation(
            ctx=state_ctx,
            cancellation_targets=interp.cancellation_targets,
        )
        return cancel_decision.response


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
        return {
            "ok": False,
            "run_id": run_id,
            "warning_id": warning_id,
            "geom_type": "POINT",
            "vertex_count": 0,
            "ship_distance_nm": None,
            "route_distance_nm": None,
            "distance_nm": None,
            "band": None,
            "plot_csv_path": None,
            "daily_ns01_csv_path": str(daily_ns01_csv),
            "daily_ns01_txt_path": str(daily_ns01_txt),
            "errors": ["Offshore warning detected but no usable point coordinate found."],
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
            "errors": ["No coordinates extracted from raw_text."],
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

    def build_key_phrase_summary(raw_text: str) -> str:
        text = " ".join(raw_text.upper().split())

        priority_phrases = [
            "UNLIT",
            "UNRELIABLE",
            "DRILLING OPERATIONS",
            "DRILLING",
            "MODU",
            "PLATFORM",
            "OFF STATION",
            "MISSING",
            "ESTABLISHED",
            "CANCEL",
            "EXERCISE",
            "FIRING",
            "SURVEY OPERATIONS",
            "PIPELAYING",
            "SUBSEA OPERATIONS",
        ]

        found = [p for p in priority_phrases if p in text]
        found = found[:3]

        return " / ".join(found)


    if offshore_objects and offshore_objects[0].geometry.vertices:

        first_obj = offshore_objects[0]

        note_text = None
        if first_obj.match_status == "POSITION_UPDATED":
            note_text = "MOVED"

        text_override = build_vertex_texts_for_platform(
            vertex=first_obj.geometry.vertices[0],
            warning_id=warning_id,
            platform_name=first_obj.platform_name,
            note_text=note_text,
        )

    else:
        # general warning label
        text_override = [{
            "lines": label_lines
        }]

    if offshore_objects and offshore_objects[0].geometry.vertices:
        first_obj = offshore_objects[0]
        note_text = None
        if first_obj.match_status == "POSITION_UPDATED":
            note_text = "MOVED"

        text_override = build_vertex_texts_for_platform(
            vertex=first_obj.geometry.vertices[0],
            warning_id=warning_id,
            platform_name=first_obj.platform_name,
            note_text=note_text,
        )
    
    key_phrase_summary = build_key_phrase_summary(raw_text)

    label_lines = [warning_id]
    if key_phrase_summary:
        label_lines.append(key_phrase_summary)

    plot_objects = []

    if offshore_objects:
        for obj in offshore_objects:
            if not obj.geometry.vertices:
                continue

            # build a single-point classified clone for this offshore object
            single_vertices = [LatLon(
                lat=obj.geometry.vertices[0].lat,
                lon=obj.geometry.vertices[0].lon,
            )]

            single_classified = classified.__class__(
                run_id=classified.run_id,
                processed_utc=classified.processed_utc,
                navarea=classified.navarea,
                source_kind=classified.source_kind,
                source_ref=classified.source_ref,
                warning_id=classified.warning_id,
                title=classified.title,
                body=classified.body,
                validity=classified.validity,
                geometry=Geometry(
                    geom_type="POINT",
                    vertices=single_vertices,
                    closed=False,
                ),
                ship_position=classified.ship_position,
                distance_nm=classified.distance_nm,
                band=classified.band,
                status=classified.status,
                errors=classified.errors,
            )

            note_text = "MOVED" if obj.match_status == "POSITION_UPDATED" else None

            obj_text_override = build_vertex_texts_for_platform(
                vertex=obj.geometry.vertices[0],
                warning_id=warning_id,
                platform_name=obj.platform_name,
                note_text=note_text,
            )

            plot_objects.append(
                build_line_aggregate(
                    single_classified,
                    text_objects_override=obj_text_override,
                )
            )
    else:
        general_text_override = [{
            "lines": label_lines
        }]

        plot_objects.append(
            build_line_aggregate(
                classified,
                text_objects_override=general_text_override,
            )
        )

    output_result = persist_operational_warning_output(
        classified=classified,
        plot_objects=plot_objects,
        plot_csv=plot_csv,
        daily_ns01_csv=daily_ns01_csv,
        daily_ns01_txt=daily_ns01_txt,
        active_table_csv=active_table_csv,
        active_session_csv=active_session_csv,
        warning_id=warning_id,
        navarea=navarea,
        created_utc=created_utc,
        run_id=run_id,
        operator_name=operator_name,
        vessel_name=vessel_name,
        plotted=plotted,
    )


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
        "daily_ns01_txt_path": output_result.daily_ns01_txt_path,
        "active_session_csv_path": output_result.active_session_csv_path,
        "active_session_ok": output_result.active_session_ok,
        "profile_id": profile_match.profile.internal_id if profile_match.profile else None,
        "profile_score": profile_match.score,
        "profile_reasons": profile_match.reasons,
    }