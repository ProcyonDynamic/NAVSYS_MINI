from __future__ import annotations

from pathlib import Path

from .uchm_family_constant_registry import LINE_BASIC, POINT_BASIC, TEXT_BASIC


def _fixture_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[3].joinpath(*parts)


LINE_BASIC_DONOR: dict[str, object] = {
    "family_name": "LINE_BASIC",
    "donor_file": _fixture_path("tests", "fixtures", "jrc_usercharts", "L01_base.uchm"),
    "family_constant": LINE_BASIC,
    "object_kind": "LINE",
    "supported_vertex_count": 2,
    "style_offsets": [0x170, 0x1C4],
    "scale_offsets": {
        "min": 0x0D4,
        "max": 0x0D8,
    },
    "geometry_offsets": {
        "a_lat": 0x174,
        "a_lon": 0x178,
        "b_lat": 0x1C8,
        "b_lon": 0x1CC,
    },
    "degree_scale": 1_536_000,
    "notes": [
        "Proven minimal donor for native 2-point LINE writing.",
        "Derived from tests/fixtures/jrc_usercharts/L01_base.uchm.",
    ],
}


DONOR_DESCRIPTORS: dict[str, dict[str, object]] = {
    "LINE_BASIC": LINE_BASIC_DONOR,
}


def get_donor_descriptor(family_name: str) -> dict[str, object]:
    normalized = " ".join((family_name or "").upper().split())
    try:
        return DONOR_DESCRIPTORS[normalized]
    except KeyError as exc:
        raise KeyError(f"Unknown UCHM donor descriptor: {family_name}") from exc


def get_line_basic_descriptor() -> dict[str, object]:
    return get_donor_descriptor("LINE_BASIC")


TEXT_BASIC_DONOR: dict[str, object] = {
    "family_name": "TEXT_BASIC",
    "donor_file": _fixture_path("tests", "fixtures", "jrc_usercharts", "A6_free_text.uchm"),
    "family_constant": TEXT_BASIC,
    "object_kind": "TEXT",
    "supported_vertex_count": 1,
    "text_offsets": {
        "metadata_word": 0x124,
        "text_start": 0x128,
        "text_capacity": 9,
    },
    "scale_offsets": {
        "min": 0x0D4,
        "max": 0x0D8,
    },
    "anchor_offsets": {
        "lat": 0x168,
        "lon": 0x16C,
    },
    "default_metadata_word": 0x00001409,
    "default_scamin": 75_000_000,
    "default_scamax": 1_000,
    "degree_scale": 1_536_000,
    "notes": [
        "Minimal donor for native single TEXT writing.",
        "Derived from tests/fixtures/jrc_usercharts/A6_free_text.uchm.",
        "Text payload region proven with ASCII content up to 9 bytes in donor evidence.",
        "Rotation/size/color variants exist but are not yet generalized in this first path.",
    ],
}


POINT_BASIC_DONOR: dict[str, object] = {
    "family_name": "POINT_BASIC",
    "donor_file": _fixture_path("tests", "fixtures", "jrc_usercharts", "N01_native_object.uchm"),
    "family_constant": POINT_BASIC,
    "object_kind": "POINT",
    "supported_vertex_count": 1,
    "symbol_control_offset": 0x12F,
    "allowed_symbol_controls": [0x08, 0x09],
    "default_symbol_control": 0x08,
    "symbol_control_by_kind": {
        "X": 0x08,
        "DEFAULT": 0x08,
        "UNKNOWN": 0x08,
        "X_ALT09": 0x09,
    },
    "scale_offsets": {
        "min": 0x0D4,
        "max": 0x0D8,
    },
    "geometry_offsets": {
        "lat": 0x130,
        "lon": 0x134,
    },
    "degree_scale": 1_536_000,
    "notes": [
        "Proven minimal donor for native 1-point POINT writing.",
        "Derived from tests/fixtures/jrc_usercharts/N01_native_object.uchm.",
        "Supports only two proven symbol-control lanes: 0x08 and 0x09.",
        "X_ALT09 is a cautious internal alias for the observed 0x09 variant; semantic symbol meaning is not yet proven.",
        "Leaves unresolved 0x0CC..0x0CF donor bytes untouched.",
    ],
}


DONOR_DESCRIPTORS["POINT_BASIC"] = POINT_BASIC_DONOR
DONOR_DESCRIPTORS["TEXT_BASIC"] = TEXT_BASIC_DONOR


def get_point_basic_descriptor() -> dict[str, object]:
    return get_donor_descriptor("POINT_BASIC")


def get_text_basic_descriptor() -> dict[str, object]:
    return get_donor_descriptor("TEXT_BASIC")
