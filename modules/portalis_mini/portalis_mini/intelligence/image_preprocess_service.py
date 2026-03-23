from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

import cv2
import numpy as np


@dataclass(slots=True)
class PreprocessOptions:
    grayscale: bool = True
    denoise: bool = True
    deskew: bool = True
    contrast_boost: bool = True
    adaptive_binarize: bool = False
    resize_min_width: int = 1800
    sharpen: bool = True
    trim_border: bool = False
    crop_to_content: bool = True
    crop_pad: int = 30
    save_debug_steps: bool = False
    auto_rotate: bool = False

@dataclass(slots=True)
class PreprocessResult:
    ok: bool
    source_path: str
    output_path: str
    width: int
    height: int
    channels: int
    steps_applied: List[str]
    diagnostics: Dict[str, Any]
    debug_paths: List[str]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    return image


def _save_image(path: Path, image: np.ndarray) -> None:
    _ensure_parent(path)
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise ValueError(f"Failed to save image: {path}")


def _to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _resize_if_needed(image: np.ndarray, min_width: int) -> Tuple[np.ndarray, bool, float]:
    h, w = image.shape[:2]
    if w >= min_width:
        return image, False, 1.0

    scale = min_width / float(w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return resized, True, scale


def _denoise(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, None, 15, 7, 21)
    return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)


def _boost_contrast_gray(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _sharpen_gray(gray: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(gray, -1, kernel)


def _adaptive_binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15
    )


def _estimate_skew_angle(gray: np.ndarray) -> float:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    return float(angle)


def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.15:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    matrix[0, 2] += (new_w / 2) - center[0]
    matrix[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


def _trim_border(gray: np.ndarray, threshold: int = 245) -> np.ndarray:
    mask = gray < threshold
    coords = np.column_stack(np.where(mask))
    if coords.size == 0:
        return gray

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return gray[y0:y1, x0:x1]


def preprocess_image(
    image_path: str | Path,
    output_path: str | Path,
    options: Optional[PreprocessOptions] = None,
) -> PreprocessResult:
    options = options or PreprocessOptions()

    image_path = Path(image_path)
    output_path = Path(output_path)

    debug_paths: List[str] = []
    steps_applied: List[str] = []
    diagnostics: Dict[str, Any] = {}

    image = _load_image(image_path)
    diagnostics["original_shape"] = list(image.shape)

    if options.crop_to_content:
        before_shape = list(image.shape)
        image = _crop_to_content(image, pad=options.crop_pad)
        after_shape = list(image.shape)
        diagnostics["crop_to_content_before_shape"] = before_shape
        diagnostics["crop_to_content_after_shape"] = after_shape
        steps_applied.append("crop_to_content")
        if options.auto_rotate:
            image = _auto_rotate_to_upright(image)
            steps_applied.append("auto_rotate")

    image, resized, scale = _resize_if_needed(image, options.resize_min_width)
    diagnostics["resized"] = resized
    diagnostics["resize_scale"] = scale
    if resized:
        steps_applied.append("resize")

    if options.denoise:
        image = _denoise(image)
        steps_applied.append("denoise")

    gray = _to_gray(image)
    if options.grayscale:
        steps_applied.append("grayscale")

    if options.contrast_boost:
        gray = _boost_contrast_gray(gray)
        steps_applied.append("contrast_boost")

    if options.sharpen:
        gray = _sharpen_gray(gray)
        steps_applied.append("sharpen")

    if options.deskew:
        angle = _estimate_skew_angle(gray)
        diagnostics["deskew_angle_deg"] = angle
        gray = _rotate_image(gray, angle)
        steps_applied.append("deskew")

    if options.trim_border:
        gray = _trim_border(gray)
        steps_applied.append("trim_border")

    if options.adaptive_binarize:
        gray = _adaptive_binarize(gray)
        steps_applied.append("adaptive_binarize")

    _save_image(output_path, gray)

    h, w = gray.shape[:2]
    return PreprocessResult(
        ok=True,
        source_path=str(image_path),
        output_path=str(output_path),
        width=w,
        height=h,
        channels=1,
        steps_applied=steps_applied,
        diagnostics=diagnostics,
        debug_paths=debug_paths,
    )

def _auto_rotate_to_upright(image: np.ndarray) -> np.ndarray:
    rotations = [
        (0, image),
        (90, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
        (180, cv2.rotate(image, cv2.ROTATE_180)),
        (270, cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]

    best_score = -1
    best_img = image

    for angle, img in rotations:
        gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # heuristic: horizontal text produces more horizontal gradients
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        score = np.mean(np.abs(sobel))

        if score > best_score:
            best_score = score
            best_img = img

    return best_img

def _crop_to_content(image: np.ndarray, pad: int = 30) -> np.ndarray:
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Blur slightly to suppress tiny texture noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge map
    edges = cv2.Canny(blur, 50, 150)

    # Close gaps to form larger document contours
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find outer contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    H, W = gray.shape[:2]
    page_area = H * W

    best_rect = None
    best_score = -1.0

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h

        # Ignore tiny junk
        if area < 0.10 * page_area:
            continue

        # Prefer tall-ish, large regions
        aspect = h / max(w, 1)
        fill_score = area / page_area
        score = fill_score + 0.15 * min(aspect, 2.5)


        if score > best_score:
            best_score = score
            best_rect = (x, y, w, h)

    if best_rect is None:
        return image

    x, y, w, h = best_rect

    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)

    cropped = image[y0:y1, x0:x1]

    orig_h, orig_w = image.shape[:2]
    crop_h, crop_w = cropped.shape[:2]

    orig_area = orig_h * orig_w
    crop_area = crop_h * crop_w

    # Reject suspicious crops that are too small or too distorted
    if crop_area < 0.35 * orig_area:
        return image

    aspect_orig = orig_h / max(orig_w, 1)
    aspect_crop = crop_h / max(crop_w, 1)

    if abs(aspect_crop - aspect_orig) > 0.8:
        return image

    return cropped

def _extract_bottom_mrz_zone(image: np.ndarray, fraction: float = 0.28) -> np.ndarray:
    h, w = image.shape[:2]
    y0 = int(h * (1.0 - fraction))
    return image[y0:h, 0:w]

def save_preprocess_metadata(result: PreprocessResult, metadata_path: str | Path) -> None:
    metadata_path = Path(metadata_path)
    _ensure_parent(metadata_path)
    metadata_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")