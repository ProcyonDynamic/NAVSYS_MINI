# NAVSYS / PORTALIS OCR STACK — API BLUEPRINT
Version: v0.1  
Status: Internal build contract  
Format: Python-style pseudocontracts for implementation guidance

## 1. Core Enums

```python
from enum import Enum

class SourceType(str, Enum):
    PHONE = "PHONE"
    TABLET = "TABLET"
    WEBCAM = "WEBCAM"
    SCANNER = "SCANNER"
    MFP = "MFP"
    PDF_RASTER = "PDF_RASTER"
    UNKNOWN = "UNKNOWN"

class CaptureQualityState(str, Enum):
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    REVIEW_SUGGESTED = "REVIEW_SUGGESTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RECAPTURE_RECOMMENDED = "RECAPTURE_RECOMMENDED"

class MatchState(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    FAMILY_MATCH = "FAMILY_MATCH"
    NO_MATCH = "NO_MATCH"

class RegionClass(str, Enum):
    HEADER = "HEADER"
    METADATA = "METADATA"
    TABLE = "TABLE"
    TABLE_ROW = "TABLE_ROW"
    TABLE_CELL = "TABLE_CELL"
    REMARKS_BLOCK = "REMARKS_BLOCK"
    FOOTER = "FOOTER"
    IDENTITY_BLOCK = "IDENTITY_BLOCK"
    NUMBER_BLOCK = "NUMBER_BLOCK"
    COORDINATE_BLOCK = "COORDINATE_BLOCK"
    STAMP = "STAMP"
    SIGNATURE = "SIGNATURE"
    PHOTO = "PHOTO"
    QR_BARCODE = "QR_BARCODE"
    UNKNOWN = "UNKNOWN"

class OrientationClass(str, Enum):
    HORIZONTAL = "HORIZONTAL"
    VERTICAL_90 = "VERTICAL_90"
    VERTICAL_270 = "VERTICAL_270"
    DIAGONAL = "DIAGONAL"
    UNKNOWN = "UNKNOWN"

class SegmentationLevel(str, Enum):
    PAGE = "PAGE"
    ZONE = "ZONE"
    LINE = "LINE"
    CHAR = "CHAR"

class ConfidenceState(str, Enum):
    PASS = "PASS"
    NORMALIZED = "NORMALIZED"
    FALLBACK_USED = "FALLBACK_USED"
    REVIEW_SUGGESTED = "REVIEW_SUGGESTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
```

---

## 2. Core Data Models

```python
from dataclasses import dataclass, field
from typing import Any, Optional

BBox = tuple[int, int, int, int]  # x, y, w, h

@dataclass
class RawCapture:
    capture_id: str
    source_type: SourceType
    input_path: str
    source_hint: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PreprocessedCapture:
    capture_id: str
    source_type: SourceType
    preprocess_profile: str
    image_path: str
    page_detected: bool
    page_count_estimate: int
    perspective_corrected: bool
    spread_split_applied: bool
    dewarp_applied: bool
    rotation_deg: float
    contrast_normalized: bool
    noise_reduction_applied: bool
    capture_quality_score: float
    capture_quality_state: CaptureQualityState
    review_flag: bool
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class PageSurface:
    capture_id: str
    page_id: str
    image_path: str
    bbox: Optional[BBox]
    normalized_width: int
    normalized_height: int
    page_confidence: float
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentClassResult:
    page_id: str
    document_family: str
    score: float
    candidate_families: list[tuple[str, float]]

@dataclass
class ProfileMatchResult:
    page_id: str
    selected_profile_id: Optional[str]
    document_family: str
    match_state: MatchState
    match_score: float
    candidate_profiles: list[tuple[str, float]]
    anchor_evidence: list[str] = field(default_factory=list)
    geometry_evidence: list[str] = field(default_factory=list)
    fallback_mode: bool = False
    review_flag: bool = False

@dataclass
class OCRUnit:
    page_id: str
    zone_id: str
    line_id: Optional[str]
    segmentation_level: SegmentationLevel
    region_class: RegionClass
    bbox: BBox
    parent_bbox: Optional[BBox]
    orientation_class: OrientationClass
    confidence: float
    ocr_ready_crop_path: str
    review_flag: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class OrientedOCRUnit:
    page_id: str
    zone_id: str
    line_id: Optional[str]
    segmentation_level: SegmentationLevel
    region_class: RegionClass
    bbox: BBox
    detected_angle_deg: float
    normalized_angle_deg: float
    orientation_class: OrientationClass
    applied_transform: str
    confidence: float
    image_path: str
    review_flag: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class OCRTextResult:
    page_id: str
    zone_id: str
    line_id: Optional[str]
    region_class: RegionClass
    text: str
    engine_name: str
    ocr_confidence: float
    segmentation_level: SegmentationLevel
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldCandidate:
    field_name: str
    field_value: str
    field_type: str
    source_page_id: str
    source_zone_id: str
    source_line_id: Optional[str]
    ocr_confidence: float
    parser_confidence: float
    profile_id: Optional[str]
    region_class: RegionClass
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class ResolvedField:
    field_name: str
    field_value: str
    normalized_value: Optional[str]
    ocr_confidence: float
    format_confidence: float
    cross_validation_score: float
    overall_confidence: float
    confidence_state: ConfidenceState
    fallback_used: bool
    review_flag: bool
    source_zone_id: str
    source_line_id: Optional[str]
    critical_field_flag: bool = False
    trace: dict[str, Any] = field(default_factory=dict)

@dataclass
class CanonicalFieldBundle:
    document_id: str
    fields: list[ResolvedField]
    profile_id: Optional[str]
    archive_ready: bool
    review_required: bool
    trace: dict[str, Any] = field(default_factory=dict)
```

---

## 3. Service Contracts

### 3.1 Capture Ingest

```python
def ingest_capture(
    input_path: str,
    source_type: SourceType,
    source_hint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RawCapture:
    ...
```

Behavior:
- creates `capture_id`
- records raw input metadata
- does not alter content

---

### 3.2 Preprocessing

```python
def preprocess_capture(
    capture: RawCapture,
    preprocess_profile: str | None = None,
) -> PreprocessedCapture:
    ...
```

Responsibilities:
- page edge detection
- perspective correction
- spread split
- grayscale/contrast normalization
- denoise
- whole-image deskew
- capture quality scoring

---

### 3.3 Page Geometry

```python
def build_page_surfaces(
    preprocessed: PreprocessedCapture,
) -> list[PageSurface]:
    ...
```

Responsibilities:
- output one page or multiple split pages
- keep normalized coordinate system

---

### 3.4 Document Classification

```python
def classify_document_family(
    page: PageSurface,
) -> DocumentClassResult:
    ...
```

Responsibilities:
- family-level identification before profile matching

---

### 3.5 Profile Match

```python
def match_extraction_profile(
    page: PageSurface,
    doc_class: DocumentClassResult,
) -> ProfileMatchResult:
    ...
```

Responsibilities:
- profile lookup
- anchor/geometry/layout evidence scoring
- safe degradation to generic extraction

---

### 3.6 Segmentation

```python
def segment_page(
    page: PageSurface,
    profile: ProfileMatchResult | None = None,
) -> list[OCRUnit]:
    ...
```

Responsibilities:
- page → zones → lines
- optional critical char fallback planning
- emit structural region classes

---

### 3.7 Orientation

```python
def normalize_orientation(
    units: list[OCRUnit],
) -> list[OrientedOCRUnit]:
    ...
```

Responsibilities:
- per-unit angle detection
- local rotate / deskew
- orientation trace metadata

---

### 3.8 OCR Routing

```python
def ocr_units(
    units: list[OrientedOCRUnit],
    preferred_engine: str | None = None,
) -> list[OCRTextResult]:
    ...
```

Responsibilities:
- engine routing
- OCR execution
- confidence capture

---

### 3.9 Field Parsing

```python
def extract_field_candidates(
    results: list[OCRTextResult],
    profile: ProfileMatchResult | None = None,
) -> list[FieldCandidate]:
    ...
```

Responsibilities:
- profile-guided or generic field extraction
- field aliases and local parse rules

---

### 3.10 Field Confidence

```python
def resolve_field_confidence(
    fields: list[FieldCandidate],
) -> list[ResolvedField]:
    ...
```

Responsibilities:
- regex/grammar validation
- cross-field checks
- suspicious OCR pattern checks
- targeted fallback retry for critical short fields
- escalation state

---

### 3.11 Canonical Mapping

```python
def map_to_canonical_bundle(
    document_id: str,
    fields: list[ResolvedField],
    profile: ProfileMatchResult | None = None,
) -> CanonicalFieldBundle:
    ...
```

Responsibilities:
- map fields to canonical Portalis schema
- indicate if archive-ready or review-blocked

---

### 3.12 Full Orchestrator

```python
def run_document_pipeline(
    input_path: str,
    source_type: SourceType,
    source_hint: str | None = None,
) -> CanonicalFieldBundle:
    ...
```

Expected sequence:
1. ingest_capture
2. preprocess_capture
3. build_page_surfaces
4. classify_document_family
5. match_extraction_profile
6. segment_page
7. normalize_orientation
8. ocr_units
9. extract_field_candidates
10. resolve_field_confidence
11. map_to_canonical_bundle

---

## 4. File / Module Layout Suggestion

```text
modules/portalis_ocr/
    models.py
    capture_ingest_service.py
    preprocess_service.py
    page_geometry_service.py
    document_classifier.py
    profile_registry.py
    profile_matcher.py
    segmentation_service.py
    orientation_service.py
    ocr_router.py
    field_extractor.py
    field_confidence_service.py
    canonical_mapper.py
    document_pipeline.py

data/PORTALIS/
    ocr_profiles/
    preprocess_profiles/
    outputs/
    review/
```

---

## 5. Minimal Profile File Schema

```json
{
  "profile_id": "DECK_LOG_GREEK_EN_V1",
  "family_name": "deck_log",
  "version": "1",
  "anchor_phrases": ["DECK LOG"],
  "geometry_hints": {
    "remarks_zone": [0.72, 0.12, 0.25, 0.65]
  },
  "zone_rules": [
    {"name": "remarks", "region_class": "REMARKS_BLOCK"},
    {"name": "footer", "region_class": "FOOTER"}
  ],
  "field_rules": [
    {"field_name": "date", "type": "date"},
    {"field_name": "remarks_text", "type": "text"}
  ]
}
```

---

## 6. Review Policy Notes

Critical fields should require stricter acceptance:
- coordinates
- IMO number
- certificate number
- expiry date
- passport number
- visa control/FIN number

Narrative fields may tolerate:
- REVIEW_SUGGESTED
- lower OCR confidence
- no char fallback

---

## 7. Trace / Audit Requirements

Each stage should emit metadata suitable for later TCE use.

Minimum stage traces:
- preprocessing trace
- profile match trace
- segmentation trace
- orientation trace
- OCR engine trace
- field confidence trace
- review reason trace

---

## 8. Practical v0.1 Target

A realistic first implementation should support:
- scanner + photo image input
- one or two preprocess profiles
- family classification
- profile-guided hints for 2–4 document classes
- zone/line segmentation
- orientation correction
- Surya primary OCR
- Tesseract fallback
- confidence scoring + review escalation
- canonical output bundle
