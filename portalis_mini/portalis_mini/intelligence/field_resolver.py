from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .candidate_extractor import Candidate
from .profiles.profile_registry import DocumentProfile, FieldRule


@dataclass(slots=True)
class ResolvedField:
    field_name: str
    value: str
    confidence: float
    chosen_candidate: Candidate
    alternate_candidates: List[Candidate] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class FieldResolutionResult:
    document_type: str
    resolved_fields: Dict[str, ResolvedField]
    warnings: List[str] = field(default_factory=list)
    trace: Dict[str, object] = field(default_factory=dict)


class FieldResolver:
    def resolve(
        self,
        document_type: str,
        profile: DocumentProfile,
        candidates: List[Candidate],
    ) -> FieldResolutionResult:
        resolved_fields: Dict[str, ResolvedField] = {}
        warnings: List[str] = []

        for canonical_field, rule in profile.field_rules.items():
            matching = self._filter_candidates(rule, candidates)
            if not matching:
                if rule.required:
                    warnings.append(f"Missing required field: {canonical_field}")
                continue

            ranked = sorted(
                matching,
                key=lambda c: self._score_candidate(rule, c),
                reverse=True,
            )

            best = ranked[0]
            resolved_fields[canonical_field] = ResolvedField(
                field_name=canonical_field,
                value=best.value,
                confidence=min(1.0, self._score_candidate(rule, best)),
                chosen_candidate=best,
                alternate_candidates=ranked[1:4],
            )

        return FieldResolutionResult(
            document_type=document_type,
            resolved_fields=resolved_fields,
            warnings=warnings,
            trace={
                "candidate_count": len(candidates),
                "resolved_count": len(resolved_fields),
            },
        )

    def _filter_candidates(self, rule: FieldRule, candidates: List[Candidate]) -> List[Candidate]:
        out: List[Candidate] = []

        for candidate in candidates:
            type_ok = candidate.candidate_type in rule.accepted_candidate_types
            label_ok = (not rule.accepted_labels) or (candidate.label in rule.accepted_labels)

            if candidate.candidate_type == "labeled_value":
                if type_ok and label_ok:
                    out.append(candidate)
            else:
                if type_ok:
                    if candidate.label is None or label_ok:
                        out.append(candidate)

        return out

    def _score_candidate(self, rule: FieldRule, candidate: Candidate) -> float:
        score = candidate.confidence

        if candidate.label and candidate.label in rule.accepted_labels:
            score += 0.15

        if candidate.source_method in rule.preferred_source_methods:
            score += 0.12

        if candidate.candidate_type == "mrz_field":
            score += 0.30
        
        if candidate.source_method == "mrz_parse":
            score += 0.15
            
        return min(score, 1.0)