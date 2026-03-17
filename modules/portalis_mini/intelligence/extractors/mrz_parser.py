from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class MRZResult:
    raw_line_1: str
    raw_line_2: str

    document_type: str

    passport_number: Optional[str]
    nationality: Optional[str]
    surname: Optional[str]
    given_names: Optional[str]
    birth_date: Optional[str]
    sex: Optional[str]
    expiry_date: Optional[str]

    confidence: float = 0.95


MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{30,44}$")


def extract_mrz_from_ocr_lines(lines: List[str]) -> Optional[MRZResult]:
    """
    Search OCR lines for a valid passport MRZ pair.
    """

    clean_lines = []

    for line in lines:
        text = line.strip().replace(" ", "")
        if MRZ_LINE_RE.match(text):
            clean_lines.append(text)

    if len(clean_lines) < 2:
        return None

    # try adjacent pairs
    for i in range(len(clean_lines) - 1):

        line1 = clean_lines[i]
        line2 = clean_lines[i + 1]

        if len(line1) != 44 or len(line2) != 44:
            continue

        if not line1.startswith("P<"):
            continue

        result = parse_passport_mrz(line1, line2)

        if result:
            return result

    return None


def parse_passport_mrz(line1: str, line2: str) -> Optional[MRZResult]:

    try:

        # LINE 1
        # P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<

        nationality = line1[2:5]

        names_section = line1[5:]
        name_parts = names_section.split("<<")

        surname = name_parts[0].replace("<", " ").strip()

        given_names = ""
        if len(name_parts) > 1:
            given_names = name_parts[1].replace("<", " ").strip()

        # LINE 2
        # L898902C36UTO7408122F1204159ZE184226B<<<<<<1

        passport_number = line2[0:9].replace("<", "")

        nationality2 = line2[10:13]

        birth_raw = line2[13:19]
        birth_date = format_mrz_date(birth_raw)

        sex = line2[20]

        expiry_raw = line2[21:27]
        expiry_date = format_mrz_date(expiry_raw)

        if nationality2:
            nationality = nationality2

        return MRZResult(
            raw_line_1=line1,
            raw_line_2=line2,
            document_type="passport",
            passport_number=passport_number,
            nationality=nationality,
            surname=surname,
            given_names=given_names,
            birth_date=birth_date,
            sex=sex,
            expiry_date=expiry_date,
        )

    except Exception:
        return None


def format_mrz_date(raw: str) -> Optional[str]:
    """
    Convert YYMMDD → ISO date.
    """

    if len(raw) != 6:
        return None

    try:

        year = int(raw[0:2])
        month = int(raw[2:4])
        day = int(raw[4:6])

        # heuristic century
        if year > 40:
            year += 1900
        else:
            year += 2000

        return f"{year:04d}-{month:02d}-{day:02d}"

    except Exception:
        return None