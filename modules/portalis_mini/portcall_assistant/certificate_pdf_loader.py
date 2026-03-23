from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

import pdfplumber


def _read_pdf_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def load_certificate(pdf_path: str) -> Dict[str, str]:
    text = _read_pdf_text(pdf_path)
    filename = Path(pdf_path).name

    cert_type = _extract(r"(Certificate of Registry)", text) or filename
    cert_number = _extract(r"(?:Certificate No\.?|No\.|Number)\s*[:#]?\s*([A-Z0-9\-\/]+)", text)
    issue_date = _extract(r"(?:Issue Date|Date of Issue)\s*[:#]?\s*([A-Za-z0-9\-\s]+)", text)
    expiry_date = _extract(r"(?:Expiry Date|Date of Expiry|Valid Until)\s*[:#]?\s*([A-Za-z0-9\-\s]+)", text)
    issuer = (
        _extract(r"(Republic of the Marshall Islands)", text)
        or _extract(r"(Lloyd'?s Register)", text)
        or _extract(r"(Maritime Administrator)", text)
    )
    last_survey = _extract(r"(?:Last Survey Date|Survey Date|Endorsement Date)\s*[:#]?\s*([A-Za-z0-9\-\s]+)", text)

    return {
        "name": cert_type,
        "number": cert_number,
        "issuer": issuer,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "last_survey_date": last_survey,
        "source_file": filename,
    }