from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .active_warning_table import load_active_warning_table, save_active_warning_table

_WARNING_ID_RE = re.compile(
    r"\bNAVAREA\s+(?P<navarea>[IVX]+)\s+(?P<number>\d{1,4})/(?P<year>\d{2,4})\b",
    re.IGNORECASE,
)

_LISTED_ID_RE = re.compile(
    r"\b(?P<number>\d{1,4})/(?P<year>\d{2,4})\b",
    re.IGNORECASE,
)


@dataclass
class CumulativeReconcileResult:
    ok: bool
    cumulative_warning_id: str
    cumulative_issued_utc: str
    listed_ids: list[str]
    kept_ids: list[str]
    omitted_ids: list[str]
    newer_preserved_ids: list[str]
    errors: list[str]


def _normalize_year_2(year_text: str) -> str:
    year_text = (year_text or "").strip()
    if len(year_text) >= 2:
        return year_text[-2:]
    return year_text


def _normalize_warning_id(
    *,
    navarea: str,
    number: str,
    year: str,
) -> str:
    return f"NAVAREA {navarea.upper()} {int(number)}/{_normalize_year_2(year)}"


def extract_cumulative_ids(raw_text: str) -> list[str]:
    text = raw_text or ""
    ids: list[str] = []
    seen: set[str] = set()

    navarea_match = re.search(r"\bNAVAREA\s+([IVX]+)\b", text, re.IGNORECASE)
    navarea = navarea_match.group(1).upper() if navarea_match else "IV"

    for m in _WARNING_ID_RE.finditer(text):
        wid = _normalize_warning_id(
            navarea=m.group("navarea"),
            number=m.group("number"),
            year=m.group("year"),
        )

        wid = " ".join(wid.split())
        if wid not in seen:
            seen.add(wid)
            ids.append(wid)

    for m in _LISTED_ID_RE.finditer(text):
        start = max(0, m.start() - 12)
        prefix = text[start:m.start()].upper()

        if "NAVAREA" in prefix:
            continue

        wid = _normalize_warning_id(
            navarea=navarea,
            number=m.group("number"),
            year=m.group("year"),
        )

        wid = " ".join(wid.split())
        if wid not in seen:
            seen.add(wid)
            ids.append(wid)

    return ids

def reconcile_cumulative_snapshot(
    *,
    active_table_csv_path: str,
    cumulative_warning_id: str,
    cumulative_navarea: str,
    cumulative_issued_utc: str,
    listed_ids: list[str],
) -> CumulativeReconcileResult:

    path = Path(active_table_csv_path)

    if not path.exists():
        return CumulativeReconcileResult(
            ok=False,
            cumulative_warning_id=cumulative_warning_id,
            cumulative_issued_utc=cumulative_issued_utc,
            listed_ids=listed_ids,
            kept_ids=[],
            omitted_ids=[],
            newer_preserved_ids=[],
            errors=[f"active table not found: {path}"],
        )

    records = load_active_warning_table(path)

    listed_set = {" ".join(x.upper().split()) for x in listed_ids}
    kept_ids = []
    omitted_ids = []
    newer_preserved_ids = []

    for record in records:
        record_navarea = (record.navarea or "").strip().upper()
        record_id = " ".join((record.warning_id or "").upper().split())
        record_issued = (record.issued_utc or "").strip()

        if record_navarea != (cumulative_navarea or "").strip().upper():
            continue

        if not record_issued:
            continue

        if record_issued <= cumulative_issued_utc:
            if record_id in listed_set:
                record.state = "ACTIVE"
                record.state_reason = "LISTED_IN_LATEST_CUMULATIVE"
                record.last_seen_in_cumulative_id = cumulative_warning_id
                record.last_seen_in_cumulative_utc = cumulative_issued_utc
                record.omitted_by_cumulative_id = ""
                record.omitted_by_cumulative_utc = ""
                kept_ids.append(record.warning_id)
            else:
                if record.state != "CANCELLED_EXPLICIT":
                    record.state = "OMITTED_BY_CUMULATIVE"
                    record.state_reason = "NOT_PRESENT_IN_LATEST_CUMULATIVE"
                    record.omitted_by_cumulative_id = cumulative_warning_id
                    record.omitted_by_cumulative_utc = cumulative_issued_utc
                    omitted_ids.append(record.warning_id)
        else:
            if record.state == "ACTIVE":
                newer_preserved_ids.append(record.warning_id)

    save_active_warning_table(path, records)

    return CumulativeReconcileResult(
        ok=True,
        cumulative_warning_id=cumulative_warning_id,
        cumulative_issued_utc=cumulative_issued_utc,
        listed_ids=listed_ids,
        kept_ids=kept_ids,
        omitted_ids=omitted_ids,
        newer_preserved_ids=newer_preserved_ids,
        errors=[],
    )