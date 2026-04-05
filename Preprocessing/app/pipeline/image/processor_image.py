"""
Image Preprocessing Branch
---------------------------
Steps  (matches diagram Image 3):
  1. OCR          – TrOCR / Tesseract
  2. UI detection – OpenCV (edge / structure heuristics)
  3. EXIF extract – exifread + anomaly flags
"""

from __future__ import annotations
import io
import hashlib
import logging
from pathlib import Path
from typing import Union

import cv2
import exifread
import numpy as np
import pytesseract
from PIL import Image as PILImage

from Preprocessing.app.models.feature_object import (
    EXIFData,
    ImageMetadata,
    InputType,
    NormalizedFeatureObject,
    OCRResult,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
# 1.  OCR
# ══════════════════════════════════════════════════════

def run_ocr(pil_img: PILImage.Image) -> OCRResult:
    """
    Extract text from image using Tesseract.
    Returns OCRResult with raw_text and a rough confidence score.
    """
    try:
        # Get detailed output with confidence per word
        data = pytesseract.image_to_data(
            pil_img,
            output_type=pytesseract.Output.DICT,
            config="--psm 3"           # fully automatic page segmentation
        )

        words      = [w for w in data["text"] if w.strip()]
        confs      = [c for c, w in zip(data["conf"], data["text"])
                      if w.strip() and c != -1]

        raw_text   = " ".join(words)
        confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.0

        # Detect language via simple heuristic (Arabic unicode range)
        language = _detect_language(raw_text)

        return OCRResult(
            raw_text=raw_text,
            language=language,
            confidence=round(confidence, 3),
        )

    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return OCRResult(raw_text="", confidence=0.0)


def _detect_language(text: str) -> str:
    """Simple script-based language hint."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    latin_chars  = sum(1 for c in text if c.isalpha() and ord(c) < 256)
    if not text.strip():
        return "unknown"
    return "ar" if arabic_chars > latin_chars else "en"


# ══════════════════════════════════════════════════════
# 2.  UI / Layout detection  (LayoutLM → OpenCV heuristic)
# ══════════════════════════════════════════════════════

def run_ui_detection(pil_img: PILImage.Image) -> dict:
    """
    Lightweight OpenCV-based structure detection.
    Returns a dict of flags useful for downstream agents:
      - has_text_blocks   : dense text regions found
      - has_table         : horizontal line grid detected
      - has_ui_elements   : buttons / form-like rectangles
      - edge_density      : ratio of edge pixels (manipulation signal)
    """
    try:
        img_np  = np.array(pil_img.convert("RGB"))
        gray    = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        edges   = cv2.Canny(gray, 50, 150)

        edge_density = float(np.count_nonzero(edges)) / edges.size

        # Detect horizontal lines (table heuristic)
        h_kernel   = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        h_lines    = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel)
        has_table  = bool(np.count_nonzero(h_lines) > 200)

        # Detect rectangular UI elements
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        rect_count  = sum(
            1 for c in contours
            if _is_rect_like(c) and cv2.contourArea(c) > 500
        )
        has_ui_elements = rect_count > 3

        return {
            "has_text_blocks":  edge_density > 0.05,
            "has_table":        has_table,
            "has_ui_elements":  has_ui_elements,
            "edge_density":     round(edge_density, 4),
        }

    except Exception as e:
        logger.warning(f"UI detection failed: {e}")
        return {"has_text_blocks": False, "has_table": False,
                "has_ui_elements": False, "edge_density": 0.0}


def _is_rect_like(contour) -> bool:
    peri  = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
    return len(approx) == 4


# ══════════════════════════════════════════════════════
# 3.  EXIF extraction
# ══════════════════════════════════════════════════════

def run_exif_extract(image_bytes: bytes) -> EXIFData:
    """
    Extract EXIF metadata and flag anomalies.
    Anomaly: EXIF completely missing on a JPEG is itself suspicious.
    """
    try:
        tags = exifread.process_file(
            io.BytesIO(image_bytes), details=False, stop_tag="EOF"
        )

        if not tags:
            return EXIFData(exif_stripped=True)

        def get(tag: str) -> str | None:
            v = tags.get(tag)
            return str(v) if v else None

        gps_lat = _parse_gps(tags, "GPS GPSLatitude",  "GPS GPSLatitudeRef")
        gps_lon = _parse_gps(tags, "GPS GPSLongitude", "GPS GPSLongitudeRef")

        dt_orig     = get("EXIF DateTimeOriginal")
        dt_modified = get("Image DateTime")
        mismatch    = bool(
            dt_orig and dt_modified and dt_orig != dt_modified
        )

        return EXIFData(
            camera_make    = get("Image Make"),
            camera_model   = get("Image Model"),
            gps_lat        = gps_lat,
            gps_lon        = gps_lon,
            datetime_taken = dt_orig or dt_modified,
            software       = get("Image Software"),
            exif_stripped  = False,
            datetime_mismatch = mismatch,
        )

    except Exception as e:
        logger.warning(f"EXIF extraction failed: {e}")
        return EXIFData(exif_stripped=True)


def _parse_gps(tags: dict, coord_tag: str, ref_tag: str) -> float | None:
    try:
        coord = tags.get(coord_tag)
        ref   = str(tags.get(ref_tag, ""))
        if not coord:
            return None
        vals  = coord.values
        deg   = float(vals[0].num) / float(vals[0].den)
        mn    = float(vals[1].num) / float(vals[1].den)
        sec   = float(vals[2].num) / float(vals[2].den)
        result = deg + mn / 60 + sec / 3600
        if ref in ("S", "W"):
            result = -result
        return round(result, 6)
    except Exception:
        return None


# ══════════════════════════════════════════════════════
# Pipeline entry point
# ══════════════════════════════════════════════════════

def preprocess_image(
    image_bytes: bytes,
    source_ref: str = "uploaded_image",
) -> NormalizedFeatureObject:
    """
    Full image preprocessing pipeline.
    Returns a NormalizedFeatureObject ready for the agent committee.
    """
    errors: list[str] = []

    # ── Load image ──
    try:
        pil_img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return NormalizedFeatureObject(
            input_type=InputType.IMAGE,
            source_ref=source_ref,
            errors=[f"Cannot open image: {e}"],
        )

    width, height = pil_img.size
    fmt           = pil_img.format or "unknown"

    # ── Step 1: OCR ──
    ocr = run_ocr(pil_img)

    # ── Step 2: UI detection ──
    ui_flags = run_ui_detection(pil_img)

    # ── Step 3: EXIF ──
    exif = run_exif_extract(image_bytes)

    # ── Dedup hash (SHA-256 of raw bytes) ──
    dedup_hash = hashlib.sha256(image_bytes).hexdigest()

    # ── Assemble image metadata ──
    image_meta = ImageMetadata(
        width=width,
        height=height,
        format=fmt,
        file_size_bytes=len(image_bytes),
        has_transparency=("A" in pil_img.getbands()),
        ocr=ocr,
        exif=exif,
    )

    # ── Quality gate ──
    quality_passed, quality_reason = _quality_gate(pil_img, ocr, exif)

    # ── Primary text surface ──
    primary_text = ocr.raw_text.strip()

    return NormalizedFeatureObject(
        input_type     = InputType.IMAGE,
        source_ref     = source_ref,
        text           = primary_text,
        language       = ocr.language,
        image_meta     = image_meta,
        quality_passed = quality_passed,
        quality_reason = quality_reason,
        dedup_hash     = dedup_hash,
        errors         = errors,
    )


def _quality_gate(
    img: PILImage.Image,
    ocr: OCRResult,
    exif: EXIFData,
) -> tuple[bool, str]:
    w, h = img.size
    if w < 50 or h < 50:
        return False, "Image too small"
    if w * h < 2500:
        return False, "Resolution too low"
    return True, "OK"