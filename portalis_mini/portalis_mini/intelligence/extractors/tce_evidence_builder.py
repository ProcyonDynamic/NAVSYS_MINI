from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class TCEFieldEvidence:
    field_name: str
    canonical_value: str
    confidence: float
    source_method: str
    source_page: int | None
    source_lines: List[str]
    slices: List[str]
    review_status: str
    trace: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TCEEvidenceBundle:
    document_type: str
    evidences: List[TCEFieldEvidence]
    warnings: List[str]
    trace: Dict[str, Any] = field(default_factory=dict)


class TCEEvidenceBuilder:
    FIELD_SLICE_MAP = {
        "passport_number": ["WHAT", "WHO"],
        "surname": ["WHO"],
        "given_names": ["WHO"],
        "nationality": ["WHO", "WHERE"],
        "date_of_birth": ["WHEN", "WHO"],
        "sex": ["WHO"],
        "expiry_date": ["WHEN", "WHAT"],
        "issue_date": ["WHEN", "WHAT"],
        "place_of_birth": ["WHERE", "WHO"],
    }

    def build_from_passport_extraction(self, extraction_result) -> TCEEvidenceBundle:
        evidences: List[TCEFieldEvidence] = []

        for field_name, field in extraction_result.fields.items():
            evidences.append(
                TCEFieldEvidence(
                    field_name=field_name,
                    canonical_value=field.field_value,
                    confidence=field.confidence,
                    source_method=field.source_method,
                    source_page=1,
                    source_lines=field.source_lines,
                    slices=self.FIELD_SLICE_MAP.get(field_name, ["WHAT"]),
                    review_status="REVIEW_REQUIRED" if extraction_result.review_required else "AUTO",
                    trace=field.trace,
                )
            )

        return TCEEvidenceBundle(
            document_type=extraction_result.document_type,
            evidences=evidences,
            warnings=extraction_result.warnings,
            trace=extraction_result.trace,
        )