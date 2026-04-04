"""
Normalized Feature Object
--------------------------
The unified output schema that every preprocessing branch produces.
All downstream agents consume this object — nothing else.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class InputType(str, Enum):
    IMAGE    = "image"
    URL      = "url"
    DOCUMENT = "document"
    VIDEO    = "video"


# ── Image sub-objects ──────────────────────────────────────────────

class OCRResult(BaseModel):
    raw_text:       str            = ""
    language:       Optional[str]  = None
    confidence:     float          = 0.0          # 0-1


class EXIFData(BaseModel):
    camera_make:    Optional[str]  = None
    camera_model:   Optional[str]  = None
    gps_lat:        Optional[float] = None
    gps_lon:        Optional[float] = None
    datetime_taken: Optional[str]  = None
    software:       Optional[str]  = None
    # Anomaly flags set by the pipeline
    exif_stripped:  bool           = False        # no EXIF at all
    datetime_mismatch: bool        = False        # creation vs modification mismatch


class ImageMetadata(BaseModel):
    width:          int            = 0
    height:         int            = 0
    format:         Optional[str]  = None         # JPEG, PNG …
    file_size_bytes: int           = 0
    has_transparency: bool         = False
    ocr:            OCRResult      = Field(default_factory=OCRResult)
    exif:           EXIFData       = Field(default_factory=EXIFData)


# ── URL sub-objects ────────────────────────────────────────────────

class MetaExtract(BaseModel):
    title:          Optional[str]  = None
    description:    Optional[str]  = None
    og_image:       Optional[str]  = None         # Open Graph image URL
    og_type:        Optional[str]  = None
    canonical_url:  Optional[str]  = None
    language:       Optional[str]  = None
    schema_types:   list[str]      = Field(default_factory=list)


class DomainInfo(BaseModel):
    domain:         str            = ""
    registrar:      Optional[str]  = None
    creation_date:  Optional[str]  = None
    age_days:       Optional[int]  = None
    country:        Optional[str]  = None
    # Risk flags set by the pipeline
    is_new_domain:  bool           = False        # < 90 days old
    is_suspicious:  bool           = False        # heuristic checks


class PageScrape(BaseModel):
    status_code:    int            = 0
    final_url:      str            = ""           # after redirects
    raw_text:       str            = ""           # visible text
    html_length:    int            = 0
    links_found:    int            = 0
    images_found:   int            = 0
    meta:           MetaExtract    = Field(default_factory=MetaExtract)
    domain_info:    DomainInfo     = Field(default_factory=DomainInfo)


# ── Document sub-objects ───────────────────────────────────────────

class TextExtract(BaseModel):
    raw_text:           str           = ""
    page_count:         int           = 0
    extraction_method:  str           = ""        # pymupdf | pdfplumber | python-docx | plain


class LayoutInfo(BaseModel):
    headings:     list[str] = Field(default_factory=list)   # detected heading texts
    table_count:  int       = 0
    word_count:   int       = 0


class DocMetadata(BaseModel):
    author:            Optional[str] = None
    last_modified_by:  Optional[str] = None
    creator_software:  Optional[str] = None       # e.g. "Microsoft Word"
    creation_date:     Optional[str] = None
    modification_date: Optional[str] = None
    title:             Optional[str] = None
    subject:           Optional[str] = None
    revision:          Optional[int] = None       # DOCX revision counter


class DocumentData(BaseModel):
    text_extract:    TextExtract  = Field(default_factory=TextExtract)
    layout:          LayoutInfo   = Field(default_factory=LayoutInfo)
    doc_meta:        DocMetadata  = Field(default_factory=DocMetadata)
    file_size_bytes: int          = 0
    filename:        str          = ""


# ── Video sub-objects ──────────────────────────────────────────────

class ASRResult(BaseModel):
    raw_text:        str           = ""
    language:        Optional[str] = None         # ISO 639-1 code from Whisper
    segments:        list[dict]    = Field(default_factory=list)  # [{text, start, end}]
    word_timestamps: list[dict]    = Field(default_factory=list)  # [{word, start, end}]
    model:           str           = ""           # e.g. "whisper-base"


class VideoMetadata(BaseModel):
    duration_seconds: Optional[float] = None
    width:            Optional[int]   = None
    height:           Optional[int]   = None
    video_codec:      Optional[str]   = None      # e.g. "h264"
    audio_codec:      Optional[str]   = None      # e.g. "aac"
    fps:              Optional[float] = None
    bit_rate:         Optional[int]   = None      # bits/s
    format_name:      Optional[str]   = None      # e.g. "mov,mp4,m4a,3gp,3g2,mj2"
    has_audio:        bool            = False


class VideoData(BaseModel):
    metadata:        VideoMetadata = Field(default_factory=VideoMetadata)
    asr:             ASRResult     = Field(default_factory=ASRResult)
    keyframe_count:  int           = 0
    file_size_bytes: int           = 0


# ── Top-level Normalized Feature Object ───────────────────────────

class NormalizedFeatureObject(BaseModel):
    """
    Single unified schema consumed by every agent downstream.
    Fields that don't apply to a given input_type are left None/empty.
    """
    # ── Identity ──
    input_type:     InputType
    source_ref:     str                        # file path or original URL
    processed_at:   str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    # ── Shared text surface ──
    text:           str            = ""        # primary text content
    language:       Optional[str]  = None

    # ── Branch-specific payloads ──
    image_meta:     Optional[ImageMetadata]  = None
    url_data:       Optional[PageScrape]     = None
    document_data:  Optional[DocumentData]   = None
    video_data:     Optional[VideoData]      = None

    # ── Quality gate fields (filled after enrichment) ──
    quality_passed: bool           = False
    quality_reason: Optional[str]  = None
    dedup_hash:     Optional[str]  = None      # SHA-256 of primary content

    # ── Pipeline errors ──
    errors:         list[str]      = Field(default_factory=list)