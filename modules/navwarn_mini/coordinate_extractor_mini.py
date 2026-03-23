from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Coordinate:
    lat: float
    lon: float
    raw: str


class CoordinateExtractor:

    MASTER_PATTERN = re.compile(
        r"""
        (?<![A-Z0-9])
        (?P<lat>
            [NS]?\s*
            \d{1,3}
            (?:[\-\s°]\d{1,2}(?:\.\d+)?)
            (?:[\-\s]\d{1,2}(?:\.\d+)?)?
            \s*[NS]?
        )
        [,\s/;]+
        (?P<lon>
            [EW]?\s*
            \d{1,3}
            (?:[\-\s°]\d{1,2}(?:\.\d+)?)
            (?:[\-\s]\d{1,2}(?:\.\d+)?)?
            \s*[EW]?
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @classmethod
    def extract(cls, text: str) -> List[Coordinate]:
        results: List[Coordinate] = []
        seen: set[tuple[float, float]] = set()

        for match in cls.MASTER_PATTERN.finditer(text or ""):
            raw = match.group(0)

            lat = cls._parse_component(match.group("lat"), True)
            lon = cls._parse_component(match.group("lon"), False)

            if lat is None or lon is None:
                continue

            if abs(lat) <= 90 and abs(lon) <= 180:
                key = (round(lat, 8), round(lon, 8))
                if key not in seen:
                    seen.add(key)
                    results.append(Coordinate(lat, lon, raw))

        return results

    @staticmethod
    def _parse_component(text: str, is_lat: bool) -> Optional[float]:
        text = (text or "").upper().strip()

        hemi = 1
        t = text.strip()

        if is_lat:
            if t.startswith("S") or t.endswith("S"):
                hemi = -1
        else:
            if t.startswith("W") or t.endswith("W"):
                hemi = -1

        clean = (
            text.replace("-", " ")
                .replace("°", " ")
                .replace("'", " ")
                .replace('"', " ")
        )

        numbers = re.findall(r"\d+(?:\.\d+)?", clean)

        if not numbers:
            return None

        if len(numbers) == 1:
            deg = float(numbers[0])
            return hemi * deg

        if len(numbers) == 2:
            deg = float(numbers[0])
            minutes = float(numbers[1])
            return hemi * (deg + minutes / 60.0)

        deg = float(numbers[0])
        minutes = float(numbers[1])
        seconds = float(numbers[2])
        return hemi * (deg + minutes / 60.0 + seconds / 3600.0)