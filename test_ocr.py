from modules.portalis_mini.intelligence.ocr_service import OCRService

svc = OCRService(
    tesseract_cmd=None,
    poppler_path=None,
    default_engine="tesseract",
)

result = svc.extract_text(
    r"D:\NAVSYS_USB\sample_passport_page1.png",
    engine="tesseract",
    preprocess=True,
)

print("SOURCE:", result.source_path)
print("PAGES:", len(result.pages))
print("ENGINE:", result.pages[0].engine if result.pages else None)
print("TEXT PREVIEW:")
print(result.full_text[:1500])