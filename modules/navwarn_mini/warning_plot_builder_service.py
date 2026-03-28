from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import OffshoreObject
from .vertex_text_builder import (
    build_phrase_line_aggregate,
    policy_for_phrase,
    short_warning_id,
)
from .warning_plot_decision_models import EffectivePlotDecision
from .warning_text_payload_service import PlotTextPayload


@dataclass
class PlotObject:
    object_kind: str  # POINT / LINE / AREA / TEXT
    geom_type: str
    vertices: list[tuple[float, float]]

    text: str = ""
    point_symbol_kind: Optional[str] = None

    color_no: Optional[int] = None
    line_type: Optional[int] = None
    line_width: Optional[int] = None

    hatch_enabled: bool = False
    hatch_spacing_nm: Optional[float] = None

    source_warning_id: str = ""
    source_navarea: str = ""

    styled_vertices: list[tuple[float, float, int, int, int]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PlotBuildResult:
    objects: list[PlotObject]
    reasons: list[str] = field(default_factory=list)


def _centroid(vertices: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not vertices:
        return None
    lat = sum(v[0] for v in vertices) / len(vertices)
    lon = sum(v[1] for v in vertices) / len(vertices)
    return (lat, lon)


def _midpoint(vertices: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not vertices:
        return None
    idx = len(vertices) // 2
    return vertices[idx]


def _compact_label_text(
    *,
    warning_id: str,
    text_payload: PlotTextPayload,
    decision: EffectivePlotDecision,
) -> str:
    wid = short_warning_id(warning_id)
    short_text = " ".join((text_payload.short_text or "").upper().split())

    if decision.label_mode == "NONE":
        return ""

    if decision.suppress_body_text_for_points:
        return f"{wid} {short_text}".strip() if short_text else wid

    return f"{wid} {short_text}".strip() if short_text else wid


def _guess_point_symbol_kind(
    *,
    label_text: str,
    decision: EffectivePlotDecision,
    platform_name: str = "",
    platform_type: str = "",
) -> str:
    explicit = (decision.point_symbol_kind or "").strip().upper()
    if explicit:
        return explicit

    hay = " ".join(
        x for x in [
            label_text.upper().strip(),
            platform_name.upper().strip(),
            platform_type.upper().strip(),
            str(decision.render_family or "").upper().strip(),
        ]
        if x
    )

    if "WRECK" in hay:
        return "WRECK"
    if "BEACON" in hay:
        return "BEACON"
    if "BUOY" in hay:
        return "BUOY"
    if "PLATFORM" in hay:
        return "PLATFORM"
    if "MODU" in hay:
        return "MODU"
    if "OFFSHORE" in hay:
        return "PLATFORM"

    return "X"


def _make_text_object(
    *,
    anchor: tuple[float, float] | None,
    label_text: str,
    warning_id: str,
    navarea: str,
    object_kind: str,
) -> PlotObject | None:
    if anchor is None:
        return None

    label_text = " ".join((label_text or "").split()).upper()
    if not label_text:
        return None

    policy = policy_for_phrase(
        text=label_text,
        object_kind=object_kind,
    )

    styled = build_phrase_line_aggregate(
        anchor_lat=anchor[0],
        anchor_lon=anchor[1],
        text=label_text,
        policy=policy,
    )

    if not styled:
        return None

    return PlotObject(
        object_kind="TEXT",
        geom_type="LINE",
        vertices=[(v.lat, v.lon) for v in styled],
        text=label_text,
        source_warning_id=warning_id,
        source_navarea=navarea,
        styled_vertices=[
            (v.lat, v.lon, v.line_type, v.width, v.color_no)
            for v in styled
        ],
        metadata={
            "text_role": "phrase_label",
            "text_render_mode": "VERTEX_STROKE",
            "text_object_kind": object_kind,
            "text_char_width_nm": policy.char_width_nm,
            "text_char_height_nm": policy.char_height_nm,
            "text_char_spacing_nm": policy.char_spacing_nm,
            "text_color_no": policy.text_color_no,
            "text_line_type": policy.text_line_type,
            "text_width": policy.text_width,
            "connector_color_no": policy.connector_color_no,
            "connector_line_type": policy.connector_line_type,
            "connector_width": policy.connector_width,
        },
    )


def build_plot_objects(
    *,
    warning_id: str,
    navarea: str,
    verts: list[tuple[float, float]],
    geom_type: str,
    offshore_objects: list[OffshoreObject],
    decision: EffectivePlotDecision,
    text_payload: PlotTextPayload,
) -> PlotBuildResult:
    reasons: list[str] = []
    objects: list[PlotObject] = []

    if not decision.enable_plot:
        reasons.append("Plot disabled by effective decision")
        return PlotBuildResult(objects=objects, reasons=reasons)

    label_text = _compact_label_text(
        warning_id=warning_id,
        text_payload=text_payload,
        decision=decision,
    )

    print("[PLOT BUILDER DEBUG]", {
        "warning_id": warning_id,
        "navarea": navarea,
        "object_mode": decision.object_mode,
        "geom_type": geom_type,
        "verts_count": len(verts),
        "effective_color_no": decision.effective_color_no,
        "main_line_type": decision.main_line_type,
        "main_width": decision.main_width,
        "label_mode": decision.label_mode,
        "render_family": decision.render_family,
    })

    if decision.object_mode == "MULTI_POINT" and offshore_objects:
        reasons.append("Building MULTI_POINT offshore objects")

        for obj in offshore_objects:
            if not obj.geometry.vertices:
                continue

            pt = obj.geometry.vertices[0]
            point_vertices = [(pt.lat, pt.lon)]
            point_label = obj.platform_name if decision.label_mode == "OFFSHORE_PER_OBJECT" else label_text
            point_symbol_kind = _guess_point_symbol_kind(
                label_text=point_label,
                decision=decision,
                platform_name=obj.platform_name or "",
                platform_type=obj.platform_type or "",
            )

            objects.append(
                PlotObject(
                    object_kind="POINT",
                    geom_type="POINT",
                    vertices=point_vertices,
                    text=point_label,
                    point_symbol_kind=point_symbol_kind,
                    color_no=decision.effective_color_no,
                    line_type=decision.main_line_type,
                    line_width=decision.main_width,
                    hatch_enabled=False,
                    hatch_spacing_nm=None,
                    source_warning_id=warning_id,
                    source_navarea=navarea,
                    metadata={
                        "render_family": decision.render_family,
                        "platform_id": obj.platform_id,
                        "platform_name": obj.platform_name,
                        "platform_type": obj.platform_type,
                        "match_status": obj.match_status,
                        "identity_confidence": obj.identity_confidence,
                        "tce_thread_id": obj.tce_thread_id,
                        "label_mode": decision.label_mode,
                    },
                )
            )

            if decision.enable_text:
                text_obj = _make_text_object(
                    anchor=point_vertices[0],
                    label_text=point_label,
                    warning_id=warning_id,
                    navarea=navarea,
                    object_kind="POINT",
                )
                if text_obj is not None:
                    objects.append(text_obj)

        return PlotBuildResult(objects=objects, reasons=reasons)

    if decision.object_mode == "POINT":
        reasons.append("Building POINT object")

        point_symbol_kind = _guess_point_symbol_kind(
            label_text=label_text,
            decision=decision,
        )

        objects.append(
            PlotObject(
                object_kind="POINT",
                geom_type="POINT",
                vertices=verts[:1] if verts else [],
                text=label_text,
                point_symbol_kind=point_symbol_kind,
                color_no=decision.effective_color_no,
                line_type=decision.main_line_type,
                line_width=decision.main_width,
                hatch_enabled=False,
                hatch_spacing_nm=None,
                source_warning_id=warning_id,
                source_navarea=navarea,
                metadata={
                    "render_family": decision.render_family,
                    "label_mode": decision.label_mode,
                },
            )
        )

        if decision.enable_text and verts[:1]:
            text_obj = _make_text_object(
                anchor=verts[0],
                label_text=label_text,
                warning_id=warning_id,
                navarea=navarea,
                object_kind="POINT",
            )
            if text_obj is not None:
                objects.append(text_obj)

        return PlotBuildResult(objects=objects, reasons=reasons)

    if decision.object_mode == "LINE":
        if len(verts) < 2:
            reasons.append("Invalid LINE geometry (<2 vertices)")
            print("[PLOT BUILDER DEBUG]", {
                "warning_id": warning_id,
                "error": "LINE object rejected because verts < 2",
                "verts_count": len(verts),
            })
            return PlotBuildResult(objects=[], reasons=reasons)

        reasons.append("Building LINE object")
        objects.append(
            PlotObject(
                object_kind="LINE",
                geom_type="LINE",
                vertices=verts,
                text="",
                color_no=5,
                line_type=1,
                line_width=3,
                hatch_enabled=False,
                hatch_spacing_nm=None,
                source_warning_id=warning_id,
                source_navarea=navarea,
                metadata={
                    "render_family": decision.render_family,
                    "label_mode": decision.label_mode,
                },
            )
        )

        anchor = _midpoint(verts)
        if decision.enable_text and anchor:
            text_obj = _make_text_object(
                anchor=anchor,
                label_text=label_text,
                warning_id=warning_id,
                navarea=navarea,
                object_kind="LINE",
            )
            if text_obj is not None:
                objects.append(text_obj)

        return PlotBuildResult(objects=objects, reasons=reasons)

    if decision.object_mode == "AREA":
        if len(verts) < 3:
            reasons.append("Invalid AREA geometry (<3 vertices)")
            print("[PLOT BUILDER DEBUG]", {
                "warning_id": warning_id,
                "error": "AREA object rejected because verts < 3",
                "verts_count": len(verts),
            })
            return PlotBuildResult(objects=[], reasons=reasons)

        reasons.append("Building AREA object")
        objects.append(
            PlotObject(
                object_kind="AREA",
                geom_type="AREA",
                vertices=verts,
                text="",
                color_no=5,
                line_type=1,
                line_width=3,
                hatch_enabled=decision.hatch_enabled,
                hatch_spacing_nm=decision.hatch_spacing_nm,
                source_warning_id=warning_id,
                source_navarea=navarea,
                metadata={
                    "render_family": decision.render_family,
                    "label_mode": decision.label_mode,
                    "collapse_to_boundary_only": decision.collapse_to_boundary_only,
                },
            )
        )

        anchor = _centroid(verts)
        if decision.enable_text and anchor:
            text_obj = _make_text_object(
                anchor=anchor,
                label_text=label_text,
                warning_id=warning_id,
                navarea=navarea,
                object_kind="AREA",
            )
            if text_obj is not None:
                objects.append(text_obj)

        return PlotBuildResult(objects=objects, reasons=reasons)

    reasons.append(f"Unhandled object_mode={decision.object_mode}")
    return PlotBuildResult(objects=objects, reasons=reasons)

