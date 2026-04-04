"""
Complete pipeline smoke tests — covers all four branches:
  1. Image   (processor.py)
  2. URL     (processor.py)
  3. Document (document/processor.py)
  4. Video   (video/processor.py)

Run from the project root:
    python test_pipeline.py

Each test is self-contained and prints a structured report.
A final summary shows pass / skip / fail per branch.

Environment notes
-----------------
* Image  — requires Tesseract on PATH; skipped otherwise.
* URL    — requires outbound HTTPS; skipped if network is unreachable.
* Video  — requires FFmpeg on PATH; skipped otherwise.
* Document — fully offline; always runs.
"""

from __future__ import annotations
import asyncio
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from app.pipeline.image.processor    import preprocess_image
from app.pipeline.url.processor      import preprocess_url
from app.pipeline.document.processor import preprocess_document
from app.pipeline.video.processor    import preprocess_video
from app.pipeline.quality_gate       import enrich
from app.models.feature_object       import InputType

# ── Dependency / environment probes ──────────────────────────────

def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _network_available(url: str = "https://example.com") -> bool:
    """Quick SSL-aware connectivity check using httpx."""
    try:
        import httpx
        with httpx.Client(timeout=6, verify=False) as c:
            r = c.get(url)
            return r.status_code < 500
    except Exception:
        return False


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


# ── ANSI colours ─────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}PASS{RESET}"
SKIP = f"{YELLOW}SKIP{RESET}"
FAIL = f"{RED}FAIL{RESET}"

_results: dict[str, str] = {}   # branch → PASS | SKIP | FAIL


# ── Helpers ───────────────────────────────────────────────────────

def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*55}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*55}{RESET}")


def row(label: str, value) -> None:
    print(f"  {label:<22}: {value}")


def assert_field(label: str, value, check, branch: str) -> None:
    """Print the field and raise if check fails."""
    row(label, value)
    if not check:
        raise AssertionError(f"{label} check failed — got: {value!r}")


# ══════════════════════════════════════════════════════════════════
# 1.  IMAGE
# ══════════════════════════════════════════════════════════════════

def test_image() -> None:
    header("TEST 1 — Image pipeline")

    # ── Dependency check ──
    if not _tesseract_available():
        print(f"  {SKIP} — Tesseract not on PATH; image branch skipped")
        print(  "           Install: https://github.com/UB-Mannheim/tesseract/wiki")
        _results["Image"] = "SKIP"
        return

    from PIL import Image as PILImage

    # ── 1a. Minimal red square (no text, no EXIF) ──
    img = PILImage.new("RGB", (200, 200), color=(220, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    nfo = preprocess_image(image_bytes, source_ref="test_red_square.jpg")
    nfo = enrich(nfo)

    assert_field("input_type",     nfo.input_type,                 nfo.input_type == InputType.IMAGE,    "image")
    assert_field("quality_passed", nfo.quality_passed,             isinstance(nfo.quality_passed, bool), "image")
    assert_field("quality_reason", nfo.quality_reason,             nfo.quality_reason is not None,       "image")
    # language may be None for a plain colour image with no OCR text — that is acceptable
    row("language", nfo.language)
    assert_field("dedup_hash",     nfo.dedup_hash[:16] + "…",      len(nfo.dedup_hash) == 64,            "image")
    assert_field("image size",     f"{nfo.image_meta.width}×{nfo.image_meta.height}",
                                                                    nfo.image_meta.width == 200,          "image")
    assert_field("exif_stripped",  nfo.image_meta.exif.exif_stripped,
                                                                    isinstance(nfo.image_meta.exif.exif_stripped, bool), "image")
    assert_field("ocr confidence", nfo.image_meta.ocr.confidence,  0.0 <= nfo.image_meta.ocr.confidence <= 1.0, "image")
    assert_field("errors",         nfo.errors,                     isinstance(nfo.errors, list),         "image")

    # ── 1b. Reject path — image too small ──
    tiny = PILImage.new("RGB", (10, 10), color=(0, 0, 0))
    buf2 = io.BytesIO()
    tiny.save(buf2, format="JPEG")
    nfo2 = preprocess_image(buf2.getvalue(), source_ref="tiny.jpg")
    nfo2 = enrich(nfo2)
    assert_field("tiny → rejected", nfo2.quality_passed, not nfo2.quality_passed, "image")

    print(f"\n  {PASS} — Image branch OK")
    _results["Image"] = "PASS"


# ══════════════════════════════════════════════════════════════════
# 2.  URL
# ══════════════════════════════════════════════════════════════════

async def test_url() -> None:
    header("TEST 2 — URL pipeline")

    # ── Dependency / network check ──
    if not _network_available():
        print(f"  {SKIP} — No outbound HTTPS (SSL or network issue); URL branch skipped")
        _results["URL"] = "SKIP"
        return

    # Patch httpx inside the url processor to skip SSL verification on Windows
    # where the system CA bundle may not be trusted by Python's ssl module.
    import httpx
    from unittest.mock import patch, AsyncMock
    import app.pipeline.url.processor as url_mod

    _original_client = httpx.AsyncClient

    class _NoVerifyClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["verify"] = False
            super().__init__(*args, **kwargs)

    url = "https://example.com"

    with patch.object(url_mod.httpx, "AsyncClient", _NoVerifyClient):
        nfo = await preprocess_url(url)
    nfo = enrich(nfo)

    assert_field("input_type",     nfo.input_type,                     nfo.input_type == InputType.URL,      "url")
    assert_field("source_ref",     nfo.source_ref,                     nfo.source_ref == url,                "url")
    assert_field("quality_passed", nfo.quality_passed,                 isinstance(nfo.quality_passed, bool), "url")
    assert_field("quality_reason", nfo.quality_reason,                 nfo.quality_reason is not None,       "url")
    # language tag is absent from some pages — treat as a soft field
    row("language", nfo.language)
    assert_field("dedup_hash",     nfo.dedup_hash[:16] + "…",          len(nfo.dedup_hash) == 64,            "url")
    assert_field("status_code",    nfo.url_data.status_code,           nfo.url_data.status_code == 200,      "url")
    assert_field("page title",     nfo.url_data.meta.title,            bool(nfo.url_data.meta.title),        "url")
    assert_field("domain",         nfo.url_data.domain_info.domain,    bool(nfo.url_data.domain_info.domain),"url")
    assert_field("text preview",   nfo.text[:60],                      len(nfo.text) > 0,                    "url")
    assert_field("errors",         nfo.errors,                         isinstance(nfo.errors, list),         "url")

    # ── Reject path — unreachable URL ──
    with patch.object(url_mod.httpx, "AsyncClient", _NoVerifyClient):
        nfo_bad = await preprocess_url("http://this-domain-does-not-exist-xyz.invalid")
    nfo_bad = enrich(nfo_bad)
    assert_field("bad URL → rejected", nfo_bad.quality_passed, not nfo_bad.quality_passed, "url")

    print(f"\n  {PASS} — URL branch OK")
    _results["URL"] = "PASS"


# ══════════════════════════════════════════════════════════════════
# 3.  DOCUMENT
# ══════════════════════════════════════════════════════════════════

def test_document() -> None:
    header("TEST 3 — Document pipeline")

    # ── 3a. Plain-text document ──
    sample_txt = textwrap.dedent("""\
        Introduction

        This is a smoke-test document for the Menacraft preprocessing pipeline.
        It contains enough words to pass the quality gate comfortably.

        Section 1 – Background

        The preprocessing service handles images, URLs, documents, and videos.
        Each branch produces a NormalizedFeatureObject for the agent committee.

        Section 2 – Conclusion

        All four branches should produce a quality_passed=True result for
        well-formed inputs and quality_passed=False for degenerate inputs.
    """)
    file_bytes = sample_txt.encode("utf-8")
    nfo = preprocess_document(file_bytes, source_ref="test_doc.txt")
    nfo = enrich(nfo)

    assert_field("input_type",         nfo.input_type,                       nfo.input_type == InputType.DOCUMENT, "document")
    assert_field("quality_passed",     nfo.quality_passed,                   isinstance(nfo.quality_passed, bool),  "document")
    assert_field("quality_reason",     nfo.quality_reason,                   nfo.quality_reason is not None,        "document")
    assert_field("language",           nfo.language,                         nfo.language is not None,              "document")
    assert_field("dedup_hash",         nfo.dedup_hash[:16] + "…",            len(nfo.dedup_hash) == 64,             "document")
    assert_field("extraction_method",  nfo.document_data.text_extract.extraction_method,
                                                                              nfo.document_data.text_extract.extraction_method == "plain", "document")
    assert_field("word_count",         nfo.document_data.layout.word_count,  nfo.document_data.layout.word_count > 20, "document")
    assert_field("text preview",       nfo.text[:60],                        len(nfo.text) > 0,                     "document")
    assert_field("errors",             nfo.errors,                           isinstance(nfo.errors, list),          "document")

    # ── 3b. PDF (PyMuPDF / pdfplumber) if available ──
    _test_pdf_if_available()

    # ── 3c. Reject path — unsupported / corrupt file extension ──
    # Empty bytes decoded as plain text still has length 0 → quality gate
    # catches it via _compute_confidence (score=0 < 0.15 threshold).
    # However the plain-text extractor may set quality_passed=True before
    # enrich() runs, so we rely on enrich() to flip it via confidence score.
    # Use a file that explicitly hits the "unsupported" branch instead.
    nfo_empty = preprocess_document(b"", source_ref="empty.bin")   # .bin → unsupported
    nfo_empty = enrich(nfo_empty)
    assert_field("unsupported → rejected", nfo_empty.quality_passed, not nfo_empty.quality_passed, "document")

    print(f"\n  {PASS} — Document branch OK")
    _results["Document"] = "PASS"


def _test_pdf_if_available() -> None:
    """Best-effort PDF sub-test; skipped silently if PyMuPDF absent."""
    try:
        import fitz  # PyMuPDF

        # Build a tiny single-page PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Menacraft PDF smoke test page.")
        pdf_bytes = doc.tobytes()
        doc.close()

        nfo = preprocess_document(pdf_bytes, source_ref="test.pdf")
        nfo = enrich(nfo)

        row("PDF extraction_method", nfo.document_data.text_extract.extraction_method)
        row("PDF page_count",        nfo.document_data.text_extract.page_count)
        row("PDF quality_passed",    nfo.quality_passed)

        if not nfo.document_data.text_extract.raw_text:
            raise AssertionError("PDF extracted empty text")

    except ImportError:
        row("PDF sub-test", f"{YELLOW}skipped (PyMuPDF not installed){RESET}")


# ══════════════════════════════════════════════════════════════════
# 4.  VIDEO
# ══════════════════════════════════════════════════════════════════

def _make_test_video() -> bytes | None:
    """Create a 2-second synthetic MP4 with FFmpeg. Returns bytes or None."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "test.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=10:d=2",
            "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
            "-t", "2",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "32k",
            out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0 or not os.path.exists(out):
            return None
        with open(out, "rb") as f:
            return f.read()


def test_video() -> None:
    header("TEST 4 — Video pipeline")

    if not _ffmpeg_available():
        print(f"  {SKIP} — FFmpeg not installed; video branch skipped")
        _results["Video"] = "SKIP"
        return

    video_bytes = _make_test_video()
    if not video_bytes:
        print(f"  {SKIP} — Could not generate test video; skipping")
        _results["Video"] = "SKIP"
        return

    nfo = preprocess_video(video_bytes, source_ref="test_video.mp4")
    nfo = enrich(nfo)

    assert_field("input_type",      nfo.input_type,                          nfo.input_type == InputType.VIDEO, "video")
    assert_field("quality_passed",  nfo.quality_passed,                      isinstance(nfo.quality_passed, bool), "video")
    assert_field("quality_reason",  nfo.quality_reason,                      nfo.quality_reason is not None,    "video")
    assert_field("dedup_hash",      nfo.dedup_hash[:16] + "…",               len(nfo.dedup_hash) == 64,         "video")
    assert_field("duration",        nfo.video_data.metadata.duration_seconds,
                                                                              nfo.video_data.metadata.duration_seconds is not None, "video")
    assert_field("video_codec",     nfo.video_data.metadata.video_codec,     bool(nfo.video_data.metadata.video_codec), "video")
    assert_field("has_audio",       nfo.video_data.metadata.has_audio,       nfo.video_data.metadata.has_audio is True, "video")
    assert_field("keyframe_count",  nfo.video_data.keyframe_count,           nfo.video_data.keyframe_count >= 0, "video")
    assert_field("asr_model",       nfo.video_data.asr.model,                bool(nfo.video_data.asr.model),    "video")
    assert_field("errors",          nfo.errors,                              isinstance(nfo.errors, list),      "video")

    print(f"\n  {PASS} — Video branch OK")
    _results["Video"] = "PASS"


# ══════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════

def _run(name: str, fn) -> None:
    try:
        fn()
    except Exception:
        _results[name] = "FAIL"
        print(f"\n  {FAIL} — {name} branch raised an exception:")
        traceback.print_exc()


async def _run_async(name: str, fn) -> None:
    try:
        await fn()
    except Exception:
        _results[name] = "FAIL"
        print(f"\n  {FAIL} — {name} branch raised an exception:")
        traceback.print_exc()


async def main() -> None:
    _run("Image",    test_image)
    await _run_async("URL", test_url)
    _run("Document", test_document)
    _run("Video",    test_video)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*55}")
    print("  SUMMARY")
    print(f"{'='*55}{RESET}")
    for branch, status in _results.items():
        symbol = {"PASS": PASS, "SKIP": SKIP, "FAIL": FAIL}.get(status, status)
        print(f"  {branch:<12} {symbol}")

    failed = [b for b, s in _results.items() if s == "FAIL"]
    if failed:
        print(f"\n{RED}✗ {len(failed)} branch(es) failed: {', '.join(failed)}{RESET}\n")
        sys.exit(1)
    else:
        skipped = [b for b, s in _results.items() if s == "SKIP"]
        note = f"  ({len(skipped)} skipped due to missing system deps)" if skipped else ""
        print(f"\n{GREEN}✓ All tests passed.{RESET}{note}\n")


if __name__ == "__main__":
    asyncio.run(main())