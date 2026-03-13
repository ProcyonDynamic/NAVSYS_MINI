from __future__ import annotations
import re
from typing import List, Tuple

from .coordinate_extractor_mini import CoordinateExtractor
from modules.navwarn_mini.coord_repair import repair_split_coords

def normalize_coord_text(s: str) -> str:
    if not s:
        return ""

    s = repair_split_coords(s)

    s = (
        s.replace("°", " ")
         .replace("'", " ")
         .replace('"', " ")
         .replace("/", " ")
    )

    s = re.sub(r"(\d)([NSEW])", r"\1 \2", s)
    s = re.sub(r"([NSEW])(\d)", r"\1 \2", s)

    s = re.sub(r"(?<=\d)-(?=\d)", " ", s)

    s = re.sub(r"\s+", " ", s)

    return s.strip()


def extract_vertices_from_text(text: str) -> List[Tuple[float, float]]:

    text = normalize_coord_text(text)

    verts: List[Tuple[float, float]] = []
    seen = set()

    for c in CoordinateExtractor.extract(text):

        pair = (round(c.lat, 8), round(c.lon, 8))

        if pair not in seen:
            seen.add(pair)
            verts.append((c.lat, c.lon))

    return verts