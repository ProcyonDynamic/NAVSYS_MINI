from __future__ import annotations

from typing import List, Dict, Optional

from .pdf_ocr_loader import ocr_pdf_pages

# For Mini v0.1: since many PDFs are photo-PDFs, we can OCR everything.
# If later you want hybrid TEXT/OCR, we can add pdfplumber/pypdf text extraction.
def ingest_pdf_ocr_only(
    pdf_path: str,
    *,
    poppler_path: Optional[str] = None,
    tesseract_cmd: Optional[str] = None,
    dpi: int = 250
) -> List[Dict]:
    return ocr_pdf_pages(
        pdf_path,
        poppler_path=poppler_path,
        tesseract_cmd=tesseract_cmd,
        dpi=dpi
    )