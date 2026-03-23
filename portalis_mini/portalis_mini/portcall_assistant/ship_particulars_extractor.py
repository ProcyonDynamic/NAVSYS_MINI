from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from .models import ExtractedField


class ShipParticularsExtractor:
    FIELD_PATTERNS = {
        "vessel_name": [r"(?:vessel\s+name|name\s+of\s+ship)\s*[:\-]\s*([^\n]+)"],
        "imo_number": [r"\bIMO\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d{7})\b"],
        "call_sign": [r"(?:call\s*sign)\s*[:\-]\s*([A-Z0-9]{3,10})\b"],
        "flag_state": [r"(?:flag|flag\s+state|port\s+of\s+registry)\s*[:\-]\s*([^\n]+)"],
        "gross_tonnage": [r"(?:gross\s+tonnage|GRT|GT)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"],
        "net_tonnage": [r"(?:net\s+tonnage|NRT|NT)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"],
        "deadweight": [r"(?:deadweight|DWT)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"],
        "loa_m": [r"(?:length\s+overall|LOA)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*m?\b"],
        "beam_m": [r"(?:beam|breadth)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*m?\b"],
        "owner_name": [r"(?:owner|registered\s+owner)\s*[:\-]\s*([^\n]+)"],
        "operator_name": [r"(?:operator|manager|technical\s+manager)\s*[:\-]\s*([^\n]+)"],
    }

    def extract(self, text: str, source_name: str) -> tuple[Dict[str, ExtractedField], List[str]]:
        out: Dict[str, ExtractedField] = {}
        warnings: List[str] = []
        for field_name, patterns in self.FIELD_PATTERNS.items():
            value = None
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    value = self._clean(match.group(1))
                    break
            if value:
                out[field_name] = ExtractedField(
                    value=value,
                    source=source_name,
                    confidence=0.86,
                    method="regex_pdf_extract",
                )
            else:
                warnings.append(f"Ship particulars: no match for {field_name}")
        return out, warnings

    def _clean(self, value: str) -> str:
        value = " ".join(value.replace("\xa0", " ").split())
        return value.strip(" .:-")
