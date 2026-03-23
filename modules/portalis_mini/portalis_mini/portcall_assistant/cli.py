from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import PortCallContextBuilder
from .models import VoyageInput


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Portalis port-call context bundle.")
    parser.add_argument("--crew-excel", required=True)
    parser.add_argument("--ship-particulars", required=True)
    parser.add_argument("--certificate", action="append", default=[])
    parser.add_argument("--voyage-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--use-ocr", action="store_true")
    args = parser.parse_args()

    ocr_service = None
    if args.use_ocr:
        try:
            from portalis_mini.intelligence.ocr_service import OCRService

            ocr_service = OCRService(default_engine="surya")
        except Exception as exc:
            print(f"OCR service unavailable, continuing without OCR: {exc}")

    voyage_data = json.loads(Path(args.voyage_json).read_text(encoding="utf-8"))
    builder = PortCallContextBuilder(ocr_service=ocr_service)
    builder.build(
        crew_excel_path=args.crew_excel,
        ship_particulars_pdf=args.ship_particulars,
        certificate_pdfs=args.certificate,
        voyage_input=VoyageInput(**voyage_data),
        output_dir=args.output_dir,
    )
    print(f"Port call context written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
