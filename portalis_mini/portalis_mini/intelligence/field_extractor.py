from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class ExtractionResult:
    document_type: str
    extracted_fields: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class FieldExtractor:
    PASSPORT_NO_PATTERNS = [
        r"\bPassport\s*(?:No|Number)?[:\s]+([A-Z0-9<]{6,20})\b",
        r"\b([A-Z]{1,3}[0-9]{5,10})\b",
    ]

    DATE_PATTERNS = [
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
        r"\b(\d{2}\s+[A-Z][a-z]{2}\s+\d{4})\b",
    ]

    def extract(self, document_type: str, text: str) -> ExtractionResult:
        text = text or ""

        if document_type == "passport":
            return self._extract_passport(text)

        if document_type == "seaman_book":
            return self._extract_seaman_book(text)

        if document_type == "yellow_fever_certificate":
            return self._extract_yellow_fever(text)

        return ExtractionResult(
            document_type=document_type,
            warnings=[f"No extractor implemented for document type: {document_type}"],
        )

    def _extract_passport(self, text: str) -> ExtractionResult:
        result = ExtractionResult(document_type="passport")

        passport_no = self._first_match(self.PASSPORT_NO_PATTERNS, text)
        if passport_no:
            result.extracted_fields["passport.number"] = passport_no
        else:
            result.warnings.append("Passport number not found")

        nationality = self._extract_after_label(
            text,
            labels=["Nationality", "Citizenship"],
        )
        if nationality:
            result.extracted_fields["crew.nationality"] = nationality

        dob = self._extract_after_label(
            text,
            labels=["Date of birth", "Birth date"],
        )
        if dob:
            result.extracted_fields["crew.date_of_birth"] = dob

        pob = self._extract_after_label(
            text,
            labels=["Place of birth"],
        )
        if pob:
            result.extracted_fields["crew.place_of_birth"] = pob

        expiry = self._extract_after_label(
            text,
            labels=["Date of expiry", "Expiry date", "Expiration date"],
        )
        if expiry:
            result.extracted_fields["passport.expiry_date"] = expiry

        surname = self._extract_after_label(
            text,
            labels=["Surname", "Family name", "Last name"],
        )
        if surname:
            result.extracted_fields["crew.family_name"] = surname

        given = self._extract_after_label(
            text,
            labels=["Given names", "Given name", "First name", "Forenames"],
        )
        if given:
            result.extracted_fields["crew.given_name"] = given

        return result

    def _extract_seaman_book(self, text: str) -> ExtractionResult:
        result = ExtractionResult(document_type="seaman_book")

        number = self._extract_after_label(
            text,
            labels=["Seaman Book No", "Seaman's Book No", "Book Number", "Document Number"],
        )
        if number:
            result.extracted_fields["seaman_book.number"] = number
        else:
            result.warnings.append("Seaman book number not found")

        issuing_state = self._extract_after_label(
            text,
            labels=["Issued by", "Issuing State", "Authority"],
        )
        if issuing_state:
            result.extracted_fields["seaman_book.issuing_state"] = issuing_state

        expiry = self._extract_after_label(
            text,
            labels=["Date of expiry", "Expiry date", "Valid until"],
        )
        if expiry:
            result.extracted_fields["seaman_book.expiry_date"] = expiry

        surname = self._extract_after_label(
            text,
            labels=["Surname", "Family name", "Last name"],
        )
        if surname:
            result.extracted_fields["crew.family_name"] = surname

        given = self._extract_after_label(
            text,
            labels=["Given names", "Given name", "First name"],
        )
        if given:
            result.extracted_fields["crew.given_name"] = given

        dob = self._extract_after_label(
            text,
            labels=["Date of birth", "Birth date"],
        )
        if dob:
            result.extracted_fields["crew.date_of_birth"] = dob

        return result

    def _extract_yellow_fever(self, text: str) -> ExtractionResult:
        result = ExtractionResult(document_type="yellow_fever_certificate")

        cert_no = self._extract_after_label(
            text,
            labels=["Certificate No", "Certificate Number", "Cert No"],
        )
        if cert_no:
            result.extracted_fields["vaccination.yellow_fever.number"] = cert_no

        issue_date = self._extract_after_label(
            text,
            labels=["Date", "Date of vaccination", "Vaccination date"],
        )
        if issue_date:
            result.extracted_fields["vaccination.yellow_fever.issue_date"] = issue_date
        else:
            result.warnings.append("Yellow fever issue date not found")

        expiry = self._extract_after_label(
            text,
            labels=["Valid until", "Expiry date", "Expiration date"],
        )
        if expiry:
            result.extracted_fields["vaccination.yellow_fever.expiry_date"] = expiry

        surname = self._extract_after_label(
            text,
            labels=["Surname", "Family name", "Last name"],
        )
        if surname:
            result.extracted_fields["crew.family_name"] = surname

        given = self._extract_after_label(
            text,
            labels=["Given name", "Given names", "First name"],
        )
        if given:
            result.extracted_fields["crew.given_name"] = given

        return result

    def _first_match(self, patterns: List[str], text: str) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_after_label(self, text: str, labels: List[str]) -> Optional[str]:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:\-]?\s*(.+)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = value.split("\n")[0].strip()
                value = re.sub(r"\s{2,}", " ", value)
                if value:
                    return value
        return None