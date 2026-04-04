from __future__ import annotations

import argparse
import binascii
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from modules.navwarn_mini.uchm.uchm_donor_registry import (
    get_line_basic_descriptor,
    get_point_basic_descriptor,
)
from modules.navwarn_mini.uchm.uchm_export_service import export_plot_objects_to_uchm
from modules.navwarn_mini.uchm.uchm_family_constant_registry import LINE_REPEATED
from modules.navwarn_mini.warning_plot_builder_service import PlotObject

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "tests" / "fixtures" / "jrc_usercharts_generated" / "validation_cases"
MANIFEST_PATH = OUTPUT_DIR / "validation_manifest.json"
NOTES_PATH = OUTPUT_DIR / "validation_notes.txt"

LINE_DESCRIPTOR = get_line_basic_descriptor()
POINT_DESCRIPTOR = get_point_basic_descriptor()


@dataclass(frozen=True)
class CaseDefinition:
    filename: str
    plot_objects: list[PlotObject]
    assumptions: list[str]


def _line(
    *,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    line_type: int,
    line_width: int,
    color_no: int,
) -> PlotObject:
    return PlotObject(
        object_kind="LINE",
        geom_type="LINE",
        vertices=[(start_lat, start_lon), (end_lat, end_lon)],
        line_type=line_type,
        line_width=line_width,
        color_no=color_no,
    )


def _point(
    *,
    lat: float,
    lon: float,
    symbol_kind: str,
) -> PlotObject:
    return PlotObject(
        object_kind="POINT",
        geom_type="POINT",
        vertices=[(lat, lon)],
        point_symbol_kind=symbol_kind,
    )


def _case_definitions() -> list[CaseDefinition]:
    return [
        CaseDefinition(
            filename="generated_LINE_LINE.uchm",
            plot_objects=[
                _line(start_lat=24.250000, start_lon=-58.750000, end_lat=24.900000, end_lon=-57.950000, line_type=1, line_width=3, color_no=5),
                _line(start_lat=25.150000, start_lon=-57.100000, end_lat=25.850000, end_lon=-56.250000, line_type=1, line_width=3, color_no=5),
            ],
            assumptions=[
                "Package uses current multi-object assembly path.",
                "All-LINE package currently uses LINE_REPEATED family constant.",
            ],
        ),
        CaseDefinition(
            filename="generated_POINT_POINT.uchm",
            plot_objects=[
                _point(lat=23.307348307291665, lon=-56.46746354166667, symbol_kind="X"),
                _point(lat=19.659824869791667, lon=-84.14971354166667, symbol_kind="X_ALT09"),
            ],
            assumptions=[
                "POINT+POINT package uses current provisional package family selection.",
                "Point controls map X->0x08 and X_ALT09->0x09.",
            ],
        ),
        CaseDefinition(
            filename="generated_LINE_POINT.uchm",
            plot_objects=[
                _line(start_lat=26.000000, start_lon=-60.000000, end_lat=26.450000, end_lon=-59.200000, line_type=1, line_width=2, color_no=9),
                _point(lat=26.900000, lon=-58.650000, symbol_kind="X_ALT09"),
            ],
            assumptions=[
                "LINE+POINT package uses current provisional package family selection.",
                "Mixed-family package acceptance is not yet JRC-validated.",
            ],
        ),
        CaseDefinition(
            filename="generated_LINE_SINGLE.uchm",
            plot_objects=[
                _line(start_lat=21.250000, start_lon=-54.500000, end_lat=22.100000, end_lon=-53.650000, line_type=1, line_width=4, color_no=4),
            ],
            assumptions=[
                "Single-object native line path uses LINE_BASIC donor mutation.",
            ],
        ),
        CaseDefinition(
            filename="generated_POINT_SINGLE_08.uchm",
            plot_objects=[
                _point(lat=23.307348307291665, lon=-56.46746354166667, symbol_kind="X"),
            ],
            assumptions=[
                "Single-object native point path uses POINT_BASIC donor mutation.",
                "Symbol control lane 0x08 is grounded to X/default.",
            ],
        ),
        CaseDefinition(
            filename="generated_POINT_SINGLE_09.uchm",
            plot_objects=[
                _point(lat=19.659824869791667, lon=-84.14971354166667, symbol_kind="X_ALT09"),
            ],
            assumptions=[
                "Single-object native point path uses POINT_BASIC donor mutation.",
                "X_ALT09 is a cautious alias for the proven 0x09 control lane.",
            ],
        ),
    ]


def _point_symbol_control(symbol_kind: str) -> int | None:
    normalized = " ".join((symbol_kind or "").upper().split())
    return {
        "X": 0x08,
        "DEFAULT": 0x08,
        "UNKNOWN": 0x08,
        "X_ALT09": 0x09,
    }.get(normalized)


def _expected_package_family(plot_objects: list[PlotObject]) -> str:
    kinds = [obj.object_kind for obj in plot_objects]
    if len(plot_objects) == 1 and kinds == ["LINE"]:
        return "LINE_BASIC"
    if len(plot_objects) == 1 and kinds == ["POINT"]:
        return "POINT_BASIC"
    if kinds == ["LINE", "LINE"]:
        return "LINE_REPEATED"
    if kinds in (["POINT", "POINT"], ["LINE", "POINT"], ["POINT", "LINE"]):
        first_kind = kinds[0]
        return "POINT_BASIC" if first_kind == "POINT" else "LINE_BASIC"
    return "UNKNOWN"


def _describe_case(case: CaseDefinition, output_path: Path) -> dict[str, object]:
    object_entries: list[dict[str, object]] = []
    for obj in case.plot_objects:
        entry: dict[str, object] = {
            "object_kind": obj.object_kind,
            "vertices": [[lat, lon] for lat, lon in obj.vertices],
            "scale_values": {
                "scamin": 100_000_000,
                "scamax": 1_000,
            },
        }
        if obj.object_kind == "LINE":
            entry["descriptor_family"] = str(LINE_DESCRIPTOR["family_name"])
            entry["line_type"] = int(obj.line_type or 0)
            entry["line_width"] = int(obj.line_width or 0)
            entry["color_no"] = int(obj.color_no or 0)
        elif obj.object_kind == "POINT":
            entry["descriptor_family"] = str(POINT_DESCRIPTOR["family_name"])
            entry["symbol_kind"] = str(obj.point_symbol_kind or "X")
            entry["symbol_control"] = _point_symbol_control(str(obj.point_symbol_kind or "X"))
        object_entries.append(entry)

    return {
        "filename": case.filename,
        "output_path": str(output_path),
        "object_count": len(case.plot_objects),
        "object_kinds": [obj.object_kind for obj in case.plot_objects],
        "descriptor_families": [entry["descriptor_family"] for entry in object_entries],
        "expected_package_family": _expected_package_family(case.plot_objects),
        "backend_path_used": "modules.navwarn_mini.uchm.uchm_export_service.export_plot_objects_to_uchm",
        "objects": object_entries,
        "provisional_assumptions": case.assumptions,
    }


def _write_notes() -> None:
    NOTES_PATH.write_text(
        "\n".join([
            "UCHM validation harness output",
            "",
            "Purpose:",
            "- Generate deterministic native .uchm files for manual JRC import/resave testing.",
            "- Preserve generated-side metadata in validation_manifest.json.",
            "- Support byte-diff comparison against a JRC-resaved file.",
            "",
            "Important current assumptions:",
            "- Single LINE uses LINE_BASIC donor mutation.",
            "- Single POINT uses POINT_BASIC donor mutation.",
            "- LINE+LINE package uses LINE_REPEATED family constant.",
            "- LINE+POINT and POINT+POINT package family selection remains provisional.",
            "- Point symbol controls currently supported: 0x08 (X/default) and 0x09 (X_ALT09 alias).",
        ]),
        encoding="utf-8",
    )


def generate_validation_cases() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_cases: list[dict[str, object]] = []
    generated_paths: list[str] = []

    for case in _case_definitions():
        output_path = OUTPUT_DIR / case.filename
        result = export_plot_objects_to_uchm(plot_objects=case.plot_objects, plot_path=output_path)
        if not result.ok:
            raise RuntimeError(f"Failed to generate {case.filename}: {result.unsupported_reason or result.errors}")
        manifest_cases.append(_describe_case(case, output_path))
        generated_paths.append(str(output_path))

    manifest = {
        "output_dir": str(OUTPUT_DIR),
        "case_count": len(manifest_cases),
        "cases": manifest_cases,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_notes()

    report = {
        "output_dir": str(OUTPUT_DIR),
        "generated_count": len(generated_paths),
        "generated_files": [Path(path).name for path in generated_paths],
        "manifest": str(MANIFEST_PATH),
        "notes": str(NOTES_PATH),
    }
    print(json.dumps(report, indent=2))
    return report


def _logical_end_from_header(data: bytes) -> int | None:
    if len(data) < 0x44:
        return None
    return int.from_bytes(data[0x40:0x44], byteorder="little", signed=False)


def _tail_value(data: bytes) -> int | None:
    if len(data) < 4:
        return None
    return int.from_bytes(data[-4:], byteorder="little", signed=False)


def _changed_ranges(left: bytes, right: bytes) -> list[dict[str, int]]:
    max_len = max(len(left), len(right))
    diffs: list[int] = []
    for idx in range(max_len):
        left_byte = left[idx] if idx < len(left) else None
        right_byte = right[idx] if idx < len(right) else None
        if left_byte != right_byte:
            diffs.append(idx)

    if not diffs:
        return []

    ranges: list[dict[str, int]] = []
    start = prev = diffs[0]
    for idx in diffs[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        ranges.append({"start": start, "end": prev, "size": prev - start + 1})
        start = prev = idx
    ranges.append({"start": start, "end": prev, "size": prev - start + 1})
    return ranges


def _resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.exists():
        return candidate
    repo_relative = REPO_ROOT / candidate
    if repo_relative.exists():
        return repo_relative
    return candidate


def compare_files(generated_path: str | Path, resaved_path: str | Path) -> dict[str, object]:
    left_path = _resolve_input_path(generated_path)
    right_path = _resolve_input_path(resaved_path)
    left = left_path.read_bytes()
    right = right_path.read_bytes()

    report = {
        "generated_file": str(left_path),
        "resaved_file": str(right_path),
        "generated_size": len(left),
        "resaved_size": len(right),
        "generated_logical_end": _logical_end_from_header(left),
        "resaved_logical_end": _logical_end_from_header(right),
        "generated_tail": _tail_value(left),
        "resaved_tail": _tail_value(right),
        "generated_crc32_payload": binascii.crc32(left[0x40:-4]) & 0xFFFFFFFF if len(left) >= 0x44 else None,
        "resaved_crc32_payload": binascii.crc32(right[0x40:-4]) & 0xFFFFFFFF if len(right) >= 0x44 else None,
        "changed_ranges": _changed_ranges(left, right),
    }
    print(json.dumps(report, indent=2))
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic UCHM validation cases and compare resaved files.")
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("generate", help="Generate validation cases into the standard output folder.")

    compare_parser = subparsers.add_parser("compare", help="Compare a generated file with a JRC-resaved file.")
    compare_parser.add_argument("generated_file", help="Path to the generated .uchm file.")
    compare_parser.add_argument("resaved_file", help="Path to the JRC-resaved .uchm file.")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in (None, "generate"):
        generate_validation_cases()
        return 0

    if args.command == "compare":
        compare_files(args.generated_file, args.resaved_file)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
