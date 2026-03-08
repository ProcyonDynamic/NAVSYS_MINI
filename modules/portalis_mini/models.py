from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class VesselRecord:
    ship_name: str = ""
    imo: str = ""
    call_sign: str = ""
    flag: str = ""
    gross_tonnage: str = ""
    deadweight: str = ""
    loa: str = ""
    beam: str = ""
    summer_draft: str = ""
    manager: str = ""
    operator: str = ""


@dataclass
class VoyageRecord:
    voyage_no: str = ""
    departure_port: str = ""
    arrival_port: str = ""
    eta: str = ""
    etb: str = ""
    etc: str = ""
    cargo_summary: str = ""
    port_history: str = ""


@dataclass
class DocumentStatusRecord:
    doc_name: str
    required: bool = False
    filled: bool = False
    printed: bool = False
    signed: bool = False
    recorded: bool = False
    sent: bool = False
    notes: str = ""


@dataclass
class PortalisState:
    vessel: VesselRecord = field(default_factory=VesselRecord)
    voyage: VoyageRecord = field(default_factory=VoyageRecord)
    documents: List[DocumentStatusRecord] = field(default_factory=list)