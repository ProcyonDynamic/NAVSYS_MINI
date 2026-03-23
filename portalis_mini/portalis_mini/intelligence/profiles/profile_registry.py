from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class FieldRule:
    canonical_field: str
    accepted_candidate_types: List[str]
    accepted_labels: List[str] = field(default_factory=list)
    preferred_source_methods: List[str] = field(default_factory=list)
    required: bool = False


@dataclass(slots=True)
class DocumentProfile:
    document_type: str
    expected_fields: List[str]
    field_rules: Dict[str, FieldRule]
    priority_signals: List[str] = field(default_factory=list)
    validators: Dict[str, str] = field(default_factory=dict)


def build_passport_profile() -> DocumentProfile:
    return DocumentProfile(
        document_type="passport",
        expected_fields=[
            "passport_number",
            "surname",
            "given_names",
            "nationality",
            "date_of_birth",
            "sex",
            "expiry_date",
            "place_of_birth",
            "issue_date",
        ],
        field_rules={
            "passport_number": FieldRule(
                canonical_field="passport_number",
                accepted_candidate_types=["mrz_field", "labeled_value", "passport_like_number", "id_number"],
                accepted_labels=["passport_number"],
                preferred_source_methods=["mrz_parse", "label_value_regex", "regex_passport_like"],
                required=True,
            ),
            "surname": FieldRule(
                canonical_field="surname",
                accepted_candidate_types=["mrz_field", "labeled_value", "person_name"],
                accepted_labels=["surname"],
                preferred_source_methods=["mrz_parse", "label_value_regex"],
                required=True,
            ),
            "given_names": FieldRule(
                canonical_field="given_names",
                accepted_candidate_types=["mrz_field", "labeled_value", "person_name"],
                accepted_labels=["given_names"],
                preferred_source_methods=["mrz_parse", "label_value_regex"],
                required=True,
            ),
            "nationality": FieldRule(
                canonical_field="nationality",
                accepted_candidate_types=["mrz_field", "labeled_value", "country_code"],
                accepted_labels=["nationality"],
                preferred_source_methods=["mrz_parse", "label_value_regex"],
                required=True,
            ),
            "date_of_birth": FieldRule(
                canonical_field="date_of_birth",
                accepted_candidate_types=["mrz_field", "labeled_value", "date"],
                accepted_labels=["date_of_birth"],
                preferred_source_methods=["mrz_parse", "label_value_regex", "regex_date"],
            ),
            "sex": FieldRule(
                canonical_field="sex",
                accepted_candidate_types=["mrz_field", "labeled_value", "sex_marker"],
                accepted_labels=["sex"],
                preferred_source_methods=["mrz_parse", "label_value_regex", "regex_sex"],
            ),
            "expiry_date": FieldRule(
                canonical_field="expiry_date",
                accepted_candidate_types=["mrz_field", "labeled_value", "date"],
                accepted_labels=["date_of_expiry"],
                preferred_source_methods=["mrz_parse", "label_value_regex", "regex_date"],
            ),
            "place_of_birth": FieldRule(
                canonical_field="place_of_birth",
                accepted_candidate_types=["labeled_value", "location_text"],
                accepted_labels=["place_of_birth"],
                preferred_source_methods=["label_value_regex", "heuristic_location"],
            ),
            "issue_date": FieldRule(
                canonical_field="issue_date",
                accepted_candidate_types=["labeled_value", "date"],
                accepted_labels=["issue_date"],
                preferred_source_methods=["label_value_regex", "regex_date"],
            ),
        },
        priority_signals=["mrz", "passport", "nationality", "date of birth"],
        validators={
            "passport_number": "passport_number_basic",
            "date_of_birth": "date_basic",
            "expiry_date": "date_basic",
            "issue_date": "date_basic",
            "sex": "sex_basic",
        },
    )


class ProfileRegistry:
    def __init__(self) -> None:
        self._profiles: Dict[str, DocumentProfile] = {
            "passport": build_passport_profile(),
        }

    def get_profile(self, document_type: str) -> Optional[DocumentProfile]:
        return self._profiles.get(document_type)

    def register_profile(self, profile: DocumentProfile) -> None:
        self._profiles[profile.document_type] = profile