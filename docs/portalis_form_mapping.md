# Portalis Form Mapping

This file maps the real-world Excel autofill workbook and standard arrival docs to Portalis data sources.

## Standard arrival document set
- Crew List
- Vaccination List
- Health Declaration
- Last 10 Ports
- Crew Effects
- Narcotics
- Passenger List
- NIL List
- Cargo Manifest
- Stores Declaration

## Architecture rule
Portalis supports mixed renderers:
Data -> Form Model -> Renderer

Possible renderers:
- TXT
- PDF
- DOCX
- XLSX
- Email text

## Real-world benchmark
The current Excel workbook acts as the operational benchmark for:
- multi-tab autofill workflows
- standard arrival document generation
- unusual port-specific forms (example: Mexico forms)

## Planned direction
Portalis should generate:
- individual documents
- full Arrival Package bundles
- later port-specific forms based on port requirements