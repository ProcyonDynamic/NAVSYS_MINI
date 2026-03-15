
from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, Optional

from image_preprocess_service import (
    PreprocessOptions,
    preprocess_image,
    save_preprocess_metadata,
)

import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pytesseract
from PIL import Image
from pdf2image import convert_from_path


from paddleocr import PaddleOCR

def run_ocr_on_image(
    image_path: str | Path,
    work_dir: str | Path,
    engine: str = "paddle",
    preprocess: bool = True,
) -> Dict[str, Any]:
    image_path = Path(image_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    ocr_input_path = image_path
    preprocess_result = None

    if preprocess:
        pre_dir = work_dir / "preprocessed"
        pre_dir.mkdir(parents=True, exist_ok=True)

        out_path = pre_dir / f"{image_path.stem}_preprocessed.png"
        meta_path = pre_dir / f"{image_path.stem}_preprocess.json"

        preprocess_result = preprocess_image(
            image_path=image_path,
            output_path=out_path,
            options=PreprocessOptions(
                grayscale=True,
                denoise=True,
                deskew=True,
                contrast_boost=True,
                adaptive_binarize=False,
                resize_min_width=1800,
                sharpen=True,
                trim_border=False,
                save_debug_steps=False,
            ),
        )
        save_preprocess_metadata(preprocess_result, meta_path)
        ocr_input_path = Path(preprocess_result.output_path)

    # --- replace this block with your real OCR logic ---
    if engine == "paddle":
        text = f"[PADDLE OCR PLACEHOLDER] OCR executed on {ocr_input_path.name}"
        raw = {"engine": "paddle", "input_path": str(ocr_input_path)}
    elif engine == "tesseract":
        text = f"[TESSERACT PLACEHOLDER] OCR executed on {ocr_input_path.name}"
        raw = {"engine": "tesseract", "input_path": str(ocr_input_path)}
    else:
        raise ValueError(f"Unsupported OCR engine: {engine}")
    # ---------------------------------------------------

    return {
        "ok": True,
        "engine": engine,
        "source_image_path": str(image_path),
        "ocr_input_path": str(ocr_input_path),
        "preprocess_result": None if preprocess_result is None else preprocess_result.__dict__,
        "text": text,
        "raw": raw,
    }

@dataclass(slots=True)
class OCRPageResult:
    page_number: int
    text: str


@dataclass(slots=True)
class OCRResult:
    source_path: str
    pages: List[OCRPageResult]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


class OCRServiceError(Exception):
    """Raised when OCR processing fails."""


class OCRService:
    def __init__(self, tesseract_cmd: str | None = None, poppler_path: str | None = None) -> None:
        self.poppler_path = poppler_path
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text(self, file_path: str | Path) -> OCRResult:
        path = Path(file_path)

        if not path.exists():
            raise OCRServiceError(f"File not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_from_pdf(path)

        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return self._extract_from_image(path)

        raise OCRServiceError(f"Unsupported file type for OCR: {suffix}")

    def _extract_from_pdf(self, path: Path) -> OCRResult:
        try:
            images = convert_from_path(str(path), poppler_path=self.poppler_path)
        except Exception as exc:
            raise OCRServiceError(f"Failed to convert PDF to images: {exc}") from exc

        pages: List[OCRPageResult] = []

        for idx, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image)
            pages.append(OCRPageResult(page_number=idx, text=text.strip()))

        return OCRResult(source_path=str(path), pages=pages)

    def _extract_from_image(self, path: Path) -> OCRResult:
        try:
            image = Image.open(path)
            text = pytesseract.image_to_string(image)
        except Exception as exc:
            raise OCRServiceError(f"Failed to OCR image: {exc}") from exc

        return OCRResult(
            source_path=str(path),
            pages=[OCRPageResult(page_number=1, text=text.strip())],
        )