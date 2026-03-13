from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from .models import TextObject, LatLon


@dataclass(frozen=True)
class VertexTextPolicy:
    show_platform_name: bool = True
    show_warning_id: bool = True
    show_note: bool = True

    name_size: int = 12
    id_size: int = 10
    note_size: int = 9

    name_rotation_deg: float = 0.0
    id_rotation_deg: float = 0.0
    note_rotation_deg: float = 0.0

    # simple chart offsets in degrees for now; later config/editor can replace
    name_dx: float = 0.06
    name_dy: float = 0.03
    id_dx: float = 0.06
    id_dy: float = 0.00
    note_dx: float = 0.06
    note_dy: float = -0.03


def short_warning_id(warning_id: str) -> str:
    parts = " ".join(warning_id.upper().split()).split()
    # NAVAREA IV 123/26 -> IV 123/26
    if len(parts) >= 3 and parts[0] == "NAVAREA":
        return f"{parts[1]} {parts[2]}"
    return warning_id.strip()


def build_vertex_texts_for_platform(
    *,
    vertex: LatLon,
    warning_id: str,
    platform_name: Optional[str],
    note_text: Optional[str] = None,
    policy: Optional[VertexTextPolicy] = None,
) -> List[TextObject]:
    p = policy or VertexTextPolicy()
    texts: List[TextObject] = []

    if p.show_platform_name and platform_name:
        texts.append(
            TextObject(
                lat=vertex.lat + p.name_dy,
                lon=vertex.lon + p.name_dx,
                rotation_deg=p.name_rotation_deg,
                size=p.name_size,
                text=platform_name,
            )
        )

    if p.show_warning_id:
        texts.append(
            TextObject(
                lat=vertex.lat + p.id_dy,
                lon=vertex.lon + p.id_dx,
                rotation_deg=p.id_rotation_deg,
                size=p.id_size,
                text=short_warning_id(warning_id),
            )
        )

    if p.show_note and note_text:
        texts.append(
            TextObject(
                lat=vertex.lat + p.note_dy,
                lon=vertex.lon + p.note_dx,
                rotation_deg=p.note_rotation_deg,
                size=p.note_size,
                text=note_text,
            )
        )

    return texts