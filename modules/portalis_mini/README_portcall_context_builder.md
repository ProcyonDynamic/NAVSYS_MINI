# Portalis Port Call Context Builder v0.1

This scaffold assembles one reusable port-call dataset from:
- crew Excel workbook
- ship particulars PDF
- vessel certificate PDFs
- manual voyage JSON input

## Output files
- `portcall_context.json`
- `field_pack.json`
- `review_report.md`

## CLI

```bash
python -m portalis_mini.portcall_assistant.cli \
  --crew-excel path/to/crew.xlsx \
  --ship-particulars path/to/ship_particulars.pdf \
  --certificate path/to/cert1.pdf \
  --certificate path/to/cert2.pdf \
  --voyage-json path/to/voyage_input.json \
  --output-dir path/to/output \
  --use-ocr
```

## Notes
- Direct PDF text extraction is tried first.
- OCR is only used when the PDF text layer is weak or missing.
- Crew Excel column matching is alias-based and can be extended in `crew_excel_loader.py`.
- This is a controlled assembler, not a fully universal document parser.
