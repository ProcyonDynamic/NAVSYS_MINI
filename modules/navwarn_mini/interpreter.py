from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import Geometry, LatLon, Validity, WarningDraft

from modules.navwarn_mini.coord_repair import repair_split_coords


from .keyphrase_builder import build_key_phrases
from .semantic_models import SemanticPacket

WarningType = str
PhrasePattern = str
BlockType = str


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WarningBlock:
    block_type: BlockType
    raw_text: str
    normalized_text: str
    confidence: float
    extracted: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class WarningStructure:
    header_blocks: List[WarningBlock]
    time_blocks: List[WarningBlock]
    reference_blocks: List[WarningBlock]
    cancellation_blocks: List[WarningBlock]
    geometry_blocks: List[WarningBlock]
    description_blocks: List[WarningBlock]
    admin_blocks: List[WarningBlock]
    unknown_blocks: List[WarningBlock]

    @property
    def all_blocks(self) -> List[WarningBlock]:
        return (
            self.header_blocks
            + self.time_blocks
            + self.reference_blocks
            + self.cancellation_blocks
            + self.geometry_blocks
            + self.description_blocks
            + self.admin_blocks
            + self.unknown_blocks
        )


@dataclass(frozen=True)
class InterpretationResult:
    normalized_title: str
    normalized_body: str
    warning_type: WarningType
    phrase_pattern: PhrasePattern
    geometry: Geometry
    validity: Validity
    confidence: float
    confidence_breakdown: Dict[str, float]
    errors: List[str]
    structure: WarningStructure
    cancellation_targets: List[str]
    is_cancellation: bool
    is_reference_message: bool
    platform_name: Optional[str]
    semantic_packet: Optional[SemanticPacket] = None
    key_phrases: List[str] = field(default_factory=list)
    format_fingerprint: Optional[FormatFingerprint] = None
    

@dataclass(frozen=True)
class FormatFingerprint:
    has_header: bool
    has_time_block: bool
    has_reference_block: bool
    has_cancellation_block: bool
    has_geometry_block: bool
    has_description_block: bool
    has_admin_block: bool

    coord_count: int
    geometry_phrase: str
    has_list_labels: bool
    looks_like_offshore_list: bool
    looks_like_single_point_notice: bool
    has_cancel_this_msg_clause: bool
    has_explicit_cancel_targets: bool

# ---------------------------------------------------------------------------
# Phrase / type rules
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

_WARNING_TYPE_RULES: list[tuple[WarningType, tuple[str, ...]]] = [
    ("CANCELLATION", ("CANCEL THIS MSG", "CANCELLED", "CANCELS", "CANCEL NAVAREA")),
    ("CUMULATIVE", ("IN FORCE WARNINGS", "WARNINGS IN FORCE", "CUMULATIVE")),
    ("MILITARY_EXERCISE", ("MILITARY EXERCISE", "GUNNERY", "FIRING", "NAVAL EXERCISE")),
    ("MODU", (
        "MODU",
        "MOBILE OFFSHORE DRILLING UNIT",
        "SEMI-SUBMERSIBLE", "JACK-UP",
        "MOBILE OFFSHORE DRILLING UNITS",
        "OFFSHORE DRILLING UNIT",
        "OFFSHORE DRILLING UNITS",
        "SEMI-SUBMERSIBLE",
        "SEMI SUBMERSIBLE",
        "JACK-UP",
        "JACK UP",
        "DRILLING UNIT POSITIONS",
        "DRILLING UNITS POSITIONS",
        "DRILLING UNIT POSITION",
        "DRILLING UNTIS POSITION",
        "DRILLING-UNIT-POSITIONS",
    )),
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

# Offshore / platform family that should always behave as point objects
_PLATFORM_TYPES = {
    "MODU",
    "DRILLING",
}

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(
    r"\bNAVAREA\s+(?P<navarea>[IVX]+)\s+(?P<number>\d{1,4})/(?P<year>\d{2,4})\b",
    re.IGNORECASE,
)

_DTG_RE = re.compile(
    r"\b\d{6}\s*(?:UTC|Z)?\s*[A-Z]{3}\s*\d{2,4}\b",
    re.IGNORECASE,
)

_UFN_RE = re.compile(r"\bUFN\b|\bUNTIL\s+FURTHER\s+NOTICE\b", re.IGNORECASE)

_REFERENCE_RE = re.compile(
    r"\b(IN\s+FORCE\s+WARNINGS?|WARNINGS?\s+IN\s+FORCE|REFERS?\s+TO|REFERENCE|REFERENCES)\b",
    re.IGNORECASE,
)

_CANCELLATION_RE = re.compile(
    r"\b(CANCEL(?:S|LED|ING)?|CANCEL\s+THIS\s+MSG|CANCELLING)\b",
    re.IGNORECASE,
)

_GEOMETRY_HINT_RE = re.compile(
    r"\b(AREA\s+BOUNDED\s+BY|BOUNDED\s+BY|JOINING|BETWEEN|WITHIN|CENTERED\s+ON|CENTRED\s+ON|VICINITY\s+OF)\b",
    re.IGNORECASE,
)

_ADMIN_RE = re.compile(
    r"\b(THIS\s+MSG|NNNN|BT|UNCLAS|END|NOTE:)\b",
    re.IGNORECASE,
)

_WARNING_ID_ANYWHERE_RE = re.compile(
    r"\bNAVAREA\s+[IVX]+\s+\d{1,4}/\d{2,4}\b",
    re.IGNORECASE,
)

_PLATFORM_NAME_RE = re.compile(
    r"\b(MODU|DRILLING\s+RIG|SEMI[-\s]?SUBMERSIBLE|JACK[-\s]?UP)\s+([A-Z0-9\- ]{3,40})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = repair_split_coords(text)

    cleaned = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    cleaned = cleaned.replace("\u00b0", " ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = cleaned.upper().strip()

    # Small OCR repairs
    cleaned = re.sub(r"(\d)([NS])(\d)", r"\1 \2 \3", cleaned)
    cleaned = re.sub(r"(\d)([EW])(\d)", r"\1 \2 \3", cleaned)
    # Preserve DMS coordinates like 18-42-17N
    cleaned = re.sub(
        r"(\d{1,3})-(\d{1,2})-(\d{1,2})([NSEW])",
        r"\1-\2-\3\4",
        cleaned
    )

    # Normalize only degree-minute formats, NOT DMS 
    cleaned = re.sub(
        r"(\d{1,3})\s+(\d{1,2}\.\d+)\s*([NSEW])",
        r"\1 \2 \3",
        cleaned
    )
    
    return cleaned

# ---------------------------------------------------------------------------
# Coordinate detection
# ---------------------------------------------------------------------------



def detect_coordinates(text: str) -> List[LatLon]:
    from .coordinate_extractor_mini import CoordinateExtractor

    found: List[LatLon] = []
    seen: set[tuple[float, float]] = set()

    for coord in CoordinateExtractor.extract(text or ""):
        key = (round(coord.lat, 8), round(coord.lon, 8))
        if key in seen:
            continue
        seen.add(key)
        found.append(LatLon(lat=coord.lat, lon=coord.lon))

    return found


# ---------------------------------------------------------------------------
# Block segmentation / classification
# ---------------------------------------------------------------------------

def split_into_candidate_blocks(title: str, body: str) -> List[str]:
    pieces: List[str] = []

    for part in [title, body]:
        if not part:
            continue
        for chunk in re.split(r"\n\s*\n", part.strip()):
            chunk = chunk.strip()
            if chunk:
                pieces.append(chunk)

    flattened: List[str] = []
    for piece in pieces:
        lines = [ln.strip() for ln in piece.splitlines() if ln.strip()]
        if not lines:
            continue

        current: List[str] = []
        for ln in lines:
            if re.match(r"^\d+\.\s+", ln) and current:
                flattened.append(" ".join(current).strip())
                current = [ln]
            else:
                current.append(ln)
        if current:
            flattened.append(" ".join(current).strip())

    return flattened


def classify_block(raw_text: str) -> WarningBlock:
    norm = normalize_text(raw_text)
    extracted: Dict[str, object] = {}

    header_match = _HEADER_RE.search(norm)
    ids = _WARNING_ID_ANYWHERE_RE.findall(norm)
    coords = detect_coordinates(norm)

    if header_match and norm.startswith(header_match.group(0)):
        extracted["warning_id"] = header_match.group(0).upper()
        return WarningBlock("HEADER", raw_text, norm, 0.95, extracted)

    if _REFERENCE_RE.search(norm):
        extracted["referenced_ids"] = [x.upper() for x in ids]
        return WarningBlock("REFERENCE", raw_text, norm, 0.90, extracted)

    if _CANCELLATION_RE.search(norm):
        extracted["cancellation_targets"] = [x.upper() for x in ids]
        extracted["has_cancel_this_msg"] = "CANCEL THIS MSG" in norm
        return WarningBlock("CANCELLATION", raw_text, norm, 0.95, extracted)

    if _DTG_RE.search(norm) or _UFN_RE.search(norm):
        extracted["dtgs"] = _DTG_RE.findall(norm)
        extracted["ufn"] = bool(_UFN_RE.search(norm))
        return WarningBlock("TIME", raw_text, norm, 0.80, extracted)

    if coords or _GEOMETRY_HINT_RE.search(norm):
        extracted["coord_count"] = len(coords)
        extracted["coords"] = coords
        return WarningBlock("GEOMETRY", raw_text, norm, 0.85, extracted)

    if _ADMIN_RE.search(norm):
        return WarningBlock("ADMIN", raw_text, norm, 0.70, extracted)

    if len(norm.split()) >= 3:
        return WarningBlock("DESCRIPTION", raw_text, norm, 0.60, extracted)

    return WarningBlock("UNKNOWN", raw_text, norm, 0.30, extracted)


def build_structure(title: str, body: str) -> WarningStructure:
    blocks = [classify_block(x) for x in split_into_candidate_blocks(title, body)]

    def pick(kind: str) -> List[WarningBlock]:
        return [b for b in blocks if b.block_type == kind]

    return WarningStructure(
        header_blocks=pick("HEADER"),
        time_blocks=pick("TIME"),
        reference_blocks=pick("REFERENCE"),
        cancellation_blocks=pick("CANCELLATION"),
        geometry_blocks=pick("GEOMETRY"),
        description_blocks=pick("DESCRIPTION"),
        admin_blocks=pick("ADMIN"),
        unknown_blocks=pick("UNKNOWN"),
    )


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def classify_warning(text: str, structure: Optional[WarningStructure] = None) -> WarningType:
    if structure:
        # A cumulative / in-force bulletin may contain cancel wording
        # without being a true operational cancellation warning.
        if structure.reference_blocks and not structure.geometry_blocks:
            return "CUMULATIVE"

        has_cancel_this_msg = any(
            bool(block.extracted.get("has_cancel_this_msg"))
            for block in structure.cancellation_blocks
        )
        has_cancel_targets = any(
            bool(block.extracted.get("cancellation_targets"))
            for block in structure.cancellation_blocks
        )
        has_geometry = bool(structure.geometry_blocks)

        # Only classify as standalone cancellation if it targets warnings
        # and does not introduce fresh operational geometry.
        if structure.cancellation_blocks and has_cancel_targets and not has_geometry:
            return "CANCELLATION"

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


def parse_validity(text: str, structure: Optional[WarningStructure] = None) -> Validity:
    ufn = bool(_UFN_RE.search(text))

    if structure:
        for block in structure.time_blocks + structure.cancellation_blocks:
            if block.extracted.get("ufn"):
                ufn = True

    return Validity(start_utc=None, end_utc=None, ufn=ufn)


def collect_structure_coordinates(structure: WarningStructure, combined_text: str) -> List[LatLon]:
    coords: List[LatLon] = []
    for block in structure.geometry_blocks:
        block_coords = block.extracted.get("coords")
        if isinstance(block_coords, list):
            coords.extend(block_coords)

    if coords:
        return coords

    return detect_coordinates(combined_text)


def extract_cancellation_targets(structure: WarningStructure) -> List[str]:
    targets: List[str] = []
    for block in structure.cancellation_blocks:
        ids = block.extracted.get("cancellation_targets", [])
        if isinstance(ids, list):
            targets.extend(ids)

    deduped: List[str] = []
    seen = set()
    for t in targets:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped

def extract_platform_name(text: str) -> Optional[str]:
    match = _PLATFORM_NAME_RE.search(text)
    if not match:
        return None

    name = match.group(2).strip()

    # remove trailing noise words
    name = re.sub(r"\b(OPERATING|DRILLING|AT|IN|LOCATED)\b.*$", "", name).strip()

    return name if len(name) >= 3 else None

def _detect_geometry_phrase(text: str) -> str:
    for pattern, phrase_name, _ in _PHRASE_LIBRARY:
        if re.search(pattern, text):
            return phrase_name
    return "UNSPECIFIED"


def _has_list_labels(raw_text: str) -> bool:
    return bool(
        re.search(
            r"(^|\n)\s*(?:[A-Z]{1,4}|\d+)\.\s+",
            raw_text or "",
            flags=re.IGNORECASE,
        )
    )


def _looks_like_single_point_notice(text: str, coord_count: int) -> bool:
    t = (text or "").upper()

    if coord_count != 1:
        return False

    return any(
        phrase in t
        for phrase in (
            "UNLIT",
            "UNRELIABLE",
            "MISSING",
            "DAMAGED",
            "ESTABLISHED",
            "WRECK",
            "DANGEROUS WRECK",
            "BEACON",
            "BUOY",
            "LIGHT",
            "LIGHTHOUSE",
            "RACON",
        )
    )


def build_format_fingerprint(
    *,
    title: str,
    body: str,
    combined_text: str,
    structure: WarningStructure,
    coords: List[LatLon],
    cancellation_targets: List[str],
) -> FormatFingerprint:
    raw_text = f"{title}\n{body}".strip()
    geometry_phrase = _detect_geometry_phrase(combined_text)
    has_cancel_this_msg_clause = "CANCEL THIS MSG" in combined_text.upper()

    return FormatFingerprint(
        has_header=bool(structure.header_blocks),
        has_time_block=bool(structure.time_blocks),
        has_reference_block=bool(structure.reference_blocks),
        has_cancellation_block=bool(structure.cancellation_blocks),
        has_geometry_block=bool(structure.geometry_blocks),
        has_description_block=bool(structure.description_blocks),
        has_admin_block=bool(structure.admin_blocks),
        coord_count=len(coords),
        geometry_phrase=geometry_phrase,
        has_list_labels=_has_list_labels(raw_text),
        looks_like_offshore_list=(
            "MOBILE OFFSHORE DRILLING UNITS" in combined_text.upper()
            or "POSITIONS AT" in combined_text.upper()
            or (
                "MODU" in combined_text.upper()
                and _has_list_labels(raw_text)
                and len(coords) >= 2
            )
        ),
        looks_like_single_point_notice=_looks_like_single_point_notice(combined_text, len(coords)),
        has_cancel_this_msg_clause=has_cancel_this_msg_clause,
        has_explicit_cancel_targets=bool(cancellation_targets),
    )

def classify_warning_from_fingerprint(
    *,
    combined_text: str,
    structure: WarningStructure,
    fingerprint: FormatFingerprint,
    cancellation_targets: List[str],
) -> WarningType:
    text = combined_text.upper()

    if fingerprint.has_reference_block and not fingerprint.has_geometry_block:
        return "CUMULATIVE"

    if (
        fingerprint.has_cancellation_block
        and fingerprint.has_explicit_cancel_targets
        and fingerprint.coord_count == 0
    ):
        return "CANCELLATION"

    if fingerprint.looks_like_offshore_list:
        return "MODU"

    if fingerprint.looks_like_single_point_notice:
        return "AIDS_TO_NAVIGATION"

    if fingerprint.coord_count > 0:
        if any(x in text for x in ("HAZARDOUS OPERATIONS", "ROCKET", "EXERCISE", "FIRING")):
            return "ROCKET_LAUNCH"
        if any(x in text for x in ("SURVEY OPERATIONS", "SEISMIC", "SUBSEA OPERATIONS", "PIPELINE OPERATIONS")):
            return "SURVEY"
        if "CABLE OPERATIONS" in text:
            return "SUBMARINE_CABLE"
        if any(x in text for x in ("WRECK", "DANGEROUS WRECK")):
            return "WRECK"
        if any(x in text for x in ("UNLIT", "MISSING", "DAMAGED", "ESTABLISHED", "RANGE CHANGED")):
            return "AIDS_TO_NAVIGATION"

    return classify_warning(text, structure=structure)

# ---------------------------------------------------------------------------
# Geometry builder
# ---------------------------------------------------------------------------

def build_geometry(
    *,
    coords: List[LatLon],
    phrase_pattern: PhrasePattern,
    implied_geom: Optional[str],
    warning_type: WarningType,
) -> Geometry:
    
    # MODU / offshore object lists are semantic multi-point collections,
    # not connected route lines.
    if warning_type == "MODU":
        if len(coords) >= 1:
            return Geometry(geom_type="POINT", vertices=coords, closed=False)
        return Geometry(geom_type="POINT", vertices=[], closed=False)
    
    # Offshore installations behave as annotated point objects
    if warning_type in _PLATFORM_TYPES and coords:
        return Geometry(
            geom_type="POINT",
            vertices=coords[:1],
            closed=False,
        )
    
    if implied_geom == "AREA":
        return Geometry(geom_type="AREA", vertices=coords, closed=True)

    if implied_geom == "LINE":
        return Geometry(geom_type="LINE", vertices=coords, closed=False)

    if implied_geom == "POINT":
        return Geometry(geom_type="POINT", vertices=coords[:1], closed=False)

    if len(coords) >= 3:
        return Geometry(geom_type="AREA", vertices=coords, closed=True)

    if len(coords) == 2:
        return Geometry(geom_type="LINE", vertices=coords, closed=False)

    if len(coords) == 1:
        return Geometry(geom_type="POINT", vertices=coords[:1], closed=False)

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
    structure: WarningStructure,
    precedent_score: float = 0.0,
) -> Tuple[float, Dict[str, float]]:
    phrase_score = 0.20 if phrase_pattern != "UNSPECIFIED" else 0.0
    coord_score = min(len(coords), 4) * 0.10
    type_score = 0.15 if warning_type != "UNCLASSIFIED" else 0.0
    geom_score = 0.20 if geometry.vertices else 0.0
    block_score = min(len(structure.all_blocks), 5) * 0.05
    precedent_score = max(0.0, min(precedent_score, 0.10))

    total = phrase_score + coord_score + type_score + geom_score + block_score + precedent_score
    total = round(min(total, 1.0), 3)

    breakdown = {
        "phrase_score": round(phrase_score, 3),
        "coord_score": round(coord_score, 3),
        "type_score": round(type_score, 3),
        "geometry_score": round(geom_score, 3),
        "block_score": round(block_score, 3),
        "precedent_score": round(precedent_score, 3),
        "total": total,
    }
    return total, breakdown


# ---------------------------------------------------------------------------
# Public entrypoint
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
    normalized_title = normalize_text(title)
    normalized_body = normalize_text(body)
    combined = f"{normalized_title} {normalized_body}".strip()

    from .semantic_packet_builder import build_semantic_packet
    semantic_packet = build_semantic_packet(
        raw_text=f"{title}\n{body}",
        normalized_text=combined,
    )

    key_phrases = build_key_phrases(
        warning_id=warning_id,
        semantic_packet=semantic_packet,
    )

    errors: List[str] = []

    structure = build_structure(title, body)
    phrase_pattern, implied_geom = detect_phrase_pattern(combined)

    coords = collect_structure_coordinates(structure, combined)
    validity = parse_validity(combined, structure=structure)
    platform_name = extract_platform_name(combined)
    cancellation_targets = extract_cancellation_targets(structure)

    format_fingerprint = build_format_fingerprint(
        title=title,
        body=body,
        combined_text=combined,
        structure=structure,
        coords=coords,
        cancellation_targets=cancellation_targets,
    )

    warning_type = classify_warning_from_fingerprint(
        combined_text=combined,
        structure=structure,
        fingerprint=format_fingerprint,
        cancellation_targets=cancellation_targets,
    )

    geometry = build_geometry(
        coords=coords,
        phrase_pattern=phrase_pattern,
        implied_geom=implied_geom,
        warning_type=warning_type,
    )   
    has_geometry = bool(geometry.vertices) or bool(structure.geometry_blocks)

    has_cancel_this_msg_clause = any(
        bool(block.extracted.get("has_cancel_this_msg"))
        for block in structure.cancellation_blocks
    )

    has_explicit_cancel_targets = bool(cancellation_targets)
    is_modu_family = warning_type == "MODU"
    
    # Distinguish:
    # 1) standalone cancellation bulletins
    # 2) operational warnings that contain self-expiry text like "CANCEL THIS MSG ..."
    embedded_cancel_clause = has_geometry and has_cancel_this_msg_clause
    standalone_cancellation = (
        warning_type == "CANCELLATION"
        and has_explicit_cancel_targets
        and not has_geometry
    )

    is_cancellation = standalone_cancellation
    is_reference_message = warning_type == "CUMULATIVE"

    if not coords and not is_cancellation and not is_reference_message:
        errors.append("No coordinates detected.")

    if phrase_pattern == "UNSPECIFIED" and geometry.vertices:
        errors.append("No recognized geometry phrase; geometry inferred heuristically.")

    if not geometry.vertices and not is_cancellation and not is_reference_message:
        errors.append("Geometry could not be built from interpreted content.")
    
    # Preserve operational type if geometry exists and the message is active now,
    # even if it contains future self-cancel wording.
    #
    # Do NOT downgrade to UNCLASSIFIED. These are still real operational warnings
    # that just contain an embedded expiry clause like "CANCEL THIS MSG ...".
    if embedded_cancel_clause and warning_type == "CANCELLATION":
        operational_text = combined

        if any(
            kw in operational_text
            for kw in (
                "HAZARDOUS OPERATIONS",
                "ROCKET",
                "EXERCISE",
                "FIRING",
                "SURVEY OPERATIONS",
                "CABLE OPERATIONS",
                "PIPELINE OPERATIONS",
                "DRILLING OPERATIONS",
                "SUBSEA OPERATIONS",
                "IN AREA BOUNDED BY",
                "ALONG TRACKLINE JOINING",
                "WITHIN",
                "DANGEROUS WRECK",
                "UNLIT",
                "MISSING",
                "DAMAGED",
                "ESTABLISHED",
                "RANGE CHANGED",
                "SERVICES UNAVAILABLE",
                "OFF AIR",
            )
        ):
                warning_type = classify_warning_from_fingerprint(
                    combined_text=operational_text.replace("CANCEL THIS MSG", ""),
                    structure=structure,
                    fingerprint=format_fingerprint,
                    cancellation_targets=[],
                )

                if warning_type == "CANCELLATION":
                    warning_type = "GENERAL_HAZARD"
                        
    confidence, breakdown = compute_confidence(
        coords=coords,
        phrase_pattern=phrase_pattern,
        warning_type=warning_type,
        geometry=geometry,
        structure=structure,
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
        structure=structure,
        cancellation_targets=cancellation_targets,
        is_cancellation=is_cancellation,
        is_reference_message=is_reference_message,
        platform_name=platform_name,
        key_phrases=key_phrases,
        semantic_packet=semantic_packet,
        format_fingerprint=format_fingerprint,
    )

    return draft, result


def confidence_review_bucket(confidence: float) -> str:
    if confidence >= 0.85:
        return "GREEN_AUTOPLOT"
    if confidence >= 0.60:
        return "YELLOW_REVIEW"
    return "RED_MANUAL"