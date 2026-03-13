from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import re
from .models import OffshoreObject
from .platform_registry import resolve_platform_identity
from .chart_session_builder import update_active_session_for_warning, rebuild_active_session_csv

from .vertex_text_builder import build_vertex_texts_for_platform

from .models import (
    WarningDraft,
    Geometry,
    LatLon,
    Validity,
    ShipPosition,
    SourceRef,
)
from .extract_warning import extract_vertices_and_geom
from .distance import classify_warning
from .build_line_aggregate import build_line_aggregate
from .export_jrc_csv import export_jrc_userchart_csv
from .register_ns01 import (
    next_seq_for_register,
    make_ns01_row,
    append_ns01_row,
)
from .ns01_daily import regenerate_daily_ns01_txt
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

_PLATFORM_SPLIT_RE = re.compile(
    r"\b(MODU|DRILLING RIG|SEMI[- ]?SUBMERSIBLE|JACK[- ]?UP|PLATFORM|FPSO|FSO)\b",
    re.IGNORECASE,
)

_PLATFORM_NAME_RE = re.compile(
    r"\b(MODU|DRILLING RIG|SEMI[- ]?SUBMERSIBLE|JACK[- ]?UP|PLATFORM|FPSO|FSO)\s+([A-Z0-9.\- ]{1,40})",
    re.IGNORECASE,
)


def split_platform_sections(text: str) -> list[str]:
    parts = _PLATFORM_SPLIT_RE.split(text)
    sections: list[str] = []
    current = ""
    for piece in parts:
        if _PLATFORM_SPLIT_RE.fullmatch(piece.strip()):
            if current.strip():
                sections.append(current.strip())
            current = piece.strip()
        else:
            current = f"{current} {piece}".strip()
    if current.strip():
        sections.append(current.strip())
    return [s for s in sections if len(s.split()) >= 3]


def extract_platform_name(section: str) -> Optional[str]:
    m = _PLATFORM_NAME_RE.search(section.upper())
    if not m:
        return None

    name = m.group(2).strip()

    # cut trailing operational noise
    name = re.sub(
        r"\b(OPERATING|DRILLING|AT|IN|LOCATED|ON LOCATION|ESTABLISHED|WORKING)\b.*$",
        "",
        name,
    ).strip()

    # normalize punctuation wrappers like .AAA / BBB.
    name = name.strip(" .;,:-")

    # compact whitespace
    name = " ".join(name.split())

    # accept short symbolic platform labels too
    if re.fullmatch(r"[A-Z]", name):
        return name
    if re.fullmatch(r"[A-Z]{2,4}", name):
        return name
    if re.fullmatch(r"[A-Z]\d+", name):
        return name
    if re.fullmatch(r"[A-Z]-\d+", name):
        return name

    # accept normal names
    if len(name) >= 3:
        return name

    return None

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
    created_utc = _utc_now_iso()
    yyyymmdd = _yyyymmdd_utc()
    
    root = Path(output_root)
    plots_dir = root / "NAVWARN" / "plots"
    reports_dir = root / "NAVWARN" / "reports"

    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    daily_ns01_csv = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.csv"
    daily_ns01_txt = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.txt"
    safe_warning = _safe_name(warning_id) if warning_id.strip() else "UNNAMED"
    plot_csv = plots_dir / f"jrc_{safe_warning}_{run_id}.csv"

    active_table_csv = root / "NAVWARN" / "active_warning_table.csv"
    merged_result = {"ok": False, "mode": "not_run"}

    root = Path(output_root)
    plots_dir = root / "NAVWARN" / "plots"
    reports_dir = root / "NAVWARN" / "reports"

    plots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    daily_ns01_csv = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.csv"
    daily_ns01_txt = reports_dir / f"NS-01_navwarn_register_{yyyymmdd}.txt"
    plot_csv = plots_dir / f"jrc_userchart_{run_id}.csv"
    
    active_table_csv = root / "NAVWARN" / "active_warning_table.csv"
    
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

    # ----------------------------------------------
    # Duplicate detection
    # ----------------------------------------------

    existing_ids = _load_existing_warning_ids(daily_ns01_csv)

    normalized_warning_id = " ".join(warning_id.upper().split())
    is_duplicate = normalized_warning_id in existing_ids

    if is_duplicate:
        return {
            "ok": True,
            "state": WarningState.DUPLICATE,
            "status": "DUPLICATE_WARNING",
            "warning_id": warning_id,
        }

    # ----------------------------------------------
    # Semantic branching
    # ----------------------------------------------

    if interp.is_reference_message:
        
        upsert_warning_record(
            active_table_csv,
            ActiveWarningRecord(
            warning_id=warning_id,
            navarea=navarea,
            state="REFERENCE",
            source_warning_id=warning_id,
            cancel_targets=";".join(interp.cancellation_targets),
            last_updated_utc=created_utc,
            plotted="NO",
            plot_ref="",
            ),
        )
        active_session_csv = root / "NAVWARN" / "active_sessions" / "jrc_active_session.csv"

        merged_result = {"ok": False}

        merged_result = rebuild_active_session_csv(
            active_table_csv_path=str(active_table_csv),
            output_csv_path=str(active_session_csv),
        )
        
        return {
            "ok": True,
            "state": WarningState.REFERENCE,
            "status": "REFERENCE_BULLETIN",
            "warning_id": warning_id,
            "cancel_targets": interp.cancellation_targets,
        }

    if interp.is_cancellation:
        
        upsert_warning_record(
            active_table_csv,
            ActiveWarningRecord(
            warning_id=warning_id,
            navarea=navarea,
            state="CANCELLED",
            source_warning_id=warning_id,
            cancel_targets=";".join(interp.cancellation_targets),
            last_updated_utc=created_utc,
            plotted="NO",
            plot_ref="",
            ),
        )

        mark_cancelled_targets(
            active_table_csv,
            interp.cancellation_targets,
            created_utc,
        )
        
        merged_result = rebuild_active_session_csv(
            active_table_csv_path=str(active_table_csv),
            output_csv_path=str(active_session_csv),
        )
        
        return {
            "ok": True,
            "state": WarningState.CANCELLED,
            "status": "CANCELLATION_WARNING",
            "warning_id": warning_id,
            "cancel_targets": interp.cancellation_targets,
        }
    
    offshore_objects: list[OffshoreObject] = []

    if interp.warning_type in ("MODU", "DRILLING"):
        registry_csv = root / "NAVWARN" / "platform_registry.csv"
        sections = split_platform_sections(raw_text)

        # Multi-platform bulletin
        if len(sections) > 1:
            for sec in sections:
                sec_name = extract_platform_name(sec)
                sec_verts, _sec_geom_type = extract_vertices_and_geom(sec)

                if not sec_verts:
                    continue

                first = sec_verts[0]
                sec_geometry = Geometry(
                    geom_type="POINT",
                    vertices=[LatLon(lat=first[0], lon=first[1])],
                    closed=False,
                )

                ident = resolve_platform_identity(
                    registry_csv_path=str(registry_csv),
                    platform_name=sec_name,
                    platform_type=interp.warning_type,
                    geometry=sec_geometry,
                    warning_id=warning_id,
                    observed_utc=created_utc,
                )

                offshore_objects.append(
                    OffshoreObject(
                        platform_id=ident["platform_id"],
                        platform_name=sec_name,
                        platform_type=interp.warning_type,
                        match_status=ident["match_status"],
                        identity_confidence=ident["identity_confidence"],
                        tce_thread_id=ident["tce_thread_id"],
                        geometry=sec_geometry,
                        source_warning_id=warning_id,
                        source_navarea=navarea,
                    )
                )

            if offshore_objects:
                first_obj = offshore_objects[0]
                verts = [(first_obj.geometry.vertices[0].lat, first_obj.geometry.vertices[0].lon)]
                geom_type = "POINT"
            else:
                verts, geom_type = extract_vertices_and_geom(raw_text)

        else:
            coords = []
            for block in interp.structure.geometry_blocks:
                block_coords = block.extracted.get("coords", [])
                if isinstance(block_coords, list):
                    coords.extend(block_coords)

            if coords:
                first = coords[0]
                base_geometry = Geometry(
                    geom_type="POINT",
                    vertices=[LatLon(lat=first.lat, lon=first.lon)],
                    closed=False,
                )

                ident = resolve_platform_identity(
                    registry_csv_path=str(registry_csv),
                    platform_name=extract_platform_name(raw_text),
                    platform_type=interp.warning_type,
                    geometry=base_geometry,
                    warning_id=warning_id,
                    observed_utc=created_utc,
                )

                offshore_objects.append(
                    OffshoreObject(
                        platform_id=ident["platform_id"],
                        platform_name=extract_platform_name(raw_text),
                        platform_type=interp.warning_type,
                        match_status=ident["match_status"],
                        identity_confidence=ident["identity_confidence"],
                        tce_thread_id=ident["tce_thread_id"],
                        geometry=base_geometry,
                        source_warning_id=warning_id,
                        source_navarea=navarea,
                    )
                )

                verts = [(first.lat, first.lon)]
                geom_type = "POINT"
            else:
                verts, geom_type = extract_vertices_and_geom(raw_text)
    else:
        verts, geom_type = extract_vertices_and_geom(raw_text)

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

    # 8) Build plot object
    text_override = None

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

    obj = build_line_aggregate(
        classified,
        text_objects_override=text_override,
    )
    # 9) Export JRC CSV
    export_jrc_userchart_csv(
        objects=[obj],
        output_csv_path=str(plot_csv),
    )

    # 10) Append NS-01
    seq = next_seq_for_register(str(daily_ns01_csv))
    row = make_ns01_row(seq, classified, plotted=plotted)
    append_ns01_row(str(daily_ns01_csv), row)

    # 11) Regenerate daily printable NS-01
    regenerate_daily_ns01_txt(
        daily_ns01_csv_path=str(daily_ns01_csv),
        out_txt_path=str(daily_ns01_txt),
        run_id=run_id,
        generated_utc=created_utc,
        operator_name=operator_name,
        vessel_name=vessel_name,
    )
    
    
    upsert_warning_record(
        active_table_csv,
        ActiveWarningRecord(
            warning_id=warning_id,
            navarea=navarea,
            state="ACTIVE",
            source_warning_id=warning_id,
            cancel_targets="",
            last_updated_utc=created_utc,
            plotted="YES",
            plot_ref=str(plot_csv),
        ),
    )
    
    merged_result = update_active_session_for_warning(
        active_table_csv_path=str(active_table_csv),
        output_csv_path=str(active_session_csv),
        warning_plot_csv_path=str(plot_csv),
        warning_state="ACTIVE",
        is_replacement=False, 
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
        "plot_csv_path": str(plot_csv),
        "daily_ns01_csv_path": str(daily_ns01_csv),
        "daily_ns01_txt_path": str(daily_ns01_txt),
        "errors": [],
        "active_session_csv_path": str(active_session_csv),
        "active_session_ok": merged_result["ok"],
    }