from __future__ import annotations

import re
from typing import Dict, List, Optional


HEADER_LINE_RE = re.compile(
    r"""
    ^\s*
    (?P<full_id>NAVAREA\s+(?P<navarea>[IVX]+)\s+(?P<number>\d{1,4})/(?P<year>\d{2,4}))
    (?:
        [\s,:;\-]+
        (?P<rest>.*)
    )?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

CANCEL_REF_LINE_RE = re.compile(
    r"""
    ^\s*
    (?:
        CANCEL(?:S|LED|ING)?
        |
        CANCELLING
        |
        CANCEL\s+NAVAREA
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

DTG_RE = re.compile(
    r"""
    \b
    \d{6}
    \s*
    (?:UTC|Z)?
    \s*
    [A-Z]{3}
    \s*
    \d{2,4}
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

WARNING_ID_LINE_RE = re.compile(
    r"^\s*NAVAREA\s+[IVX]+\s+\d{1,4}/\d{2,4}\s*$",
    re.IGNORECASE,
)

IN_FORCE_CONTEXT_RE = re.compile(
    r"""
    \b(
        IN\s+FORCE
        |IN-FORCE
        |WARNINGS?\s+IN\s+FORCE
        |THIS\s+WARNING\s+REFERS?\s+TO
        |REFERS?\s+TO
        |REFERENCE
        |REFERENCES
        |CANCEL(?:S|LED|ING)?
        |SUPERSEDES?
        |CANCEL\s+THIS\s+MSG
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

REFERENCE_BLOCK_START_RE = re.compile(
    r"""
    \b(
        IN\s+FORCE\s+WARNINGS?
        |WARNINGS?\s+IN\s+FORCE
        |IN-FORCE\s+WARNINGS?
        |THIS\s+WARNING\s+REFERS?\s+TO
        |REFERS?\s+TO
        |REFERENCE
        |REFERENCES
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

BODYISH_RE = re.compile(
    r"""
    \b(
        DRILLING|OPERATIONS?|EXERCISE|HAZARD|BUOY|DERELICT|WRECK|PIPELAYING|
        SUBMARINE|CABLE|SURVEY|ANCHORING|DREDGING|ROCKET|MISSILE|FIRING|
        POSITION|POSITIONS|AREA|BOUND|BOUNDED|WITHIN|ALONG|BETWEEN|CENTERED
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _normalize_warning_id(full_id: str) -> str:
    parts = re.split(r"\s+", full_id.strip().upper())
    return f"{parts[0]} {parts[1]} {parts[2]}"


def _prev_nonempty(lines: List[str], idx: int) -> str:
    for j in range(idx - 1, -1, -1):
        if lines[j].strip():
            return lines[j].strip()
    return ""


def _next_nonempty(lines: List[str], idx: int) -> str:
    for j in range(idx + 1, len(lines)):
        if lines[j].strip():
            return lines[j].strip()
    return ""


def _strong_header_id(line: str, seen_ids: set[str]) -> Optional[str]:
    stripped = line.strip()
    if not stripped:
        return None

    if CANCEL_REF_LINE_RE.match(stripped):
        return None

    m = HEADER_LINE_RE.match(stripped)
    if not m:
        return None

    warning_id = _normalize_warning_id(m.group("full_id"))
    rest = (m.group("rest") or "").strip()

    if warning_id in seen_ids:
        return None

    if not rest:
        return None

    if DTG_RE.search(rest):
        return warning_id

    upper_rest = rest.upper()
    if any(
        token in upper_rest
        for token in ("UTC", "Z ", "NAVAREA WARNING", "COASTAL WARNING", "SUBAREA")
    ):
        return warning_id

    return None


def _is_probable_bare_header(
    line: str,
    prev_line: str,
    next_line: str,
    seen_ids: set[str],
) -> Optional[str]:
    m = HEADER_LINE_RE.match(line.strip())
    if not m:
        return None

    warning_id = _normalize_warning_id(m.group("full_id"))
    rest = (m.group("rest") or "").strip()

    if warning_id in seen_ids:
        return None

    # This helper is only for bare-ID lines.
    if rest:
        return None

    prev_upper = prev_line.upper()
    next_upper = next_line.upper()

    # Reject if previous context says we're inside a list/reference/cancel block.
    if prev_line and IN_FORCE_CONTEXT_RE.search(prev_upper):
        return None

    # Reject if next line is another bare warning ID; that's likely a list.
    if next_line and WARNING_ID_LINE_RE.match(next_line):
        return None

    # Accept if the next line looks like real bulletin body text.
    if next_line and (DTG_RE.search(next_line) or BODYISH_RE.search(next_upper)):
        return warning_id

    # Accept if previous line is empty-ish separator and next line is non-reference prose.
    if not prev_line and next_line and not IN_FORCE_CONTEXT_RE.search(next_upper):
        return warning_id

    return None


def _looks_like_true_header(
    lines: List[str],
    idx: int,
    seen_ids: set[str],
    in_reference_block: bool,
) -> Optional[str]:
    line = lines[idx]
    stripped = line.strip()
    if not stripped:
        return None

    strong_id = _strong_header_id(stripped, seen_ids)
    if strong_id:
        return strong_id

    if in_reference_block:
        return None

    prev_line = _prev_nonempty(lines, idx)
    next_line = _next_nonempty(lines, idx)

    return _is_probable_bare_header(
        line=stripped,
        prev_line=prev_line,
        next_line=next_line,
        seen_ids=seen_ids,
    )



def split_navarea_bulletin(text: str) -> List[Dict[str, str]]:
    if not text or not text.strip():
        return []

    text = _normalize_text(text)
    lines = text.split("\n")

    out: List[Dict[str, str]] = []
    seen_ids: set[str] = set()

    current_id: str = ""
    current_lines: List[str] = []
    in_reference_block = False

    def flush_current() -> None:
        nonlocal current_id, current_lines
        raw = "\n".join(current_lines).strip()
        if raw:
            out.append({"warning_id": current_id, "raw_text": raw})
        current_id = ""
        current_lines = []

    for idx, line in enumerate(lines):
        stripped = line.strip()

        if REFERENCE_BLOCK_START_RE.search(stripped):
            in_reference_block = True

        header_id = _looks_like_true_header(lines, idx, seen_ids, in_reference_block)

        if header_id:
            flush_current()
            current_id = header_id
            current_lines = [line]
            seen_ids.add(header_id)
            in_reference_block = False
            continue

        if current_lines:
            current_lines.append(line)

    flush_current()
    return out