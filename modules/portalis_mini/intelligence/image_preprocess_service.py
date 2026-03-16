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
    save_debug_steps: bool = False


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

    image = _crop_to_content(image)
    steps_applied.append("crop_to_content")
    image_path = Path(image_path)
    output_path = Path(output_path)

    debug_paths: List[str] = []
    steps_applied: List[str] = []
    diagnostics: Dict[str, Any] = {}

    image = _load_image(image_path)
    diagnostics["original_shape"] = list(image.shape)

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

def _crop_to_content(image: np.ndarray, threshold: int = 245, pad: int = 20) -> np.ndarray:
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    mask = gray < threshold
    coords = np.column_stack(np.where(mask))
    if coords.size == 0:
        return image

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1

    y0 = max(0, y0 - pad)
    x0 = max(0, x0 - pad)
    y1 = min(gray.shape[0], y1 + pad)
    x1 = min(gray.shape[1], x1 + pad)

    return image[y0:y1, x0:x1]

def save_preprocess_metadata(result: PreprocessResult, metadata_path: str | Path) -> None:
    metadata_path = Path(metadata_path)
    _ensure_parent(metadata_path)
    metadata_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")