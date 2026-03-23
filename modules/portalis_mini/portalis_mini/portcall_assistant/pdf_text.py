from __future__ import annotations

from pathlib import Path
from typing import Optional

import fitz


def extract_pdf_text(pdf_path: str | Path) -> str:
    path = Path(pdf_path)
    doc = fitz.open(path)
    try:
        parts = []
        for page in doc:
            text = page.get_text("text") or ""
            parts.append(text)
        return "\n\n".join(parts).strip()
    finally:
        doc.close()


def has_meaningful_pdf_text(text: str, minimum_chars: int = 80) -> bool:
    compact = " ".join(text.split())
    return len(compact) >= minimum_chars
