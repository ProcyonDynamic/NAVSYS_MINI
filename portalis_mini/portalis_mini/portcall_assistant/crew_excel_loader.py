from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


CANONICAL_CREW_FIELDS = {
    "full_name": ["name", "full name", "crew name", "seafarer name"],
    "family_name": ["surname", "last name", "family name"],
    "given_name": ["given name", "first name", "given names"],
    "middle_name": ["middle name", "middlename", "second name"],
    "rank": ["rank", "position"],
    "nationality": ["nationality", "citizenship"],
    "date_of_birth": ["date of birth", "dob", "birth date"],
    "place_of_birth": ["place of birth", "birth place"],
    "passport_number": ["passport", "passport no", "passport number", "passport #"],
    "passport_expiry": ["passport expiry", "passport exp", "passport expiration"],
    "seaman_book_number": ["seaman book", "sbook no", "seaman book no"],
    "seaman_book_expiry": ["seaman book expiry", "sbook expiry"],
    "us_visa_number": ["us visa", "visa no", "visa number", "c1d visa", "us visa number"],
    "us_visa_expiry": ["visa expiry", "us visa expiry", "c1d expiry"],
    "gender": ["sex", "gender"],
    "height_cm": ["height", "height cm"],
    "weight_kg": ["weight", "weight kg"],
    "crew_id": ["crew id", "id"],
}


@dataclass(slots=True)
class CrewWorkbookLoadResult:
    rows: List[Dict[str, Any]]
    matched_columns: Dict[str, str]
    warnings: List[str]


class CrewExcelLoader:
    def load(self, excel_path: str | Path, sheet_name: Optional[str] = None) -> CrewWorkbookLoadResult:
        path = Path(excel_path)
        df = pd.read_excel(path, sheet_name=sheet_name or 0)
        df.columns = [self._normalize_header(str(col)) for col in df.columns]

        matched_columns: Dict[str, str] = {}
        warnings: List[str] = []

        for canonical_field, aliases in CANONICAL_CREW_FIELDS.items():
            matched = self._match_column(df.columns.tolist(), aliases)
            if matched:
                matched_columns[canonical_field] = matched

        required = ["full_name", "family_name", "given_name", "rank", "passport_number"]
        if not any(field in matched_columns for field in ["full_name", "family_name"]):
            warnings.append("Could not confidently match crew name columns.")
        for field in required:
            if field not in matched_columns and field not in {"full_name", "family_name", "given_name"}:
                warnings.append(f"No column matched for recommended field: {field}")

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            record = self._row_to_canonical(row.to_dict(), matched_columns)
            if any(v not in (None, "") for v in record.values()):
                rows.append(record)

        return CrewWorkbookLoadResult(rows=rows, matched_columns=matched_columns, warnings=warnings)

    def _row_to_canonical(self, row: Dict[str, Any], matched_columns: Dict[str, str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for canonical_field, matched_column in matched_columns.items():
            value = row.get(matched_column)
            if pd.isna(value):
                value = None
            elif hasattr(value, "isoformat"):
                value = value.isoformat()
            elif isinstance(value, float) and value.is_integer():
                value = int(value)
            out[canonical_field] = value

        if not out.get("full_name"):
            parts = [out.get("family_name"), out.get("given_name"), out.get("middle_name")]
            out["full_name"] = " ".join(str(part).strip() for part in parts if part)
        return out

    def _normalize_header(self, header: str) -> str:
        return " ".join(header.strip().lower().replace("_", " ").split())

    def _match_column(self, columns: List[str], aliases: List[str]) -> Optional[str]:
        alias_set = {self._normalize_header(alias) for alias in aliases}
        for column in columns:
            if column in alias_set:
                return column
        for column in columns:
            for alias in alias_set:
                if alias in column or column in alias:
                    return column
        return None
