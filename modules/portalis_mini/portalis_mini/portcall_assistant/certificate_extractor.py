from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from .models import ExtractedField


CERTIFICATE_NAME_PATTERNS = [
    r"(international\s+oil\s+pollution\s+prevention\s+certificate)",
    r"(international\s+air\s+pollution\s+prevention\s+certificate)",
    r"(cargo\s+ship\s+safety\s+construction\s+certificate)",
    r"(cargo\s+ship\s+safety\s+equipment\s+certificate)",
    r"(cargo\s+ship\s+safety\s+radio\s+certificate)",
    r"(international\s+ship\s+security\s+certificate)",
    r"(safety\s+management\s+certificate)",
    r"(document\s+of\s+compliance)",
    r"(maritime\s+labour\s+certificate)",
]

DATE_PATTERNS = {
    "issue_date": [
        r"(?:date\s+of\s+issue|issued\s+on|issue\s+date)\s*[:\-]?\s*([A-Z0-9,\-\/ ]{6,30})",
    ],
    "expiry_date": [
        r"(?:date\s+of\s+expiry|expiry\s+date|valid\s+until|expires\s+on)\s*[:\-]?\s*([A-Z0-9,\-\/ ]{6,30})",
    ],
}

NUMBER_PATTERNS = [
    r"(?:certificate\s*(?:no\.?|number)|cert\.\s*no\.?)\s*[:\-]?\s*([A-Z0-9\-/]{4,40})",
    r"(?:no\.?|number)\s*[:\-]\s*([A-Z0-9\-/]{4,40})",
]

ISSUER_PATTERNS = [
    r"(?:issued\s+by|issuing\s+authority)\s*[:\-]\s*([^\n]+)",
    r"(?:administration)\s*[:\-]\s*([^\n]+)",
]


class CertificateExtractor:
    def extract(self, text: str, source_name: str) -> tuple[Dict[str, ExtractedField], List[str]]:
        warnings: List[str] = []
        out: Dict[str, ExtractedField] = {}

        name = self._first_match(CERTIFICATE_NAME_PATTERNS, text)
        if name:
            out["canonical_name"] = ExtractedField(name.title(), source_name, 0.82, "regex_pdf_extract")
        else:
            warnings.append("Certificate: could not classify canonical name")

        number = self._first_match(NUMBER_PATTERNS, text)
        if number:
            out["number"] = ExtractedField(number, source_name, 0.84, "regex_pdf_extract")
        else:
            warnings.append("Certificate: could not locate certificate number")

        for field_name, patterns in DATE_PATTERNS.items():
            value = self._first_match(patterns, text)
            if value:
                out[field_name] = ExtractedField(value, source_name, 0.78, "regex_pdf_extract")
            else:
                warnings.append(f"Certificate: could not locate {field_name}")

        issuer = self._first_match(ISSUER_PATTERNS, text)
        if issuer:
            out["issuer"] = ExtractedField(issuer, source_name, 0.72, "regex_pdf_extract")

        return out, warnings

    def _first_match(self, patterns: List[str], text: str) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._clean(match.group(1))
        return None

    def _clean(self, value: str) -> str:
        value = " ".join(value.replace("\xa0", " ").split())
        return value.strip(" .:-")
