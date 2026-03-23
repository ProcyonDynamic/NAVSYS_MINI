from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .extractors.mrz_parser import extract_mrz_from_ocr_lines

@dataclass(slots=True)
class Candidate:
    candidate_type: str
    value: str
    confidence: float
    source_method: str
    source_page: Optional[int] = None
    source_line: Optional[str] = None
    source_bbox: Any = None
    label: Optional[str] = None
    trace: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateExtractionResult:
    candidates: List[Candidate]
    warnings: List[str] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)


class CandidateExtractor:
    DATE_PATTERNS = [
        re.compile(r"\b(\d{2}[ /.-][A-Z]{3}[ /.-]\d{2,4})\b", re.IGNORECASE),
        re.compile(r"\b(\d{1,2}[ /.-]\d{1,2}[ /.-]\d{2,4})\b"),
        re.compile(r"\b([A-Z]{3,9}\s+\d{1,2},?\s+\d{4})\b", re.IGNORECASE),
    ]

    SEX_RE = re.compile(r"\b(M|F)\b")
    MRZ_HINT_RE = re.compile(r"^P<[A-Z0-9<]+$")
    COUNTRY3_RE = re.compile(r"\b[A-Z]{3}\b")
    ID_NUMBER_RE = re.compile(r"\b[A-Z]{1,3}[0-9]{5,12}\b")
    PASSPORT_NO_RE = re.compile(r"\b[A-Z]{1,2}[0-9]{6,9}\b")
    HEIGHT_RE = re.compile(r"\b(1[.,]\d{2}|[1-2]\d{2}\s?CM)\b", re.IGNORECASE)

    LABEL_VALUE_PATTERNS = [
        ("passport_number", re.compile(r"passport\s*no\.?\s*[:\-]?\s*([A-Z0-9]+)", re.IGNORECASE)),
        ("surname", re.compile(r"surname\s*[:\-]?\s*([A-Z<>\- ]+)", re.IGNORECASE)),
        ("given_names", re.compile(r"\bname\s*[:\-]?\s*([A-Z<>\- ]+)", re.IGNORECASE)),
        ("nationality", re.compile(r"nationality\s*[:\-]?\s*([A-Z ]+)", re.IGNORECASE)),
        ("date_of_birth", re.compile(r"date of birth\s*[:\-]?\s*([A-Z0-9 /.-]+)", re.IGNORECASE)),
        ("place_of_birth", re.compile(r"place of birth\s*[:\-]?\s*([A-Z\-\s]+)", re.IGNORECASE)),
        ("date_of_expiry", re.compile(r"(date of expiry|expiry)\s*[:\-]?\s*([A-Z0-9 /.-]+)", re.IGNORECASE)),
        ("issue_date", re.compile(r"(iss\.?\s*date|date of issue|issue date)\s*[:\-]?\s*([A-Z0-9 /.-]+)", re.IGNORECASE)),
        ("sex", re.compile(r"sex\s*[:\-]?\s*(M|F)", re.IGNORECASE)),
    ]

    PASSPORT_CONTEXT_WORDS = {
        "passport", "nationality", "surname", "name", "date of birth",
        "place of birth", "expiry", "sex", "country"
    }

    def extract(self, ocr_payload: Dict[str, Any]) -> CandidateExtractionResult:

        candidates: List[Candidate] = []
        warnings: List[str] = []

        pages = ocr_payload.get("pages", [])
        if not pages:
            warnings.append("OCR payload contains no pages.")
            return CandidateExtractionResult(
                candidates=[],
                warnings=warnings,
                trace={"page_count": 0},
            )

        all_line_texts: List[str] = []

        for page in pages:

            page_number = page.get("page_number")
            lines = self._normalize_page_lines(page)

            for line_obj in lines:

                text = line_obj["text"]
                bbox = line_obj.get("bbox")

                if not text.strip():
                    continue

                # collect lines for MRZ detection
                all_line_texts.append(text)

                # extract candidates from this line
                candidates.extend(
                    self._extract_line_candidates(
                        text=text,
                        page_number=page_number,
                        bbox=bbox,
                    )
                )

        # --- MRZ detection (run once) ---
        mrz_result = extract_mrz_from_ocr_lines(all_line_texts)

        if mrz_result:
            candidates.extend(self._mrz_result_to_candidates(mrz_result))

        # --- deduplicate ---
        candidates = self._dedupe_candidates(candidates)

        return CandidateExtractionResult(
            candidates=candidates,
            warnings=warnings,
            trace={
                "page_count": len(pages),
                "candidate_count": len(candidates),
            },
        )

    def _mrz_result_to_candidates(self, mrz_result) -> List[Candidate]:
        out: List[Candidate] = []

        def add(label: str, value: str | None):
            if not value:
                return
            out.append(Candidate(
                candidate_type="mrz_field",
                value=value,
                confidence=mrz_result.confidence,
                source_method="mrz_parse",
                source_page=None,
                source_line=mrz_result.raw_line_2,
                source_bbox=None,
                label=label,
                trace={"label": label},
            ))

        add("passport_number", mrz_result.passport_number)
        add("surname", mrz_result.surname)
        add("given_names", mrz_result.given_names)
        add("nationality", mrz_result.nationality)
        add("date_of_birth", mrz_result.birth_date)
        add("sex", mrz_result.sex)
        add("expiry_date", mrz_result.expiry_date)

        return out



    def _normalize_page_lines(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_lines = page.get("lines") or []

        normalized: List[Dict[str, Any]] = []

        if raw_lines:
            for line in raw_lines:
                if isinstance(line, dict):
                    normalized.append({
                        "text": (line.get("text") or "").strip(),
                        "bbox": line.get("bbox"),
                    })
                else:
                    normalized.append({
                        "text": str(line).strip(),
                        "bbox": None,
                    })
            return normalized

        # fallback if OCR engine only gave flat text
        page_text = page.get("text") or ""
        for line in page_text.splitlines():
            normalized.append({
                "text": line.strip(),
                "bbox": None,
            })

        return normalized

    def _extract_line_candidates(
        self,
        text: str,
        page_number: Optional[int],
        bbox: Any,
    ) -> List[Candidate]:
        out: List[Candidate] = []

        upper_text = text.upper().strip()

        # ---- raw text line candidate
        out.append(Candidate(
            candidate_type="text_line",
            value=text.strip(),
            confidence=0.40,
            source_method="ocr_line",
            source_page=page_number,
            source_line=text,
            source_bbox=bbox,
        ))

        # ---- MRZ whole-line hint
        if self.MRZ_HINT_RE.match(upper_text) and len(upper_text) >= 30:
            out.append(Candidate(
                candidate_type="mrz_line",
                value=upper_text,
                confidence=0.95,
                source_method="mrz_line_detect",
                source_page=page_number,
                source_line=text,
                source_bbox=bbox,
            ))

        # ---- labeled value candidates
        out.extend(self._extract_labeled_candidates(
            text=text,
            page_number=page_number,
            bbox=bbox,
        ))

        # ---- dates
        for pattern in self.DATE_PATTERNS:
            for match in pattern.finditer(text):
                value = self._clean_value(match.group(1))
                if value:
                    out.append(Candidate(
                        candidate_type="date",
                        value=value,
                        confidence=0.72,
                        source_method="regex_date",
                        source_page=page_number,
                        source_line=text,
                        source_bbox=bbox,
                    ))

        # ---- id-like values
        for match in self.ID_NUMBER_RE.finditer(upper_text):
            value = self._clean_value(match.group(0))
            if value:
                out.append(Candidate(
                    candidate_type="id_number",
                    value=value,
                    confidence=0.70,
                    source_method="regex_id",
                    source_page=page_number,
                    source_line=text,
                    source_bbox=bbox,
                ))

        for match in self.PASSPORT_NO_RE.finditer(upper_text):
            value = self._clean_value(match.group(0))
            if value:
                out.append(Candidate(
                    candidate_type="passport_like_number",
                    value=value,
                    confidence=0.78,
                    source_method="regex_passport_like",
                    source_page=page_number,
                    source_line=text,
                    source_bbox=bbox,
                ))

        # ---- sex markers
        for match in self.SEX_RE.finditer(upper_text):
            value = self._clean_value(match.group(1))
            if value:
                out.append(Candidate(
                    candidate_type="sex_marker",
                    value=value,
                    confidence=0.65,
                    source_method="regex_sex",
                    source_page=page_number,
                    source_line=text,
                    source_bbox=bbox,
                ))

        # ---- 3-letter country codes
        for match in self.COUNTRY3_RE.finditer(upper_text):
            value = self._clean_value(match.group(0))
            if value in {"GRC", "USA", "RUS", "CYP", "GBR", "FRA", "DEU", "ITA", "ESP", "NLD", "BEL", "POL", "ROU", "BGR", "GRC"}:
                out.append(Candidate(
                    candidate_type="country_code",
                    value=value,
                    confidence=0.62,
                    source_method="regex_country_code",
                    source_page=page_number,
                    source_line=text,
                    source_bbox=bbox,
                ))

        # ---- place / location-ish uppercase lines
        if self._looks_like_location_line(upper_text):
            out.append(Candidate(
                candidate_type="location_text",
                value=self._clean_value(upper_text),
                confidence=0.55,
                source_method="heuristic_location",
                source_page=page_number,
                source_line=text,
                source_bbox=bbox,
            ))

        # ---- person-name-ish uppercase lines
        if self._looks_like_person_name_line(upper_text):
            out.append(Candidate(
                candidate_type="person_name",
                value=self._clean_value(upper_text.replace("<", " ")),
                confidence=0.58,
                source_method="heuristic_person_name",
                source_page=page_number,
                source_line=text,
                source_bbox=bbox,
            ))

        # ---- height
        for match in self.HEIGHT_RE.finditer(upper_text):
            value = self._clean_value(match.group(1))
            if value:
                out.append(Candidate(
                    candidate_type="height",
                    value=value,
                    confidence=0.60,
                    source_method="regex_height",
                    source_page=page_number,
                    source_line=text,
                    source_bbox=bbox,
                ))

        return out

    def _extract_labeled_candidates(
        self,
        text: str,
        page_number: Optional[int],
        bbox: Any,
    ) -> List[Candidate]:
        out: List[Candidate] = []

        for label, pattern in self.LABEL_VALUE_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue

            if label == "date_of_expiry":
                value = match.group(2)
            elif label == "issue_date":
                value = match.group(2)
            else:
                value = match.group(1)

            value = self._clean_value(value)
            if not value:
                continue

            out.append(Candidate(
                candidate_type="labeled_value",
                value=value,
                confidence=0.82,
                source_method="label_value_regex",
                source_page=page_number,
                source_line=text,
                source_bbox=bbox,
                label=label,
                trace={"label": label},
            ))

        return out

    def _looks_like_location_line(self, text: str) -> bool:
        if len(text) < 3 or len(text) > 40:
            return False

        if any(ch.isdigit() for ch in text):
            return False

        words = [w for w in re.split(r"\s+", text) if w]
        if not words:
            return False

        return (
            len(words) <= 3
            and all(word.isalpha() or "-" in word for word in words)
            and text == text.upper()
        )

    def _looks_like_person_name_line(self, text: str) -> bool:
        if len(text) < 4 or len(text) > 60:
            return False

        if any(ctx in text.lower() for ctx in self.PASSPORT_CONTEXT_WORDS):
            return False

        if any(ch.isdigit() for ch in text):
            return False

        words = [w for w in re.split(r"\s+", text.replace("<", " ")) if w]
        if not words or len(words) > 6:
            return False

        alpha_ratio = sum(ch.isalpha() or ch in {" ", "<", "-"} for ch in text) / max(len(text), 1)
        return alpha_ratio > 0.85 and text == text.upper()

    def _clean_value(self, value: str) -> str:
        value = value.strip()
        value = re.sub(r"\s+", " ", value)
        value = value.strip(" .,:;-")
        return value

    def _dedupe_candidates(self, candidates: List[Candidate]) -> List[Candidate]:
        seen = set()
        deduped: List[Candidate] = []

        for c in candidates:
            key = (
                c.candidate_type,
                c.label,
                c.value.upper(),
                c.source_page,
                c.source_method,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)

        return deduped