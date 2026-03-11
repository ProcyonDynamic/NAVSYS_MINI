from __future__ import annotations

from dataclasses import asdict, is_dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Iterable, Optional

from .interpreter import InterpretationResult, confidence_review_bucket, interpret_warning
from .models import ShipPosition, WarningDraft


# -----------------------------------------------------------------------------
# Small dynamic-call helpers
# -----------------------------------------------------------------------------

def _resolve_callable(module_name: str, candidates: list[str]):
    """
    Import a sibling module and return the first callable that exists.

    This lets the pipeline stay deterministic while tolerating evolving helper
    names during development.
    """
    try:
        module = import_module(f"{__package__}.{module_name}")
    except Exception:
        return None

    for name in candidates:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    return None


def _first_path(result: Any) -> Optional[str]:
    if isinstance(result, str):
        return result
    if isinstance(result, Path):
        return str(result)
    if isinstance(result, dict):
        for key in (
            "path",
            "csv_path",
            "txt_path",
            "out_path",
            "output_path",
            "plot_csv_path",
            "ns01_csv_path",
            "ns01_txt_path",
        ):
            value = result.get(key)
            if isinstance(value, (str, Path)):
                return str(value)
    return None


def _coerce_errors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, tuple):
        return [str(x) for x in value]
    return [str(value)]


def _ensure_dir(path: str | Path) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


# -----------------------------------------------------------------------------
# Pipeline stage wrappers
# -----------------------------------------------------------------------------

def _classify_distance_and_band(
    *,
    draft: WarningDraft,
    ship_position: ShipPosition | None,
) -> tuple[Optional[float], str, list[str]]:
    """
    A5/A6 helper.

    Tries to use existing route-distance / distance modules if available.
    Falls back to confidence-driven banding if no distance engine is wired yet.
    """
    errors: list[str] = []
    distance_nm: Optional[float] = None

    # Candidate functions from current repo layout:
    # - route_distance.py
    # - distance.py
    distance_fn = _resolve_callable(
        "route_distance",
        [
            "compute_route_distance_nm",
            "compute_distance_nm",
            "route_distance_nm",
            "get_route_distance_nm",
        ],
    ) or _resolve_callable(
        "distance",
        [
            "compute_distance_nm",
            "distance_nm",
            "get_distance_nm",
        ],
    )

    if distance_fn is not None:
        try:
            result = distance_fn(draft=draft, ship_position=ship_position)
            if isinstance(result, (int, float)):
                distance_nm = float(result)
            elif isinstance(result, dict):
                value = result.get("distance_nm")
                if isinstance(value, (int, float)):
                    distance_nm = float(value)
                errors.extend(_coerce_errors(result.get("errors")))
        except Exception as exc:
            errors.append(f"Distance stage failed: {exc}")

    # Conservative fallback until distance/risk rules are fully wired.
    if distance_nm is None:
        band = "AMBER"
    else:
        band = "RED" if distance_nm <= 50.0 else "AMBER"

    return distance_nm, band, errors


def _build_plot_objects(*, warning_id: str, run_id: str, band: str, geometry):
    """
    A7 helper.

    Attempts to use existing build_line_aggregate module if available.
    """
    build_fn = _resolve_callable(
        "build_line_aggregate",
        [
            "build_line_aggregate",
            "build_line_aggregate_object",
            "build_plot_object",
        ],
    )
    if build_fn is None:
        return None, ["Plot object builder not found in build_line_aggregate.py"]

    try:
        # Preferred keyword signature
        result = build_fn(
            warning_id=warning_id,
            run_id=run_id,
            band=band,
            geometry=geometry,
        )
        return result, []
    except TypeError:
        # Fallback positional-ish signature
        try:
            result = build_fn(run_id, warning_id, band, geometry)
            return result, []
        except Exception as exc:
            return None, [f"Plot builder failed: {exc}"]
    except Exception as exc:
        return None, [f"Plot builder failed: {exc}"]


def _export_plot_csv(*, plot_object: Any, out_plots_dir: str) -> tuple[Optional[str], list[str]]:
    """
    A7 helper.

    Attempts to use existing export_jrc_csv module if available.
    """
    export_fn = _resolve_callable(
        "export_jrc_csv",
        [
            "export_jrc_csv",
            "write_jrc_csv",
            "export_plot_csv",
        ],
    )
    if export_fn is None:
        return None, ["JRC CSV exporter not found in export_jrc_csv.py"]

    try:
        result = export_fn(plot_object=plot_object, out_dir=out_plots_dir)
    except TypeError:
        try:
            result = export_fn(plot_object, out_plots_dir)
        except Exception as exc:
            return None, [f"JRC export failed: {exc}"]
    except Exception as exc:
        return None, [f"JRC export failed: {exc}"]

    path = _first_path(result)
    errors = []
    if isinstance(result, dict):
        errors.extend(_coerce_errors(result.get("errors")))
    return path, errors


def _write_ns01(
    *,
    draft: WarningDraft,
    processed_utc: str,
    ship_position: ShipPosition | None,
    distance_nm: Optional[float],
    band: str,
    out_reports_dir: str,
) -> tuple[Optional[str], Optional[str], list[str]]:
    """
    A8 helper.

    Tries register + report modules separately because repo already contains:
    - register_ns01.py
    - report_ns01.py
    """
    errors: list[str] = []

    register_fn = _resolve_callable(
        "register_ns01",
        [
            "append_ns01_row",
            "register_ns01",
            "write_ns01_register",
            "build_ns01_row",
        ],
    )
    report_fn = _resolve_callable(
        "report_ns01",
        [
            "write_ns01_report",
            "report_ns01",
            "export_ns01",
        ],
    )

    ns01_payload = {
        "draft": draft,
        "processed_utc": processed_utc,
        "ship_position": ship_position,
        "distance_nm": distance_nm,
        "band": band,
        "out_dir": out_reports_dir,
    }

    register_result = None
    report_result = None

    if register_fn is not None:
        try:
            register_result = register_fn(**ns01_payload)
        except TypeError:
            try:
                register_result = register_fn(draft, processed_utc, ship_position, distance_nm, band, out_reports_dir)
            except Exception as exc:
                errors.append(f"NS01 register stage failed: {exc}")
        except Exception as exc:
            errors.append(f"NS01 register stage failed: {exc}")
    else:
        errors.append("NS01 register function not found in register_ns01.py")

    if report_fn is not None:
        try:
            report_result = report_fn(**ns01_payload)
        except TypeError:
            try:
                report_result = report_fn(draft, processed_utc, ship_position, distance_nm, band, out_reports_dir)
            except Exception as exc:
                errors.append(f"NS01 report stage failed: {exc}")
        except Exception as exc:
            errors.append(f"NS01 report stage failed: {exc}")
    else:
        errors.append("NS01 report function not found in report_ns01.py")

    ns01_csv_path = None
    ns01_txt_path = None

    for result in (register_result, report_result):
        if isinstance(result, dict):
            maybe_csv = result.get("ns01_csv_path") or result.get("csv_path")
            maybe_txt = result.get("ns01_txt_path") or result.get("txt_path")
            if isinstance(maybe_csv, (str, Path)):
                ns01_csv_path = str(maybe_csv)
            if isinstance(maybe_txt, (str, Path)):
                ns01_txt_path = str(maybe_txt)
            errors.extend(_coerce_errors(result.get("errors")))
        elif isinstance(result, (str, Path)):
            text = str(result)
            if text.lower().endswith(".csv"):
                ns01_csv_path = text
            elif text.lower().endswith(".txt"):
                ns01_txt_path = text

    return ns01_csv_path, ns01_txt_path, errors


# -----------------------------------------------------------------------------
# Public pipeline
# -----------------------------------------------------------------------------

def run_navwarn_pipeline(
    *,
    draft: WarningDraft,
    ship_position: ShipPosition | None,
    run_id: str,
    processed_utc: str,
    out_processed_dir: str,
    out_plots_dir: str,
    out_reports_dir: str,
) -> dict:
    """
    Executes NavWarn A3..A8 in a deterministic, silence-by-default manner.

    Current wiring strategy:
    - use interpreter.py as the canonical A3 layer
    - reuse existing helper modules where available
    - degrade gracefully with explicit error reporting when a downstream helper
      is not fully wired yet

    Returns:
    {
      "ok": bool,
      "warning_id": str,
      "band": "RED"|"AMBER",
      "distance_nm": float|None,
      "plot_csv_path": str|None,
      "ns01_csv_path": str|None,
      "ns01_txt_path": str|None,
      "review_bucket": str,
      "confidence": float,
      "interpretation": {...},
      "errors": [str]
    }
    """
    out_processed_dir = _ensure_dir(out_processed_dir)
    out_plots_dir = _ensure_dir(out_plots_dir)
    out_reports_dir = _ensure_dir(out_reports_dir)

    errors: list[str] = []

    # ------------------------------------------------------------------
    # A3 - interpretation
    # ------------------------------------------------------------------
    interpreted_draft, interpretation = interpret_warning(
        warning_id=draft.warning_id,
        navarea=draft.navarea,
        source_kind=draft.source_kind,
        title=draft.title,
        body=draft.body,
        run_id=run_id,
        created_utc=draft.created_utc,
        source_ref=draft.source_ref,
        operator_name=draft.operator_name,
        operator_watch=draft.operator_watch,
        operator_notes=draft.operator_notes,
        precedent_score=0.0,  # TCE hook to be added later
    )
    errors.extend(interpretation.errors)

    # ------------------------------------------------------------------
    # A5/A6 - distance + banding
    # ------------------------------------------------------------------
    distance_nm, band, distance_errors = _classify_distance_and_band(
        draft=interpreted_draft,
        ship_position=ship_position,
    )
    errors.extend(distance_errors)

    # Safety override:
    # weak interpretation should never become an optimistic RED/auto action.
    review_bucket = confidence_review_bucket(interpretation.confidence)
    if review_bucket == "RED_MANUAL":
        band = "AMBER"

    # ------------------------------------------------------------------
    # A7 - plotting
    # ------------------------------------------------------------------
    plot_csv_path: Optional[str] = None
    plot_object, plot_build_errors = _build_plot_objects(
        warning_id=interpreted_draft.warning_id,
        run_id=run_id,
        band=band,
        geometry=interpreted_draft.geometry,
    )
    errors.extend(plot_build_errors)

    if plot_object is not None:
        exported_plot_path, plot_export_errors = _export_plot_csv(
            plot_object=plot_object,
            out_plots_dir=out_plots_dir,
        )
        plot_csv_path = exported_plot_path
        errors.extend(plot_export_errors)

    # ------------------------------------------------------------------
    # A8 - NS01 register/report
    # ------------------------------------------------------------------
    ns01_csv_path, ns01_txt_path, ns01_errors = _write_ns01(
        draft=interpreted_draft,
        processed_utc=processed_utc,
        ship_position=ship_position,
        distance_nm=distance_nm,
        band=band,
        out_reports_dir=out_reports_dir,
    )
    errors.extend(ns01_errors)

    ok = (
        interpretation.geometry.vertices != []
        and review_bucket != "RED_MANUAL"
        and plot_csv_path is not None
        and ns01_csv_path is not None
    )

    interpretation_payload = {
        "warning_type": interpretation.warning_type,
        "phrase_pattern": interpretation.phrase_pattern,
        "confidence": interpretation.confidence,
        "confidence_breakdown": interpretation.confidence_breakdown,
        "geometry_type": interpretation.geometry.geom_type,
        "vertex_count": len(interpretation.geometry.vertices),
        "validity_ufn": interpretation.validity.ufn,
    }

    return {
        "ok": ok,
        "warning_id": interpreted_draft.warning_id,
        "band": band,
        "distance_nm": distance_nm,
        "plot_csv_path": plot_csv_path,
        "ns01_csv_path": ns01_csv_path,
        "ns01_txt_path": ns01_txt_path,
        "review_bucket": review_bucket,
        "confidence": interpretation.confidence,
        "interpretation": interpretation_payload,
        "errors": errors,
    }
