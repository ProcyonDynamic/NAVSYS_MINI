from modules.portalis_core.ocr_service import OCRService

svc = OCRService(
    tesseract_cmd=None,   # set if needed on Windows
    poppler_path=None,    # set if needed on Windows
    default_engine="paddle",
)

res = svc.extract_text("sample_doc.png", engine="paddle", preprocess=True)
print(res.full_text[:200])

res2 = svc.extract_text("sample_doc.pdf", engine="paddle", preprocess=True)
print(res2.full_text[:200])