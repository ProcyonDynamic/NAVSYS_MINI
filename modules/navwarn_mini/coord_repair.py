from __future__ import annotations

import re


_LAT = r"\d{1,2}\s+\d{1,2}(?:\.\d+)?\s*[NS]"
_LON = r"\d{1,3}\s+\d{1,2}(?:\.\d+)?\s*[EW]"


def _compact_ws(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_hemisphere_breaks(text: str) -> str:
    t = text

    # digit -> newline -> hemisphere
    t = re.sub(r"(\d)\s*\n\s*([NSEWnsew])\b", r"\1 \2", t)

    # hemisphere -> newline -> digit
    t = re.sub(r"\b([NSEWnsew])\s*\n\s*(\d)", r"\1 \2", t)

    return t


def repair_deg_min_breaks(text: str) -> str:
    t = text

    # join 2-part coordinate where degrees are on one line and minutes/hemi on the next
    t = re.sub(
        r"(\d{1,3})\s*\n\s*(\d{1,2}(?:\.\d+)?)\s*([NSEWnsew])\b",
        r"\1 \2 \3",
        t,
    )

    # join deg/min split with explicit punctuation/spacing noise
    t = re.sub(
        r"(\d{1,3})\s*[-°'\"]?\s*\n\s*(\d{1,2}(?:\.\d+)?)\s*([NSEWnsew])\b",
        r"\1 \2 \3",
        t,
    )

    return t


def repair_lat_lon_pair_breaks(text: str) -> str:
    t = text

    t = re.sub(
        rf"({_LAT})\s*\n\s*({_LON})",
        r"\1 \2",
        t,
        flags=re.IGNORECASE,
    )

    return t


def repair_compact_coord_forms(text: str) -> str:
    t = text

    # latitude compact: ddmm.mH -> dd mm.m H
    t = re.sub(
        r"(?<!\d)(\d{2})(\d{2}\.\d+)\s*([NSns])\b",
        r"\1 \2 \3",
        t,
    )

    # longitude compact: dddmm.mH -> ddd mm.m H
    t = re.sub(
        r"(?<!\d)(\d{3})(\d{2}\.\d+)\s*([EWew])\b",
        r"\1 \2 \3",
        t,
    )

    return t


def tighten_hemisphere_suffixes(text: str) -> str:
    """
    Normalize:
      25 26.8 N -> 25 26.8N
      091 36.6 W -> 091 36.6W
    """
    t = text

    t = re.sub(r"(\d{1,2}\s+\d{1,2}(?:\.\d+)?)\s+([NSns])\b", r"\1\2", t)
    t = re.sub(r"(\d{1,3}\s+\d{1,2}(?:\.\d+)?)\s+([EWew])\b", r"\1\2", t)

    return t


def repair_split_coords(text: str) -> str:
    if not text:
        return ""

    t = text.replace("\r\n", "\n").replace("\r", "\n")

    t = repair_hemisphere_breaks(t)
    t = repair_deg_min_breaks(t)
    t = repair_compact_coord_forms(t)
    t = repair_lat_lon_pair_breaks(t)
    t = tighten_hemisphere_suffixes(t)

    t = _compact_ws(t)
    return t