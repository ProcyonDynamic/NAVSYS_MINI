from typing import Dict, Any

from .import_models import ImportExtractionResult


def run_declared_document_extractor(
    parser_key: str,
    stored_file_path: str,
    work_dir: str,
) -> ImportExtractionResult:
    """
    Declared-type dispatch compatibility layer.

    This is not the primary Portalis intelligence path for passports and other
    OCR-driven documents. The stronger path is the DocumentPipeline
    (OCR -> classify -> candidates -> resolve -> canonical map).

    Keep this dispatcher aligned with document_type_registry parser_key values.
    """

    if parser_key == "passport":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.15,
            extracted_fields={},
            alerts=["Passport parser not implemented yet."],
        )

    if parser_key == "seaman_book":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.10,
            extracted_fields={},
            alerts=["Seaman book parser not implemented yet."],
        )

    if parser_key == "visa":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.10,
            extracted_fields={},
            alerts=["Visa parser not implemented yet."],
        )

    if parser_key == "certificate":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.10,
            extracted_fields={},
            alerts=["Ship certificate parser not implemented yet."],
        )

    if parser_key == "arrival_form":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.10,
            extracted_fields={},
            alerts=["Arrival form parser not implemented yet."],
        )

    if parser_key == "anko_report":
        return ImportExtractionResult(
            ok=True,
            parser_key=parser_key,
            confidence=0.10,
            extracted_fields={},
            alerts=["ANKO report parser not implemented yet."],
        )

    return ImportExtractionResult(
        ok=False,
        parser_key=parser_key,
        confidence=0.0,
        extracted_fields={},
        alerts=[f"Unknown parser_key: {parser_key}"],
    )