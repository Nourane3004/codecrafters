"""
Menacraft – Preprocessing Service
-----------------------------------
FastAPI app exposing four endpoints:
  POST /preprocess/image    → accepts image file upload
  POST /preprocess/url      → accepts JSON { "url": "..." }
  POST /preprocess/document → accepts PDF / DOCX / TXT file upload
  POST /preprocess/video    → accepts video file upload

All return a NormalizedFeatureObject JSON.
"""

from __future__ import annotations
import logging

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from app.models.feature_object import NormalizedFeatureObject
from app.pipeline.image.processor_image    import preprocess_image
from app.pipeline.url.processor_url      import preprocess_url
from app.pipeline.document.processor_doc import preprocess_document
from app.pipeline.video.processor_vid    import preprocess_video
from app.pipeline.quality_gate       import enrich

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Menacraft Preprocessing API",
    description=(
        "Preprocessing pipeline for image, URL, document, and video inputs. "
        "Produces a NormalizedFeatureObject consumed by the agent committee."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Allowed MIME types ────────────────────────────────────────────

_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "image/bmp", "image/tiff",
}

_DOCUMENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "text/x-rst",
}

_VIDEO_TYPES = {
    "video/mp4", "video/mpeg", "video/quicktime",
    "video/x-msvideo", "video/webm", "video/x-matroska",
    "video/3gpp", "video/ogg",
}


# ── Request models ────────────────────────────────────────────────

class URLRequest(BaseModel):
    url: HttpUrl


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/preprocess/image",
    response_model=NormalizedFeatureObject,
    summary="Preprocess an uploaded image",
    description=(
        "Runs OCR, UI detection, and EXIF extraction on the uploaded image. "
        "Returns a NormalizedFeatureObject."
    ),
)
async def preprocess_image_endpoint(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WEBP …)"),
):
    if file.content_type and file.content_type not in _IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Send an image.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    logger.info(f"Processing image: {file.filename} ({len(image_bytes)} bytes)")

    nfo = preprocess_image(image_bytes, source_ref=file.filename or "upload")
    nfo = enrich(nfo)

    if not nfo.quality_passed:
        logger.warning(f"Image rejected: {nfo.quality_reason}")

    return nfo


@app.post(
    "/preprocess/url",
    response_model=NormalizedFeatureObject,
    summary="Preprocess a URL",
    description=(
        "Scrapes the page, extracts meta tags, and queries WHOIS domain info. "
        "Returns a NormalizedFeatureObject."
    ),
)
async def preprocess_url_endpoint(body: URLRequest):
    url = str(body.url)
    logger.info(f"Processing URL: {url}")

    nfo = await preprocess_url(url)
    nfo = enrich(nfo)

    if not nfo.quality_passed:
        logger.warning(f"URL rejected: {nfo.quality_reason}")

    return nfo


@app.post(
    "/preprocess/document",
    response_model=NormalizedFeatureObject,
    summary="Preprocess an uploaded document",
    description=(
        "Extracts text (PyMuPDF / pdfplumber / python-docx), parses layout "
        "(headings, tables), and reads document metadata (author, edit history). "
        "Accepts PDF, DOCX, DOC, TXT, MD. "
        "Returns a NormalizedFeatureObject."
    ),
)
async def preprocess_document_endpoint(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT …)"),
):
    if file.content_type and file.content_type not in _DOCUMENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Send a PDF, DOCX, or plain-text file."
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    logger.info(f"Processing document: {file.filename} ({len(file_bytes)} bytes)")

    nfo = preprocess_document(file_bytes, source_ref=file.filename or "document")
    nfo = enrich(nfo)

    if not nfo.quality_passed:
        logger.warning(f"Document rejected: {nfo.quality_reason}")

    return nfo


@app.post(
    "/preprocess/video",
    response_model=NormalizedFeatureObject,
    summary="Preprocess an uploaded video",
    description=(
        "Extracts keyframes (FFmpeg), transcribes audio (Whisper with timestamps), "
        "and reads codec / duration metadata (FFprobe). "
        "Accepts MP4, MOV, AVI, WebM, MKV. "
        "Returns a NormalizedFeatureObject."
    ),
)
async def preprocess_video_endpoint(
    file: UploadFile = File(..., description="Video file (MP4, MOV, AVI, WebM …)"),
):
    if file.content_type and file.content_type not in _VIDEO_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Send an MP4, MOV, AVI, WebM, or MKV file."
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    logger.info(f"Processing video: {file.filename} ({len(file_bytes)} bytes)")

    nfo = preprocess_video(file_bytes, source_ref=file.filename or "video")
    nfo = enrich(nfo)

    if not nfo.quality_passed:
        logger.warning(f"Video rejected: {nfo.quality_reason}")

    return nfo


# ── Dev runner ────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)