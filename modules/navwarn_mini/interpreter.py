from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .models import Geometry, LatLon, Validity, WarningDraft


# ---------------------------------------------------------------------------
# Interpretation result model
# ---------------------------------------------------------------------------

WarningType = str
PhrasePattern = str


@dataclass(frozen=True)
class InterpretationResult:
    """
    Structured result of the NavWarn interpretation layer.

    This sits *before* route-distance / risk scoring and *after* raw message
    extraction. It is designed to preserve both machine output and operator
    review context.
    """
    normalized_title: str
    normalized_body: str
    warning_type: WarningType
    phrase_pattern: PhrasePattern
    geometry: Geometry
    validity: Validity
    confidence: float
    confidence_breakdown: dict[str, float]
    errors: List[str]


# ---------------------------------------------------------------------------
# Phrase library
# ---------------------------------------------------------------------------

_PHRASE_LIBRARY: list[tuple[str, str, str]] = [
    (r"\bIN\s+AREA\s+BOUNDED\s+BY\b", "AREA_BOUNDED_BY", "AREA"),
    (r"\bAREA\s+BOUNDED\s+BY\b", "AREA_BOUNDED_BY", "AREA"),
    (r"\bBOUNDED\s+BY\b", "AREA_BOUNDED_BY", "AREA"),
    (r"\bALONG\s+TRACKLINE\s+JOINING\b", "ALONG_TRACKLINE_JOINING", "LINE"),
    (r"\bALONG\s+LINE\s+JOINING\b", "ALONG_LINE_JOINING", "LINE"),
    (r"\bJOINING\b", "JOINING", "LINE"),
    (r"\bBETWEEN\b", "BETWEEN", "LINE"),
    (r"\bCENTERED\s+ON\b", "CENTERED_ON", "POINT"),
    (r"\bCENTRED\s+ON\b", "CENTERED_ON", "POINT"),
    (r"\bWITHIN\b", "WITHIN", "POINT"),
    (r"\bVICINITY\s+OF\b", "VICINITY_OF", "POINT"),
]


# ---------------------------------------------------------------------------
# Warning type keywords
# ---------------------------------------------------------------------------

_WARNING_TYPE_RULES: list[tuple[WarningType, tuple[str, ...]]] = [
    ("MILITARY_EXERCISE", ("MILITARY EXERCISE", "GUNNERY", "FIRING", "NAVAL EXERCISE")),
    ("DRILLING", ("DRILLING", "DRILL SHIP", "RIG", "OFFSHORE INSTALLATION")),
    ("SUBMARINE_CABLE", ("SUBMARINE CABLE", "CABLE LAYING", "CABLE WORK")),
    ("SURVEY", ("SURVEY", "SEISMIC", "RESEARCH VESSEL")),
    ("DERELICT", ("DERELICT", "ADRIFT OBJECT", "ADRIFT", "FLOATING OBJECT")),
    ("WRECK", ("WRECK", "SUNKEN", "OBSTRUCTION")),
    ("PIRACY_SECURITY", ("PIRACY", "ARMED ROBBERY", "SECURITY INCIDENT")),
    ("ROCKET_LAUNCH", ("ROCKET", "MISSILE", "SPACE LAUNCH", "DEBRIS")),
    ("AIDS_TO_NAVIGATION", ("LIGHT UNLIT", "BUOY", "BEACON", "AID TO NAVIGATION")),
    ("GENERAL_HAZARD", ("HAZARD", "DANGEROUS", "CAUTION", "MARINERS ARE ADVISED")),
]


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Conservative normalizer for NAVWARN text.

    Goals:
    - preserve semantics
    - reduce OCR / formatting noise
    - improve regex stability
    """
    if not text:
        return ""

    cleaned = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    cleaned = cleaned.replace("\u00b0", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.upper().strip()

    # OCR and formatting repair for common coordinate separators.
    cleaned = re.sub(r"(\d)([NS])(\d)", r"\1 \2 \3", cleaned)
    cleaned = re.sub(r"(\d)([EW])(\d)", r"\1 \2 \3", cleaned)
    cleaned = re.sub(r"(\d)-(\d{2}\.\d)([NSEW])", r"\1 \2 \3", cleaned)
    cleaned = re.sub(r"(\d{1,3})\s*[-/]\s*(\d{1,2}(?:\.\d+)?)\s*([NSEW])", r"\1 \2 \3", cleaned)

    return cleaned


# ---------------------------------------------------------------------------
# Coordinate detection
# ---------------------------------------------------------------------------

_COORD_PATTERNS = [
    # 12 34.5N 045 21.3W
    re.compile(
        r"(?P<lat_deg>\d{1,2})\s+(?P<lat_min>\d{1,2}(?:\.\d+)?)\s*(?P<lat_hemi>[NS])"
        r"[\s,;/]+"
        r"(?P<lon_deg>\d{1,3})\s+(?P<lon_min>\d{1,2}(?:\.\d+)?)\s*(?P<lon_hemi>[EW])"
    ),
    # 1234.5N 04521.3W
    re.compile(
        r"(?P<lat_comp>\d{4,5}(?:\.\d+)?)\s*(?P<lat_hemi>[NS])"
        r"[\s,;/]+"
        r"(?P<lon_comp>\d{5,6}(?:\.\d+)?)\s*(?P<lon_hemi>[EW])"
    ),
]


def _compact_to_deg_min(value: str, is_lon: bool) -> Tuple[int, float]:
    digits = value.split(".")[0]
    frac = value[len(digits):]

    deg_len = 3 if is_lon else 2
    deg = int(digits[:deg_len])
    minute_str = digits[deg_len:] + frac
    minutes = float(minute_str)

    return deg, minutes


def _deg_min_to_decimal(deg: int, minutes: float, hemi: str) -> float:
    decimal = deg + (minutes / 60.0)
    if hemi in ("S", "W"):
        decimal *= -1.0
    return round(decimal, 8)


def detect_coordinates(text: str) -> List[LatLon]:
    """
    Extract all coordinate pairs found in normalized text.

    Notes:
    - intentionally conservative
    - preserves order of appearance
    - does not deduplicate aggressively
    """
    found: List[LatLon] = []

    for pattern in _COORD_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groupdict()

            if "lat_deg" in groups and groups.get("lat_deg"):
                lat_deg = int(groups["lat_deg"])
                lat_min = float(groups["lat_min"])
                lon_deg = int(groups["lon_deg"])
                lon_min = float(groups["lon_min"])
            else:
                lat_deg, lat_min = _compact_to_deg_min(groups["lat_comp"], is_lon=False)
                lon_deg, lon_min = _compact_to_deg_min(groups["lon_comp"], is_lon=True)

            lat = _deg_min_to_decimal(lat_deg, lat_min, groups["lat_hemi"])
            lon = _deg_min_to_decimal(lon_deg, lon_min, groups["lon_hemi"])
            found.append(LatLon(lat=lat, lon=lon))

    return found


# ---------------------------------------------------------------------------
# Phrase parsing / type classification
# ---------------------------------------------------------------------------

def classify_warning(text: str) -> WarningType:
    for warning_type, keywords in _WARNING_TYPE_RULES:
        for kw in keywords:
            if kw in text:
                return warning_type
    return "UNCLASSIFIED"


def detect_phrase_pattern(text: str) -> Tuple[PhrasePattern, Optional[str]]:
    for pattern, phrase_name, implied_geom in _PHRASE_LIBRARY:
        if re.search(pattern, text):
            return phrase_name, implied_geom
    return "UNSPECIFIED", None


# ---------------------------------------------------------------------------
# Validity extraction
# ---------------------------------------------------------------------------

_UFN_RE = re.compile(r"\bUFN\b|\bUNTIL\s+FURTHER\s+NOTICE\b")


def parse_validity(text: str) -> Validity:
    """
    Minimal validity parser v1.

    We keep this intentionally simple for now:
    - detect UFN
    - leave start/end parsing to a later dedicated time parser
    """
    ufn = bool(_UFN_RE.search(text))
    return Validity(start_utc=None, end_utc=None, ufn=ufn)


# ---------------------------------------------------------------------------
# Geometry builder
# ---------------------------------------------------------------------------

def build_geometry(
    *,
    coords: List[LatLon],
    phrase_pattern: PhrasePattern,
    implied_geom: Optional[str],
) -> Geometry:
    """
    Geometry inference rules.

    Current policy:
    - explicit phrase wins
    - fallback from coordinate count
    """
    if implied_geom == "AREA":
        return Geometry(geom_type="AREA", vertices=coords, closed=True)
    if implied_geom == "LINE":
        return Geometry(geom_type="LINE", vertices=coords, closed=False)
    if implied_geom == "POINT":
        first = coords[:1]
        return Geometry(geom_type="POINT", vertices=first, closed=False)

    # Fallback heuristics when phrase is weak / missing.
    if len(coords) >= 3:
        return Geometry(geom_type="AREA", vertices=coords, closed=True)
    if len(coords) == 2:
        return Geometry(geom_type="LINE", vertices=coords, closed=False)
    if len(coords) == 1:
        return Geometry(geom_type="POINT", vertices=coords, closed=False)

    return Geometry(geom_type="POINT", vertices=[], closed=False)


# ---------------------------------------------------------------------------
# Confidence engine
# ---------------------------------------------------------------------------

def compute_confidence(
    *,
    coords: List[LatLon],
    phrase_pattern: PhrasePattern,
    warning_type: WarningType,
    geometry: Geometry,
    precedent_score: float = 0.0,
) -> Tuple[float, dict[str, float]]:
    """
    Hybrid confidence model:
    - rule-based score
    - optional precedent boost from TCE / history layer

    precedent_score should normally be 0.0 .. 0.1
    """
    phrase_score = 0.30 if phrase_pattern != "UNSPECIFIED" else 0.0
    coord_score = min(len(coords), 4) * 0.10
    type_score = 0.15 if warning_type != "UNCLASSIFIED" else 0.0
    geom_score = 0.20 if geometry.vertices else 0.0

    precedent_score = max(0.0, min(precedent_score, 0.10))

    total = phrase_score + coord_score + type_score + geom_score + precedent_score
    total = round(min(total, 1.0), 3)

    breakdown = {
        "phrase_score": round(phrase_score, 3),
        "coord_score": round(coord_score, 3),
        "type_score": round(type_score, 3),
        "geometry_score": round(geom_score, 3),
        "precedent_score": round(precedent_score, 3),
        "total": total,
    }
    return total, breakdown


# ---------------------------------------------------------------------------
# Public interpretation entrypoints
# ---------------------------------------------------------------------------

def interpret_warning(
    *,
    warning_id: str,
    navarea: str,
    source_kind: str,
    title: str,
    body: str,
    run_id: str,
    created_utc: str,
    source_ref=None,
    operator_name: str = "",
    operator_watch: str = "",
    operator_notes: str = "",
    precedent_score: float = 0.0,
) -> tuple[WarningDraft, InterpretationResult]:
    """
    Main A3 interpretation function.

    Produces:
    - WarningDraft: canonical pipeline object used by the existing system
    - InterpretationResult: richer interpretation metadata for UI / TCE / review
    """
    normalized_title = normalize_text(title)
    normalized_body = normalize_text(body)
    combined = f"{normalized_title} {normalized_body}".strip()

    errors: List[str] = []

    warning_type = classify_warning(combined)
    phrase_pattern, implied_geom = detect_phrase_pattern(combined)
    coords = detect_coordinates(combined)
    validity = parse_validity(combined)
    geometry = build_geometry(
        coords=coords,
        phrase_pattern=phrase_pattern,
        implied_geom=implied_geom,
    )

    if not coords:
        errors.append("No coordinates detected.")
    if phrase_pattern == "UNSPECIFIED":
        errors.append("No recognized geometry phrase.")
    if not geometry.vertices:
        errors.append("Geometry could not be built from interpreted content.")

    confidence, breakdown = compute_confidence(
        coords=coords,
        phrase_pattern=phrase_pattern,
        warning_type=warning_type,
        geometry=geometry,
        precedent_score=precedent_score,
    )

    draft = WarningDraft(
        run_id=run_id,
        created_utc=created_utc,
        navarea=navarea,
        source_kind=source_kind,  # type: ignore[arg-type]
        source_ref=source_ref,
        warning_id=warning_id,
        title=normalized_title or title,
        body=normalized_body or body,
        validity=validity,
        geometry=geometry,
        operator_name=operator_name,
        operator_watch=operator_watch,
        operator_notes=operator_notes,
    )

    result = InterpretationResult(
        normalized_title=normalized_title,
        normalized_body=normalized_body,
        warning_type=warning_type,
        phrase_pattern=phrase_pattern,
        geometry=geometry,
        validity=validity,
        confidence=confidence,
        confidence_breakdown=breakdown,
        errors=errors,
    )

    return draft, result


def confidence_review_bucket(confidence: float) -> str:
    """
    UI / workflow helper.

    Recommended policy:
    - GREEN_AUTOPLOT: high confidence
    - YELLOW_REVIEW: usable but operator should inspect
    - RED_MANUAL: weak interpretation, operator input needed
    """
    if confidence >= 0.85:
        return "GREEN_AUTOPLOT"
    if confidence >= 0.60:
        return "YELLOW_REVIEW"
    return "RED_MANUAL"
