"""
Claim Verifier Agent
---------------------
Verifies extracted claims against a ChromaDB vector store.
NLI backend: Groq  (llama-3.3-70b-versatile)
Fallback:    cosine-similarity heuristic (if Groq unavailable)
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from claim_extractor import ClaimExtractor, ExtractedClaim, select_richest_text

logger = logging.getLogger(__name__)

# ── Groq client ────────────────────────────────────────────────────────────────
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False
    logger.warning("groq package not installed — NLI will use similarity heuristic")

_GROQ_MODEL = "llama-3.3-70b-versatile"

_NLI_SYSTEM = (
    "You are a fact-checking NLI model. "
    "Given a CLAIM and EVIDENCE passages, respond ONLY with a JSON object: "
    '{"verdict": "SUPPORTED"|"CONTRADICTED"|"INSUFFICIENT", '
    '"confidence": 0.0-1.0, "explanation": "<one sentence>"}'
)


# =============================================================================
# Output models
# =============================================================================

@dataclass
class RetrievedChunk:
    chunk_id: str
    source_url: str
    text_snippet: str
    similarity_score: float
    collection: str


@dataclass
class VerifiedClaim:
    claim_id: int
    claim_text: str
    claim_type: str
    verifiability: str
    red_flags: List[str]
    verdict: str
    confidence: float
    explanation: str
    top_chunk_ids: List[str]


@dataclass
class ClaimVerifyResult:
    input_type: str
    source_ref: str
    dedup_hash: str
    quality_passed: bool
    claims: List[ExtractedClaim]
    verified_claims: List[VerifiedClaim]
    retrieved_chunks: List[RetrievedChunk]
    overall_support_score: float
    overall_contradiction_score: float
    agent_errors: List[str]


# =============================================================================
# VectorStore (unchanged)
# =============================================================================

class VectorStore:
    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "fact_corpus",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self._model = SentenceTransformer(embedding_model)
        self._client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"VectorStore ready: {collection_name}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def query(self, query_text: str, n_results: int = 5) -> List[RetrievedChunk]:
        embedding = self.embed([query_text])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                RetrievedChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    source_url=meta.get("source_url", ""),
                    text_snippet=doc,
                    similarity_score=1.0 - dist,
                    collection=self._collection.name,
                )
            )
        return chunks

    def upsert(
        self,
        texts: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ):
        embeddings = self.embed(texts)
        if ids is None:
            import hashlib
            ids = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in texts]
        self._collection.upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )


# =============================================================================
# ClaimVerifier
# =============================================================================

class ClaimVerifier:
    _VERIF_THRESHOLDS = {"HIGH": 0.65, "MEDIUM": 0.75, "LOW": 0.85}

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        use_llm_nli: bool = True,
        adjust_by_verifiability: bool = True,
    ):
        self._vs = vector_store
        self._top_k = top_k
        self._use_llm_nli = use_llm_nli
        self._adjust_by_verifiability = adjust_by_verifiability

        api_key = os.environ.get("GROQ_API_KEY", "")
        if _groq_available and api_key:
            self._groq = Groq(api_key=api_key)
            self._nli_ready = True
        else:
            self._groq = None
            self._nli_ready = False
            if use_llm_nli:
                logger.warning(
                    "Groq NLI unavailable — verifier will fall back to similarity heuristic"
                )

    def _nli_score_sync(self, claim: str, evidence: List[str]) -> Dict[str, Any]:
        """Synchronous Groq NLI call — run via asyncio.to_thread."""
        evidence_text = "\n---\n".join(evidence[:3])
        response = self._groq.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _NLI_SYSTEM},
                {"role": "user", "content": f"CLAIM: {claim}\n\nEVIDENCE:\n{evidence_text}"},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)

    async def _nli_score(self, claim: str, evidence: List[str]) -> Dict[str, Any]:
        return await asyncio.to_thread(self._nli_score_sync, claim, evidence)

    async def verify_claim(
        self, claim: ExtractedClaim
    ) -> Tuple[VerifiedClaim, List[RetrievedChunk]]:
        chunks = self._vs.query(claim.claim_text, n_results=self._top_k)
        evidence_texts = [c.text_snippet for c in chunks]

        if self._use_llm_nli and self._nli_ready and evidence_texts:
            try:
                verdict_dict = await self._nli_score(claim.claim_text, evidence_texts)
                verdict     = verdict_dict.get("verdict", "INSUFFICIENT")
                confidence  = float(verdict_dict.get("confidence", 0.0))
                explanation = verdict_dict.get("explanation", "")
            except Exception as exc:
                logger.error(f"Groq NLI failed for claim {claim.claim_id}: {exc}")
                verdict, confidence, explanation = "ERROR", 0.0, str(exc)
        else:
            # Similarity-based heuristic fallback
            avg_sim   = sum(c.similarity_score for c in chunks) / len(chunks) if chunks else 0.0
            threshold = (
                self._VERIF_THRESHOLDS.get(claim.verifiability, 0.75)
                if self._adjust_by_verifiability
                else 0.75
            )
            if avg_sim > threshold:
                verdict, confidence = "SUPPORTED", avg_sim
            elif avg_sim < threshold - 0.2:
                verdict, confidence = "CONTRADICTED", avg_sim
            else:
                verdict, confidence = "INSUFFICIENT", avg_sim
            explanation = f"Heuristic: similarity={avg_sim:.2f}, threshold={threshold}"

        verified = VerifiedClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            verifiability=claim.verifiability,
            red_flags=claim.red_flags,
            verdict=verdict,
            confidence=confidence,
            explanation=explanation,
            top_chunk_ids=[c.chunk_id for c in chunks],
        )
        return verified, chunks

    async def verify_all(
        self, claims: List[ExtractedClaim]
    ) -> Tuple[List[VerifiedClaim], List[RetrievedChunk]]:
        tasks = [self.verify_claim(c) for c in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        verified_list: List[VerifiedClaim] = []
        all_chunks: List[RetrievedChunk] = []
        seen_ids: set = set()

        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Claim verification error: {r}")
                verified_list.append(
                    VerifiedClaim(
                        claim_id=-1, claim_text="", claim_type="", verifiability="",
                        red_flags=[], verdict="ERROR", confidence=0.0,
                        explanation=str(r), top_chunk_ids=[],
                    )
                )
            else:
                verified, chunks = r
                verified_list.append(verified)
                for chunk in chunks:
                    if chunk.chunk_id not in seen_ids:
                        all_chunks.append(chunk)
                        seen_ids.add(chunk.chunk_id)

        return verified_list, all_chunks


# =============================================================================
# RAGAgent
# =============================================================================

class RAGAgent:
    def __init__(
        self,
        vector_store: VectorStore,
        claim_extractor: ClaimExtractor,
        use_llm_nli: bool = True,
        top_k: int = 5,
    ):
        self._extractor = claim_extractor
        self._verifier = ClaimVerifier(
            vector_store=vector_store,
            top_k=top_k,
            use_llm_nli=use_llm_nli,
        )

    async def run(self, nfo: Any) -> ClaimVerifyResult:
        errors: List[str] = []

        if not nfo.quality_passed:
            logger.warning(f"Quality gate failed: {nfo.quality_reason}")
            return ClaimVerifyResult(
                input_type=nfo.input_type,
                source_ref=nfo.source_ref,
                dedup_hash=getattr(nfo, "dedup_hash", ""),
                quality_passed=False,
                claims=[],
                verified_claims=[],
                retrieved_chunks=[],
                overall_support_score=0.0,
                overall_contradiction_score=0.0,
                agent_errors=[f"Skipped: {nfo.quality_reason}"],
            )

        text = select_richest_text(nfo)
        extraction_result = await self._extractor.extract(
            text, nfo.input_type.value if hasattr(nfo.input_type, "value") else str(nfo.input_type)
        )

        if not extraction_result.success:
            errors.append(f"extraction failed: {extraction_result.error}")
            claims: List[ExtractedClaim] = []
        else:
            claims = extraction_result.claims

        if claims:
            verified_claims, retrieved_chunks = await self._verifier.verify_all(claims)
        else:
            verified_claims, retrieved_chunks = [], []

        support_sum = contra_sum = total_conf = 0.0
        for vc in verified_claims:
            conf = vc.confidence
            total_conf += conf
            if vc.verdict == "SUPPORTED":
                support_sum += conf
            elif vc.verdict == "CONTRADICTED":
                contra_sum += conf

        support_score = support_sum / total_conf if total_conf > 0 else 0.0
        contra_score  = contra_sum  / total_conf if total_conf > 0 else 0.0

        return ClaimVerifyResult(
            input_type=nfo.input_type,
            source_ref=nfo.source_ref,
            dedup_hash=getattr(nfo, "dedup_hash", ""),
            quality_passed=True,
            claims=claims,
            verified_claims=verified_claims,
            retrieved_chunks=retrieved_chunks,
            overall_support_score=support_score,
            overall_contradiction_score=contra_score,
            agent_errors=errors,
        )