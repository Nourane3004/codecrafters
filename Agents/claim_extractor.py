"""
Claim Extractor Agent
----------------------
Extracts factual claims from any text source.
LLM backend: Groq  (llama-3.3-70b-versatile)
Fallback:     heuristic regex (if Groq is unavailable)
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional, Literal, List, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Groq client (optional import so the module loads even without the package) ─
try:
    from groq import Groq          # pip install groq
    _groq_available = True
except ImportError:
    _groq_available = False
    logger.warning("groq package not installed — claim extractor will use heuristic fallback")

_GROQ_MODEL = "llama-3.3-70b-versatile"


# =============================================================================
# Output models
# =============================================================================

class ExtractedClaim(BaseModel):
    claim_id: int
    claim_text: str
    claim_type: Literal["FACTUAL", "STATISTICAL", "TEMPORAL", "IDENTITY", "CAUSAL", "OPINION"] = "FACTUAL"
    verifiability: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    entities: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    raw_quote: Optional[str] = None


class ClaimExtractionResult(BaseModel):
    success: bool
    claims: List[ExtractedClaim] = Field(default_factory=list)
    total_claims: int = 0
    high_risk_claims: int = 0
    dominant_claim_types: List[str] = Field(default_factory=list)
    confidence_contribution: float = 0.0
    extraction_method: Literal["llm", "heuristic", "failed"] = "failed"
    reasoning_notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# =============================================================================
# Text selector (unchanged logic, bug-fixes from original comments preserved)
# =============================================================================

def select_richest_text(nfo: Any) -> str:
    input_type_val = nfo.input_type.value if hasattr(nfo.input_type, "value") else str(nfo.input_type)

    if input_type_val == "image":
        if nfo.image_meta and nfo.image_meta.ocr.raw_text and nfo.image_meta.ocr.confidence >= 0.7:
            return nfo.image_meta.ocr.raw_text
        return nfo.text

    if input_type_val == "url":
        if nfo.url_data and nfo.url_data.raw_text:
            prefix = ""
            if nfo.url_data.meta.title:
                prefix += f"Title: {nfo.url_data.meta.title}\n"
            if nfo.url_data.meta.description:
                prefix += f"Description: {nfo.url_data.meta.description}\n\n"
            return prefix + nfo.url_data.raw_text
        return nfo.text

    if input_type_val == "document":
        if nfo.document_data:
            text = nfo.document_data.text_extract.raw_text
            if nfo.document_data.layout.headings:
                heading_block = "\n".join(nfo.document_data.layout.headings)
                return heading_block + "\n\n" + text
            return text
        return nfo.text

    if input_type_val == "video":
        if nfo.video_data and nfo.video_data.asr.raw_text:
            return nfo.video_data.asr.raw_text
        return nfo.text

    return nfo.text


# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """You are a precision fact-extraction engine for a misinformation detection system.

Your ONLY job: analyze the provided text and extract every factual claim it makes.

Return ONLY a valid JSON object — no markdown, no explanation, no preamble.

JSON schema (strict):
{
  "claims": [
    {
      "claim_id": 1,
      "claim_text": "<concise statement of the claim>",
      "claim_type": "<FACTUAL|STATISTICAL|TEMPORAL|IDENTITY|CAUSAL|OPINION>",
      "verifiability": "<HIGH|MEDIUM|LOW>",
      "entities": ["<entity1>", "<entity2>"],
      "red_flags": ["<flag1>", "<flag2>"],
      "raw_quote": "<exact sentence from source or null>"
    }
  ]
}

Claim types:
- FACTUAL: asserts something is true about the world
- STATISTICAL: uses numbers, percentages, quantities
- TEMPORAL: makes claims about timing ("first", "last year", "in 2020")
- IDENTITY: claims about who someone is or what an org is
- CAUSAL: X caused Y claims
- OPINION: presented as fact but is subjective

Red flag vocabulary (use ONLY these exact strings if applicable):
- absolute_language       (always, never, everyone, no one)
- urgency_trigger         (breaking, act now, share before deleted)
- appeal_to_fear          (threatens harm, catastrophe framing)
- unverified_attribution  (anonymous source, "some experts say")
- emotional_amplifier     (shocking, outrageous, disgusting)
- vague_quantifier        (many, most, a lot — without citation)
- conspiracy_framing      (they don't want you to know, hidden truth)

Verifiability rules:
- HIGH: has specific names, dates, numbers → can be fact-checked
- MEDIUM: partially specific, some elements checkable
- LOW: vague, opinion-based, or unfalsifiable

If text is empty or has no claims, return: {"claims": []}
"""


# =============================================================================
# Main extractor
# =============================================================================

class ClaimExtractor:
    """
    Async claim extractor.
    Uses Groq (llama-3.3-70b-versatile) as the LLM backend.
    Falls back to heuristic extraction if Groq is unavailable or the key is missing.
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        api_key = os.environ.get("GROQ_API_KEY", "")
        if _groq_available and api_key:
            self._client = Groq(api_key=api_key)
            self._llm_ready = True
        else:
            self._client = None
            self._llm_ready = False
            if not _groq_available:
                logger.warning("groq package missing — using heuristic fallback")
            else:
                logger.warning("GROQ_API_KEY not set — using heuristic fallback")

    async def extract(self, text: str, source_type: str = "unknown") -> ClaimExtractionResult:
        if not text or not text.strip():
            return ClaimExtractionResult(
                success=False,
                extraction_method="failed",
                error="No text provided",
                reasoning_notes=["Input text was empty"],
            )

        if self._llm_ready:
            result = await asyncio.to_thread(self._extract_with_groq, text, source_type)
            if result.success:
                return result
            logger.warning(f"Groq extraction failed: {result.error} — falling back to heuristic")

        return self._extract_with_heuristics(text, source_type)

    def _extract_with_groq(self, text: str, source_type: str) -> ClaimExtractionResult:
        """Synchronous Groq call — run via asyncio.to_thread."""
        try:
            response = self._client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Source type: {source_type}\n\nText:\n{text[:12000]}"},
                ],
                temperature=0.0,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()
            return self._parse_llm_response(raw)
        except Exception as exc:
            return ClaimExtractionResult(
                success=False,
                extraction_method="failed",
                error=str(exc),
            )

    def _parse_llm_response(self, raw: str) -> ClaimExtractionResult:
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return self._build_result(data.get("claims", []), "llm")

    def _extract_with_heuristics(self, text: str, source_type: str) -> ClaimExtractionResult:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
        red_flag_patterns = {
            "absolute_language":     r"\b(always|never|everyone|no one|nobody|all people)\b",
            "urgency_trigger":       r"\b(breaking|act now|share before|deleted|censored|urgent)\b",
            "appeal_to_fear":        r"\b(danger|threat|catastrophe|crisis|disaster|deadly)\b",
            "unverified_attribution":r"\b(sources say|experts believe|some say|anonymous)\b",
            "emotional_amplifier":   r"\b(shocking|outrageous|disgusting|unbelievable)\b",
            "vague_quantifier":      r"\b(many|most|a lot|tons of|countless)\b",
            "conspiracy_framing":    r"\b(hidden|they don.t want|secret|cover.?up|suppressed)\b",
        }
        stat_pattern    = re.compile(r"\b\d+(?:\.\d+)?%|\b\d[\d,]*\s*(million|billion|thousand|people|cases)\b", re.I)
        temporal_pattern= re.compile(r"\b(in \d{4}|last (year|month|week)|yesterday|recently|since \d{4})\b", re.I)
        entity_pattern  = re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b")

        claims = []
        for i, sentence in enumerate(sentences[:15], start=1):
            red_flags = [f for f, pat in red_flag_patterns.items() if re.search(pat, sentence, re.I)]
            is_stat     = bool(stat_pattern.search(sentence))
            is_temporal = bool(temporal_pattern.search(sentence))
            entities    = list(set(entity_pattern.findall(sentence)))[:5]

            if is_stat:
                ctype, verif = "STATISTICAL", "HIGH"
            elif is_temporal:
                ctype, verif = "TEMPORAL", "MEDIUM"
            elif red_flags:
                ctype, verif = "FACTUAL", "MEDIUM"
            else:
                ctype, verif = "FACTUAL", "LOW"

            claims.append({
                "claim_id":    i,
                "claim_text":  sentence[:200],
                "claim_type":  ctype,
                "verifiability": verif,
                "entities":    entities,
                "red_flags":   red_flags,
                "raw_quote":   sentence,
            })

        return self._build_result(claims, "heuristic")

    def _build_result(self, raw_claims: List[dict], method: str) -> ClaimExtractionResult:
        parsed = []
        for raw in raw_claims:
            try:
                parsed.append(ExtractedClaim(**raw))
            except Exception as exc:
                logger.warning(f"Skipping malformed claim: {exc}")

        high_risk = sum(1 for c in parsed if c.verifiability == "HIGH" and c.red_flags)
        type_counts: dict = {}
        for c in parsed:
            type_counts[c.claim_type] = type_counts.get(c.claim_type, 0) + 1
        dominant = sorted(type_counts, key=type_counts.get, reverse=True)[:3]  # type: ignore[arg-type]

        base       = 0.5 if parsed else 0.0
        high_bonus = min(0.3, sum(0.1 for c in parsed if c.verifiability == "HIGH"))
        risk_pen   = min(0.3, high_risk * 0.05)
        confidence = round(min(1.0, base + high_bonus - risk_pen), 2)

        notes = []
        if not parsed:
            notes.append("No claims extracted")
        else:
            notes.append(f"Extracted {len(parsed)} claims via {method}")
            if high_risk:
                notes.append(f"{high_risk} high-risk claim(s) detected")
            if dominant:
                notes.append(f"Dominant types: {', '.join(dominant)}")

        return ClaimExtractionResult(
            success=True,
            claims=parsed,
            total_claims=len(parsed),
            high_risk_claims=high_risk,
            dominant_claim_types=dominant,
            confidence_contribution=confidence,
            extraction_method=method,
            reasoning_notes=notes,
        )