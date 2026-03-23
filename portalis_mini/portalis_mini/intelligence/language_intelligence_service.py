from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass(slots=True)
class LanguageAnalysisResult:
    detected_language: str
    secondary_languages: List[str] = field(default_factory=list)
    mixed_language: bool = False
    normalized_text: str = ""
    matched_signals: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class LanguageIntelligenceService:
    """Detects OCR language/script signals and performs first-pass maritime text normalization."""

    LANGUAGE_KEYWORDS: Dict[str, List[str]] = {
        "english": [
            "passport",
            "nationality",
            "date of birth",
            "place of birth",
            "expiry date",
            "issued by",
            "certificate",
            "vaccination",
            "crew list",
            "pre arrival",
        ],
        "greek": [
            "ελληνικη",
            "διαβατηριο",
            "υπηκοοτητα",
            "τοπος γεννησης",
            "ημερομηνια",
            "εμβολιασμου",
        ],
        "russian": [
            "паспорт",
            "гражданство",
            "дата рождения",
            "место рождения",
            "дата выдачи",
            "срок действия",
        ],
        "ukrainian": [
            "паспорт",
            "громадянство",
            "дата народження",
            "місце народження",
            "дата видачі",
            "строк дії",
        ],
        "polish": [
            "rzeczpospolita polska",
            "paszport",
            "obywatelstwo",
            "data urodzenia",
            "miejsce urodzenia",
            "data wydania",
            "data waznosci",
        ],
        "romanian": [
            "pasaport",
            "cetatenie",
            "data nasterii",
            "locul nasterii",
            "data eliberarii",
            "data expirarii",
        ],
        "croatian": [
            "putovnica",
            "drzavljanstvo",
            "datum rodenja",
            "mjesto rodenja",
            "datum izdavanja",
            "datum isteka",
        ],
    }

    OCR_REPLACEMENTS: Dict[str, str] = {
        "EAAHNIKH": "HELLENIC",
        "EAAHNIKH J HELLENIC": "HELLENIC",
        "E\u039b\u039bHNIKH": "HELLENIC",
        "PASZP0RT": "PASZPORT",
        "P4SSP0RT": "PASSPORT",
        "NATI0NALITY": "NATIONALITY",
        "PL4CE OF BIRTH": "PLACE OF BIRTH",
        "D4TE OF BIRTH": "DATE OF BIRTH",
        "EXP1RY": "EXPIRY",
        "0MB": "OMB",
    }

    def analyze_text(self, text: str) -> LanguageAnalysisResult:
        cleaned = self._normalize_ocr_text(text)
        lowered = cleaned.lower()

        script_signals = self._detect_scripts(cleaned)
        keyword_hits = self._detect_keyword_hits(lowered)
        language_scores = self._score_languages(script_signals, keyword_hits)

        detected_language = self._pick_primary_language(language_scores)
        secondary_languages = self._pick_secondary_languages(language_scores, detected_language)
        mixed_language = len([lang for lang, score in language_scores.items() if score > 0]) > 1

        warnings: List[str] = []
        if detected_language == "unknown":
            warnings.append("Could not confidently detect OCR language")

        matched_signals = {
            "scripts": sorted(list(script_signals)),
            **{lang: hits for lang, hits in keyword_hits.items() if hits},
        }

        return LanguageAnalysisResult(
            detected_language=detected_language,
            secondary_languages=secondary_languages,
            mixed_language=mixed_language,
            normalized_text=cleaned,
            matched_signals=matched_signals,
            warnings=warnings,
        )

    def _normalize_ocr_text(self, text: str) -> str:
        normalized = text or ""

        # First apply direct OCR correction rules.
        for bad, good in self.OCR_REPLACEMENTS.items():
            normalized = normalized.replace(bad, good)

        # Collapse whitespace and normalize common OCR punctuation spacing.
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r" ?/ ?", " / ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"\s+:", ":", normalized)
        normalized = re.sub(r":\s+", ": ", normalized)

        return normalized.strip()

    def _detect_scripts(self, text: str) -> Set[str]:
        scripts: Set[str] = set()

        if re.search(r"[A-Za-z]", text):
            scripts.add("latin")
        if re.search(r"[\u0370-\u03FF\u1F00-\u1FFF]", text):
            scripts.add("greek_script")
        if re.search(r"[\u0400-\u04FF]", text):
            scripts.add("cyrillic")

        return scripts

    def _detect_keyword_hits(self, lowered_text: str) -> Dict[str, List[str]]:
        hits: Dict[str, List[str]] = {lang: [] for lang in self.LANGUAGE_KEYWORDS}

        for language, keywords in self.LANGUAGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lowered_text:
                    hits[language].append(keyword)

        return hits

    def _score_languages(
        self,
        script_signals: Set[str],
        keyword_hits: Dict[str, List[str]],
    ) -> Dict[str, int]:
        scores: Dict[str, int] = {lang: 0 for lang in self.LANGUAGE_KEYWORDS}

        for language, hits in keyword_hits.items():
            scores[language] += len(hits) * 10

        if "greek_script" in script_signals:
            scores["greek"] += 15
        if "cyrillic" in script_signals:
            scores["russian"] += 8
            scores["ukrainian"] += 8
        if "latin" in script_signals:
            scores["english"] += 2
            scores["polish"] += 2
            scores["romanian"] += 2
            scores["croatian"] += 2

        return scores

    def _pick_primary_language(self, scores: Dict[str, int]) -> str:
        best_language = "unknown"
        best_score = 0

        for language, score in scores.items():
            if score > best_score:
                best_language = language
                best_score = score

        if best_score == 0:
            return "unknown"

        return best_language

    def _pick_secondary_languages(self, scores: Dict[str, int], primary: str) -> List[str]:
        secondaries: List[str] = []

        for language, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
            if language == primary:
                continue
            if score > 0:
                secondaries.append(language)

        return secondaries[:3]
