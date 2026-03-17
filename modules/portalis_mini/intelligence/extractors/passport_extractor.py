from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .mrz_parser import MRZResult, extract_mrz_from_ocr_lines


@dataclass(slots=True)
class ExtractedField:
    field_name: str
    field_value: str
    confidence: float
    source_method: str
    source_lines: List[str] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PassportExtractionResult:
    document_type: str
    fields: Dict[str, ExtractedField]
    mrz_result: Optional[MRZResult]
    warnings: List[str]
    review_required: bool
    trace: Dict[str, Any] = field(default_factory=dict)


class PassportExtractor:
    LABEL_PATTERNS = {
        "passport_number": [
            r"passport no\.?\s*[:\-]?\s*([A-Z0-9]+)",
            r"διαβατηρίου.*?([A-Z0-9]{6,12})",
        ],
        "surname": [
            r"surname\s*[:\-]?\s*([A-Z<>\- ]+)",
        ],
        "given_names": [
            r"name\s*[:\-]?\s*([A-Z<>\- ]+)",
        ],
        "nationality": [
            r"nationality\s*[:\-]?\s*([A-Z ]+)",
        ],
        "sex": [
            r"sex\s*[:\-]?\s*([MF])",
        ],
        "place_of_birth": [
            r"place of birth\s*[:\-]?\s*([A-Z\-\s]+)",
        ],
    }

    def extract_from_ocr_payload(self, ocr_payload: Dict[str, Any]) -> PassportExtractionResult:
        warnings: List[str] = []
        all_lines: List[str] = []

        for page in ocr_payload.get("pages", []):
            for line in page.get("lines", []):
                text = (line.get("text") or "").strip()
                if text:
                    all_lines.append(text)

        mrz_result = extract_mrz_from_ocr_lines(all_lines)

        fields: Dict[str, ExtractedField] = {}

        if mrz_result:
            fields["passport_number"] = ExtractedField(
                field_name="passport_number",
                field_value=mrz_result.passport_number,
                confidence=mrz_result.confidence,
                source_method="mrz",
                source_lines=[mrz_result.raw_line_1, mrz_result.raw_line_2],
            )
            fields["surname"] = ExtractedField(
                field_name="surname",
                field_value=mrz_result.surname,
                confidence=mrz_result.confidence,
                source_method="mrz",
                source_lines=[mrz_result.raw_line_1],
            )
            fields["given_names"] = ExtractedField(
                field_name="given_names",
                field_value=mrz_result.given_names,
                confidence=mrz_result.confidence,
                source_method="mrz",
                source_lines=[mrz_result.raw_line_1],
            )
            fields["nationality"] = ExtractedField(
                field_name="nationality",
                field_value=mrz_result.nationality,
                confidence=mrz_result.confidence,
                source_method="mrz",
                source_lines=[mrz_result.raw_line_2],
            )
            if mrz_result.birth_date:
                fields["date_of_birth"] = ExtractedField(
                    field_name="date_of_birth",
                    field_value=mrz_result.birth_date,
                    confidence=mrz_result.confidence,
                    source_method="mrz",
                    source_lines=[mrz_result.raw_line_2],
                )
            if mrz_result.sex:
                fields["sex"] = ExtractedField(
                    field_name="sex",
                    field_value=mrz_result.sex,
                    confidence=mrz_result.confidence,
                    source_method="mrz",
                    source_lines=[mrz_result.raw_line_2],
                )
            if mrz_result.expiry_date:
                fields["expiry_date"] = ExtractedField(
                    field_name="expiry_date",
                    field_value=mrz_result.expiry_date,
                    confidence=mrz_result.confidence,
                    source_method="mrz",
                    source_lines=[mrz_result.raw_line_2],
                )

            warnings.extend(mrz_result.warnings)

        # Label-based backfill / enrichment
        joined_text = "\n".join(all_lines).upper()

        for field_name, patterns in self.LABEL_PATTERNS.items():
            if field_name in fields:
                continue

            value = self._first_match(joined_text, patterns)
            if value:
                fields[field_name] = ExtractedField(
                    field_name=field_name,
                    field_value=self._cleanup_value(value),
                    confidence=0.70,
                    source_method="label_ocr",
                    source_lines=[],
                )

        review_required = False

        required_fields = ["passport_number", "surname", "given_names", "nationality"]
        for req in required_fields:
            if req not in fields or not fields[req].field_value.strip():
                review_required = True
                warnings.append(f"Missing required field: {req}")

        if mrz_result is None:
            review_required = True
            warnings.append("MRZ not detected; extraction relies on OCR labels only.")

        return PassportExtractionResult(
            document_type="passport",
            fields=fields,
            mrz_result=mrz_result,
            warnings=warnings,
            review_required=review_required,
            trace={
                "line_count": len(all_lines),
                "mrz_detected": mrz_result is not None,
            },
        )

    def _first_match(self, text: str, patterns: List[str]) -> Optional[str]:
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip()
        return None

    def _cleanup_value(self, value: str) -> str:
        value = value.replace("<", " ")
        value = re.sub(r"\s+", " ", value)
        return value.strip()