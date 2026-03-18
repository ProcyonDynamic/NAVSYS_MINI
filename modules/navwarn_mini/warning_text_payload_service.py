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

def build_object_short_text(platform_type: str | None, platform_name: str | None) -> str:
    if platform_name and platform_type:
        return f"{platform_type} {platform_name}".strip()
    return platform_name or platform_type or "OFFSHORE"

def build_plot_text_payload(
    *,
    warning_id: str,
    raw_text: str,
    interp_warning_type: str,
    short_name: str | None = None,
    max_body_chars: int = 48,
) -> PlotTextPayload:

    cleaned = _normalize(raw_text)

    # Title (always stable)
    title_text = warning_id

    # Short text (chart label)
    if short_name:
        short_text = short_name
    elif interp_warning_type == "MODU":
        short_text = "OFFSHORE"
    elif interp_warning_type == "PLATFORM":
        short_text = "PLATFORM"
    elif "BOUNDED BY" in raw_text.upper():
        short_text = "OPERATIONAL AREA"
    else:
        short_text = interp_warning_type or "WARNING"

    # Body (truncated)
    body_text = _truncate(cleaned, max_body_chars)

    return PlotTextPayload(
        title_text=title_text,
        short_text=short_text,
        body_text=body_text,
    )