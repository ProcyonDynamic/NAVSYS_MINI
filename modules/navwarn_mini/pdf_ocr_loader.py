from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional

from pdf2image import convert_from_path
import pytesseract


class PDFOCRError(Exception):
    pass


def ocr_pdf_pages(
    pdf_path: str,
    *,
    poppler_path: Optional[str] = None,
    tesseract_cmd: Optional[str] = None,
    dpi: int = 250
) -> List[Dict]:
    """
    OCR each page of a PDF (scanned/photo PDFs).
    Returns:
      [{ "page": 1, "text": "...", "source": "OCR" }, ...]
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise PDFOCRError(f"PDF not found: {pdf_path}")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            poppler_path=poppler_path
        )
    except Exception as e:
        raise PDFOCRError(f"Failed to convert PDF to images: {e}")

    pages = []
    for i, img in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(img)
        except Exception:
            text = ""
        pages.append({"page": i, "text": text or "", "source": "OCR"})
    return pages