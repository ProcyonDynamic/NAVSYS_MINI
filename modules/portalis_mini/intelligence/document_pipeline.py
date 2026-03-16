from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .canonical_mapper import CanonicalMapper, CanonicalMappingResult
from .document_classifier import DocumentClassification, DocumentClassifier
from .field_extractor import ExtractionResult, FieldExtractor
from .ocr_service import OCRResult, OCRService


@dataclass(slots=True)
class DocumentPipelineResult:
    source_path: str
    ocr_text: str
    classification: Optional[DocumentClassification] = None
    extraction: Optional[ExtractionResult] = None
    canonical: Optional[CanonicalMappingResult] = None
    warnings: List[str] = field(default_factory=list)


class DocumentPipeline:
    def __init__(
        self,
        ocr_service: OCRService,
        classifier: DocumentClassifier,
        extractor: FieldExtractor,
        mapper: CanonicalMapper,
        ocr_engine: str = "paddle",
    ) -> None:
        self.ocr_service = ocr_service
        self.classifier = classifier
        self.extractor = extractor
        self.mapper = mapper
        self.ocr_engine = ocr_engine

    def process_file(self, file_path: str | Path) -> DocumentPipelineResult:
        file_path = Path(file_path)

        ocr_result: OCRResult = self.ocr_service.extract_text(
            file_path=file_path,
            work_dir=file_path.parent / "_portalis_work",
            engine=self.ocr_engine,
            preprocess=True,
        )
        full_text = ocr_result.full_text

        result = DocumentPipelineResult(
            source_path=str(file_path),
            ocr_text=full_text,
        )

        classification = self.classifier.classify(full_text)
        result.classification = classification

        if classification is None:
            result.warnings.append("Document type could not be classified")
            return result

        extraction = self.extractor.extract(classification.document_type, full_text)
        result.extraction = extraction
        result.warnings.extend(extraction.warnings)

        canonical = self.mapper.map_fields(extraction.extracted_fields)
        result.canonical = canonical
        result.warnings.extend(canonical.warnings)

        return result