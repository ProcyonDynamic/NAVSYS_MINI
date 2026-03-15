from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from portalis_models import CrewRecord, IdentityDocument


class RecordUpdateServiceError(Exception):
    """Raised when Portalis record updates fail."""


class RecordUpdateService:
    def __init__(self, portalis_data_root: str | Path) -> None:
        self.data_root = Path(portalis_data_root)
        self.crew_root = self.data_root / "crew"
        self.certs_root = self.data_root / "certs"
        self.generated_root = self.data_root / "generated"

        self.crew_root.mkdir(parents=True, exist_ok=True)
        self.certs_root.mkdir(parents=True, exist_ok=True)
        self.generated_root.mkdir(parents=True, exist_ok=True)

    def update_crew_from_mapped_fields(
        self,
        crew_id: str,
        mapped_fields: Dict[str, str],
        source_file: Optional[str] = None,
    ) -> Path:
        crew_dir = self.crew_root / crew_id
        crew_dir.mkdir(parents=True, exist_ok=True)

        record_path = crew_dir / "record.json"
        record = self._load_json(record_path)

        record.setdefault("crew_id", crew_id)
        record.setdefault("rank", None)
        record.setdefault("family_name", "")
        record.setdefault("given_name", "")
        record.setdefault("middle_initial", None)
        record.setdefault("nationality", None)
        record.setdefault("date_of_birth", None)
        record.setdefault("place_of_birth", None)
        record.setdefault("passports", [])
        record.setdefault("seaman_books", [])
        record.setdefault("visas", [])
        record.setdefault("vaccinations", [])
        record.setdefault("notes", None)

        if "crew.family_name" in mapped_fields:
            record["family_name"] = mapped_fields["crew.family_name"]

        if "crew.given_name" in mapped_fields:
            record["given_name"] = mapped_fields["crew.given_name"]

        if "crew.middle_initial" in mapped_fields:
            record["middle_initial"] = mapped_fields["crew.middle_initial"]

        if "crew.nationality" in mapped_fields:
            record["nationality"] = mapped_fields["crew.nationality"]

        if "crew.date_of_birth" in mapped_fields:
            record["date_of_birth"] = mapped_fields["crew.date_of_birth"]

        if "crew.place_of_birth" in mapped_fields:
            record["place_of_birth"] = mapped_fields["crew.place_of_birth"]

        passport_number = mapped_fields.get("passport.number")
        if passport_number:
            passport_entry = self._find_or_create_document_entry(
                record["passports"],
                number=passport_number,
                document_type="passport",
            )

            passport_entry["number"] = passport_number
            passport_entry["issuing_state"] = mapped_fields.get("passport.issue_state")
            passport_entry["issue_date"] = mapped_fields.get("passport.issue_date")
            passport_entry["expiry_date"] = mapped_fields.get("passport.expiry_date")
            passport_entry["nationality"] = mapped_fields.get("crew.nationality")
            passport_entry["source_file"] = source_file

        self._write_json(record_path, record)
        return record_path

    def _find_or_create_document_entry(
        self,
        entries: list[Dict[str, Any]],
        number: str,
        document_type: str,
    ) -> Dict[str, Any]:
        for entry in entries:
            if entry.get("number") == number:
                return entry

        new_entry: Dict[str, Any] = {
            "document_type": document_type,
            "number": number,
        }
        entries.append(new_entry)
        return new_entry

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)