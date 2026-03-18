from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import OffshoreObject
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


def _build_text_string(
    *,
    decision: EffectivePlotDecision,
    text_payload: PlotTextPayload,
) -> str:
    if not decision.enable_text:
        return ""

    if decision.label_mode == "NONE":
        return ""

    if decision.suppress_body_text_for_points:
        return f"{text_payload.title_text} {text_payload.short_text}".strip()

    return f"{text_payload.title_text} {text_payload.short_text}".strip()


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

    label_text = _build_text_string(
        decision=decision,
        text_payload=text_payload,
    )

    # 1. Offshore per-object mode
    if decision.object_mode == "MULTI_POINT" and offshore_objects:
        reasons.append("Building MULTI_POINT offshore objects")

        for obj in offshore_objects:
            if not obj.geometry.vertices:
                continue

            pt = obj.geometry.vertices[0]
            point_vertices = [(pt.lat, pt.lon)]

            objects.append(
                PlotObject(
                    object_kind="POINT",
                    geom_type="POINT",
                    vertices=point_vertices,
                    text=obj.platform_name if decision.label_mode == "OFFSHORE_PER_OBJECT" else label_text,
                    point_symbol_kind=decision.point_symbol_kind,
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

        return PlotBuildResult(objects=objects, reasons=reasons)

    # 2. Generic POINT
    if decision.object_mode == "POINT":
        reasons.append("Building POINT object")
        objects.append(
            PlotObject(
                object_kind="POINT",
                geom_type="POINT",
                vertices=verts[:1] if verts else [],
                text=label_text,
                point_symbol_kind=decision.point_symbol_kind,
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

        # optional text anchor object
        if decision.enable_text and verts[:1]:
            objects.append(
                PlotObject(
                    object_kind="TEXT",
                    geom_type="POINT",
                    vertices=verts[:1],
                    text=label_text,
                    color_no=decision.effective_color_no,
                    source_warning_id=warning_id,
                    source_navarea=navarea,
                    metadata={"text_role": "point_label"},
                )
            )

        return PlotBuildResult(objects=objects, reasons=reasons)

    # 3. Generic LINE
    if decision.object_mode == "LINE":
        reasons.append("Building LINE object")
        objects.append(
            PlotObject(
                object_kind="LINE",
                geom_type="LINE",
                vertices=verts,
                text="",
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

        anchor = _midpoint(verts)
        if decision.enable_text and anchor:
            objects.append(
                PlotObject(
                    object_kind="TEXT",
                    geom_type="POINT",
                    vertices=[anchor],
                    text=label_text,
                    color_no=decision.effective_color_no,
                    source_warning_id=warning_id,
                    source_navarea=navarea,
                    metadata={"text_role": "line_label"},
                )
            )

        return PlotBuildResult(objects=objects, reasons=reasons)

    # 4. Generic AREA
    if decision.object_mode == "AREA":
        reasons.append("Building AREA object")
        objects.append(
            PlotObject(
                object_kind="AREA",
                geom_type="AREA",
                vertices=verts,
                text="",
                color_no=decision.effective_color_no,
                line_type=decision.main_line_type,
                line_width=decision.main_width,
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
            objects.append(
                PlotObject(
                    object_kind="TEXT",
                    geom_type="POINT",
                    vertices=[anchor],
                    text=label_text,
                    color_no=decision.effective_color_no,
                    source_warning_id=warning_id,
                    source_navarea=navarea,
                    metadata={"text_role": "area_label"},
                )
            )

        return PlotBuildResult(objects=objects, reasons=reasons)

    # 5. Safe fallback
    reasons.append(f"Unhandled object_mode={decision.object_mode}; fallback to POINT")
    if verts:
        objects.append(
            PlotObject(
                object_kind="POINT",
                geom_type="POINT",
                vertices=[verts[0]],
                text=label_text,
                point_symbol_kind=decision.point_symbol_kind,
                color_no=decision.effective_color_no,
                line_type=decision.main_line_type,
                line_width=decision.main_width,
                source_warning_id=warning_id,
                source_navarea=navarea,
                metadata={"fallback": True},
            )
        )

    return PlotBuildResult(objects=objects, reasons=reasons)