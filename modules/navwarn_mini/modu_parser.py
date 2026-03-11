from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ModuEntry:
    label: str
    name: str
    coordinate: Optional[str]
    note: str = ""


MODU_HINTS = [
    "MOBILE OFFSHORE DRILLING UNITS",
    "POSITIONS AT",
    "NEW POSITION",
    "NEW RIG",
]


def looks_like_modu_list(text: str) -> bool:
    t = (text or "").upper()

    label_count = len(
        re.findall(r"^\s*[A-Z]{1,4}\.\s+", t, flags=re.MULTILINE)
    )

    hint_hits = sum(1 for h in MODU_HINTS if h in t)

    return label_count >= 3 and hint_hits >= 1


def split_modu_entries(text: str) -> List[ModuEntry]:

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    entries: List[ModuEntry] = []

    current_label = None
    current_lines = []

    def flush():

        nonlocal current_label, current_lines

        if not current_label:
            return

        body = " ".join(x.strip() for x in current_lines if x.strip())

        note = ""

        if "(" in body and ")" in body:
            notes = re.findall(r"\((.*?)\)", body)
            note = " | ".join(notes)

        entries.append(
            ModuEntry(
                label=current_label,
                name=body,
                coordinate=None,
                note=note,
            )
        )

        current_label = None
        current_lines = []

    for line in lines:

        m = re.match(r"^\s*([A-Z]{1,4})\.\s+(.*)", line)

        if m:

            flush()

            current_label = m.group(1)

            current_lines = [m.group(2)]

        elif current_label:

            current_lines.append(line)

    flush()

    return entries