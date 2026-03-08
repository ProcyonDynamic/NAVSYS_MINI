from __future__ import annotations


def textarea_to_list(text: str) -> list[str]:
    lines = []
    for ln in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = ln.strip()
        if s:
            lines.append(s)
    return lines


def list_to_textarea(items: list[str]) -> str:
    return "\n".join(items or [])