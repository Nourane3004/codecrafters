"""
orchestrator_api.py
===================
TruthGuard — Orchestrator API Layer
No mock data. All results are derived purely from user input.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Domain models
# ══════════════════════════════════════════════════════════════════════════════

class ContentNature(str, Enum):
    RAW_IMAGE              = "raw_image"
    SOCIAL_POST_SCREENSHOT = "social_post_screenshot"
    NEWS_ARTICLE           = "news_article"
    SCIENTIFIC_CLAIM       = "scientific_claim"
    GOVERNMENT_DOC         = "government_document"
    VIDEO_CLIP             = "video_clip"
    AUDIO_CLIP             = "audio_clip"
    ADVERTISEMENT          = "advertisement"
    MEME                   = "meme"
    CHAT_SCREENSHOT        = "chat_screenshot"
    URL_LINK               = "url_link"
    UNKNOWN                = "unknown"


class AnalysisGoal(str, Enum):
    AUTHENTICITY        = "authenticity"
    CONTEXT             = "contextual_consistency"
    SOURCE_CREDIBILITY  = "source_credibility"
    CLAIM_VERIFICATION  = "claim_verification"
    NETWORK_ANALYSIS    = "network_analysis"
    LINGUISTIC_ANALYSIS = "linguistic_analysis"
    DEEPFAKE_DETECTION  = "deepfake_detection"
    METADATA_FORENSICS  = "metadata_forensics"


class AgentActivationPlan(BaseModel):
    image_forensics: bool = False
    video_forensics: bool = False
    claim_extract:   bool = False
    claim_verify:    bool = False
    source_cred:     bool = False
    context_agent:   bool = False
    network_agent:   bool = False
    linguistic:      bool = False
    reasons:         List[str] = Field(default_factory=list)


class AnalyseResponse(BaseModel):
    action:                str
    label:                 str
    risk_score:            float
    risk_band:             str
    confidence:            float
    explanation:           str
    requires_human_review: bool
    agent_plan:            AgentActivationPlan
    active_pipelines:      List[str]
    routing_notes:         List[str]
    agent_results:         Dict[str, Any]
    audit_trail:           Dict[str, Any]
    processing_time_ms:    int


# ══════════════════════════════════════════════════════════════════════════════
# Agent planner
# ══════════════════════════════════════════════════════════════════════════════

def plan_agents(
    input_type:     str,
    content_nature: ContentNature,
    analysis_goals: List[AnalysisGoal],
    source_url:     Optional[str],
    post_text:      Optional[str],
) -> AgentActivationPlan:
    plan    = AgentActivationPlan()
    reasons = []

    if input_type == "image":
        plan.image_forensics = True
        reasons.append("File type is image → image_forensics activated")
    elif input_type == "video":
        plan.video_forensics = True
        plan.linguistic      = True
        reasons.append("File type is video → video_forensics + linguistic activated")
    elif input_type in ("document", "url"):
        plan.claim_extract = True
        plan.claim_verify  = True
        plan.linguistic    = True
        reasons.append(f"File type is {input_type} → claim pipeline + linguistic activated")

    NATURE_RULES: Dict[ContentNature, List[str]] = {
        ContentNature.SOCIAL_POST_SCREENSHOT: ["image_forensics","claim_extract","claim_verify","source_cred","context_agent","linguistic","network_agent"],
        ContentNature.MEME:                   ["image_forensics","claim_extract","claim_verify","context_agent","linguistic"],
        ContentNature.CHAT_SCREENSHOT:        ["image_forensics","claim_extract","linguistic","context_agent"],
        ContentNature.NEWS_ARTICLE:           ["claim_extract","claim_verify","source_cred","linguistic","context_agent"],
        ContentNature.SCIENTIFIC_CLAIM:       ["claim_extract","claim_verify","context_agent"],
        ContentNature.GOVERNMENT_DOC:         ["claim_extract","claim_verify","source_cred","linguistic"],
        ContentNature.ADVERTISEMENT:          ["linguistic","claim_extract","claim_verify","source_cred"],
        ContentNature.VIDEO_CLIP:             ["video_forensics","linguistic","claim_extract","context_agent"],
        ContentNature.URL_LINK:               ["source_cred","claim_extract","claim_verify","network_agent"],
    }
    if content_nature in NATURE_RULES:
        for field in NATURE_RULES[content_nature]:
            setattr(plan, field, True)
        reasons.append(f"ContentNature={content_nature.value} → {', '.join(NATURE_RULES[content_nature])}")

    if source_url:
        plan.source_cred   = True
        plan.network_agent = True
        reasons.append("Source URL provided → source_cred + network_agent activated")

    if post_text and len(post_text.strip()) > 20:
        plan.claim_extract = True
        plan.claim_verify  = True
        reasons.append("Post text provided → claim extraction from typed text")

    GOAL_FIELDS: Dict[AnalysisGoal, List[str]] = {
        AnalysisGoal.AUTHENTICITY:        ["image_forensics", "linguistic"],
        AnalysisGoal.DEEPFAKE_DETECTION:  ["video_forensics", "image_forensics"],
        AnalysisGoal.METADATA_FORENSICS:  ["image_forensics"],
        AnalysisGoal.SOURCE_CREDIBILITY:  ["source_cred"],
        AnalysisGoal.CLAIM_VERIFICATION:  ["claim_extract", "claim_verify"],
        AnalysisGoal.CONTEXT:             ["context_agent"],
        AnalysisGoal.NETWORK_ANALYSIS:    ["network_agent"],
        AnalysisGoal.LINGUISTIC_ANALYSIS: ["linguistic"],
    }
    for goal in analysis_goals:
        if goal in GOAL_FIELDS:
            for field in GOAL_FIELDS[goal]:
                setattr(plan, field, True)
            reasons.append(f"Goal '{goal.value}' → {', '.join(GOAL_FIELDS[goal])} activated")

    plan.reasons = reasons
    return plan


# ══════════════════════════════════════════════════════════════════════════════
# Text extraction — real, no mock
# ══════════════════════════════════════════════════════════════════════════════

def extract_text(file_bytes: Optional[bytes], input_type: str, filename: str = "") -> str:
    """Extract real text from the uploaded file. No fake data."""
    if not file_bytes:
        return ""

    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()

    # PDF
    if ext == "pdf" or input_type == "document":
        try:
            import fitz
            doc  = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            if text.strip():
                logger.info(f"[extract] PDF: {len(text)} chars extracted")
                return text.strip()
        except ImportError:
            logger.error("[extract] PyMuPDF not installed — run: pip install pymupdf")
        except Exception as e:
            logger.warning(f"[extract] PDF extraction failed: {e}")

    # DOCX
    if ext == "docx":
        try:
            import zipfile, io as _io
            zf   = zipfile.ZipFile(_io.BytesIO(file_bytes))
            xml  = zf.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            logger.info(f"[extract] DOCX: {len(text)} chars extracted")
            return text
        except Exception as e:
            logger.warning(f"[extract] DOCX extraction failed: {e}")

    # Plain text / URL scraped content
    if ext in ("txt", "md", "csv") or input_type == "url":
        try:
            decoded = file_bytes.decode("utf-8", errors="ignore").strip()
            if decoded:
                logger.info(f"[extract] Plain text: {len(decoded)} chars")
                return decoded
        except Exception as e:
            logger.warning(f"[extract] Text decode failed: {e}")

    logger.info(f"[extract] No text extractable — input_type={input_type} ext={ext}")
    return ""


def split_into_claims(text: str) -> List[str]:
    """Split text into clean, meaningful sentences suitable as claims."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned   = []
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and not s.startswith("http") and s[0].isupper():
            cleaned.append(s)
    return cleaned[:8]


# ══════════════════════════════════════════════════════════════════════════════
# Real claim analysis — deterministic heuristics on actual text
# ══════════════════════════════════════════════════════════════════════════════

def analyse_claims(claims_text: List[str]) -> List[Dict[str, Any]]:
    results = []
    for i, text in enumerate(claims_text):
        text_lower = text.lower()

        factual_markers = ["percent", "%", "million", "billion", "thousand",
                           "study", "research", "report", "data", "statistics",
                           "according to", "found that", "showed", "confirmed",
                           "in 20", "in 19", "died", "killed", "arrested",
                           "elected", "signed", "announced", "released"]
        opinion_markers = ["should", "must", "need to", "believe", "think",
                           "feel", "opinion", "seems", "appears", "might",
                           "could", "perhaps", "allegedly"]
        vague_markers   = ["some", "many", "few", "several", "often",
                           "sometimes", "usually", "generally"]

        factual_score = sum(1 for m in factual_markers if m in text_lower)
        opinion_score = sum(1 for m in opinion_markers if m in text_lower)
        vague_score   = sum(1 for m in vague_markers   if m in text_lower)

        if factual_score >= 2:
            verifiability = "HIGH"
            claim_type    = "STATISTICAL" if any(m in text_lower for m in ["%","percent","million","billion"]) else "FACTUAL"
        elif opinion_score > factual_score:
            verifiability = "LOW"
            claim_type    = "OPINION"
        elif vague_score > 0:
            verifiability = "MEDIUM"
            claim_type    = "VAGUE"
        else:
            verifiability = "MEDIUM"
            claim_type    = "FACTUAL"

        risk_flags  = []
        alarm_words = ["shocking", "secret", "they don't want you", "banned",
                       "censored", "exposed", "wake up", "share before deleted",
                       "mainstream media", "deep state", "miracle", "cure",
                       "doctors hate", "one weird trick"]
        for w in alarm_words:
            if w in text_lower:
                risk_flags.append(f"Sensationalist language: '{w}'")

        if re.search(r"\b(all|every|never|always|no one|everyone)\b", text_lower):
            risk_flags.append("Absolute generalisation detected")
        if re.search(r"\b\d{1,3}[,.]?\d{3}[,.]?\d*\b", text):
            risk_flags.append("Contains specific statistic — cross-check with source")

        results.append({
            "id":            i + 1,
            "text":          text,
            "type":          claim_type,
            "verifiability": verifiability,
            "risk_flags":    risk_flags,
        })
    return results


def verify_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic verification based on claim content signals."""
    verifications = []
    support_map   = {
        "VERIFIED":           0.80,
        "PARTIALLY_VERIFIED": 0.50,
        "UNVERIFIED":         0.30,
        "CONTRADICTED":       0.10,
    }

    for claim in claims:
        text_lower = claim["text"].lower()
        flags      = claim.get("risk_flags", [])

        has_alarm    = any("Sensationalist" in f for f in flags)
        has_absolute = any("Absolute" in f      for f in flags)
        is_opinion   = claim["type"] == "OPINION"
        is_vague     = claim["type"] == "VAGUE"
        has_stat     = any("statistic" in f     for f in flags)

        if is_opinion:
            status = "UNVERIFIED"
            reason = "This is an opinion — not factually verifiable."
        elif is_vague:
            status = "UNVERIFIED"
            reason = "Too vague to verify — lacks specific, checkable details."
        elif has_alarm and has_absolute:
            status = "CONTRADICTED"
            reason = "Sensationalist language + absolute generalisation — high disinformation signal."
        elif has_alarm:
            status = "PARTIALLY_VERIFIED"
            reason = "Sensationalist framing detected — treat with caution, verify the source."
        elif has_stat and claim["verifiability"] == "HIGH":
            status = "PARTIALLY_VERIFIED"
            reason = "Contains specific statistics — requires cross-referencing with original source."
        elif claim["verifiability"] == "HIGH" and not has_alarm:
            status = "VERIFIED"
            reason = "Specific, checkable details present with no disinformation markers."
        else:
            status = "UNVERIFIED"
            reason = "Insufficient information to verify this claim automatically."

        verifications.append({
            "claim_id":      claim["id"],
            "claim_text":    claim["text"],
            "status":        status,
            "reason":        reason,
            "support_score": support_map[status],
            "risk_flags":    flags,
        })
    return verifications


def analyse_linguistics(text: str) -> Dict[str, Any]:
    """Real linguistic analysis on actual text content."""
    if not text:
        return {"available": False, "reason": "No text to analyse", "risk_score": 0.5}

    text_lower = text.lower()
    words      = text_lower.split()
    sentences  = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    clickbait_phrases = ["you won't believe", "shocking", "mind blowing", "incredible",
                         "this is why", "the truth about", "what they don't", "exposed",
                         "wake up", "share this", "before it's deleted", "going viral", "breaking"]
    clickbait_hits  = [p for p in clickbait_phrases if p in text_lower]
    clickbait_score = min(len(clickbait_hits) / 5.0, 1.0)

    emotional_words = ["outrage", "furious", "disgusting", "terrifying", "horrifying",
                       "unbelievable", "disgrace", "scandal", "catastrophe", "crisis",
                       "emergency", "danger", "threat", "attack", "destroy"]
    emotional_hits  = [w for w in emotional_words if w in text_lower]
    emotional_score = min(len(emotional_hits) / 5.0, 1.0)

    if len(sentences) >= 3:
        lengths      = [len(s.split()) for s in sentences]
        avg_len      = sum(lengths) / len(lengths)
        variance     = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        ai_gen_score = max(0.0, min(1.0, 1.0 - (variance / 50.0)))
    else:
        ai_gen_score = 0.0

    caps_ratio   = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    caps_warning = caps_ratio > 0.15

    red_flags = []
    if clickbait_hits:
        red_flags.append(f"Clickbait language detected: {', '.join(clickbait_hits[:3])}")
    if emotional_hits:
        red_flags.append(f"Emotional manipulation: {', '.join(emotional_hits[:3])}")
    if ai_gen_score > 0.65:
        red_flags.append("Uniform sentence structure — possible AI-generated text")
    if caps_warning:
        red_flags.append(f"Excessive capitalisation ({round(caps_ratio*100)}% of characters)")

    max_risk = max(clickbait_score, emotional_score, ai_gen_score)

    return {
        "available":             True,
        "clickbait_score":       round(clickbait_score, 3),
        "emotional_score":       round(emotional_score, 3),
        "ai_generated_score":    round(ai_gen_score, 3),
        "linguistic_risk_level": "HIGH" if max_risk > 0.6 else "MEDIUM" if max_risk > 0.3 else "LOW",
        "red_flags":             red_flags,
        "word_count":            len(words),
        "sentence_count":        len(sentences),
        "risk_score":            round(max_risk, 3),
        "confidence_contribution": round(min(0.9, 0.5 + max_risk * 0.4), 2),
    }


def analyse_source(source_url: Optional[str], platform: Optional[str]) -> Dict[str, Any]:
    """Real source credibility based on domain reputation."""
    domain    = "unknown"
    red_flags = []
    has_ssl   = False

    known_fake_news = ["infowars", "naturalnews", "beforeitsnews", "worldnewsdailyreport",
                       "empirenews", "thedcgazette", "usapoliticstoday", "abcnews.com.co"]
    known_satire    = ["theonion", "babylonbee", "clickhole", "waterfordwhispersnews"]
    trusted_outlets = ["reuters", "apnews", "bbc", "npr", "theguardian", "nytimes",
                       "washingtonpost", "economist", "ft.com", "bloomberg", "aljazeera"]
    suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click"]

    if source_url:
        try:
            from urllib.parse import urlparse
            parsed  = urlparse(source_url if source_url.startswith("http") else "http://" + source_url)
            domain  = parsed.netloc.replace("www.", "")
            has_ssl = source_url.startswith("https://")
        except Exception:
            domain = source_url[:60]

        domain_lower  = domain.lower()
        is_fake_news  = any(f in domain_lower for f in known_fake_news)
        is_satire     = any(s in domain_lower for s in known_satire)
        is_trusted    = any(t in domain_lower for t in trusted_outlets)
        has_bad_tld   = any(source_url.endswith(t) for t in suspicious_tlds)

        if is_fake_news:
            red_flags.append("Domain is in the known fake-news registry")
            overall_score = 0.05
        elif is_satire:
            red_flags.append("This is a known satire site — content is not factual news")
            overall_score = 0.20
        elif is_trusted:
            overall_score = 0.90
        elif has_bad_tld:
            red_flags.append("Suspicious domain extension — common in low-credibility sites")
            overall_score = 0.25
        else:
            overall_score = 0.55

        for outlet in trusted_outlets:
            if outlet in domain_lower and not domain_lower.startswith(outlet):
                red_flags.append(f"Domain appears to impersonate '{outlet}' — possible spoofing")
                overall_score = min(overall_score, 0.10)

        if not has_ssl:
            red_flags.append("No HTTPS — connection is not encrypted")
            overall_score = min(overall_score, 0.45)

    elif platform:
        platform_scores = {
            "Twitter": 0.55, "Facebook": 0.50, "Telegram": 0.35,
            "WhatsApp": 0.30, "Instagram": 0.50, "TikTok": 0.45, "Reddit": 0.55,
        }
        overall_score = platform_scores.get(platform, 0.45)
        domain        = platform
        has_ssl       = True
        if platform in ("Telegram", "WhatsApp"):
            red_flags.append(f"{platform}: closed channel — content origin cannot be traced")
    else:
        overall_score = 0.50

    return {
        "domain":              domain,
        "overall_score":       round(overall_score, 3),
        "risk_score":          round(1.0 - overall_score, 3),
        "has_ssl":             has_ssl,
        "is_known_fake_news":  any("fake-news" in f for f in red_flags),
        "is_known_satire":     any("satire" in f     for f in red_flags),
        "red_flags":           red_flags,
        "confidence":          0.80,
    }


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI app
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="TruthGuard Orchestrator API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "4.0.0", "mode": "real-input-only"}


@app.get("/agents")
def list_agents():
    return {"agents": [
        {"id": "claim_extract",   "name": "Claim Extractor",   "desc": "Extracts real claims from text/PDF",         "weight": 0.00},
        {"id": "claim_verify",    "name": "Claim Verifier",    "desc": "Heuristic verification of extracted claims", "weight": 0.30},
        {"id": "linguistic",      "name": "Linguistic Agent",  "desc": "Clickbait, emotional manipulation, AI-text", "weight": 0.25},
        {"id": "source_cred",     "name": "Source Credibility","desc": "Domain reputation & fake-news registry",     "weight": 0.25},
        {"id": "image_forensics", "name": "Image Forensics",   "desc": "EXIF metadata analysis",                    "weight": 0.10},
        {"id": "context_agent",   "name": "Context Agent",     "desc": "Contextual consistency check",              "weight": 0.10},
    ]}


@app.post("/analyse/plan", response_model=AgentActivationPlan)
async def get_agent_plan(
    input_type:     str           = Form(...),
    content_nature: str           = Form(...),
    analysis_goals: str           = Form(...),
    source_url:     Optional[str] = Form(None),
    post_text:      Optional[str] = Form(None),
):
    import json
    try:
        goals = [AnalysisGoal(g) for g in json.loads(analysis_goals)]
    except Exception:
        goals = []
    return plan_agents(
        input_type=input_type,
        content_nature=ContentNature(content_nature),
        analysis_goals=goals,
        source_url=source_url,
        post_text=post_text,
    )


@app.post("/analyse", response_model=AnalyseResponse)
async def analyse(
    input_type:     str                  = Form(...),
    content_nature: str                  = Form(...),
    analysis_goals: str                  = Form(...),
    source_url:     Optional[str]        = Form(None),
    post_text:      Optional[str]        = Form(None),
    platform:       Optional[str]        = Form(None),
    author_handle:  Optional[str]        = Form(None),
    file:           Optional[UploadFile] = File(None),
):
    import json
    t_start = time.perf_counter()

    try:
        goals = [AnalysisGoal(g) for g in json.loads(analysis_goals)]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid analysis_goals: {e}")

    try:
        nature = ContentNature(content_nature)
    except Exception:
        nature = ContentNature.UNKNOWN

    plan = plan_agents(
        input_type=input_type,
        content_nature=nature,
        analysis_goals=goals,
        source_url=source_url,
        post_text=post_text,
    )

    # Read file
    file_bytes: Optional[bytes] = None
    filename   = ""
    source_ref = source_url or "upload"
    if file:
        file_bytes = await file.read()
        filename   = file.filename or ""
        source_ref = filename or "upload"
        logger.info(f"[orchestrator] file={source_ref} size={len(file_bytes)} bytes")

    # ── Determine working text ─────────────────────────────────────────────────
    working_text = ""
    if post_text and post_text.strip():
        working_text      = post_text.strip()
        extraction_method = "typed_text"
        logger.info(f"[text] Using typed post_text ({len(working_text)} chars)")
    elif file_bytes:
        working_text      = extract_text(file_bytes, input_type, filename)
        extraction_method = "file_extraction" if working_text else "ocr_required"
        logger.info(f"[text] File extraction: {len(working_text)} chars")
    else:
        extraction_method = "none"

    # ── Run agents ─────────────────────────────────────────────────────────────
    agent_results:    Dict[str, Any] = {}
    active_pipelines: List[str]      = []

    # Claim extraction
    if plan.claim_extract:
        active_pipelines.append("TEXT")
        if working_text:
            raw_claims = split_into_claims(working_text)
            claims     = analyse_claims(raw_claims)
            note       = ""
        else:
            claims = []
            note   = (
                "No text could be extracted. "
                "For images: type the visible text in the 'Post text' field on Step 2. "
                "For PDFs: ensure the file is not a scanned image."
            )

        agent_results["claim_extract"] = {
            "success":           True,
            "total_claims":      len(claims),
            "claims":            claims,
            "high_risk_claims":  sum(1 for c in claims if c["verifiability"] == "HIGH"),
            "extraction_method": extraction_method,
            "note":              note,
        }

    # Claim verification
    if plan.claim_verify and "claim_extract" in agent_results:
        claims_to_verify   = agent_results["claim_extract"]["claims"]
        verifications      = verify_claims(claims_to_verify)
        verified_count     = sum(1 for v in verifications if v["status"] == "VERIFIED")
        contradicted_count = sum(1 for v in verifications if v["status"] == "CONTRADICTED")
        avg_support        = (
            sum(v["support_score"] for v in verifications) / len(verifications)
            if verifications else 0.5
        )
        agent_results["claim_verify"] = {
            "verifications":               verifications,
            "overall_support_score":       round(avg_support, 3),
            "overall_contradiction_score": round(1.0 - avg_support, 3),
            "verified_count":              verified_count,
            "contradicted_count":          contradicted_count,
            "total_checked":               len(verifications),
            "risk_score":                  round(1.0 - avg_support, 3),
            "confidence":                  0.75,
        }

    # Linguistic analysis
    if plan.linguistic:
        if "TEXT" not in active_pipelines:
            active_pipelines.append("TEXT")
        agent_results["linguistic"] = analyse_linguistics(working_text)

    # Source credibility
    if plan.source_cred:
        active_pipelines.append("URL")
        agent_results["source_cred"] = analyse_source(source_url, platform)

    # Image forensics
    if plan.image_forensics and file_bytes:
        active_pipelines.append("VISION")
        exif_info  = {}
        risk_score = 0.30
        red_flags  = []

        try:
            from PIL import Image, ExifTags
            import io as _io
            img  = Image.open(_io.BytesIO(file_bytes))
            exif = img._getexif() or {}
            for tag_id, val in exif.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                exif_info[str(tag)] = str(val)[:120]

            software = exif_info.get("Software", "").lower()
            if any(s in software for s in ["photoshop", "gimp", "affinity", "lightroom"]):
                red_flags.append(f"Image edited with: {exif_info.get('Software', 'unknown editor')}")
                risk_score = 0.65

            if not exif_info:
                red_flags.append("No EXIF metadata — stripped (common in re-uploaded or edited images)")
                risk_score = 0.55

        except ImportError:
            red_flags.append("Pillow not installed — run: pip install pillow")
        except Exception as e:
            red_flags.append(f"EXIF read error: {e}")

        agent_results["image_forensics"] = {
            "risk_score":      round(risk_score, 3),
            "confidence":      0.60,
            "exif":            exif_info,
            "anomalies":       red_flags,
            "red_flags":       red_flags,
            "exif_consistent": len(red_flags) == 0,
            "note":            "Full pixel-level forensics (ELA/FFT) require the OpenCV pipeline.",
        }

    # Context agent
    if plan.context_agent:
        ctx_flags         = []
        consistency_score = 0.70

        if working_text:
            text_lower = working_text.lower()
            future_re  = re.findall(r"\b(will|going to|soon|upcoming|next year)\b", text_lower)
            past_re    = re.findall(r"\b(happened|occurred|confirmed|revealed|exposed)\b", text_lower)

            if future_re and past_re:
                ctx_flags.append("Mixed tenses: combines past-event claims with future predictions")
                consistency_score -= 0.20

            for a, b in [("always", "never"), ("confirmed", "allegedly"), ("proven", "might"), ("fact", "rumor")]:
                if a in text_lower and b in text_lower:
                    ctx_flags.append(f"Contradictory terms used together: '{a}' and '{b}'")
                    consistency_score -= 0.15

            consistency_score = round(max(0.0, min(1.0, consistency_score)), 3)

        agent_results["context_agent"] = {
            "overall_consistency_score": consistency_score,
            "temporal_coherence_score":  consistency_score,
            "risk_score":                round(1.0 - consistency_score, 3),
            "confidence":                0.65,
            "temporal_issues":           ctx_flags,
            "checks": [{
                "is_consistent":       consistency_score > 0.5,
                "confidence":          0.65,
                "contradicting_facts": ctx_flags,
                "supporting_facts":    [] if ctx_flags else ["No major contextual inconsistencies detected"],
            }],
        }

    active_pipelines = list(set(active_pipelines))

    # ── Evidence fusion ────────────────────────────────────────────────────────
    WEIGHTS = {
        "claim_verify":    0.30,
        "linguistic":      0.25,
        "source_cred":     0.25,
        "image_forensics": 0.10,
        "context_agent":   0.10,
        "claim_extract":   0.00,
    }

    weighted_sum = 0.0
    weight_total = 0.0
    for agent_id, res in agent_results.items():
        w = WEIGHTS.get(agent_id, 0.0)
        if w == 0.0:
            continue
        risk = res.get("risk_score", 0.5)
        conf = res.get("confidence", res.get("confidence_contribution", 0.7))
        weighted_sum += risk * w * conf
        weight_total += w * conf

    if weight_total > 0:
        risk_score = round(min(1.0, max(0.0, weighted_sum / weight_total)), 3)
        confidence = round(min(0.95, weight_total / sum(WEIGHTS.values())), 3)
    else:
        risk_score = 0.50
        confidence = 0.50

    # Verdict
    if risk_score < 0.25:
        band, action, label = "GREEN",  "auto-allow",  "Likely Authentic"
        requires_review     = False
        explanation         = "No significant disinformation signals found in the submitted content."
    elif risk_score < 0.50:
        band, action, label = "AMBER",  "flag-review", "Needs Human Review"
        requires_review     = True
        explanation         = "Some risk signals detected. A human reviewer should assess this before acting on it."
    elif risk_score < 0.75:
        band, action, label = "ORANGE", "flag-review", "Likely Misleading"
        requires_review     = True
        explanation         = "Multiple disinformation signals found. This content is likely misleading or manipulated."
    else:
        band, action, label = "RED",    "auto-block",  "High Risk — Do Not Share"
        requires_review     = False
        explanation         = "Strong disinformation markers detected. Do not share or act on this content."

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)

    return AnalyseResponse(
        action=action,
        label=label,
        risk_score=risk_score,
        risk_band=band,
        confidence=confidence,
        explanation=explanation,
        requires_human_review=requires_review,
        agent_plan=plan,
        active_pipelines=active_pipelines,
        routing_notes=plan.reasons,
        agent_results=agent_results,
        audit_trail={
            "input_type":         input_type,
            "content_nature":     nature.value,
            "analysis_goals":     [g.value for g in goals],
            "source_ref":         source_ref,
            "extraction_method":  extraction_method,
            "working_text_chars": len(working_text),
            "agents_activated": [k for k, v in {
                "image_forensics": plan.image_forensics,
                "video_forensics": plan.video_forensics,
                "claim_extract":   plan.claim_extract,
                "claim_verify":    plan.claim_verify,
                "source_cred":     plan.source_cred,
                "context_agent":   plan.context_agent,
                "network_agent":   plan.network_agent,
                "linguistic":      plan.linguistic,
            }.items() if v],
        },
        processing_time_ms=elapsed_ms,
    )


if __name__ == "__main__":
    uvicorn.run("orchestrator_api:app", host="0.0.0.0", port=8001, reload=True)