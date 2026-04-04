"""
Claim Extractor Agent – Version améliorée
------------------------------------------
- Extrait des allégations factuelles à partir de n'importe quelle source textuelle
- Supporte plusieurs fournisseurs LLM (Anthropic, OpenAI, Ollama)
- Retourne une structure riche (ExtractedClaim) + une liste simple pour compatibilité
- Intègre la logique de sélection de texte selon le type d'entrée (image, URL, document, vidéo)
- Asynchrone, avec fallback heuristique
"""

import asyncio
import json
import logging
import re
from typing import Optional, Literal, List, Union, Any
from dataclasses import dataclass, field
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)



# =============================================================================
# Modèles de sortie (compatibles avec le verifier)
# =============================================================================

class ExtractedClaim(BaseModel):
    """Allégation unique extraite du contenu."""
    claim_id: int = Field(..., description="Index séquentiel")
    claim_text: str = Field(..., description="Texte de l'allégation")
    claim_type: Literal["FACTUAL", "STATISTICAL", "TEMPORAL", "IDENTITY", "CAUSAL", "OPINION"] = "FACTUAL"
    verifiability: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    entities: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    raw_quote: Optional[str] = None

class ClaimExtractionResult(BaseModel):
    """Résultat complet de l'extraction."""
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
# Sélecteur de texte selon le type d'entrée (copié depuis l'ancien ClaimExtractor)
# =============================================================================

def select_richest_text(nfo: Any) -> str:
    """
    Sélectionne la meilleure surface textuelle à partir d'un NormalizedFeatureObject.
    Supporte les champs: image_meta, url_data, doc_data, video_data.
    """
    if nfo.input_type == "IMAGE":
        if nfo.image_meta and nfo.image_meta.ocr.raw_text and nfo.image_meta.ocr.confidence >= 0.7:
            return nfo.image_meta.ocr.raw_text
        return nfo.text.raw_text

    if nfo.input_type == "URL":
        if nfo.url_data and nfo.url_data.raw_text:
            prefix = ""
            if nfo.url_data.meta.title:
                prefix += f"Title: {nfo.url_data.meta.title}\n"
            if nfo.url_data.meta.description:
                prefix += f"Description: {nfo.url_data.meta.description}\n\n"
            return prefix + nfo.url_data.raw_text
        return nfo.text.raw_text

    if nfo.input_type == "DOCUMENT":
        if nfo.doc_data and nfo.doc_data.layout_blocks:
            return "\n\n".join(block.text for block in nfo.doc_data.layout_blocks)
        return nfo.text.raw_text

    if nfo.input_type == "VIDEO":
        if nfo.video_data and nfo.video_data.asr.raw_text:
            return nfo.video_data.asr.raw_text
        return nfo.text.raw_text

    return nfo.text.raw_text

# =============================================================================
# Prompt système (identique à la version améliorée)
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
# Extractor principal (asynchrone, multi-provider)
# =============================================================================

class ClaimExtractor:
    """
    Extracteur d'allégations asynchrone supportant:
    - Anthropic (Claude)
    - OpenAI compatible (Ollama, vLLM, etc.)
    - Fallback heuristique
    """

    def __init__(
        self,
        provider: Literal["anthropic", "openai_compat"] = "openai_compat",
        model: str = "mistral",                     # pour openai_compat
        anthropic_model: str = "claude-3-sonnet-20240229",
        api_base: str = "http://localhost:11434/v1", # pour openai_compat
        api_key: Optional[str] = None,               # pour anthropic
        timeout: float = 60.0,
    ):
        self.provider = provider
        self.model = model
        self.anthropic_model = anthropic_model
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

        if provider == "anthropic":
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=api_key)
                self._available = True
            except ImportError:
                logger.warning("anthropic package not installed, falling back to heuristic")
                self._available = False
        else:
            self._available = True  # on suppose httpx fonctionne

    async def extract(self, text: str, source_type: str = "unknown") -> ClaimExtractionResult:
        """Point d'entrée principal."""
        if not text or not text.strip():
            return ClaimExtractionResult(
                success=False,
                extraction_method="failed",
                error="No text provided",
                reasoning_notes=["Input text was empty"]
            )

        if self.provider == "anthropic" and self._available:
            result = await self._extract_with_anthropic(text, source_type)
            if result.success:
                return result
            logger.warning(f"Anthropic extraction failed: {result.error}")

        elif self.provider == "openai_compat":
            result = await self._extract_with_openai(text, source_type)
            if result.success:
                return result
            logger.warning(f"OpenAI-compat extraction failed: {result.error}")

        # Fallback heuristique
        return self._extract_with_heuristics(text, source_type)

    async def _extract_with_anthropic(self, text: str, source_type: str) -> ClaimExtractionResult:
        try:
            # Troncature
            user_content = text[:12000] if len(text) > 12000 else text
            response = self._anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Source type: {source_type}\n\nText:\n{user_content}"}]
            )
            raw_json = response.content[0].text.strip()
            return self._parse_llm_response(raw_json, "llm")
        except Exception as e:
            return ClaimExtractionResult(
                success=False, extraction_method="failed", error=str(e)
            )

    async def _extract_with_openai(self, text: str, source_type: str) -> ClaimExtractionResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Source type: {source_type}\n\nText:\n{text[:12000]}"}
            ],
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.api_base}/chat/completions", json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
        return self._parse_llm_response(raw, "llm")

    def _parse_llm_response(self, raw_json: str, method: str) -> ClaimExtractionResult:
        # Nettoyage des markdown
        raw_json = re.sub(r'^```(?:json)?', '', raw_json, flags=re.MULTILINE).strip()
        raw_json = re.sub(r'```$', '', raw_json, flags=re.MULTILINE).strip()
        data = json.loads(raw_json)
        return self._build_result(data.get("claims", []), method)

    def _extract_with_heuristics(self, text: str, source_type: str) -> ClaimExtractionResult:
        """Fallback basé sur des regex."""
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]
        claims = []
        red_flag_patterns = {
            "absolute_language": r"\b(always|never|everyone|no one|nobody|all people)\b",
            "urgency_trigger": r"\b(breaking|act now|share before|deleted|censored|urgent)\b",
            "appeal_to_fear": r"\b(danger|threat|catastrophe|crisis|disaster|deadly)\b",
            "unverified_attribution": r"\b(sources say|experts believe|some say|anonymous)\b",
            "emotional_amplifier": r"\b(shocking|outrageous|disgusting|unbelievable)\b",
            "vague_quantifier": r"\b(many|most|a lot|tons of|countless)\b",
            "conspiracy_framing": r"\b(hidden|they don.t want|secret|cover.?up|suppressed)\b",
        }
        stat_pattern = re.compile(r'\b\d+(?:\.\d+)?%|\b\d[\d,]*\s*(million|billion|thousand|people|cases)\b', re.I)
        temporal_pattern = re.compile(r'\b(in \d{4}|last (year|month|week)|yesterday|recently|since \d{4})\b', re.I)
        entity_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b')

        for i, sentence in enumerate(sentences[:15], start=1):
            red_flags = [flag for flag, pat in red_flag_patterns.items() if re.search(pat, sentence, re.I)]
            is_stat = bool(stat_pattern.search(sentence))
            is_temporal = bool(temporal_pattern.search(sentence))
            entities = list(set(entity_pattern.findall(sentence)))[:5]

            if is_stat:
                ctype, verif = "STATISTICAL", "HIGH"
            elif is_temporal:
                ctype, verif = "TEMPORAL", "MEDIUM"
            elif red_flags:
                ctype, verif = "FACTUAL", "MEDIUM"
            else:
                ctype, verif = "FACTUAL", "LOW"

            claims.append({
                "claim_id": i,
                "claim_text": sentence[:200],
                "claim_type": ctype,
                "verifiability": verif,
                "entities": entities,
                "red_flags": red_flags,
                "raw_quote": sentence,
            })
        return self._build_result(claims, "heuristic")

    def _build_result(self, raw_claims: List[dict], method: str) -> ClaimExtractionResult:
        parsed = []
        for raw in raw_claims:
            try:
                parsed.append(ExtractedClaim(**raw))
            except Exception as e:
                logger.warning(f"Skipping malformed claim: {raw} — {e}")

        high_risk = sum(1 for c in parsed if c.verifiability == "HIGH" and c.red_flags)

        type_counts = {}
        for c in parsed:
            type_counts[c.claim_type] = type_counts.get(c.claim_type, 0) + 1
        dominant = sorted(type_counts, key=type_counts.get, reverse=True)[:3]

        # Score de confiance pour le quality gate
        base = 0.5 if parsed else 0.0
        high_bonus = min(0.3, sum(0.1 for c in parsed if c.verifiability == "HIGH"))
        risk_penalty = min(0.3, high_risk * 0.05)
        confidence = round(min(1.0, base + high_bonus - risk_penalty), 2)

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