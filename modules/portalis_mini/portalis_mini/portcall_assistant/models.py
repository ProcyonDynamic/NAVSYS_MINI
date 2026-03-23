from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ExtractedField:
    value: Any = None
    source: Optional[str] = None
    confidence: float = 0.0
    method: Optional[str] = None
    notes: Optional[str] = None


@dataclass(slots=True)
class VoyageInput:
    current_port: Optional[str] = None
    last_port: Optional[str] = None
    next_port: Optional[str] = None
    eta: Optional[str] = None
    etd: Optional[str] = None
    berth: Optional[str] = None
    terminal: Optional[str] = None
    agent: Optional[str] = None
    voyage_number: Optional[str] = None
    reason_of_call: Optional[str] = None
    cargo_summary: Optional[str] = None
    security_level: Optional[str] = None
    persons_on_board: Optional[int] = None
    last_10_ports: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PortCallContext:
    generated_at: str
    vessel_profile: Dict[str, ExtractedField] = field(default_factory=dict)
    certificate_registry: List[Dict[str, ExtractedField]] = field(default_factory=list)
    crew_registry: List[Dict[str, Any]] = field(default_factory=list)
    voyage_profile: Dict[str, ExtractedField] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_plain_dict(self) -> Dict[str, Any]:
        return _convert(self)


def _convert(value: Any) -> Any:
    if isinstance(value, ExtractedField):
        return asdict(value)
    if is_dataclass(value):
        return {k: _convert(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _convert(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert(v) for v in value]
    return value
