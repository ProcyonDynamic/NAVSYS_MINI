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


def load_ship_particulars(pdf_path: str) -> Dict[str, str]:
    text = _read_pdf_text(pdf_path)

    return {
        "ship_name": _extract(r"Name of Ship:\s*(.+)", text),
        "imo": _extract(r"IMO No\.\s*([0-9]+)", text),
        "call_sign": _extract(r"Call Sign\s*([A-Z0-9]+)", text),
        "flag": _extract(r"Flag\s*([A-Z\s]+)", text),
        "home_port": _extract(r"Home Port\s*([A-Z\s]+)", text),
        "official_no": _extract(r"Register/Official No\.\s*([0-9]+)", text),
        "ship_type": _extract(r"Ship's Type\s*[: ]\s*(.+)", text),
    }