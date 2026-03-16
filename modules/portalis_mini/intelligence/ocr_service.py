from __future__ import annotations

import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytesseract
from PIL import Image
from pdf2image import convert_from_path

try:
    SURYA_AVAILABLE = None
except Exception:
    RecognitionPredictor = None
    DetectionPredictor = None
    SURYA_AVAILABLE = False

from .image_preprocess_service import (
    PreprocessOptions,
    PreprocessResult,
    preprocess_image,
    save_preprocess_metadata,
)


@dataclass(slots=True)
class OCRPageResult:
    page_number: int
    text: str
    engine: str
    source_image_path: Optional[str] = None
    preprocess_result: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class OCRResult:
    source_path: str
    pages: List[OCRPageResult]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


class OCRServiceError(Exception):
    pass


class OCRService:
    def __init__(
        self,
        tesseract_cmd: str | None = None,
        poppler_path: str | None = None,
        default_engine: str = "surya",
    ) -> None:
        self.poppler_path = poppler_path
        self.default_engine = default_engine
        self._surya_recognizer = None
        self._surya_detector = None

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _get_surya(self):
        global SURYA_AVAILABLE

        try:
            if self._surya_detector is not None and self._surya_recognizer is not None:
                return self._surya_detector, self._surya_recognizer

            from surya.detection import DetectionPredictor
            from surya.recognition import RecognitionPredictor

            self._surya_detector = DetectionPredictor()
            self._surya_recognizer = RecognitionPredictor()
            SURYA_AVAILABLE = True
            return self._surya_detector, self._surya_recognizer

        except Exception as exc:
            SURYA_AVAILABLE = False
            raise OCRServiceError(f"Surya init failed: {exc}") from exc

    def extract_text(
        self,
        file_path: str | Path,
        work_dir: str | Path | None = None,
        engine: str | None = None,
        preprocess: bool = True,
    ) -> OCRResult:
        path = Path(file_path)
        if not path.exists():
            raise OCRServiceError(f"File not found: {path}")

        engine = engine or self.default_engine
        work_dir = Path(work_dir) if work_dir else path.parent / "_ocr_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_from_pdf(path, work_dir=work_dir, engine=engine, preprocess=preprocess)

        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return self._extract_from_image(path, work_dir=work_dir, engine=engine, preprocess=preprocess)

        raise OCRServiceError(f"Unsupported file type for OCR: {suffix}")

    def _extract_from_pdf(
        self,
        path: Path,
        work_dir: Path,
        engine: str,
        preprocess: bool,
    ) -> OCRResult:
        try:
            images = convert_from_path(str(path), poppler_path=self.poppler_path)
        except Exception as exc:
            raise OCRServiceError(f"Failed to convert PDF to images: {exc}") from exc

        pages: List[OCRPageResult] = []
        pdf_img_dir = work_dir / path.stem / "pdf_pages"
        pdf_img_dir.mkdir(parents=True, exist_ok=True)

        for idx, image in enumerate(images, start=1):
            raw_page_path = pdf_img_dir / f"page_{idx:03d}.png"
            image.save(raw_page_path)

            page_result = self._ocr_single_image(
                image_path=raw_page_path,
                page_number=idx,
                work_dir=work_dir / path.stem,
                engine=engine,
                preprocess=preprocess,
            )
            pages.append(page_result)

        return OCRResult(source_path=str(path), pages=pages)

    def _extract_from_image(
        self,
        path: Path,
        work_dir: Path,
        engine: str,
        preprocess: bool,
    ) -> OCRResult:
        page = self._ocr_single_image(
            image_path=path,
            page_number=1,
            work_dir=work_dir / path.stem,
            engine=engine,
            preprocess=preprocess,
        )
        return OCRResult(source_path=str(path), pages=[page])

    def _ocr_single_image(
        self,
        image_path: Path,
        page_number: int,
        work_dir: Path,
        engine: str,
        preprocess: bool,
    ) -> OCRPageResult:
        work_dir.mkdir(parents=True, exist_ok=True)

        ocr_input_path = image_path
        preprocess_result: Optional[PreprocessResult] = None

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

        text: str
        raw: Dict[str, Any]

        actual_engine = engine

        if engine == "surya":
            try:
                text, raw = self._run_surya(ocr_input_path)
            except OCRServiceError as exc:
                text, tesseract_raw = self._run_tesseract(ocr_input_path)
                actual_engine = "tesseract"
                raw = {
                    "fallback_from": "surya",
                    "fallback_reason": str(exc),
                    "tesseract_result": tesseract_raw,
                }
        elif engine == "tesseract":
            text, raw = self._run_tesseract(ocr_input_path)
            actual_engine = "tesseract"
        else:
            raise OCRServiceError(f"Unsupported OCR engine: {engine}")
        
        return OCRPageResult(
            page_number=page_number,
            text=text.strip(),
            engine=actual_engine,
            source_image_path=str(ocr_input_path),
            preprocess_result=None if preprocess_result is None else {
                "source_path": preprocess_result.source_path,
                "output_path": preprocess_result.output_path,
                "steps_applied": preprocess_result.steps_applied,
                "diagnostics": preprocess_result.diagnostics,
            },
            raw=raw,
        )

    def _run_tesseract(self, image_path: Path) -> tuple[str, Dict[str, Any]]:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(
                image,
                lang="eng+ell",
                config="--oem 3 --psm 6"
            )
            
            return text, {
                "engine": "tesseract",
                "input_path": str(image_path),
            }
        except Exception as exc:
            raise OCRServiceError(f"Tesseract OCR failed: {exc}") from exc

    def _run_surya(self, image_path: Path) -> tuple[str, Dict[str, Any]]:
        try:
            from PIL import Image

            detector, recognizer = self._get_surya()

            image = Image.open(image_path).convert("RGB")

            det_results = detector([image])
            rec_results = recognizer([image], det_results)

            lines: List[str] = []
            raw_lines: List[Dict[str, Any]] = []

            page_result = rec_results[0]

            text_lines = getattr(page_result, "text_lines", None)
            if text_lines is None:
                raise OCRServiceError("Surya returned no text_lines output.")

            for line in text_lines:
                text = getattr(line, "text", "") or ""
                if not text.strip():
                    continue

                polygon = getattr(line, "polygon", None)
                bbox = getattr(line, "bbox", None)

                lines.append(text)
                raw_lines.append({
                    "text": text,
                    "polygon": polygon,
                    "bbox": bbox,
                })

            return "\n".join(lines), {
                "engine": "surya",
                "input_path": str(image_path),
                "lines": raw_lines,
            }

        except Exception as exc:
            raise OCRServiceError(f"Surya OCR failed: {exc}") from exc