from .models import WarningDraft

from navwarn_mini.coords import extract_vertices_from_text
from navwarn_mini.models import LatLon, Geometry

# pick a source text to extract coordinates from
source_text = vertices_text.strip() if vertices_text.strip() else body

pairs = extract_vertices_from_text(source_text)   # [(lat, lon), ...]
vertices = [LatLon(lat=a, lon=b) for (a, b) in pairs]

geometry = Geometry(
    geom_type=geom_type,   # "POINT"|"LINE"|"AREA" (operator chooses in v0.1)
    vertices=vertices,
    closed=False
)

def build_warning_draft_from_operator_input(
    *,
    run_id: str,
    created_utc: str,
    navarea: str,
    source_kind: str,
    source_title: str,
    source_url: str,
    source_retrieved_utc: str,
    warning_id: str,
    title: str,
    body: str,
    geom_type: str,
    vertices_text: str,
    validity_start_utc: str | None,
    validity_end_utc: str | None,
    validity_ufn: bool,
    operator_name: str = "",
    operator_watch: str = "",
    operator_notes: str = ""
) -> WarningDraft:
    """
    Create WarningDraft from raw operator inputs (strings).

    - vertices_text: may contain multiple coordinate formats (e.g. 25-14.2N 081-33.1W,
      25°14.2'N 081°33.1'W, -3.1234 -38.5678, etc.)
    - This function should parse coordinates into decimal degrees and fill draft.geometry.vertices.
    - Do not compute distance/band here.
    """
    raise NotImplementedError