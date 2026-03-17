# NAVSYS / PORTALIS OCR STACK — ANALYTICAL GMM
Version: v0.1  
Status: Build-follow blueprint  
Scope: Portalis OCR architecture only

## 1. Purpose

This GMM maps the accepted OCR architecture into buildable modules, data flow, contracts, and sequencing.

The stack is designed around five accepted injections:

1. Document Capture & Preprocessing Layer
2. Template/Profile-Guided Document Extraction Layer
3. Hierarchical OCR Segmentation Layer
4. Orientation-Aware OCR Layer
5. Field Confidence & Review Escalation Layer

These layers together answer:

- how raw capture is conditioned
- what kind of document is being seen
- how it should be segmented
- how each zone should be oriented
- whether the extracted field may be trusted

---

## 2. Top-Level Flow

```text
RAW INPUT
  ↓
CAPTURE & PREPROCESSING
  ↓
PAGE GEOMETRY / NORMALIZATION
  ↓
DOCUMENT CLASSIFICATION
  ↓
TEMPLATE / PROFILE MATCHING
  ↓
HIERARCHICAL SEGMENTATION
  ↓
ORIENTATION-AWARE NORMALIZATION
  ↓
OCR ENGINE BRANCH
  ↓
FIELD PARSER / EXTRACTOR
  ↓
FIELD CONFIDENCE & REVIEW
  ↓
CANONICAL MAPPER
  ↓
PORTALIS ARCHIVE / TCE / REVIEW
```

---

## 3. Analytical Module Map

### 3.1 Input Layer

#### `capture_ingest_service`
Responsibility:
- accepts raw images/PDF pages from scanner, phone capture, manual upload
- creates intake record
- assigns `capture_id`

Inputs:
- image path, PDF page raster, or in-memory image
- optional source hint

Outputs:
- `RawCapture`

Notes:
- no OCR here
- no semantic assumptions here

---

### 3.2 Capture & Preprocessing Layer

#### `preprocess_service`
Responsibility:
- normalize capture defects before OCR stack proceeds

Subfunctions:
- source-aware preprocess profile selection
- page boundary detection
- perspective correction
- spread split
- light dewarp
- brightness / contrast normalization
- denoise
- whole-image deskew / gross rotation correction
- capture quality scoring

Input:
- `RawCapture`

Output:
- `PreprocessedCapture`

Doctrine:
- clean the page before reading the page
- preserve before beautify

---

### 3.3 Page Geometry Layer

#### `page_geometry_service`
Responsibility:
- establish page working plane
- detect page count estimate after preprocessing
- persist page surfaces for downstream segmentation

Input:
- `PreprocessedCapture`

Output:
- list of `PageSurface`

Notes:
- if spread split occurred, emit 2+ pages
- provides normalized coordinates for downstream profile matching

---

### 3.4 Document Classification Layer

#### `document_classifier`
Responsibility:
- classify document family at a high level before profile match

Examples:
- deck_log
- navtex_strip
- certificate
- survey_form
- passport_or_id
- unknown

Input:
- `PageSurface`
- optional OCR-lite preview / anchor text hints

Output:
- `DocumentClassResult`

Notes:
- this is family-level, not full profile lock

---

### 3.5 Template / Profile-Guided Extraction Layer

#### `profile_registry`
Responsibility:
- store extraction profiles for recurring form families

#### `profile_matcher`
Responsibility:
- evaluate candidate profiles using:
  - anchor text
  - layout signatures
  - geometry cues
  - expected headers / ratios / row structures

Match states:
- EXACT_MATCH
- STRONG_MATCH
- PARTIAL_MATCH
- FAMILY_MATCH
- NO_MATCH

Input:
- `PageSurface`
- `DocumentClassResult`

Output:
- `ProfileMatchResult`

Doctrine:
- recognize the form before extracting the fields
- uncertain profile match must degrade safely to generic extraction

---

### 3.6 Hierarchical Segmentation Layer

#### `segmentation_service`
Responsibility:
- segment page progressively:
  - page
  - zones
  - lines
  - optional fallback character slices

Subfunctions:
- zone segmentation
- line segmentation inside text-bearing zones
- critical-field char-slice fallback generation

Region classes:
- HEADER
- METADATA
- TABLE
- TABLE_ROW
- TABLE_CELL
- REMARKS_BLOCK
- FOOTER
- IDENTITY_BLOCK
- NUMBER_BLOCK
- COORDINATE_BLOCK
- STAMP
- SIGNATURE
- PHOTO
- QR_BARCODE
- UNKNOWN

Input:
- `PageSurface`
- optional `ProfileMatchResult`

Output:
- list of `OCRUnit`

Doctrine:
- segment the structure before reading the symbols

---

### 3.7 Orientation-Aware OCR Layer

#### `orientation_service`
Responsibility:
- classify local orientation of each OCR unit and normalize before OCR

Orientation classes:
- HORIZONTAL
- VERTICAL_90
- VERTICAL_270
- DIAGONAL
- UNKNOWN

Subfunctions:
- dominant page skew handling
- local angle estimation
- per-zone rotate / deskew
- region role tagging
- audit metadata emission

Input:
- `OCRUnit`

Output:
- `OrientedOCRUnit`

Doctrine:
- find the angle before reading the meaning

---

### 3.8 OCR Engine Branch

#### `ocr_router`
Responsibility:
- route oriented OCR units to the most suitable OCR branch

Branches:
- Surya for printed/layout-heavy zones
- Tesseract fallback
- TrOCR for handwriting branch when applicable

Input:
- `OrientedOCRUnit`

Output:
- `OCRTextResult`

Notes:
- OCR should run only after structural and orientation prep
- fallback OCR passes must be justified, not brute-force global

---

### 3.9 Field Parser / Extractor

#### `field_extractor`
Responsibility:
- convert OCR text units into candidate fields based on:
  - profile guidance
  - region class
  - aliases / triggers
  - local structure

Input:
- `OCRTextResult`
- `ProfileMatchResult`
- segmentation metadata

Output:
- list of `FieldCandidate`

---

### 3.10 Field Confidence & Review Escalation Layer

#### `field_confidence_service`
Responsibility:
- judge whether candidate fields are reliable enough to accept

Signals:
- OCR confidence
- segmentation confidence
- orientation confidence
- format validity
- profile expectation match
- cross-field consistency
- suspicious OCR substitution patterns

States:
- PASS
- NORMALIZED
- FALLBACK_USED
- REVIEW_SUGGESTED
- REVIEW_REQUIRED

Input:
- list of `FieldCandidate`

Output:
- list of `ResolvedField`

Doctrine:
- confidence before acceptance
- prefer reviewable uncertainty over silent incorrect certainty

---

### 3.11 Canonical Mapping Layer

#### `canonical_mapper`
Responsibility:
- map accepted resolved fields into Portalis canonical schema

Input:
- list of `ResolvedField`

Output:
- `CanonicalFieldBundle`

Notes:
- only fields that pass confidence policy should reach this stage automatically
- review-required fields may enter as pending/unconfirmed candidates

---

### 3.12 Archive / Review / TCE Outputs

#### `document_pipeline`
Responsibility:
- orchestrate all prior services
- persist outputs
- emit review queue items
- expose trace data to TCE later

Outputs:
- archive-ready document record
- OCR audit trace
- review packet
- field bundle
- profile trace
- preprocessing trace

---

## 4. Build Order Recommendation

### Phase A — Foundation
1. `capture_ingest_service`
2. `preprocess_service`
3. `page_geometry_service`

### Phase B — Recognition
4. `document_classifier`
5. `profile_registry`
6. `profile_matcher`

### Phase C — Structural OCR
7. `segmentation_service`
8. `orientation_service`
9. `ocr_router`

### Phase D — Meaningful Extraction
10. `field_extractor`
11. `field_confidence_service`
12. `canonical_mapper`

### Phase E — Orchestration
13. `document_pipeline`
14. review packet generation
15. audit output / trace files

---

## 5. Canonical Doctrines

1. OCR quality begins before OCR.
2. Known forms should not be rediscovered from zero.
3. A document should be read hierarchically, not flat.
4. Orientation is part of document structure.
5. OCR output is a candidate interpretation, not truth.
6. Structured uncertainty is better than false certainty.

---

## 6. Critical Integration Notes

- Profile matching must be advisory, not tyrannical.
- Main-body text must not be globally distorted because a minor zone is angled.
- Character fallback must remain rare and targeted.
- Capture-quality degradation must influence downstream confidence.
- Every major stage should emit trace metadata for audit and future TCE use.

---

## 7. Minimal v0.1 Deliverable

A practical first end-to-end version should support:

- scanner/photo image intake
- preprocessing
- page normalization
- family-level classification
- profile-guided hints
- zone + line segmentation
- orientation normalization
- Surya primary OCR + Tesseract fallback
- field confidence evaluation
- review-required escalation
- canonical field output for a small set of document families

Recommended initial families:
- certificate
- passport/ID-style doc
- deck-log-like page
- NAVTEX/NAVTEX-strip-like page
