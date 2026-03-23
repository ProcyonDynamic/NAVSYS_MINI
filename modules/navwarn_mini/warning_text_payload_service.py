from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlotTextPayload:
    title_text: str
    short_text: str
    body_text: str


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def build_plot_text_payload(
    *,
    warning_id: str,
    raw_text: str,
    interp_warning_type: str,
    key_phrases: list[str] | None = None,
) -> PlotTextPayload:
    cleaned = _normalize(raw_text)

    # Stable title for audit / identity
    title_text = warning_id or "WARNING"

    # Chart label: semantic-first, fallback to type
    if key_phrases:
        filtered = []
        warning_id_upper = (warning_id or "").upper().strip()

        for phrase in key_phrases[:4]:
            phrase_clean = (phrase or "").upper().strip()
            if not phrase_clean:
                continue
            if phrase_clean == warning_id_upper:
                continue
            if phrase_clean not in filtered:
                filtered.append(phrase_clean)

        short_text = " | ".join(filtered) if filtered else (interp_warning_type or "WARNING")

    elif interp_warning_type == "MODU":
        short_text = "OFFSHORE"

    elif interp_warning_type == "PLATFORM":
        short_text = "PLATFORM"

    elif "BOUNDED BY" in raw_text.upper():
        short_text = "OPERATIONAL AREA"

    else:
        short_text = interp_warning_type or "WARNING"
        
    # Printable / expandable body text
    max_body_chars = 160
    body_text = _truncate(cleaned, max_body_chars)

    return PlotTextPayload(
        title_text=title_text,
        short_text=short_text,
        body_text=body_text,
    )