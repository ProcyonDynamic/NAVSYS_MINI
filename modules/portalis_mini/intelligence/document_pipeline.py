from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .ocr_service import OCRResult, OCRService
from .document_classifier import DocumentClassification, DocumentClassifier
from .field_extractor import ExtractionResult, FieldExtractor
from .canonical_mapper import CanonicalMapper, CanonicalMappingResult

from .candidate_extractor import CandidateExtractor
from .field_resolver import FieldResolver
from .profiles.profile_registry import ProfileRegistry
from ..archive.document_registry import DocumentRegistry

@dataclass(slots=True)
class DocumentPipelineResult:
    source_path: str
    ocr_text: str
    classification: Optional[DocumentClassification] = None
    extraction: Optional[ExtractionResult] = None
    canonical: Optional[CanonicalMappingResult] = None
    resolved_fields: Optional[dict] = None
    tce_bundle: Optional[object] = None
    warnings: List[str] = field(default_factory=list)


class DocumentPipeline:

    def __init__(
        self,
        ocr_service: OCRService,
        classifier: DocumentClassifier,
        extractor: FieldExtractor,
        mapper: CanonicalMapper,
        ocr_engine: str = "surya",
    ) -> None:

        self.ocr_service = ocr_service
        self.classifier = classifier
        self.extractor = extractor
        self.mapper = mapper
        self.ocr_engine = ocr_engine
        self.registry = DocumentRegistry(Path("data/PORTALIS"))

        # new intelligence modules
        self.candidate_extractor = CandidateExtractor()
        self.profile_registry = ProfileRegistry()
        self.field_resolver = FieldResolver()

    def process_file(self, file_path: str | Path) -> DocumentPipelineResult:

        file_path = Path(file_path)

        # ---------- OCR ----------
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

        # ---------- CLASSIFICATION ----------
        print("\nFULL OCR TEXT FOR CLASSIFIER:")
        print(full_text[:3000])
        classification = self.classifier.classify(full_text)
        result.classification = classification
        if classification is None:
            result.warnings.append("Document type could not be classified")
            return result

        # ---------- BUILD OCR PAYLOAD ----------
        payload = {
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "lines": (page.raw or {}).get("lines", []),
                }
                for page in ocr_result.pages
            ]
        }

        # ---------- CANDIDATE EXTRACTION ----------
        candidate_result = self.candidate_extractor.extract(payload)
        # DEBUG
        print("\nCANDIDATES:")
        for c in candidate_result.candidates:
            if c.candidate_type == "mrz_field":
                print("  MRZ:", c.label, "=", c.value, "|", c.source_method, "|", c.confidence)
        result.warnings.extend(candidate_result.warnings)

        # ---------- PROFILE LOOKUP ----------
        profile = self.profile_registry.get_profile(classification.document_type)

        if profile is not None:
            resolution = self.field_resolver.resolve(
                document_type=classification.document_type,
                profile=profile,
                candidates=candidate_result.candidates,
            )

            # DEBUG
            print("\nRESOLVED FIELDS:")
            for name, rf in resolution.resolved_fields.items():
                print(
                    f"  {name}: {rf.value} "
                    f"(type={rf.chosen_candidate.candidate_type}, "
                    f"label={rf.chosen_candidate.label}, "
                    f"source={rf.chosen_candidate.source_method}, "
                    f"conf={rf.confidence})"
            )

            resolved_input = self._resolved_to_canonical_input(
                classification.document_type,
                resolution.resolved_fields,
            )

            canonical = self.mapper.map_fields(resolved_input)
            result.canonical = canonical
            result.warnings.extend(canonical.warnings)
            result.warnings.extend(resolution.warnings)

            result.resolved_fields = {
                k: v.value for k, v in resolution.resolved_fields.items()
            }

            if canonical.mapped_fields:
                doc_id = self.registry.register_document(
                    doc_type=classification.document_type,
                    owner_entity="unknown",
                    owner_id="unknown",
                    source_file=file_path,
                    parsed_fields=canonical.mapped_fields,
                    confidence=0.9,
                )
                result.warnings.append(f"Document stored with ID {doc_id}")

            return result
    
    def _resolved_to_canonical_input(self, document_type: str, resolved_fields: dict) -> dict:
        if document_type == "passport":
            field_map = {
                "passport_number": "passport.number",
                "surname": "crew.surname",
                "given_names": "crew.given_names",
                "nationality": "crew.nationality",
                "date_of_birth": "crew.date_of_birth",
                "sex": "crew.sex",
                "place_of_birth": "crew.place_of_birth",
                "issue_date": "passport.issue_date",
                "expiry_date": "passport.expiry_date",
            }
        else:
            field_map = {}

        out = {}
        for src_key, resolved in resolved_fields.items():
            dst_key = field_map.get(src_key)
            if dst_key:
                out[dst_key] = resolved.value
        return out