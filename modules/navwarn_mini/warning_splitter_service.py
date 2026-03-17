from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .bulletin_splitter import split_navarea_bulletin
from .message_envelope import MessageEnvelope


@dataclass
class SplitResult:
    envelopes: list[MessageEnvelope]
    split_count: int
    errors: list[str]


_NAVAREA_RE = re.compile(r"\bNAVAREA\s+([IVXLC]+)\b", re.IGNORECASE)


def _infer_navarea(text: str) -> Optional[str]:
    m = _NAVAREA_RE.search(text or "")
    if not m:
        return None
    return m.group(1).upper()


def split_bulletin_to_envelopes(
    *,
    raw_text: str,
    source: str = "MANUAL",
    source_file: Optional[str] = None,
) -> SplitResult:
    errors: list[str] = []

    try:
        parts = split_navarea_bulletin(raw_text or "")
    except Exception as e:
        return SplitResult(
            envelopes=[],
            split_count=0,
            errors=[f"splitter_error: {e}"],
        )

    envelopes: list[MessageEnvelope] = []

    for part in parts:
        warning_id = (part.get("warning_id") or "").strip() or None
        part_text = (part.get("raw_text") or "").strip()

        if not part_text:
            continue

        navarea = _infer_navarea(warning_id or part_text)

        envelopes.append(
            MessageEnvelope(
                raw_text=part_text,
                source=source,
                source_file=source_file,
                navarea=navarea,
                warning_id=warning_id,
            )
        )

    return SplitResult(
        envelopes=envelopes,
        split_count=len(envelopes),
        errors=errors,
    )