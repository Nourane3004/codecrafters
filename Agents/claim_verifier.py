"""
Claim Verifier Agent – Version améliorée
"""
import asyncio
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field

import httpx
from sentence_transformers import SentenceTransformer
import chromadb

# Import depuis claim_extractor
from claim_extractor import ExtractedClaim, select_richest_text, ClaimExtractor

logger = logging.getLogger(__name__)

# =============================================================================
# Modèles de sortie
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
# VectorStore (identique)
# =============================================================================

class VectorStore:
    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "fact_corpus",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        self._model = SentenceTransformer(embedding_model)
        # Modern ChromaDB API (v0.4+): use PersistentClient instead of deprecated Client(Settings(...))
        self._client = chromadb.PersistentClient(path=persist_dir)
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
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            chunks.append(RetrievedChunk(
                chunk_id=meta.get("chunk_id", ""),
                source_url=meta.get("source_url", ""),
                text_snippet=doc,
                similarity_score=1.0 - dist,
                collection=self._collection.name,
            ))
        return chunks

    def upsert(self, texts: List[str], metadatas: List[dict], ids: Optional[List[str]] = None):
        embeddings = self.embed(texts)
        if ids is None:
            import hashlib
            ids = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in texts]
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

# =============================================================================
# ClaimVerifier
# =============================================================================

class ClaimVerifier:
    _VERIF_THRESHOLDS = {"HIGH": 0.65, "MEDIUM": 0.75, "LOW": 0.85}

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        llm_base_url: str = "http://localhost:11434/v1",
        use_llm_nli: bool = True,
        adjust_by_verifiability: bool = True,
    ):
        self._vs = vector_store
        self._top_k = top_k
        self._llm_base_url = llm_base_url.rstrip("/")
        self._use_llm_nli = use_llm_nli
        self._adjust_by_verifiability = adjust_by_verifiability

    async def _nli_score(self, claim: str, evidence: List[str]) -> Dict[str, Any]:
        NLI_SYSTEM = (
            "You are a fact-checking NLI model. "
            "Given a CLAIM and EVIDENCE passages, respond ONLY with a JSON object: "
            '{"verdict": "SUPPORTED"|"CONTRADICTED"|"INSUFFICIENT", '
            '"confidence": 0.0-1.0, "explanation": "<one sentence>"}'
        )
        evidence_text = "\n---\n".join(evidence[:3])
        payload = {
            "model": "mistral",
            "messages": [
                {"role": "system", "content": NLI_SYSTEM},
                {"role": "user", "content": f"CLAIM: {claim}\n\nEVIDENCE:\n{evidence_text}"}
            ],
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._llm_base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Nettoyage markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    async def verify_claim(self, claim: ExtractedClaim) -> Tuple[VerifiedClaim, List[RetrievedChunk]]:
        chunks = self._vs.query(claim.claim_text, n_results=self._top_k)
        evidence_texts = [c.text_snippet for c in chunks]

        if self._use_llm_nli and evidence_texts:
            try:
                verdict_dict = await self._nli_score(claim.claim_text, evidence_texts)
                verdict = verdict_dict.get("verdict", "INSUFFICIENT")
                confidence = float(verdict_dict.get("confidence", 0.0))
                explanation = verdict_dict.get("explanation", "")
            except Exception as e:
                logger.error(f"NLI failed for claim {claim.claim_id}: {e}")
                verdict, confidence, explanation = "ERROR", 0.0, str(e)
        else:
            avg_sim = sum(c.similarity_score for c in chunks) / len(chunks) if chunks else 0.0
            if self._adjust_by_verifiability:
                threshold = self._VERIF_THRESHOLDS.get(claim.verifiability, 0.75)
            else:
                threshold = 0.75
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

    async def verify_all(self, claims: List[ExtractedClaim]) -> Tuple[List[VerifiedClaim], List[RetrievedChunk]]:
        tasks = [self.verify_claim(c) for c in claims]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        verified_list = []
        all_chunks = []
        seen_ids = set()

        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Claim verification error: {r}")
                verified_list.append(VerifiedClaim(
                    claim_id=-1, claim_text="", claim_type="", verifiability="",
                    red_flags=[], verdict="ERROR", confidence=0.0, explanation=str(r),
                    top_chunk_ids=[]
                ))
            else:
                verified, chunks = r
                verified_list.append(verified)
                for chunk in chunks:
                    if chunk.chunk_id not in seen_ids:
                        all_chunks.append(chunk)
                        seen_ids.add(chunk.chunk_id)
        return verified_list, all_chunks

# =============================================================================
# RAGAgent unifié
# =============================================================================

class RAGAgent:
    def __init__(
        self,
        vector_store: VectorStore,
        claim_extractor: ClaimExtractor,
        llm_base_url: str = "http://localhost:11434/v1",
        use_llm_nli: bool = True,
        top_k: int = 5,
    ):
        self._extractor = claim_extractor
        self._verifier = ClaimVerifier(
            vector_store=vector_store,
            top_k=top_k,
            llm_base_url=llm_base_url,
            use_llm_nli=use_llm_nli,
        )

    async def run(self, nfo: Any) -> ClaimVerifyResult:
        errors = []

        if not nfo.quality_passed:
            logger.warning(f"Quality gate failed: {nfo.quality_reason}")
            return ClaimVerifyResult(
                input_type=nfo.input_type,
                source_ref=nfo.source_ref,
                dedup_hash=nfo.dedup_hash,
                quality_passed=False,
                claims=[],
                verified_claims=[],
                retrieved_chunks=[],
                overall_support_score=0.0,
                overall_contradiction_score=0.0,
                agent_errors=[f"Skipped: {nfo.quality_reason}"],
            )

        text = select_richest_text(nfo)
        extraction_result = await self._extractor.extract(text, nfo.input_type.lower())

        if not extraction_result.success:
            errors.append(f"extraction failed: {extraction_result.error}")
            claims = []
        else:
            claims = extraction_result.claims

        if claims:
            verified_claims, retrieved_chunks = await self._verifier.verify_all(claims)
        else:
            verified_claims, retrieved_chunks = [], []

        support_sum = 0.0
        contra_sum = 0.0
        total_conf = 0.0
        for vc in verified_claims:
            conf = vc.confidence
            total_conf += conf
            if vc.verdict == "SUPPORTED":
                support_sum += conf
            elif vc.verdict == "CONTRADICTED":
                contra_sum += conf

        support_score = support_sum / total_conf if total_conf > 0 else 0.0
        contra_score = contra_sum / total_conf if total_conf > 0 else 0.0

        return ClaimVerifyResult(
            input_type=nfo.input_type,
            source_ref=nfo.source_ref,
            dedup_hash=nfo.dedup_hash,
            quality_passed=nfo.quality_passed,
            claims=claims,
            verified_claims=verified_claims,
            retrieved_chunks=retrieved_chunks,
            overall_support_score=support_score,
            overall_contradiction_score=contra_score,
            agent_errors=errors,
        )