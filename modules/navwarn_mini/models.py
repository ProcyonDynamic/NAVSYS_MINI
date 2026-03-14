from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, List, Dict


NAVAREA = str
SourceKind = Literal["NAVAREA", "NAVTEX", "SAFETYNET", "WEB", "MANUAL"]
GeomType = Literal["POINT", "LINE", "AREA"]
Band = Literal["RED", "AMBER"]
Status = Literal["OK", "FAILED"]

@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float

@dataclass(frozen=True)
class SourceRef:
    title: str
    url: str
    retrieved_utc: str  # ISO8601 Z

@dataclass(frozen=True)
class Validity:
    start_utc: Optional[str]
    end_utc: Optional[str]
    ufn: bool

@dataclass(frozen=True)
class Geometry:
    geom_type: GeomType
    vertices: List[LatLon]
    closed: bool

@dataclass(frozen=True)
class WarningDraft:
    run_id: str
    created_utc: str
    navarea: NAVAREA
    source_kind: SourceKind
    source_ref: Optional[SourceRef]
    warning_id: str
    title: str
    body: str
    validity: Validity
    geometry: Geometry
    operator_name: str = ""
    operator_watch: str = ""
    operator_notes: str = ""

@dataclass(frozen=True)
class ShipPosition:
    lat: float
    lon: float
    time_utc: str  # ISO8601 Z

@dataclass(frozen=True)
class WarningClassified:
    run_id: str
    processed_utc: str
    navarea: NAVAREA
    source_kind: SourceKind
    source_ref: Optional[SourceRef]
    warning_id: str
    title: str
    body: str
    validity: Validity
    geometry: Geometry
    ship_position: Optional[ShipPosition]
    distance_nm: Optional[float]
    band: Band
    status: Status
    errors: List[str]

@dataclass(frozen=True)
class StyledVertex:
    lat: float
    lon: float
    line_type: int
    width: int
    color_no: int
    comment: str = ""

@dataclass(frozen=True)
class TextObject:
    lat: float
    lon: float
    rotation_deg: float
    size: int
    text: str

@dataclass(frozen=True)
class LineAggregateObject:
    run_id: str
    warning_id: str
    band: Band
    default_line_type: int
    default_width: int
    default_color_no: int
    vertices: List[StyledVertex]
    text_objects: List[TextObject]
    label_payload: Optional[LabelPayload] = None
    
    
# ---------------------------------------------------------------------------
# Offshore / platform object model
# ---------------------------------------------------------------------------



@dataclass(frozen=True)
class OffshoreObject:
    platform_id: Optional[str]
    platform_name: Optional[str]
    platform_type: Optional[str]
    match_status: str
    identity_confidence: float
    tce_thread_id: Optional[str]
    geometry: Geometry
    source_warning_id: str
    source_navarea: str


@dataclass(frozen=True)
class PlatformRegistryEntry:
    platform_id: str
    platform_name: Optional[str]
    platform_type: Optional[str]
    current_geometry: Geometry
    last_seen_utc: str
    first_seen_utc: str
    last_warning_id: str
    aliases: List[str]
    state: str
    tce_thread_id: str