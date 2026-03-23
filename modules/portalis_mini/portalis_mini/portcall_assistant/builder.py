from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from .certificate_extractor import CertificateExtractor
from .crew_excel_loader import CrewExcelLoader
from .fieldpacks import FieldPackMapper
from .models import ExtractedField, PortCallContext, VoyageInput
from .pdf_text import extract_pdf_text, has_meaningful_pdf_text
from .review_report import write_review_report
from .ship_particulars_extractor import ShipParticularsExtractor


class PortCallContextBuilder:
    def __init__(self, ocr_service: object | None = None) -> None:
        self.ocr_service = ocr_service
        self.crew_loader = CrewExcelLoader()
        self.ship_extractor = ShipParticularsExtractor()
        self.certificate_extractor = CertificateExtractor()
        self.field_mapper = FieldPackMapper()

    def build(
        self,
        crew_excel_path: str | Path,
        ship_particulars_pdf: str | Path,
        certificate_pdfs: Iterable[str | Path],
        voyage_input: VoyageInput,
        output_dir: str | Path,
    ) -> PortCallContext:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []

        crew_result = self.crew_loader.load(crew_excel_path)
        warnings.extend(crew_result.warnings)

        ship_text, ship_method = self._extract_document_text(ship_particulars_pdf)
        vessel_profile, vessel_warnings = self.ship_extractor.extract(
            ship_text,
            source_name=Path(ship_particulars_pdf).name,
        )
        warnings.extend(f"{ship_method}: {w}" for w in vessel_warnings)

        certificate_registry = []
        for certificate_pdf in certificate_pdfs:
            cert_text, cert_method = self._extract_document_text(certificate_pdf)
            cert_fields, cert_warnings = self.certificate_extractor.extract(
                cert_text,
                source_name=Path(certificate_pdf).name,
            )
            certificate_registry.append(cert_fields)
            warnings.extend(f"{Path(certificate_pdf).name}/{cert_method}: {w}" for w in cert_warnings)

        voyage_profile = self._voyage_to_fields(voyage_input)

        context = PortCallContext(
            generated_at=datetime.utcnow().isoformat() + "Z",
            vessel_profile=vessel_profile,
            certificate_registry=certificate_registry,
            crew_registry=crew_result.rows,
            voyage_profile=voyage_profile,
            warnings=warnings,
        )

        (output_dir / "portcall_context.json").write_text(
            json.dumps(context.to_plain_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "field_pack.json").write_text(
            json.dumps(
                {
                    "common": self.field_mapper.build_common_field_pack(context),
                    "crew_rows": self.field_mapper.build_crew_rows(context),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        write_review_report(context, output_dir / "review_report.md")
        return context

    def _extract_document_text(self, path: str | Path) -> tuple[str, str]:
        path = Path(path)
        text = extract_pdf_text(path)
        if has_meaningful_pdf_text(text):
            return text, "direct_pdf"

        if self.ocr_service is None:
            return text, "direct_pdf_insufficient_no_ocr"

        ocr_result = self.ocr_service.extract_text(path, work_dir=path.parent / "_portcall_ocr")
        return ocr_result.full_text, f"ocr_{getattr(self.ocr_service, 'default_engine', 'unknown')}"

    def _voyage_to_fields(self, voyage_input: VoyageInput) -> dict[str, ExtractedField]:
        out: dict[str, ExtractedField] = {}
        for key, value in asdict(voyage_input).items():
            if key == "extras":
                continue
            if value not in (None, "", []):
                out[key] = ExtractedField(
                    value=value,
                    source="manual_voyage_input",
                    confidence=1.0,
                    method="manual_entry",
                )
        for key, value in voyage_input.extras.items():
            out[key] = ExtractedField(
                value=value,
                source="manual_voyage_input",
                confidence=1.0,
                method="manual_entry",
            )
        return out
