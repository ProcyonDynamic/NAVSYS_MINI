from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

ReviewState = Literal["AUTO", "REVIEWED", "OVERRIDDEN", "REJECTED"]


@dataclass(frozen=True)
class PlotVertex:
    lat: float
    lon: float


@dataclass(frozen=True)
class GeometryOverride:
    enabled: bool = False
    geometry_type: str = "POINT"
    vertices: list[PlotVertex] = field(default_factory=list)
    closed: bool = False


@dataclass(frozen=True)
class TextOverride:
    enabled: bool = False
    title: Optional[str] = None
    body: Optional[str] = None


@dataclass(frozen=True)
class StyleOverride:
    enabled: bool = False
    line_type: Optional[int] = None
    width: Optional[int] = None
    color_no: Optional[int] = None


@dataclass(frozen=True)
class OperatorEditInfo:
    name: str = ""
    watch: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PlotOverride:
    warning_id: str
    run_id: str
    review_state: ReviewState = "AUTO"
    geometry_override: GeometryOverride = field(default_factory=GeometryOverride)
    text_override: TextOverride = field(default_factory=TextOverride)
    style_override: StyleOverride = field(default_factory=StyleOverride)
    operator: OperatorEditInfo = field(default_factory=OperatorEditInfo)
    edited_utc: str = ""


@dataclass(frozen=True)
class WarningVertexView:
    idx: int
    lat: float
    lon: float


@dataclass(frozen=True)
class WarningValidityView:
    start_utc: Optional[str]
    end_utc: Optional[str]
    ufn: bool


@dataclass(frozen=True)
class WarningSourceView:
    source_kind: str
    source_title: Optional[str]
    source_url: Optional[str]


@dataclass(frozen=True)
class WarningOperatorView:
    name: str
    watch: str
    notes: str


@dataclass(frozen=True)
class WarningOverrideView:
    exists: bool
    geometry_overridden: bool
    text_overridden: bool
    style_overridden: bool


@dataclass(frozen=True)
class PlotEditorWarningViewModel:
    warning_id: str
    run_id: str
    navarea: str
    title: str
    body: str
    warning_type: str
    phrase_pattern: str
    geometry_type: str
    vertices: list[WarningVertexView]
    closed: bool
    band: str
    distance_nm: Optional[float]
    status: str
    plotted: str
    review_state: ReviewState
    confidence: float
    validity: WarningValidityView
    source: WarningSourceView
    operator: WarningOperatorView
    override: WarningOverrideView
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlotRegistryItem:
    warning_id: str
    run_id: str
    navarea: str
    title: str
    warning_type: str
    band: str
    distance_nm: Optional[float]
    status: str
    plotted: str
    review_state: ReviewState
    confidence: float
    has_override: bool


def dataclass_to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


def _opt_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _normalize_review_state(value: Any) -> ReviewState:
    text = str(value or "AUTO").strip().upper()
    if text in ("AUTO", "REVIEWED", "OVERRIDDEN", "REJECTED"):
        return text  # type: ignore[return-value]
    return "AUTO"


def plot_override_from_dict(data: dict[str, Any]) -> PlotOverride:
    geometry_raw = data.get("geometry_override") or {}
    text_raw = data.get("text_override") or {}
    style_raw = data.get("style_override") or {}
    operator_raw = data.get("operator") or {}

    vertices = [
        PlotVertex(
            lat=float(v["lat"]),
            lon=float(v["lon"]),
        )
        for v in (geometry_raw.get("vertices") or [])
    ]

    geometry_override = GeometryOverride(
        enabled=bool(geometry_raw.get("enabled", False)),
        geometry_type=str(geometry_raw.get("geometry_type", "POINT")),
        vertices=vertices,
        closed=bool(geometry_raw.get("closed", False)),
    )

    text_override = TextOverride(
        enabled=bool(text_raw.get("enabled", False)),
        title=text_raw.get("title"),
        body=text_raw.get("body"),
    )

    style_override = StyleOverride(
        enabled=bool(style_raw.get("enabled", False)),
        line_type=_opt_int(style_raw.get("line_type")),
        width=_opt_int(style_raw.get("width")),
        color_no=_opt_int(style_raw.get("color_no")),
    )

    operator = OperatorEditInfo(
        name=str(operator_raw.get("name", "")),
        watch=str(operator_raw.get("watch", "")),
        reason=str(operator_raw.get("reason", "")),
    )

    return PlotOverride(
        warning_id=str(data.get("warning_id", "")),
        run_id=str(data.get("run_id", "")),
        review_state=_normalize_review_state(data.get("review_state")),
        geometry_override=geometry_override,
        text_override=text_override,
        style_override=style_override,
        operator=operator,
        edited_utc=str(data.get("edited_utc", "")),
    )


def make_override_view(override: Optional[PlotOverride]) -> WarningOverrideView:
    if override is None:
        return WarningOverrideView(
            exists=False,
            geometry_overridden=False,
            text_overridden=False,
            style_overridden=False,
        )

    return WarningOverrideView(
        exists=True,
        geometry_overridden=bool(override.geometry_override.enabled),
        text_overridden=bool(override.text_override.enabled),
        style_overridden=bool(override.style_override.enabled),
    )


def build_vertex_views(vertices: list[Any]) -> list[WarningVertexView]:
    out: list[WarningVertexView] = []
    for idx, v in enumerate(vertices):
        lat = getattr(v, "lat", None)
        lon = getattr(v, "lon", None)
        if lat is None or lon is None:
            continue
        out.append(WarningVertexView(idx=idx, lat=float(lat), lon=float(lon)))
    return out
