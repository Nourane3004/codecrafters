"""
Quality Gate + Enrichment Layer
---------------------------------
Sits between the preprocessing pipeline and the agent committee.
Matches diagram Image 4:
  - Language detect   (refine / confirm language)
  - Confidence score  (overall preprocessing confidence)
  - Dedup hash        (already computed upstream, verified here)
  - Reject path       (too low quality → stop pipeline)
"""

from __future__ import annotations
import hashlib
import logging

from Preprocessing.app.models.feature_object import NormalizedFeatureObject, InputType

logger = logging.getLogger(__name__)


# ── Language confidence mapping ──────────────────────────────────
# Maps detected language codes to human-readable labels
LANG_MAP = {
    "ar":      "Arabic",
    "en":      "English",
    "fr":      "French",
    "unknown": "Unknown",
}


def enrich(nfo: NormalizedFeatureObject) -> NormalizedFeatureObject:
    """
    Apply quality gate and enrichment to a NormalizedFeatureObject.

    Returns the same object (mutated) with:
      - quality_passed   confirmed / overridden
      - quality_reason   set to a human-readable string
      - language         normalised
      - dedup_hash       verified / regenerated if missing

    If quality_passed is False, the pipeline should STOP here
    and return the rejection reason to the caller.
    """

    # ── 1. Dedup hash safety net ─────────────────────────────────
    if not nfo.dedup_hash:
        nfo.dedup_hash = hashlib.sha256(nfo.text.encode()).hexdigest()

    # ── 2. Language normalisation ────────────────────────────────
    if nfo.language:
        # Strip region suffix (e.g. "en-US" → "en")
        lang_code    = nfo.language.split("-")[0].lower()
        nfo.language = LANG_MAP.get(lang_code, lang_code)

    # ── 3. Content-specific quality checks ──────────────────────
    # If the processor already failed the quality gate, respect it.
    if not nfo.quality_passed:
        return nfo

    failed, reason = _content_quality_checks(nfo)
    if failed:
        nfo.quality_passed = False
        nfo.quality_reason = reason
        return nfo

    # ── 4. Preprocessing confidence score ───────────────────────
    score = _compute_confidence(nfo)
    if score < 0.15:
        nfo.quality_passed = False
        nfo.quality_reason = f"Preprocessing confidence too low ({score:.0%})"
        return nfo

    # Only mark passed if not already failed upstream
    if nfo.quality_passed:
        nfo.quality_reason = f"OK (confidence {score:.0%})"
    return nfo


# ── Internal helpers ─────────────────────────────────────────────

def _content_quality_checks(nfo: NormalizedFeatureObject) -> tuple[bool, str]:
    """Returns (failed: bool, reason: str)."""

    if nfo.input_type == InputType.IMAGE:
        meta = nfo.image_meta
        if not meta:
            return True, "No image metadata extracted"
        if meta.width == 0 or meta.height == 0:
            return True, "Zero-dimension image"

    if nfo.input_type == InputType.URL:
        data = nfo.url_data
        if not data:
            return True, "No URL data extracted"
        if data.status_code == 0:
            return True, "Page unreachable"

    if nfo.input_type == InputType.DOCUMENT:
        doc = nfo.document_data
        if not doc:
            return True, "No document data extracted"
        if doc.text_extract.extraction_method in ("failed", "unsupported"):
            return True, f"Document extraction {doc.text_extract.extraction_method}"

    if nfo.input_type == InputType.VIDEO:
        vid = nfo.video_data
        if not vid:
            return True, "No video data extracted"
        meta = vid.metadata
        if meta.duration_seconds is not None and meta.duration_seconds < 0.5:
            return True, "Video too short"

    return False, ""


def _compute_confidence(nfo: NormalizedFeatureObject) -> float:
    """
    Simple heuristic confidence score (0-1) based on how much
    useful data was successfully extracted.
    """
    score = 0.0

    # Text content present?
    if nfo.text and len(nfo.text.strip()) > 30:
        score += 0.4

    if nfo.input_type == InputType.IMAGE and nfo.image_meta:
        meta = nfo.image_meta
        score += 0.3 * meta.ocr.confidence
        if not meta.exif.exif_stripped:
            score += 0.2
        if not nfo.errors:
            score += 0.1

    if nfo.input_type == InputType.URL and nfo.url_data:
        data = nfo.url_data
        if 200 <= data.status_code < 300:
            score += 0.3
        if data.meta.title:
            score += 0.15
        if data.meta.description:
            score += 0.1
        if not data.domain_info.is_suspicious:
            score += 0.05

    if nfo.input_type == InputType.DOCUMENT and nfo.document_data:
        doc = nfo.document_data
        if doc.text_extract.page_count > 0:
            score += 0.2
        if doc.layout.headings:
            score += 0.15
        if doc.doc_meta.author:
            score += 0.1
        if doc.doc_meta.creation_date:
            score += 0.05
        if not nfo.errors:
            score += 0.1

    if nfo.input_type == InputType.VIDEO and nfo.video_data:
        vid = nfo.video_data
        if vid.metadata.duration_seconds:
            score += 0.2
        if vid.metadata.video_codec:
            score += 0.1
        if vid.asr.raw_text:
            score += 0.2
        if vid.keyframe_count > 0:
            score += 0.1
        if not nfo.errors:
            score += 0.0   # no additional bonus — errors are soft for video

    return min(score, 1.0)