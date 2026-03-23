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

    vessel_data = data.get("vessel", {}).copy()

    # Backward compatibility for older saved state keys
    if "ship_name" in vessel_data and "name" not in vessel_data:
        vessel_data["name"] = vessel_data.pop("ship_name")

    if "imo" in vessel_data and "imo_number" not in vessel_data:
        vessel_data["imo_number"] = vessel_data.pop("imo")

    if "flag" in vessel_data and "flag_state" not in vessel_data:
        vessel_data["flag_state"] = vessel_data.pop("flag")

    if "operator" in vessel_data and "operator_name" not in vessel_data:
        vessel_data["operator_name"] = vessel_data.pop("operator")

    if "manager" in vessel_data and "owner_name" not in vessel_data:
        vessel_data["owner_name"] = vessel_data.pop("manager")

    allowed_vessel_keys = {
        "vessel_id",
        "name",
        "imo_number",
        "call_sign",
        "flag_state",
        "vessel_type",
        "gross_tonnage",
        "net_tonnage",
        "deadweight",
        "owner_name",
        "operator_name",
        "audit",
    }

    vessel_data = {k: v for k, v in vessel_data.items() if k in allowed_vessel_keys}

    vessel_data.setdefault("vessel_id", "default_vessel")
    vessel_data.setdefault("name", "")

    vessel = VesselRecord(**vessel_data)
    voyage_data = data.get("voyage", {}).copy()

    # Backward compatibility
    if "voyage_no" in voyage_data and "voyage_number" not in voyage_data:
        voyage_data["voyage_number"] = voyage_data.pop("voyage_no")

    if "port_from" in voyage_data and "departure_port" not in voyage_data:
        voyage_data["departure_port"] = voyage_data.pop("port_from")

    if "port_to" in voyage_data and "arrival_port" not in voyage_data:
        voyage_data["arrival_port"] = voyage_data.pop("port_to")

    # Keep only allowed fields (VERY important)
    allowed_voyage_keys = {
        "voyage_number",
        "departure_port",
        "arrival_port",
        "eta",
        "etd",
        "last_port",
        "next_port",
        "agent",
        "remarks",
    }

    voyage_data = data.get("voyage", {}) or {}
    voyage = VoyageRecord(**voyage_data) if voyage_data else VoyageRecord()
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