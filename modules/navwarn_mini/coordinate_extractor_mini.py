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
        (?P<lat>
            [NS]?\s*
            \d{1,3}
            (?:[\-\s°]\d{1,2}(?:\.\d+)?)      # minutes, decimal allowed here
            (?:[\-\s]\d{1,2}(?:\.\d+)?)?      # optional seconds
            \s*[NS]?
        )
        [,\s/;]+
        (?P<lon>
            [EW]?\s*
            \d{1,3}
            (?:[\-\s°]\d{1,2}(?:\.\d+)?)      # minutes, decimal allowed here
            (?:[\-\s]\d{1,2}(?:\.\d+)?)?      # optional seconds
            \s*[EW]?
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @classmethod
    def extract(cls, text: str) -> List[Coordinate]:
        results: List[Coordinate] = []

        for match in cls.MASTER_PATTERN.finditer(text or ""):
            raw = match.group(0)

            lat = cls._parse_component(match.group("lat"), True)
            lon = cls._parse_component(match.group("lon"), False)

            if lat is None or lon is None:
                continue

            if abs(lat) <= 90 and abs(lon) <= 180:
                results.append(Coordinate(lat, lon, raw))

        return results

    @staticmethod
    def _parse_component(text: str, is_lat: bool) -> Optional[float]:

        text = (text or "").upper().strip()

        hemi = 1
        if ("S" in text and is_lat) or ("W" in text and not is_lat):
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

        if len(numbers) == 2:
            deg = float(numbers[0])
            minutes = float(numbers[1])
            return hemi * (deg + minutes / 60)

        if len(numbers) >= 3:
            deg = float(numbers[0])
            minutes = float(numbers[1])
            seconds = float(numbers[2])
            return hemi * (deg + minutes / 60 + seconds / 3600)

        return None