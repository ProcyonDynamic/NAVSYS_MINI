from __future__ import annotations
import json
from pathlib import Path


def _load_json_array(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_semantic_registry() -> list[dict]:
    base = Path(__file__).resolve().parent / "semantic_registry"

    files = [
        "navarea_terms.json",
        "mrcc_terms.json",
        "navtex_terms.json",
        "radio_terms.json",
        "distress_terms.json",
        "ice_terms.json",
        "aton_terms.json",
        "offshore_terms.json",
        "station_terms.json",
        "vessel_terms.json",
    ]

    rows: list[dict] = []
    for name in files:
        rows.extend(_load_json_array(base / name))
    return rows