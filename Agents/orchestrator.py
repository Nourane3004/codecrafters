"""
orchestrator.py
===============
Prefect Orchestrator — TruthGuard / MENACRAFT
================================================
Wires the full pipeline together:

  Input (bytes + type)
    └─► Preprocessing Service  (FastAPI call or direct import)
          └─► AI Agent Committee  (8 agents, parallel)
                └─► Evidence Fusion + Risk Scoring
                      └─► Decision Engine
                            └─► FusionResult

Prefect task/flow anatomy
─────────────────────────
  Flow  : analyse_content          — top-level entry point
  Tasks : preprocess_task          — calls the preprocessing service
          run_agent_committee      — fans-out to all 8 agent tasks (parallel)
          claim_extract_task       — individual agent task
          claim_verify_task        — individual agent task
          source_cred_task         — individual agent task
          image_forensics_task     — individual agent task
          video_forensics_task     — individual agent task
          context_task             — individual agent task
          network_task             — individual agent task
          linguistic_task          — individual agent task
          fuse_evidence_task       — calls evidence_fusion.py
          decide_task              — maps fused result → decision

All tasks use:
  - retries=2, retry_delay_seconds=5
  - result caching disabled (fresh run each time)
  - Prefect logging (replaces print / bare logger calls)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

# ── project imports ────────────────────────────────────────────────────────────
# Preprocessing (direct import — no HTTP hop in local mode)
from Preprocessing.app.models.feature_object import NormalizedFeatureObject, InputType
from Preprocessing.app.pipeline.image.processor_image    import preprocess_image
from Preprocessing.app.pipeline.url.processor_url        import preprocess_url
from Preprocessing.app.pipeline.document.processor_doc   import preprocess_document
from Preprocessing.app.pipeline.video.processor_vid      import preprocess_video
from Preprocessing.app.pipeline.quality_gate             import enrich

# Agents
from Agents.claim_extractor   import ClaimExtractor, ClaimExtractionResult
from Agents.claim_verifier    import VectorStore, RAGAgent, ClaimVerifyResult
from Agents.context_agent     import ContextAgent, ContextAgentResult
from Agents.source_cred_agent import SourceCredibilityAgent, SourceCredibilityResult
from Agents.network_agent     import analyse_network, NetworkAnalysisResult
from Agents.linguistic_agent  import analyse_linguistics, LinguisticAnalysisResult
from Agents.agent_image_forensics import process as image_forensics_process
from Agents.agent_video_forensics import process as video_forensics_process

# Evidence fusion + decision engine
from Agents.evidence_fusion import (
    fuse_evidence,
    FusionResult,
    DecisionEngine,
    PipelineResult,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Preprocessing task
# ══════════════════════════════════════════════════════════════════════════════

@task(
    name="preprocess",
    retries=2,
    retry_delay_seconds=5,
    description="Route raw input through the correct preprocessing pipeline branch.",
)
async def preprocess_task(
    file_bytes: Optional[bytes],
    source_ref: str,
    input_type: str,          # "image" | "url" | "document" | "video"
    url: Optional[str] = None,
) -> NormalizedFeatureObject:
    log = get_run_logger()
    log.info(f"[preprocess] source={source_ref!r}  type={input_type}")
    t0 = time.perf_counter()

    input_type = input_type.lower()

    if input_type == "image":
        if file_bytes is None:
            raise ValueError("file_bytes required for image input")
        nfo = preprocess_image(file_bytes, source_ref=source_ref)

    elif input_type == "url":
        target_url = url or source_ref
        nfo = await preprocess_url(target_url)

    elif input_type == "document":
        if file_bytes is None:
            raise ValueError("file_bytes required for document input")
        nfo = preprocess_document(file_bytes, source_ref=source_ref)

    elif input_type == "video":
        if file_bytes is None:
            raise ValueError("file_bytes required for video input")
        nfo = preprocess_video(file_bytes, source_ref=source_ref)

    else:
        raise ValueError(f"Unsupported input_type: {input_type!r}")

    nfo = enrich(nfo)
    elapsed = time.perf_counter() - t0

    log.info(
        f"[preprocess] done in {elapsed:.2f}s  "
        f"quality_passed={nfo.quality_passed}  "
        f"reason={nfo.quality_reason!r}"
    )
    return nfo


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Individual agent tasks  (all @task, all retried)
# ══════════════════════════════════════════════════════════════════════════════

@task(name="agent_claim_extract", retries=2, retry_delay_seconds=5)
async def claim_extract_task(nfo: NormalizedFeatureObject) -> ClaimExtractionResult:
    log = get_run_logger()
    log.info("[agent] claim_extract starting")
    extractor = ClaimExtractor(provider="openai_compat")   # swap to "anthropic" if needed
    text = nfo.text or ""
    result = await extractor.extract(text, source_type=nfo.input_type.value)
    log.info(f"[agent] claim_extract  total_claims={result.total_claims}  high_risk={result.high_risk_claims}")
    return result


@task(name="agent_claim_verify", retries=2, retry_delay_seconds=5)
async def claim_verify_task(
    nfo: NormalizedFeatureObject,
    extraction_result: ClaimExtractionResult,
) -> ClaimVerifyResult:
    log = get_run_logger()
    log.info("[agent] claim_verify starting")
    vs = VectorStore()
    extractor = ClaimExtractor(provider="openai_compat")
    rag = RAGAgent(vector_store=vs, claim_extractor=extractor)
    result = await rag.run(nfo)
    log.info(
        f"[agent] claim_verify  support={result.overall_support_score:.2f}  "
        f"contradiction={result.overall_contradiction_score:.2f}"
    )
    return result


@task(name="agent_source_cred", retries=2, retry_delay_seconds=5)
async def source_cred_task(nfo: NormalizedFeatureObject) -> SourceCredibilityResult:
    log = get_run_logger()
    log.info("[agent] source_cred starting")
    agent = SourceCredibilityAgent()
    result = await agent.run(nfo)
    log.info(f"[agent] source_cred  score={result.overall_score:.2f}  flags={result.red_flags}")
    return result


@task(name="agent_image_forensics", retries=2, retry_delay_seconds=5)
def image_forensics_task(
    nfo: NormalizedFeatureObject,
    file_bytes: Optional[bytes],
) -> Optional[dict]:
    """Run image forensics only when input_type is IMAGE."""
    log = get_run_logger()
    if nfo.input_type != InputType.IMAGE or file_bytes is None:
        log.info("[agent] image_forensics skipped (not an image)")
        return None
    log.info("[agent] image_forensics starting")
    result_nfo = image_forensics_process(
        file_bytes=file_bytes,
        filename=nfo.source_ref,
        mime_type="image/jpeg",
    )
    payload = {
        "anomalies_detected": result_nfo.anomalies_detected,
        "confidence_score": result_nfo.confidence_score,
        "reasoning_notes": result_nfo.reasoning_notes,
        "metadata": result_nfo.metadata,
    }
    log.info(
        f"[agent] image_forensics  anomalies={len(result_nfo.anomalies_detected)}  "
        f"confidence={result_nfo.confidence_score:.2f}"
    )
    return payload


@task(name="agent_video_forensics", retries=2, retry_delay_seconds=5)
def video_forensics_task(
    nfo: NormalizedFeatureObject,
    file_bytes: Optional[bytes],
) -> Optional[dict]:
    """Run video forensics only when input_type is VIDEO."""
    log = get_run_logger()
    if nfo.input_type != InputType.VIDEO or file_bytes is None:
        log.info("[agent] video_forensics skipped (not a video)")
        return None
    log.info("[agent] video_forensics starting")
    result_nfo = video_forensics_process(
        file_bytes=file_bytes,
        filename=nfo.source_ref,
        mime_type="video/mp4",
    )
    payload = {
        "anomalies_detected": result_nfo.anomalies_detected,
        "confidence_score": result_nfo.confidence_score,
        "reasoning_notes": result_nfo.reasoning_notes,
        "metadata": result_nfo.metadata,
    }
    log.info(
        f"[agent] video_forensics  anomalies={len(result_nfo.anomalies_detected)}  "
        f"confidence={result_nfo.confidence_score:.2f}"
    )
    return payload


@task(name="agent_context", retries=2, retry_delay_seconds=5)
async def context_task(
    nfo: NormalizedFeatureObject,
    extraction_result: ClaimExtractionResult,
) -> ContextAgentResult:
    log = get_run_logger()
    log.info("[agent] context starting")
    agent = ContextAgent(use_mock=True)   # flip use_mock=False for production
    result = await agent.run(nfo, extraction_result.claims)
    log.info(
        f"[agent] context  consistency={result.overall_consistency_score:.2f}  "
        f"temporal={result.temporal_coherence_score:.2f}"
    )
    return result


@task(name="agent_network", retries=2, retry_delay_seconds=5)
def network_task(nfo: NormalizedFeatureObject) -> NetworkAnalysisResult:
    log = get_run_logger()
    log.info("[agent] network starting")
    url = ""
    if nfo.url_data and nfo.url_data.final_url:
        url = nfo.url_data.final_url
    result = analyse_network(
        source_type=nfo.input_type.value,
        url=url,
        extracted_text=nfo.text,
        metadata={"domain_age_days": nfo.url_data.domain_info.age_days} if nfo.url_data else None,
    )
    log.info(
        f"[agent] network  bot_prob={result.bot_probability:.2f}  "
        f"risk={result.network_risk_level}"
    )
    return result


@task(name="agent_linguistic", retries=2, retry_delay_seconds=5)
def linguistic_task(nfo: NormalizedFeatureObject) -> LinguisticAnalysisResult:
    log = get_run_logger()
    log.info("[agent] linguistic starting")
    title = ""
    if nfo.url_data and nfo.url_data.meta and nfo.url_data.meta.title:
        title = nfo.url_data.meta.title
    result = analyse_linguistics(
        extracted_text=nfo.text,
        title=title,
        source_type=nfo.input_type.value,
    )
    log.info(
        f"[agent] linguistic  clickbait={result.clickbait_score:.2f}  "
        f"ai_gen={result.ai_generated_score:.2f}  risk={result.linguistic_risk_level}"
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Evidence fusion task
# ══════════════════════════════════════════════════════════════════════════════

@task(name="fuse_evidence", retries=1, retry_delay_seconds=3)
def fuse_evidence_task(
    nfo:                NormalizedFeatureObject,
    claim_extraction:   ClaimExtractionResult,
    claim_verification: ClaimVerifyResult,
    source_cred:        SourceCredibilityResult,
    image_forensics:    Optional[dict],
    video_forensics:    Optional[dict],
    context:            ContextAgentResult,
    network:            NetworkAnalysisResult,
    linguistic:         LinguisticAnalysisResult,
) -> FusionResult:
    log = get_run_logger()
    log.info("[fusion] aggregating agent results")
    result = fuse_evidence(
        nfo=nfo,
        claim_extraction=claim_extraction,
        claim_verification=claim_verification,
        source_cred=source_cred,
        image_forensics=image_forensics,
        video_forensics=video_forensics,
        context=context,
        network=network,
        linguistic=linguistic,
    )
    log.info(
        f"[fusion] risk_score={result.risk_score:.3f}  "
        f"risk_band={result.risk_band}  "
        f"confidence={result.meta_confidence:.3f}"
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Decision task
# ══════════════════════════════════════════════════════════════════════════════

@task(name="decide", retries=1, retry_delay_seconds=2)
def decide_task(fusion: FusionResult) -> PipelineResult:
    log = get_run_logger()
    log.info("[decision] running decision engine")
    engine = DecisionEngine()
    result = engine.decide(fusion)
    log.info(
        f"[decision] action={result.action}  "
        f"label={result.label}  "
        f"requires_human_review={result.requires_human_review}"
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL FLOW
# ══════════════════════════════════════════════════════════════════════════════

@flow(
    name="analyse_content",
    description=(
        "Full TruthGuard misinformation analysis pipeline: "
        "preprocessing → 8 parallel agents → evidence fusion → decision."
    ),
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
)
async def analyse_content(
    source_ref: str,
    input_type: str,                      # "image" | "url" | "document" | "video"
    file_bytes: Optional[bytes] = None,   # required for image / document / video
    url: Optional[str] = None,            # required for URL input
) -> PipelineResult:
    """
    Master orchestration flow.

    Parameters
    ----------
    source_ref : str
        Human-readable identifier (filename, URL, etc.).
    input_type : str
        One of "image", "url", "document", "video".
    file_bytes : bytes | None
        Raw file content (required for file-based inputs).
    url : str | None
        URL to analyse (required when input_type="url").

    Returns
    -------
    PipelineResult
        Final verdict with action, label, explanation, and full audit trail.
    """
    log = get_run_logger()
    log.info(f"╔══ analyse_content  source={source_ref!r}  type={input_type} ══╗")
    t_start = time.perf_counter()

    # ── 1. Preprocessing ──────────────────────────────────────────────────────
    # In Prefect v3, use .submit().result() — never await .result()
    nfo = preprocess_task.submit(
        file_bytes=file_bytes,
        source_ref=source_ref,
        input_type=input_type,
        url=url,
    ).result()

    if not nfo.quality_passed:
        log.warning(f"Quality gate rejected input: {nfo.quality_reason}")
        # Return a fast-path result instead of running all agents
        return PipelineResult(
            action="auto-block",
            label="QUALITY_GATE_FAIL",
            risk_score=1.0,
            risk_band="CRITICAL",
            confidence=1.0,
            explanation=f"Input rejected by quality gate: {nfo.quality_reason}",
            requires_human_review=False,
            audit_trail={"quality_reason": nfo.quality_reason},
        )

    # ── 2. Claim extraction first (others may depend on claims list) ──────────
    # In Prefect v3, .result() is synchronous — never await it.
    extraction_future = claim_extract_task.submit(nfo)
    extraction: ClaimExtractionResult = extraction_future.result()

    # ── 3. Parallel agent committee ───────────────────────────────────────────
    # Submit all tasks — Prefect's ConcurrentTaskRunner runs them in parallel.
    source_future  = source_cred_task.submit(nfo)
    network_future = network_task.submit(nfo)
    ling_future    = linguistic_task.submit(nfo)
    img_future     = image_forensics_task.submit(nfo, file_bytes)
    vid_future     = video_forensics_task.submit(nfo, file_bytes)

    # Tasks that also need the extracted claims
    verify_future  = claim_verify_task.submit(nfo, extraction)
    context_future = context_task.submit(nfo, extraction)

    # Resolve all futures synchronously (Prefect v3 — .result() blocks until done)
    source_cred     = source_future.result()
    network         = network_future.result()
    linguistic      = ling_future.result()
    image_forensics = img_future.result()
    video_forensics = vid_future.result()
    claim_verify    = verify_future.result()
    context         = context_future.result()

    # ── 4. Evidence fusion ────────────────────────────────────────────────────
    fusion = fuse_evidence_task(
        nfo=nfo,
        claim_extraction=extraction,
        claim_verification=claim_verify,
        source_cred=source_cred,
        image_forensics=image_forensics,
        video_forensics=video_forensics,
        context=context,
        network=network,
        linguistic=linguistic,
    )

    # ── 5. Decision engine ────────────────────────────────────────────────────
    final = decide_task(fusion)

    elapsed = time.perf_counter() - t_start
    log.info(
        f"╚══ DONE in {elapsed:.2f}s  "
        f"action={final.action}  label={final.label}  "
        f"risk={final.risk_score:.3f} ══╝"
    )
    return final


# ══════════════════════════════════════════════════════════════════════════════
# CLI helper — run a single file directly: python orchestrator.py <path>
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python orchestrator.py <input_type> <path_or_url>")
        print("  input_type: image | url | document | video")
        sys.exit(1)

    _type = sys.argv[1]
    _ref  = sys.argv[2]
    _bytes: Optional[bytes] = None
    _url:   Optional[str]   = None

    if _type == "url":
        _url = _ref
    else:
        with open(_ref, "rb") as fh:
            _bytes = fh.read()

    result = asyncio.run(
        analyse_content(
            source_ref=_ref,
            input_type=_type,
            file_bytes=_bytes,
            url=_url,
        )
    )

    print("\n" + "═" * 60)
    print(f"  ACTION : {result.action}")
    print(f"  LABEL  : {result.label}")
    print(f"  RISK   : {result.risk_score:.3f}  ({result.risk_band})")
    print(f"  CONF   : {result.confidence:.3f}")
    print(f"  HUMAN  : {result.requires_human_review}")
    print(f"  EXPLAIN: {result.explanation}")
    print("═" * 60)