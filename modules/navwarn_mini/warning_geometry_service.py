from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .extract_warning import extract_vertices_and_geom
from .models import Geometry, LatLon, OffshoreObject
from .platform_registry import resolve_platform_identity


_PLATFORM_SPLIT_RE = re.compile(
    r"\b(MODU|DRILLING RIG|SEMI[- ]?SUBMERSIBLE|JACK[- ]?UP|PLATFORM|FPSO|FSO)\b",
    re.IGNORECASE,
)

_PLATFORM_NAME_RE = re.compile(
    r"\b(MODU|DRILLING RIG|SEMI[- ]?SUBMERSIBLE|JACK[- ]?UP|PLATFORM|FPSO|FSO)\s+([A-Z0-9.\- ]{1,40})",
    re.IGNORECASE,
)


@dataclass
class GeometryResolution:
    verts: list[tuple[float, float]]
    geom_type: str
    offshore_objects: list[OffshoreObject]


def split_platform_sections(text: str) -> list[str]:
    parts = _PLATFORM_SPLIT_RE.split(text)
    sections: list[str] = []
    current = ""
    saw_keyword = False

    for piece in parts:
        piece = piece.strip()
        if not piece:
            continue

        if _PLATFORM_SPLIT_RE.fullmatch(piece):
            if current.strip() and saw_keyword:
                sections.append(current.strip())
            current = piece
            saw_keyword = True
        else:
            current = f"{current} {piece}".strip()

    if current.strip() and saw_keyword:
        sections.append(current.strip())

    return sections


def detect_platform_list_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if re.match(
            r"^[A-Z][A-Z0-9.\-]{0,15}\s+\d{1,2}[-\s]\d{1,2}(\.\d+)?[NS]\s+\d{1,3}[-\s]\d{1,2}(\.\d+)?[EW]",
            line,
            re.IGNORECASE,
        ):
            lines.append(line)

    return lines


def split_platform_sections_fallback(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    coord_like = re.compile(
        r"\d{1,2}[- ]\d{1,2}(?:\.\d+)?\s*[NS].*\d{1,3}[- ]\d{1,2}(?:\.\d+)?\s*[EW]",
        re.IGNORECASE,
    )

    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        has_coord = bool(coord_like.search(line))

        if has_coord and current:
            sections.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append(" ".join(current).strip())

    return [s for s in sections if coord_like.search(s)]


def extract_platform_name(section: str) -> Optional[str]:
    m = _PLATFORM_NAME_RE.search(section.upper())
    if not m:
        return None

    name = m.group(2).strip()

    name = re.sub(
        r"\s+\d{1,2}[- ]\d{1,2}(?:\.\d+)?[NS]\s+\d{1,3}[- ]\d{1,2}(?:\.\d+)?[EW]\.?\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()

    name = re.sub(
        r"\b(OPERATING|DRILLING|AT|IN|LOCATED|ON LOCATION|ESTABLISHED|WORKING)\b.*$",
        "",
        name,
    ).strip()

    name = name.strip(" .;,:-")
    name = " ".join(name.split())

    if re.fullmatch(r"[A-Z]{1,8}", name):
        return name
    if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,15}", name):
        return name

    if len(name) >= 3:
        return name

    return None


def extract_platform_name_fallback(section: str) -> Optional[str]:
    m = re.match(r"^[\s.;,:-]*([A-Z][A-Z0-9.\-]{0,15})\b", section.upper().strip())
    if not m:
        return None

    name = m.group(1).strip(" .;,:-")
    return name or None


def resolve_warning_geometry(
    *,
    raw_text: str,
    warning_id: str,
    navarea: str,
    created_utc: str,
    interp_warning_type: str,
    interp_geometry_blocks,
    output_root: str,
) -> GeometryResolution:
    platform_sections = split_platform_sections(raw_text)

    if len(platform_sections) <= 1:
        fallback_sections = split_platform_sections_fallback(raw_text)
        if len(fallback_sections) > len(platform_sections):
            platform_sections = fallback_sections

    if len(platform_sections) <= 1:
        list_lines = detect_platform_list_lines(raw_text)
        if len(list_lines) >= 2:
            platform_sections = list_lines

    is_offshore_warning = (
        interp_warning_type in ("MODU", "DRILLING", "PLATFORM")
        or bool(platform_sections)
        or any(
            kw in raw_text.upper()
            for kw in (
                "MODU",
                "DRILLING RIG",
                "SEMI-SUBMERSIBLE",
                "JACK-UP",
                "JACK UP",
                "PLATFORM",
                "FPSO",
                "FSO",
            )
        )
    )

    offshore_objects: list[OffshoreObject] = []

    if is_offshore_warning:
        root = Path(output_root)
        registry_csv = root / "NAVWARN" / "platform_registry.csv"

        if platform_sections:
            for sec in platform_sections:
                sec_name = extract_platform_name(sec) or extract_platform_name_fallback(sec)
                sec_verts, _ = extract_vertices_and_geom(sec)

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
                    platform_type=interp_warning_type,
                    geometry=sec_geometry,
                    warning_id=warning_id,
                    observed_utc=created_utc,
                )

                offshore_objects.append(
                    OffshoreObject(
                        platform_id=ident["platform_id"],
                        platform_name=sec_name,
                        platform_type=interp_warning_type,
                        match_status=ident["match_status"],
                        identity_confidence=ident["identity_confidence"],
                        tce_thread_id=ident["tce_thread_id"],
                        geometry=sec_geometry,
                        source_warning_id=warning_id,
                        source_navarea=navarea,
                    )
                )

        if not offshore_objects:
            coords = []
            for block in interp_geometry_blocks:
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
                    platform_name=extract_platform_name(raw_text) or extract_platform_name_fallback(raw_text),
                    platform_type=interp_warning_type,
                    geometry=base_geometry,
                    warning_id=warning_id,
                    observed_utc=created_utc,
                )

                offshore_objects.append(
                    OffshoreObject(
                        platform_id=ident["platform_id"],
                        platform_name=extract_platform_name(raw_text) or extract_platform_name_fallback(raw_text),
                        platform_type=interp_warning_type,
                        match_status=ident["match_status"],
                        identity_confidence=ident["identity_confidence"],
                        tce_thread_id=ident["tce_thread_id"],
                        geometry=base_geometry,
                        source_warning_id=warning_id,
                        source_navarea=navarea,
                    )
                )

        if offshore_objects:
            verts = [
                (obj.geometry.vertices[0].lat, obj.geometry.vertices[0].lon)
                for obj in offshore_objects
                if obj.geometry.vertices
            ]
            geom_type = "POINT"
            return GeometryResolution(
                verts=verts,
                geom_type=geom_type,
                offshore_objects=offshore_objects,
            )

        return GeometryResolution(
            verts=[],
            geom_type="POINT",
            offshore_objects=offshore_objects,
        )

    verts, geom_type = extract_vertices_and_geom(raw_text)
    return GeometryResolution(
        verts=verts,
        geom_type=geom_type,
        offshore_objects=[],
    )
