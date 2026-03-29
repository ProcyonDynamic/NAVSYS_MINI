from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


def _copy_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


@dataclass
class WarningEditorPayload:
    warning_id: str
    navarea: str
    run_id: str
    raw_text: str
    source_kind: str
    created_utc: str

    interp: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    pattern: dict[str, Any] = field(default_factory=dict)
    geometry: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    plot: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    override: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "warning_id": self.warning_id,
            "navarea": self.navarea,
            "run_id": self.run_id,
            "raw_text": self.raw_text,
            "source_kind": self.source_kind,
            "created_utc": self.created_utc,
            "interp": _copy_dict(self.interp),
            "profile": _copy_dict(self.profile),
            "pattern": _copy_dict(self.pattern),
            "geometry": _copy_dict(self.geometry),
            "classification": _copy_dict(self.classification),
            "plot": _copy_dict(self.plot),
            "audit": _copy_dict(self.audit),
            "override": _copy_dict(self.override),
        }
        data.update(_copy_dict(self.extras))
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WarningEditorPayload":
        known = {
            "warning_id",
            "navarea",
            "run_id",
            "raw_text",
            "source_kind",
            "created_utc",
            "interp",
            "profile",
            "pattern",
            "geometry",
            "classification",
            "plot",
            "audit",
            "override",
        }
        extras = {k: deepcopy(v) for k, v in (data or {}).items() if k not in known}
        return cls(
            warning_id=str((data or {}).get("warning_id", "")),
            navarea=str((data or {}).get("navarea", "")),
            run_id=str((data or {}).get("run_id", "")),
            raw_text=str((data or {}).get("raw_text", "")),
            source_kind=str((data or {}).get("source_kind", "MANUAL")),
            created_utc=str((data or {}).get("created_utc", "")),
            interp=_copy_dict((data or {}).get("interp")),
            profile=_copy_dict((data or {}).get("profile")),
            pattern=_copy_dict((data or {}).get("pattern")),
            geometry=_copy_dict((data or {}).get("geometry")),
            classification=_copy_dict((data or {}).get("classification")),
            plot=_copy_dict((data or {}).get("plot")),
            audit=_copy_dict((data or {}).get("audit")),
            override=_copy_dict((data or {}).get("override")),
            extras=extras,
        )


@dataclass
class WarningEditorOverride:
    warning_id: str
    navarea: str
    saved_utc: str
    operator_name: str | None = None

    geometry_override: dict[str, Any] = field(default_factory=dict)
    plot_override: dict[str, Any] = field(default_factory=dict)
    text_override: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "warning_id": self.warning_id,
            "navarea": self.navarea,
            "saved_utc": self.saved_utc,
            "operator_name": self.operator_name,
            "geometry_override": _copy_dict(self.geometry_override),
            "plot_override": _copy_dict(self.plot_override),
            "text_override": _copy_dict(self.text_override),
            "notes": _copy_dict(self.notes),
        }
        data.update(_copy_dict(self.extras))
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WarningEditorOverride":
        known = {
            "warning_id",
            "navarea",
            "saved_utc",
            "operator_name",
            "geometry_override",
            "plot_override",
            "text_override",
            "notes",
        }
        extras = {k: deepcopy(v) for k, v in (data or {}).items() if k not in known}
        return cls(
            warning_id=str((data or {}).get("warning_id", "")),
            navarea=str((data or {}).get("navarea", "")),
            saved_utc=str((data or {}).get("saved_utc", "")),
            operator_name=(data or {}).get("operator_name"),
            geometry_override=_copy_dict((data or {}).get("geometry_override")),
            plot_override=_copy_dict((data or {}).get("plot_override")),
            text_override=_copy_dict((data or {}).get("text_override")),
            notes=_copy_dict((data or {}).get("notes")),
            extras=extras,
        )
