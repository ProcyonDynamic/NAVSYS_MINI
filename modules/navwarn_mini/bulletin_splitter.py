import re
from typing import List, Dict


NAVAREA_START_RE = re.compile(
    r"(?=NAVAREA\s+[IVX]+\s+\d{1,4}/\d{2,4})",
    re.IGNORECASE,
)

NAVAREA_ID_RE = re.compile(
    r"(NAVAREA\s+[IVX]+\s+\d{1,4}/\d{2,4})",
    re.IGNORECASE,
)


def split_navarea_bulletin(text: str) -> List[Dict[str, str]]:
    if not text or not text.strip():
        return []

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    chunks = [c.strip() for c in NAVAREA_START_RE.split(text) if c.strip()]
    out = []

    for chunk in chunks:
        m = NAVAREA_ID_RE.search(chunk)
        warning_id = m.group(1).upper() if m else ""
        out.append({
            "warning_id": warning_id,
            "raw_text": chunk,
        })

    return out