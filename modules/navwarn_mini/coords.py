from __future__ import annotations

import re
from typing import List, Tuple


# -------------------------
# Normalization (OCR-safe)
# -------------------------

def normalize_coord_text(s: str) -> str:
    """
    Normalize coordinate separators so we can parse NAVAREA formats and OCR noise.
    - Converts unicode dashes to '-'
    - Converts degree/minute/second symbols to spaces
    - Converts '-' separators into spaces (NAVAREA style 24-21.874N)
    - Collapses whitespace
    """
    if not s:
        return ""

    # OCR dash variants
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")

    # common symbols -> spaces
    s = s.replace("º", "°")
    s = s.replace("°", " ")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("'", " ")
    s = s.replace('"', " ")
    s = s.replace("”", '"').replace("“", '"')

    # NAVAREA hyphen separators become spaces
    s = s.replace("-", " ")

    # make commas harmless
    s = s.replace(";", " ").replace(",", " ")
    
    # Ensure hemisphere letters are separated: "21.874N" -> "21.874 N"
    s = re.sub(r"(\d)([NS])\b", r"\1 \2", s, flags=re.IGNORECASE)
    s = re.sub(r"(\d)([EW])\b", r"\1 \2", s, flags=re.IGNORECASE)
    
    # collapse whitespace
    s = " ".join(s.split())
    return s

def cleanup_ocr_for_coords(raw_text: str) -> str:
    """
    Fix common OCR mistakes *in coordinate-looking substrings*.

    We avoid global replacements that could damage non-coordinate text.
    Strategy:
    - Work line-by-line
    - If a line looks like it contains coordinates, apply targeted fixes
    """
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    out_lines = []

    # A line is "coord-ish" if it contains hemisphere letters near digits.
    # Treat VV as W-like because OCR often reads W as VV
    coordish = re.compile(r"\d.*[NSns].*\d.*([EWew]|VV|vv)")

    for ln in text.split("\n"):
        s = ln

        if coordish.search(s):
            # Normalize weird dashes (OCR)
            s = s.replace("–", "-").replace("—", "-").replace("−", "-")
            s = re.sub(r"\bVV\b", "W", s, flags=re.IGNORECASE)
            
            s = s.replace("VV", "W")
            # OCR sometimes reads W as VV
            s = re.sub(r"\bVV\b", "W", s, flags=re.IGNORECASE)
            s = s.replace("VV", "W")

            # OCR sometimes reads N as H (rare), or S as 5 (rare). Do only near hemisphere slots.
            # Replace digit+letter patterns like '21.874H' -> '21.874N' if it makes sense.
            s = re.sub(r"(\d)\s*H\b", r"\1 N", s, flags=re.IGNORECASE)

            # Fix '5' used instead of 'S' when immediately after minutes/seconds
            s = re.sub(r"(\d)\s*5\b", r"\1 S", s)

            # Fix 'O' for 0 in numeric runs (e.g. 094 becomes O94 or 09O)
            def _o_to_zero_in_numbers(m):
                token = m.group(0)
                return token.replace("O", "0").replace("o", "0")

            s = re.sub(r"[0-9Oo]{2,}", _o_to_zero_in_numbers, s)

            # Fix 'I'/'l' for 1 in numeric runs (common in OCR)
            def _il_to_one_in_numbers(m):
                token = m.group(0)
                token = token.replace("I", "1").replace("l", "1")
                return token

            s = re.sub(r"[0-9Il]{2,}", _il_to_one_in_numbers, s)

            # Fix missing hemisphere spacing like "21.874N094" -> "21.874N 094"
            s = re.sub(r"([NSns])(\d{2,3})", r"\1 \2", s)
            s = re.sub(r"([EWew])(\d{1,2})", r"\1 \2", s)

        out_lines.append(s)

    return "\n".join(out_lines)




# -------------------------
# Block detection (Stage 1)
# -------------------------

BLOCK_TRIGGERS = [
    "IN POSITION",
    "IN POSN",
    "POSITION",
    "POSN",
    "VICINITY",
    "BOUND BY",
    "BOUNDED BY",
    "AREA BOUND BY",
    "AREAS BOUND BY",
    "WITHIN",
    "CENTERED",
    "CENTRED",
]


def extract_coordinate_blocks(raw_text: str) -> List[str]:
    """
    Stage 1:
    Return candidate text blocks that likely contain coordinates.

    Strategy:
    - Split into lines
    - Start a block when a trigger phrase appears OR a line contains an obvious coordinate token.
    - Continue collecting subsequent lines until a blank line or a "hard stop" marker.
    """
    if not raw_text:
        return []

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]

    blocks: List[str] = []
    cur: List[str] = []

    def has_trigger(line: str) -> bool:
        u = line.upper()
        return any(t in u for t in BLOCK_TRIGGERS)

    # A crude “coord-like” detector (works before normalization)
    coord_like = re.compile(r"\d{1,2}[-\s]\d{1,2}(\.\d+)?\s*[NSns].*\d{1,3}[-\s]\d{1,2}(\.\d+)?\s*[EWew]")

    hard_stop = re.compile(r"^(END|NNNN|\*{3,}|={3,})\s*$", re.IGNORECASE)

    for ln in lines:
        if hard_stop.match(ln) or ln == "":
            if cur:
                blocks.append("\n".join(cur).strip())
                cur = []
            continue

        start_block = has_trigger(ln) or bool(coord_like.search(ln))
        if start_block and not cur:
            cur.append(ln)
        elif cur:
            cur.append(ln)
        else:
            # Not in a block; ignore.
            pass

    if cur:
        blocks.append("\n".join(cur).strip())

    return blocks


# -------------------------
# Coordinate extraction (Stage 2)
# -------------------------

def _dm_to_deg(deg: float, minutes: float, hemi: str, is_lat: bool) -> float:
    v = abs(deg) + (minutes / 60.0)
    hemi = hemi.upper()
    if is_lat:
        if hemi == "S":
            v = -v
    else:
        if hemi == "W":
            v = -v
    return v


def _dms_to_deg(deg: float, minutes: float, seconds: float, hemi: str, is_lat: bool) -> float:
    v = abs(deg) + (minutes / 60.0) + (seconds / 3600.0)
    hemi = hemi.upper()
    if is_lat:
        if hemi == "S":
            v = -v
    else:
        if hemi == "W":
            v = -v
    return v


# After normalization, separators are spaces, so we parse:
# DM:  DD MM.mmm N  DDD MM.mmm W
DM_NORM = re.compile(
    r"""
    (?P<lat_deg>\d{1,2})\s+(?P<lat_min>\d{1,2}(?:\.\d+)?)\s+(?P<lat_hem>[NS])
    \s+
    (?P<lon_deg>\d{1,3})\s+(?P<lon_min>\d{1,2}(?:\.\d+)?)\s+(?P<lon_hem>[EW])
    """,
    re.VERBOSE | re.IGNORECASE
)

# DMS: DD MM SS N  DDD MM SS W
DMS_NORM = re.compile(
    r"""
    (?P<lat_deg>\d{1,2})\s+(?P<lat_min>\d{1,2})\s+(?P<lat_sec>\d{1,2}(?:\.\d+)?)\s+(?P<lat_hem>[NS])
    \s+
    (?P<lon_deg>\d{1,3})\s+(?P<lon_min>\d{1,2})\s+(?P<lon_sec>\d{1,2}(?:\.\d+)?)\s+(?P<lon_hem>[EW])
    """,
    re.VERBOSE | re.IGNORECASE
)

# Decimal degrees fallback (strict):
# Requires either:
#  - comma-separated "lat, lon"
#  - OR explicit signs "+/-" on both numbers
DEC = re.compile(
    r"""
    (?:
        (?P<lat1>[+-]\d{1,2}(?:\.\d+)?)\s+(?P<lon1>[+-]\d{1,3}(?:\.\d+)?)
        |
        (?P<lat2>[+-]?\d{1,2}(?:\.\d+)?)\s*,\s*(?P<lon2>[+-]?\d{1,3}(?:\.\d+)?)
    )
    """,
    re.VERBOSE
)

def extract_vertices_from_text(raw_text: str) -> List[Tuple[float, float]]:
    
    """
    Two-stage extractor:
    1) find candidate blocks likely to contain coordinates
    2) normalize + extract DM/DMS first, then decimal degrees fallback

    Returns ordered list of (lat, lon) in decimal degrees.
    """
    
    if not raw_text:
        return []
    
    raw_text = cleanup_ocr_for_coords(raw_text)
    blocks = extract_coordinate_blocks(raw_text)
    if not blocks:
        blocks = [raw_text]  # fallback: parse everything

    verts: List[Tuple[float, float]] = []

    for blk in blocks:
        s = normalize_coord_text(blk).upper()

        # Prefer DMS first (more specific) then DM
        for m in DMS_NORM.finditer(s):
            lat = _dms_to_deg(
                float(m.group("lat_deg")),
                float(m.group("lat_min")),
                float(m.group("lat_sec")),
                m.group("lat_hem"),
                is_lat=True,
            )
            lon = _dms_to_deg(
                float(m.group("lon_deg")),
                float(m.group("lon_min")),
                float(m.group("lon_sec")),
                m.group("lon_hem"),
                is_lat=False,
            )
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                verts.append((lat, lon))

        if verts:
            continue  # if we found DMS in this block, don't also DM-match it

        for m in DM_NORM.finditer(s):
            lat = _dm_to_deg(
                float(m.group("lat_deg")),
                float(m.group("lat_min")),
                m.group("lat_hem"),
                is_lat=True,
            )
            lon = _dm_to_deg(
                float(m.group("lon_deg")),
                float(m.group("lon_min")),
                m.group("lon_hem"),
                is_lat=False,
            )
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                verts.append((lat, lon))

    # Fallback: only if there are NO hemisphere letters anywhere.
    # This prevents DM/DMS coord text being misread as decimal degree pairs.
    if not verts:
        u = raw_text.upper()
        if not any(h in u for h in ("N", "S", "E", "W")):
            s = normalize_coord_text(raw_text)
            for m in DEC.finditer(s):
                lat = m.group("lat1") or m.group("lat2")
                lon = m.group("lon1") or m.group("lon2")
                if lat is None or lon is None:
                    continue
                latf = float(lat)
                lonf = float(lon)
                if -90 <= latf <= 90 and -180 <= lonf <= 180:
                    verts.append((latf, lonf))
    return verts