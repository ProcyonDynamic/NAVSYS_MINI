from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DocumentClassification:
    document_type: str
    confidence: float
    matched_keywords: List[str]


class DocumentClassifier:

    PASSPORT_KEYWORDS = [
        "passport",
        "nationality",
        "date of birth",
        "place of birth",
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

    def classify(self, text: str) -> Optional[DocumentClassification]:

        text_lower = text.lower()

        matches = []

        for kw in self.PASSPORT_KEYWORDS:
            if kw in text_lower:
                matches.append(kw)

        if len(matches) >= 2:
            return DocumentClassification(
                document_type="passport",
                confidence=0.9,
                matched_keywords=matches,
            )

        matches = []

        for kw in self.SEAMAN_BOOK_KEYWORDS:
            if kw in text_lower:
                matches.append(kw)

        if len(matches) >= 2:
            return DocumentClassification(
                document_type="seaman_book",
                confidence=0.9,
                matched_keywords=matches,
            )

        matches = []

        for kw in self.YELLOW_FEVER_KEYWORDS:
            if kw in text_lower:
                matches.append(kw)

        if len(matches) >= 1:
            return DocumentClassification(
                document_type="yellow_fever_certificate",
                confidence=0.8,
                matched_keywords=matches,
            )

        return None