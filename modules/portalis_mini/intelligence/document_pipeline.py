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

@dataclass(slots=True)
class DocumentPipelineResult:
    source_path: str
    ocr_text: str
    ocr_pages: List[dict] = field(default_factory=list)
    field_evidence: dict = field(default_factory=dict)
    classification: Optional[DocumentClassification] = None
    extraction: Optional[ExtractionResult] = None
    canonical: Optional[CanonicalMappingResult] = None
    resolved_fields: Optional[dict] = None
    canonical_fields: dict = field(default_factory=dict)
    confidence: float = 0.0
    review_required: bool = False
    review_reasons: List[str] = field(default_factory=list)

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
            ocr_pages=[
                {
                    "page_number": page.page_number,
                    "engine": page.engine,
                    "source_image_path": page.source_image_path,
                    "preprocess_steps": list((page.preprocess_result or {}).get("steps_applied", [])),
                }
                for page in ocr_result.pages
            ],
        )

        if not full_text.strip():
            result.warnings.append("OCR returned empty text")
            result.review_required = True
            result.review_reasons.append("EMPTY_OCR_TEXT")
            return result

        # ---------- CLASSIFICATION ----------
        print("\nFULL OCR TEXT FOR CLASSIFIER:")
        print(full_text[:3000])
        classification = self.classifier.classify(full_text)
        result.classification = classification
        if classification is None:
            result.warnings.append("Document type could not be classified")
            result.review_required = True
            result.review_reasons.append("CLASSIFICATION_FAILED")
            return result
        
        # ---------- BUILD OCR PAYLOAD ----------
        selected_pages = list(ocr_result.pages)

        if classification.document_type == "passport":
            passport_pages = [
                page
                for page in ocr_result.pages
                if self._page_matches_document_type(page.text, "passport")
            ]
            if passport_pages:
                selected_pages = passport_pages

        payload = {
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "lines": (page.raw or {}).get("lines", []),
                }
                for page in selected_pages
            ]
        }
        
        print("\nSELECTED PAGES FOR EXTRACTION:")
        print([page.page_number for page in selected_pages])
        
        # ---------- CANDIDATE EXTRACTION ----------
        candidate_result = self.candidate_extractor.extract(payload)
        # DEBUG
        print("\nCANDIDATES:")
        print(f"  total={len(candidate_result.candidates)}")
        for c in candidate_result.candidates:
            if c.candidate_type == "mrz_field":
                print("  MRZ:", c.label, "=", c.value, "|", c.source_method, "|", c.confidence)        
        
        result.warnings.extend(candidate_result.warnings)

        # ---------- PROFILE LOOKUP ----------
        profile = self.profile_registry.get_profile(classification.document_type)

        if profile is None:
            result.warnings.append(
                f"No profile found for document type: {classification.document_type}"
            )
            result.review_required = True
            result.review_reasons.append("PROFILE_NOT_FOUND")
            return result

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
        result.field_evidence = self._build_field_evidence(
            classification.document_type,
            resolution.resolved_fields,
            selected_pages,
        )

        result.canonical_fields = canonical.mapped_fields or {}
        result.confidence = 0.9 if result.canonical_fields else 0.0

        if not result.canonical_fields:
            result.review_required = True
            result.review_reasons.append("NO_CANONICAL_FIELDS")

        if resolution.warnings:
            result.review_required = True
            result.review_reasons.extend(resolution.warnings)

        if canonical.warnings:
            result.review_required = True
            result.review_reasons.extend(canonical.warnings)

        return result

    def _build_field_evidence(self, document_type: str, resolved_fields: dict, pages: list) -> dict:
        page_engine_map = {page.page_number: page.engine for page in pages}
        field_map = self._canonical_field_map(document_type)
        evidence = {}

        for source_field, resolved in resolved_fields.items():
            canonical_field = field_map.get(source_field)
            if not canonical_field:
                continue

            chosen = resolved.chosen_candidate
            evidence[canonical_field] = {
                "field_name": canonical_field,
                "parsed_value": resolved.value,
                "candidate_text": chosen.source_line or chosen.value,
                "source_engine": page_engine_map.get(chosen.source_page),
                "source_kind": chosen.candidate_type,
                "source_method": chosen.source_method,
                "source_line": chosen.source_line,
                "source_snippet": chosen.source_line or chosen.value,
                "source_page": chosen.source_page,
                "candidate_index": 0,
                "provenance_branch": "mrz" if chosen.candidate_type == "mrz_field" else "ocr",
                "provenance_path": "mapped_canonical",
                "notes": [f"mapped_from:{source_field}"],
                "warnings": list(resolved.warnings),
                "alternate_values": [
                    {
                        "value": candidate.value,
                        "source_kind": candidate.candidate_type,
                        "source_method": candidate.source_method,
                        "source_line": candidate.source_line,
                        "source_snippet": candidate.source_line or candidate.value,
                        "candidate_index": idx + 1,
                        "provenance_branch": "mrz" if candidate.candidate_type == "mrz_field" else "ocr",
                        "provenance_path": "alternate_candidate",
                    }
                    for idx, candidate in enumerate(resolved.alternate_candidates)
                ],
            }

        return evidence
    
    def _page_matches_document_type(self, text: str, document_type: str) -> bool:
        text_upper = (text or "").upper()

        if document_type == "passport":
            positive_signals = [
                "PASSPORT",
                "HELLAS",
                "SURNAME",
                "NATIONALITY",
                "PLACE OF BIRTH",
                "DATE OF BIRTH",
                "P<",
            ]

            negative_signals = [
                "VISA",
                "UNITED STATES OF AMERICA",
                "VISA TYPE",
                "ISSUE DATE",
                "ENTRIES",
            ]

            positive_score = sum(1 for s in positive_signals if s in text_upper)
            negative_score = sum(1 for s in negative_signals if s in text_upper)

            return positive_score >= 2 and negative_score == 0

        return True
    
    def _resolved_to_canonical_input(self, document_type: str, resolved_fields: dict) -> dict:
        field_map = self._canonical_field_map(document_type)

        out = {}
        for src_key, resolved in resolved_fields.items():
            dst_key = field_map.get(src_key)
            if dst_key:
                out[dst_key] = resolved.value
        return out

    def _canonical_field_map(self, document_type: str) -> dict:
        if document_type == "passport":
            return {
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
        return {}
