from __future__ import annotations
from pathlib import Path
from typing import List
import re


def load_txt_text(path: str) -> str:

    return Path(path).read_text(
        encoding="utf-8",
        errors="replace"
    )


def split_txt_blocks(raw_text: str) -> List[str]:

    if not raw_text:
        return []

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()

    matches = list(
        re.finditer(
            r"(?=NAVAREA\s+[IVX]+\s+\d{1,4}/\d{2,4})",
            text,
            flags=re.IGNORECASE,
        )
    )

    if not matches:
        return [text]

    blocks = []

    for i, m in enumerate(matches):

        start = m.start()

        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        block = text[start:end].strip()

        if block:
            blocks.append(block)

    return blocks