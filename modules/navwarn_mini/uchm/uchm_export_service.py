from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..warning_plot_builder_service import PlotObject
from .uchm_donor_registry import get_line_basic_descriptor, get_point_basic_descriptor, get_text_basic_descriptor
from .uchm_line_package_donor_writer import write_two_line_package_from_donor
from .uchm_line_writer import write_basic_line_from_donor
from .uchm_package_writer import write_multi_object_package
from .uchm_point_writer import write_basic_point_from_donor
from .uchm_text_writer import write_basic_text_from_donor


@dataclass
class UchmExportResult:
    ok: bool
    output_path: str | None
    object_kind_handled: str
    unsupported_reason: str = ""
    exported_object_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class UchmCapabilityDecision:
    supported: bool
    descriptor: dict[str, object] | None
    reason: str


def _coerce_output_path(plot_path: str | Path) -> Path:
    path = Path(plot_path)
    if path.suffix.lower() != ".uchm":
        return path.with_suffix(".uchm")
    return path


def _is_basic_line_compatible(obj: PlotObject) -> tuple[bool, str]:
    if obj.object_kind != "LINE":
        return False, f"Unsupported object_kind for native line donor path: {obj.object_kind}"
    if len(obj.vertices) != 2:
        return False, f"Native donor line path currently supports exactly 2 vertices, got {len(obj.vertices)}"
    if obj.line_type is None or obj.line_width is None or obj.color_no is None:
        return False, "Native donor line path requires line_type, line_width, and color_no"
    return True, ""


def _select_line_descriptor(obj: PlotObject) -> UchmCapabilityDecision:
    supported, reason = _is_basic_line_compatible(obj)
    if not supported:
        return UchmCapabilityDecision(
            supported=False,
            descriptor=None,
            reason=reason,
        )

    return UchmCapabilityDecision(
        supported=True,
        descriptor=get_line_basic_descriptor(),
        reason="Supported by LINE_BASIC donor descriptor",
    )


def _is_basic_point_compatible(obj: PlotObject) -> tuple[bool, str]:
    if obj.object_kind != "POINT":
        return False, f"Unsupported object_kind for native point donor path: {obj.object_kind}"
    if len(obj.vertices) != 1:
        return False, f"Native donor point path currently supports exactly 1 vertex, got {len(obj.vertices)}"

    descriptor = get_point_basic_descriptor()
    normalized_symbol_kind = _normalize_point_symbol_kind(obj.point_symbol_kind)
    symbol_control_by_kind = _point_symbol_control_by_kind(descriptor)
    if normalized_symbol_kind not in symbol_control_by_kind:
        return False, (
            "Native donor point path currently supports only symbol kinds "
            f"{sorted(symbol_control_by_kind)}, got {normalized_symbol_kind}"
        )
    return True, ""


def _normalize_point_symbol_kind(symbol_kind: str | None) -> str:
    return " ".join((symbol_kind or "X").upper().split()) or "X"


def _point_symbol_control_by_kind(descriptor: dict[str, object]) -> dict[str, int]:
    raw = descriptor["symbol_control_by_kind"]
    return {
        " ".join(str(kind).upper().split()): int(value) & 0xFF
        for kind, value in raw.items()
    }


def _resolve_point_symbol_control(obj: PlotObject, descriptor: dict[str, object]) -> int:
    normalized_symbol_kind = _normalize_point_symbol_kind(obj.point_symbol_kind)
    symbol_control_by_kind = _point_symbol_control_by_kind(descriptor)
    try:
        return symbol_control_by_kind[normalized_symbol_kind]
    except KeyError as exc:
        raise ValueError(
            "Unsupported native point symbol kind "
            f"{normalized_symbol_kind}; supported kinds are {sorted(symbol_control_by_kind)}"
        ) from exc


def _select_point_descriptor(obj: PlotObject) -> UchmCapabilityDecision:
    supported, reason = _is_basic_point_compatible(obj)
    if not supported:
        return UchmCapabilityDecision(
            supported=False,
            descriptor=None,
            reason=reason,
        )

    return UchmCapabilityDecision(
        supported=True,
        descriptor=get_point_basic_descriptor(),
        reason="Supported by POINT_BASIC donor descriptor",
    )


def _is_basic_text_compatible(obj: PlotObject) -> tuple[bool, str]:
    if obj.object_kind != "TEXT":
        return False, f"Unsupported object_kind for native text donor path: {obj.object_kind}"
    if not (obj.text or "").strip():
        return False, "Native donor text path requires non-empty text"

    descriptor = get_text_basic_descriptor()
    capacity = int(descriptor["text_offsets"]["text_capacity"])
    normalized_text = " ".join((obj.text or "").upper().split())
    try:
        encoded = normalized_text.encode("ascii")
    except UnicodeEncodeError:
        return False, "Native donor text path currently supports ASCII text only"
    if len(encoded) > capacity:
        return False, f"Native donor text path currently supports at most {capacity} ASCII bytes, got {len(encoded)}"
    return True, ""


def _select_text_descriptor(obj: PlotObject) -> UchmCapabilityDecision:
    supported, reason = _is_basic_text_compatible(obj)
    if not supported:
        return UchmCapabilityDecision(
            supported=False,
            descriptor=None,
            reason=reason,
        )

    return UchmCapabilityDecision(
        supported=True,
        descriptor=get_text_basic_descriptor(),
        reason="Supported by TEXT_BASIC donor descriptor",
    )


def export_plot_objects_to_uchm(
    *,
    plot_objects: list[PlotObject],
    plot_path: str | Path,
) -> UchmExportResult:
    path = _coerce_output_path(plot_path)

    if not plot_objects:
        return UchmExportResult(
            ok=False,
            output_path=None,
            object_kind_handled="",
            unsupported_reason="No plot objects supplied",
            exported_object_count=0,
            errors=["No plot objects supplied for UCHM export"],
        )

    if len(plot_objects) > 2:
        return UchmExportResult(
            ok=False,
            output_path=str(path),
            object_kind_handled="MULTI_OBJECT",
            unsupported_reason=f"Native donor path currently supports at most 2 plot objects, got {len(plot_objects)}",
            exported_object_count=0,
            errors=[
                f"Native donor path currently supports at most 2 plot objects, got {len(plot_objects)}"
            ],
        )

    if len(plot_objects) == 2:
        if all(obj.object_kind == "LINE" for obj in plot_objects):
            line_requests: list[dict[str, object]] = []
            for obj in plot_objects:
                capability = _select_line_descriptor(obj)
                if not capability.supported or capability.descriptor is None:
                    return UchmExportResult(
                        ok=False,
                        output_path=str(path),
                        object_kind_handled=obj.object_kind,
                        unsupported_reason=capability.reason,
                        exported_object_count=0,
                        errors=[capability.reason],
                    )
                first, second = obj.vertices
                line_requests.append({
                    "start_lat": first[0],
                    "start_lon": first[1],
                    "end_lat": second[0],
                    "end_lon": second[1],
                    "line_type": int(obj.line_type),
                    "width": int(obj.line_width),
                    "color_no": int(obj.color_no),
                })

            try:
                donor_result = write_two_line_package_from_donor(
                    plot_path=path,
                    first_line=line_requests[0],
                    second_line=line_requests[1],
                )
            except Exception as exc:
                return UchmExportResult(
                    ok=False,
                    output_path=str(path),
                    object_kind_handled="LINE+LINE",
                    unsupported_reason=str(exc),
                    exported_object_count=0,
                    errors=[f"Native donor two-line package write failed: {exc}"],
                )

            return UchmExportResult(
                ok=donor_result.ok,
                output_path=donor_result.output_path,
                object_kind_handled=donor_result.object_kind_handled,
                unsupported_reason=donor_result.unsupported_reason,
                exported_object_count=2 if donor_result.ok else 0,
                errors=[],
            )

        object_requests: list[dict[str, object]] = []
        for obj in plot_objects:
            if obj.object_kind == "LINE":
                capability = _select_line_descriptor(obj)
                if not capability.supported or capability.descriptor is None:
                    return UchmExportResult(
                        ok=False,
                        output_path=str(path),
                        object_kind_handled=obj.object_kind,
                        unsupported_reason=capability.reason,
                        exported_object_count=0,
                        errors=[capability.reason],
                    )
                first, second = obj.vertices
                object_requests.append({
                    "object_kind": "LINE",
                    "descriptor": capability.descriptor,
                    "start_lat": first[0],
                    "start_lon": first[1],
                    "end_lat": second[0],
                    "end_lon": second[1],
                    "line_type": int(obj.line_type),
                    "width": int(obj.line_width),
                    "color_no": int(obj.color_no),
                })
                continue

            if obj.object_kind == "POINT":
                capability = _select_point_descriptor(obj)
                if not capability.supported or capability.descriptor is None:
                    return UchmExportResult(
                        ok=False,
                        output_path=str(path),
                        object_kind_handled=obj.object_kind,
                        unsupported_reason=capability.reason,
                        exported_object_count=0,
                        errors=[capability.reason],
                    )
                first = obj.vertices[0]
                object_requests.append({
                    "object_kind": "POINT",
                    "descriptor": capability.descriptor,
                    "lat": first[0],
                    "lon": first[1],
                    "symbol_control": _resolve_point_symbol_control(obj, capability.descriptor),
                })
                continue

            return UchmExportResult(
                ok=False,
                output_path=str(path),
                object_kind_handled=obj.object_kind,
                unsupported_reason=f"Unsupported object_kind for native multi-object export: {obj.object_kind}",
                exported_object_count=0,
                errors=[f"Unsupported object_kind for native multi-object export: {obj.object_kind}"],
            )

        try:
            package_result = write_multi_object_package(
                plot_objects=plot_objects,
                object_requests=object_requests,
                plot_path=path,
            )
        except Exception as exc:
            return UchmExportResult(
                ok=False,
                output_path=str(path),
                object_kind_handled="+".join(obj.object_kind for obj in plot_objects),
                unsupported_reason=str(exc),
                exported_object_count=0,
                errors=[f"Native donor package write failed: {exc}"],
            )

        return UchmExportResult(
            ok=package_result.ok,
            output_path=package_result.output_path,
            object_kind_handled=package_result.object_kind_handled,
            unsupported_reason=package_result.unsupported_reason,
            exported_object_count=package_result.exported_object_count,
            errors=[],
        )

    obj = plot_objects[0]
    if obj.object_kind == "LINE":
        capability = _select_line_descriptor(obj)
    elif obj.object_kind == "POINT":
        capability = _select_point_descriptor(obj)
    elif obj.object_kind == "TEXT":
        capability = _select_text_descriptor(obj)
    else:
        capability = UchmCapabilityDecision(
            supported=False,
            descriptor=None,
            reason=f"Unsupported object_kind for native UCHM export: {obj.object_kind}",
        )

    if not capability.supported or capability.descriptor is None:
        return UchmExportResult(
            ok=False,
            output_path=str(path),
            object_kind_handled=obj.object_kind,
            unsupported_reason=capability.reason,
            exported_object_count=0,
            errors=[capability.reason],
        )

    try:
        if obj.object_kind == "LINE":
            first, second = obj.vertices
            write_result = write_basic_line_from_donor(
                descriptor=capability.descriptor,
                plot_path=path,
                start_lat=first[0],
                start_lon=first[1],
                end_lat=second[0],
                end_lon=second[1],
                line_type=int(obj.line_type),
                width=int(obj.line_width),
                color_no=int(obj.color_no),
            )
        elif obj.object_kind == "POINT":
            first = obj.vertices[0]
            write_result = write_basic_point_from_donor(
                descriptor=capability.descriptor,
                plot_path=path,
                lat=first[0],
                lon=first[1],
                symbol_control=_resolve_point_symbol_control(obj, capability.descriptor),
            )
        else:
            anchor = obj.vertices[0] if obj.vertices else (0.0, 0.0)
            write_result = write_basic_text_from_donor(
                descriptor=capability.descriptor,
                plot_path=path,
                text=" ".join((obj.text or "").upper().split()),
                anchor_lat=anchor[0],
                anchor_lon=anchor[1],
            )
    except Exception as exc:
        return UchmExportResult(
            ok=False,
            output_path=str(path),
            object_kind_handled=obj.object_kind,
            unsupported_reason=str(exc),
            exported_object_count=0,
            errors=[f"Native donor {obj.object_kind.lower()} write failed: {exc}"],
        )

    return UchmExportResult(
        ok=write_result.ok,
        output_path=write_result.output_path,
        object_kind_handled=write_result.object_kind_handled,
        unsupported_reason=write_result.unsupported_reason,
        exported_object_count=1 if write_result.ok else 0,
        errors=[],
    )
