from __future__ import annotations

from pathlib import Path

from .models import PortCallContext


def write_review_report(context: PortCallContext, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    lines: list[str] = []
    lines.append("# Port Call Context Review\n")
    lines.append(f"Generated at: {context.generated_at}\n")

    lines.append("## Vessel Profile\n")
    for key, field in context.vessel_profile.items():
        lines.append(f"- **{key}**: {field.value} _(source: {field.source}, conf: {field.confidence:.2f})_")

    lines.append("\n## Voyage Profile\n")
    for key, field in context.voyage_profile.items():
        lines.append(f"- **{key}**: {field.value} _(manual/merged)_")

    lines.append("\n## Certificates\n")
    if context.certificate_registry:
        for idx, cert in enumerate(context.certificate_registry, start=1):
            lines.append(f"### Certificate {idx}")
            for key, field in cert.items():
                lines.append(f"- **{key}**: {field.value} _(source: {field.source}, conf: {field.confidence:.2f})_")
    else:
        lines.append("- No certificates parsed.")

    lines.append("\n## Crew Registry\n")
    lines.append(f"Crew count: {len(context.crew_registry)}\n")
    for idx, member in enumerate(context.crew_registry[:20], start=1):
        lines.append(f"### Crew {idx}: {member.get('full_name', 'UNKNOWN')}")
        for key in [
            'rank', 'nationality', 'date_of_birth', 'passport_number', 'passport_expiry',
            'us_visa_number', 'us_visa_expiry', 'height_cm', 'weight_kg'
        ]:
            if member.get(key) not in (None, ""):
                lines.append(f"- **{key}**: {member.get(key)}")

    if context.warnings:
        lines.append("\n## Warnings\n")
        for warning in context.warnings:
            lines.append(f"- {warning}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
