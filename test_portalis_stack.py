def main():
    print("Testing Portalis stack...")

    import cv2
    print("OK: cv2")

    import pytesseract
    print("OK: pytesseract")

    from pdf2image import convert_from_path
    print("OK: pdf2image")

    from docx import Document
    print("OK: python-docx")

    import openpyxl
    print("OK: openpyxl")

    from lingua import Language, LanguageDetectorBuilder
    print("OK: lingua")

    import argostranslate
    print("OK: argostranslate")

    from paddleocr import PaddleOCR
    print("OK: paddleocr import")

    print("All core imports passed.")


if __name__ == "__main__":
    main()