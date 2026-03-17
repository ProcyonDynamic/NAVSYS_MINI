from pathlib import Path

from modules.portalis_mini.intelligence.ocr_service import OCRService
from modules.portalis_mini.intelligence.document_classifier import DocumentClassifier
from modules.portalis_mini.intelligence.field_extractor import FieldExtractor
from modules.portalis_mini.intelligence.canonical_mapper import CanonicalMapper
from modules.portalis_mini.intelligence.document_pipeline import DocumentPipeline

def main() -> None:
    pipeline = DocumentPipeline(
        ocr_service=OCRService(),
        classifier=DocumentClassifier(),
        extractor=FieldExtractor(),
        mapper=CanonicalMapper(),
    )

    test_file = Path(r"D:\NAVSYS_USB\data\PORTALIS\test_docs\passport_sample.pdf")
    result = pipeline.process_file(test_file)
    
    print("\nOCR TEXT PREVIEW:")
    print(result.ocr_text[:3000])

    print("SOURCE:", result.source_path)
    print("CLASSIFICATION:", result.classification)
    print("WARNINGS:", result.warnings)

    if result.extraction:
        print("\nEXTRACTED FIELDS:")
        for key, value in result.extraction.extracted_fields.items():
            print(f"  {key}: {value}")

    if result.canonical:
        print("\nCANONICAL FIELDS:")
        for key, value in result.canonical.mapped_fields.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()