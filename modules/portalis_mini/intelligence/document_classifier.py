from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class DocumentClassification:
    document_type: str
    confidence: float
    matched_keywords: List[str]


class DocumentClassifier:
    PASSPORT_KEYWORDS = [
        "passport",
        "surname",
        "given names",
        "given name",
        "nationality",
        "date of birth",
        "place of birth",
        "sex",
        "issuing authority",
        "republic",
        "passport no",
    ]

    SEAMAN_BOOK_KEYWORDS = [
        "seaman",
        "seafarer",
        "seaman's book",
        "discharge book",
    ]

    YELLOW_FEVER_KEYWORDS = [
        "yellow fever",
        "vaccination",
        "international certificate",
    ]

    CONTRACT_KEYWORDS = [
        "contract",
        "employment",
        "seafarer employment agreement",
        "agreement",
    ]

    AGENT_FORM_KEYWORDS = [
        "pre arrival",
        "crew list",
        "agent",
        "arrival information",
        "port of call",
    ]

    SMS_FORM_KEYWORDS = [
        "safety management",
        "sms",
        "checklist",
        "company form",
    ]

    MRZ_HINT_RE = re.compile(r"[A-Z0-9<]{20,}")

    def classify(self, text: str) -> Optional[DocumentClassification]:
        text_lower = text.lower()

        if self.MRZ_HINT_RE.search(text.upper()):
            return DocumentClassification(
                document_type="passport",
                confidence=0.97,
                matched_keywords=["mrz_detected"],
            )
        text_upper = text.upper()

        if "PASSPORT" in text_upper and ("SURNAME" in text_upper or "SEX" in text_upper or "NATIONALITY" in text_upper):
            return DocumentClassification(
                document_type="passport",
                confidence=0.85,
                matched_keywords=["passport_layout_detected"],
            )
        checks = [
            ("passport", self.PASSPORT_KEYWORDS, 2, 0.90),
            ("seaman_book", self.SEAMAN_BOOK_KEYWORDS, 2, 0.90),
            ("yellow_fever_certificate", self.YELLOW_FEVER_KEYWORDS, 1, 0.85),
            ("contract", self.CONTRACT_KEYWORDS, 2, 0.80),
            ("agent_form", self.AGENT_FORM_KEYWORDS, 2, 0.75),
            ("sms_form", self.SMS_FORM_KEYWORDS, 2, 0.75),
        ]

        best_match: Optional[DocumentClassification] = None

        for doc_type, keywords, threshold, confidence in checks:
            matches = [kw for kw in keywords if kw in text_lower]
            if len(matches) >= threshold:
                candidate = DocumentClassification(
                    document_type=doc_type,
                    confidence=confidence,
                    matched_keywords=matches,
                )
                if best_match is None or len(candidate.matched_keywords) > len(best_match.matched_keywords):
                    best_match = candidate

        return best_match 