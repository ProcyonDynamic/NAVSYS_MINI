from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import (
    PortalisState,
    VesselRecord,
    VoyageRecord,
    DocumentStatusRecord,
)


def load_portalis_state(json_path: str) -> PortalisState:
    p = Path(json_path)
    if not p.exists():
        return PortalisState(
            documents=[
                DocumentStatusRecord(doc_name="Crew List", required=True),
                DocumentStatusRecord(doc_name="Maritime Declaration of Health", required=True),
                DocumentStatusRecord(doc_name="Port Requirement Checklist", required=True),
                DocumentStatusRecord(doc_name="Certificate Pack", required=False),
            ]
        )

    data = json.loads(p.read_text(encoding="utf-8"))

    vessel = VesselRecord(**data.get("vessel", {}))
    voyage = VoyageRecord(**data.get("voyage", {}))
    documents = [DocumentStatusRecord(**d) for d in data.get("documents", [])]

    return PortalisState(
        vessel=vessel,
        voyage=voyage,
        documents=documents,
    )


def save_portalis_state(state: PortalisState, json_path: str) -> None:
    p = Path(json_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )