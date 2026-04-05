"""
Context Agent
--------------
Verifies claim consistency against world knowledge and temporal logic.
LLM backend: Groq  (llama-3.3-70b-versatile)
Fallback:    Wikidata entity search (no LLM required)

The mock has been removed entirely.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

import httpx

from claim_extractor import ExtractedClaim

logger = logging.getLogger(__name__)

# ── Groq client ────────────────────────────────────────────────────────────────
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False
    logger.warning("groq package not installed — context agent will use Wikidata-only fallback")

_GROQ_MODEL = "llama-3.3-70b-versatile"

_CONTEXT_SYSTEM = """You are a world-knowledge consistency checker for a misinformation detection system.

Given a factual claim, evaluate whether it is consistent with established world knowledge.

Respond ONLY with a valid JSON object — no markdown, no preamble:
{
  "is_consistent": true|false,
  "confidence": 0.0-1.0,
  "supporting_facts": ["<fact1>", "<fact2>"],
  "contradicting_facts": ["<fact1>"],
  "temporal_issues": ["<issue1>"]
}

Rules:
- is_consistent: true if the claim aligns with well-established facts
- confidence: how certain you are (0 = no idea, 1 = certain)
- supporting_facts: specific facts from your knowledge that support the claim
- contradicting_facts: specific facts that contradict it
- temporal_issues: any date/timing inconsistencies (e.g. "event predates the entity's existence")
- Be concise. Max 2 items per list.
- If you have no knowledge about the claim, set confidence to 0.3 and is_consistent to false.
"""


# =============================================================================
# Output models
# =============================================================================

@dataclass
class ContextCheck:
    claim_text: str
    claim_id: int
    is_consistent: bool
    confidence: float
    supporting_facts: List[str]
    contradicting_facts: List[str]
    temporal_issues: List[str]
    agent_errors: List[str]


@dataclass
class ContextAgentResult:
    source_ref: str
    input_type: str
    overall_consistency_score: float
    temporal_coherence_score: float
    checks: List[ContextCheck] = field(default_factory=list)
    agent_errors: List[str] = field(default_factory=list)


# =============================================================================
# Agent
# =============================================================================

class ContextAgent:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

        api_key = os.environ.get("GROQ_API_KEY", "")
        if _groq_available and api_key:
            self._groq = Groq(api_key=api_key)
            self._llm_ready = True
        else:
            self._groq = None
            self._llm_ready = False
            if not _groq_available:
                logger.warning("groq package missing — context agent will use Wikidata fallback")
            else:
                logger.warning("GROQ_API_KEY not set — context agent will use Wikidata fallback")

    async def run(self, nfo: Any, claims: List[ExtractedClaim]) -> ContextAgentResult:
        if not claims:
            return ContextAgentResult(
                source_ref=nfo.source_ref,
                input_type=str(nfo.input_type),
                overall_consistency_score=0.5,
                temporal_coherence_score=0.5,
                agent_errors=["No claims to check"],
            )

        checks = await asyncio.gather(
            *[self._check_single_claim(claim) for claim in claims],
            return_exceptions=False,
        )

        # Overall consistency (confidence-weighted)
        total_conf = sum(c.confidence for c in checks)
        if total_conf == 0:
            overall_consistency = 0.5
        else:
            overall_consistency = sum(
                (1.0 if c.is_consistent else 0.0) * c.confidence for c in checks
            ) / total_conf

        # Temporal coherence: fraction of claims with no temporal issues
        temporal_scores = [0.0 if c.temporal_issues else 1.0 for c in checks]
        temporal_coherence = sum(temporal_scores) / len(temporal_scores)

        return ContextAgentResult(
            source_ref=nfo.source_ref,
            input_type=str(nfo.input_type),
            overall_consistency_score=overall_consistency,
            temporal_coherence_score=temporal_coherence,
            checks=list(checks),
        )

    async def _check_single_claim(self, claim: ExtractedClaim) -> ContextCheck:
        if self._llm_ready:
            try:
                return await asyncio.to_thread(self._groq_check, claim)
            except Exception as exc:
                logger.warning(f"Groq context check failed for claim {claim.claim_id}: {exc} — trying Wikidata")

        # Fallback: Wikidata entity search
        return await self._wikidata_check(claim)

    # ── Groq-powered check ─────────────────────────────────────────────────────

    def _groq_check(self, claim: ExtractedClaim) -> ContextCheck:
        response = self._groq.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _CONTEXT_SYSTEM},
                {"role": "user", "content": f"Claim: {claim.claim_text}"},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)

        return ContextCheck(
            claim_text=claim.claim_text,
            claim_id=claim.claim_id,
            is_consistent=bool(data.get("is_consistent", False)),
            confidence=float(data.get("confidence", 0.5)),
            supporting_facts=data.get("supporting_facts", []),
            contradicting_facts=data.get("contradicting_facts", []),
            temporal_issues=data.get("temporal_issues", []),
            agent_errors=[],
        )

    # ── Wikidata fallback ──────────────────────────────────────────────────────

    async def _wikidata_check(self, claim: ExtractedClaim) -> ContextCheck:
        """
        Searches Wikidata for named entities in the claim.
        If at least one entity is found, marks the claim as partially consistent.
        No LLM required.
        """
        entities = claim.entities or re.findall(
            r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", claim.claim_text
        )
        found_entities: List[str] = []
        errors: List[str] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ent in entities[:3]:
                try:
                    resp = await client.get(
                        "https://www.wikidata.org/w/api.php",
                        params={
                            "action": "wbsearchentities",
                            "search": ent,
                            "language": "en",
                            "format": "json",
                            "limit": 1,
                        },
                    )
                    data = resp.json()
                    if data.get("search"):
                        label = data["search"][0].get("label", ent)
                        desc  = data["search"][0].get("description", "")
                        found_entities.append(f"{label}: {desc}" if desc else label)
                except Exception as exc:
                    errors.append(f"Wikidata lookup failed for '{ent}': {exc}")

        if found_entities:
            is_consistent = True
            confidence    = 0.55          # moderate — we found entities but didn't verify the claim
            supporting    = [f"Entity found in Wikidata: {e}" for e in found_entities]
            contradicting: List[str] = []
        else:
            is_consistent = False
            confidence    = 0.3
            supporting    = []
            contradicting = ["No named entities from this claim found in Wikidata."]

        return ContextCheck(
            claim_text=claim.claim_text,
            claim_id=claim.claim_id,
            is_consistent=is_consistent,
            confidence=confidence,
            supporting_facts=supporting,
            contradicting_facts=contradicting,
            temporal_issues=[],
            agent_errors=errors,
        )