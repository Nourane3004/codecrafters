"""
evidence_fusion.py
==================
Evidence Fusion + Risk Scoring — TruthGuard / MENACRAFT
=========================================================
Implements the "Evidence fusion + risk scoring" box from the architecture:

  ┌─────────────────────────────────────────────────────────┐
  │  Evidence fusion + risk scoring                         │
  │  Weighted ensemble · Bayesian inference · Meta-model    │
  └─────────────────────────────────────────────────────────┘
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Decision engine                                        │
  │  auto-allow │ flag for review │ auto-block              │
  └─────────────────────────────────────────────────────────┘

Three-stage risk scoring
─────────────────────────
  Stage 1 – Weighted ensemble
      Each agent contributes a normalised risk score (0-1).
      Scores are combined via a weighted average whose weights
      are tuned for the MENACRAFT threat model.

  Stage 2 – Bayesian inference
      A simple log-odds accumulator updates a prior (0.5 = unknown)
      using each agent's evidence as a likelihood ratio.
      This lets strong single-agent signals override a weak ensemble.

  Stage 3 – Meta-model combiner
      The ensemble score and the Bayesian posterior are blended
      with a learned α weight (default 0.6 ensemble / 0.4 Bayesian).
      The result is the final risk_score ∈ [0, 1].

Decision engine thresholds
──────────────────────────
  risk_score < 0.25  →  auto-allow     (GREEN)
  risk_score < 0.55  →  flag-review    (AMBER)
  risk_score < 0.80  →  flag-review    (ORANGE)
  risk_score ≥ 0.80  →  auto-block     (RED)

  Confidence override: if meta_confidence < 0.40 the decision is
  always escalated to human review regardless of risk band.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from Preprocessing.app.models.feature_object import NormalizedFeatureObject, InputType
from Agents.claim_extractor   import ClaimExtractionResult
from Agents.claim_verifier    import ClaimVerifyResult
from Agents.context_agent     import ContextAgentResult
from Agents.network_agent     import NetworkAnalysisResult
from Agents.linguistic_agent  import LinguisticAnalysisResult
from Agents.source_cred_agent import SourceCredibilityResult

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Output schemas
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentSignal:
    """Normalised signal from a single agent."""
    agent_name:   str
    risk_score:   float          # 0 (benign) → 1 (highly suspicious)
    confidence:   float          # 0 → 1, how reliable is this signal
    weight:       float          # relative weight in the ensemble
    red_flags:    list[str] = field(default_factory=list)
    reasoning:    str = ""


@dataclass
class FusionResult:
    """Full output of the fusion layer — consumed by DecisionEngine."""
    # ── final scores ──
    risk_score:       float          # 0-1, final fused risk
    risk_band:        str            # GREEN | AMBER | ORANGE | RED
    meta_confidence:  float          # 0-1, reliability of the risk_score estimate

    # ── intermediate stages (for explainability & audit) ──
    ensemble_score:   float          # Stage 1
    bayesian_score:   float          # Stage 2
    alpha:            float          # Stage 3 blend weight

    # ── per-agent signals (full audit trail) ──
    signals:          list[AgentSignal] = field(default_factory=list)

    # ── aggregated flags ──
    red_flags:        list[str] = field(default_factory=list)
    key_reasoning:    list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Final verdict returned by the orchestrator to the caller."""
    action:               str          # "auto-allow" | "flag-review" | "auto-block"
    label:                str          # human-readable risk label
    risk_score:           float
    risk_band:            str
    confidence:           float
    explanation:          str
    requires_human_review: bool
    audit_trail:          dict = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Agent weight configuration
# ══════════════════════════════════════════════════════════════════════════════
# Weights reflect the threat model priority for MENACRAFT:
# - Claim verifiability and source credibility are the most trusted signals.
# - Forensic agents are highly specific when they fire.
# - Linguistic and network signals are useful but noisier.

_AGENT_WEIGHTS: dict[str, float] = {
    "claim_verify":      0.22,
    "source_cred":       0.18,
    "image_forensics":   0.14,
    "video_forensics":   0.14,
    "context":           0.12,
    "linguistic":        0.10,
    "network":           0.10,
    "claim_extract":     0.00,   # informational only — no direct risk score
}

# Bayesian prior — start neutral
_PRIOR_LOG_ODDS: float = 0.0    # log-odds(0.5) = 0

# Meta-model blend weight: α·ensemble + (1-α)·bayesian
_ALPHA: float = 0.60


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Per-agent signal extraction helpers
# ══════════════════════════════════════════════════════════════════════════════

def _signal_from_claim_verify(r: ClaimVerifyResult) -> AgentSignal:
    """
    High contradiction → high risk.
    Low support + neutral → moderate risk.
    """
    # Contradiction dominates
    raw = r.overall_contradiction_score * 0.7 + (1.0 - r.overall_support_score) * 0.3
    risk = min(1.0, max(0.0, raw))

    # Confidence: number of verified claims gives signal quality
    verified_count = len(r.verified_claims) if r.verified_claims else 0
    conf = min(1.0, 0.3 + verified_count * 0.07)

    flags = [f"claim_verdict:{vc.verdict}:{vc.claim_text[:60]}"
             for vc in (r.verified_claims or [])
             if vc.verdict in ("CONTRADICTED", "ERROR")][:5]

    return AgentSignal(
        agent_name="claim_verify",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["claim_verify"],
        red_flags=flags,
        reasoning=(
            f"support={r.overall_support_score:.2f}  "
            f"contradiction={r.overall_contradiction_score:.2f}  "
            f"verified={verified_count}"
        ),
    )


def _signal_from_source_cred(r: SourceCredibilityResult) -> AgentSignal:
    """
    Low source credibility score → high risk.
    """
    risk = 1.0 - r.overall_score
    conf = 0.75 if r.domain else 0.35

    return AgentSignal(
        agent_name="source_cred",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["source_cred"],
        red_flags=r.red_flags,
        reasoning=(
            f"domain={r.domain!r}  score={r.overall_score:.2f}  "
            f"fake={r.is_known_fake_news}  satire={r.is_known_satire}"
        ),
    )


def _signal_from_image_forensics(r: Optional[dict]) -> AgentSignal:
    """
    Number and severity of forensic anomalies → risk.
    Skipped (None) when input is not an image.
    """
    if r is None:
        return AgentSignal(
            agent_name="image_forensics",
            risk_score=0.0,
            confidence=0.0,       # 0 confidence = no contribution to ensemble
            weight=_AGENT_WEIGHTS["image_forensics"],
        )
    anomalies = r.get("anomalies_detected", [])
    conf_score = r.get("confidence_score", 0.85)
    # Agent's confidence_score already penalises for anomalies; invert
    risk = 1.0 - conf_score
    conf = 0.80 if anomalies else 0.60

    return AgentSignal(
        agent_name="image_forensics",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["image_forensics"],
        red_flags=anomalies[:8],
        reasoning=f"anomalies={len(anomalies)}  agent_confidence={conf_score:.2f}",
    )


def _signal_from_video_forensics(r: Optional[dict]) -> AgentSignal:
    """Mirrors image forensics logic for video."""
    if r is None:
        return AgentSignal(
            agent_name="video_forensics",
            risk_score=0.0,
            confidence=0.0,
            weight=_AGENT_WEIGHTS["video_forensics"],
        )
    anomalies = r.get("anomalies_detected", [])
    conf_score = r.get("confidence_score", 0.85)
    risk = 1.0 - conf_score
    conf = 0.80 if anomalies else 0.60

    return AgentSignal(
        agent_name="video_forensics",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["video_forensics"],
        red_flags=anomalies[:8],
        reasoning=f"anomalies={len(anomalies)}  agent_confidence={conf_score:.2f}",
    )


def _signal_from_context(r: ContextAgentResult) -> AgentSignal:
    """
    Low consistency or temporal incoherence → risk.
    """
    risk = 1.0 - (r.overall_consistency_score * 0.6 + r.temporal_coherence_score * 0.4)
    risk = min(1.0, max(0.0, risk))
    conf = min(1.0, 0.40 + len(r.checks) * 0.05) if r.checks else 0.30

    flags = [
        f"temporal_issue:{ti}"
        for c in (r.checks or [])
        for ti in c.temporal_issues
    ][:6]

    return AgentSignal(
        agent_name="context",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["context"],
        red_flags=flags,
        reasoning=(
            f"consistency={r.overall_consistency_score:.2f}  "
            f"temporal={r.temporal_coherence_score:.2f}  "
            f"checks={len(r.checks)}"
        ),
    )


def _signal_from_network(r: NetworkAnalysisResult) -> AgentSignal:
    """
    Bot probability + network risk → risk score.
    Uses the agent's own confidence_contribution.
    """
    risk = r.bot_probability
    conf = r.confidence_contribution if r.confidence_contribution > 0 else 0.40

    return AgentSignal(
        agent_name="network",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["network"],
        red_flags=r.red_flags,
        reasoning=(
            f"bot_prob={r.bot_probability:.2f}  "
            f"net_risk={r.network_risk_level}  "
            f"propagation={r.propagation_pattern}"
        ),
    )


def _signal_from_linguistic(r: LinguisticAnalysisResult) -> AgentSignal:
    """
    Clickbait + AI-generated text → risk signal.
    """
    if not r.success:
        return AgentSignal(
            agent_name="linguistic",
            risk_score=0.0,
            confidence=0.0,
            weight=_AGENT_WEIGHTS["linguistic"],
        )
    # Combine both sub-scores; clickbait is slightly weighted more
    risk = min(1.0, r.clickbait_score * 0.55 + r.ai_generated_score * 0.45)
    conf = r.confidence_contribution if r.confidence_contribution > 0 else 0.40

    return AgentSignal(
        agent_name="linguistic",
        risk_score=risk,
        confidence=conf,
        weight=_AGENT_WEIGHTS["linguistic"],
        red_flags=r.red_flags,
        reasoning=(
            f"clickbait={r.clickbait_score:.2f}  "
            f"ai_gen={r.ai_generated_score:.2f}  "
            f"ling_risk={r.linguistic_risk_level}"
        ),
    )


def _signal_from_claim_extract(r: ClaimExtractionResult) -> AgentSignal:
    """
    Informational signal: high-risk claims raise the prior slightly.
    Weight = 0 → no direct ensemble contribution; used only in Bayesian stage.
    """
    risk = min(1.0, r.high_risk_claims * 0.08 + (0.0 if r.success else 0.3))
    return AgentSignal(
        agent_name="claim_extract",
        risk_score=risk,
        confidence=r.confidence_contribution,
        weight=_AGENT_WEIGHTS["claim_extract"],
        reasoning=f"total_claims={r.total_claims}  high_risk={r.high_risk_claims}",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Weighted ensemble
# ══════════════════════════════════════════════════════════════════════════════

def _weighted_ensemble(signals: list[AgentSignal]) -> tuple[float, float]:
    """
    Compute the weighted average risk score and the aggregate confidence.

    Signals with confidence=0 are excluded (inactive agents, e.g., video
    forensics when input is an image).

    Returns
    -------
    ensemble_score : float  (0-1)
    aggregate_conf : float  (0-1)
    """
    total_weight = 0.0
    weighted_sum = 0.0
    conf_sum = 0.0
    active = 0

    for sig in signals:
        if sig.confidence <= 0 or sig.weight <= 0:
            continue
        # Effective weight = declared weight × confidence
        eff_w = sig.weight * sig.confidence
        weighted_sum += sig.risk_score * eff_w
        total_weight  += eff_w
        conf_sum      += sig.confidence
        active        += 1

    if total_weight == 0 or active == 0:
        return 0.5, 0.0   # no information → maximum uncertainty

    ensemble_score = weighted_sum / total_weight
    aggregate_conf = conf_sum / active

    return round(ensemble_score, 4), round(aggregate_conf, 4)


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Bayesian log-odds accumulator
# ══════════════════════════════════════════════════════════════════════════════

def _log_odds(p: float) -> float:
    """Convert probability to log-odds (clamped to avoid ±∞)."""
    p = max(1e-6, min(1 - 1e-6, p))
    return math.log(p / (1 - p))


def _from_log_odds(lo: float) -> float:
    """Convert log-odds back to probability."""
    return 1.0 / (1.0 + math.exp(-lo))


def _bayesian_update(signals: list[AgentSignal]) -> float:
    """
    Sequential Bayesian update starting from a neutral prior (p=0.5).

    Each active agent contributes a likelihood ratio:
      LR = P(evidence | misinformation) / P(evidence | authentic)

    We approximate LR from the agent's risk_score:
      if risk_score > 0.5  →  evidence supports misinformation
      if risk_score < 0.5  →  evidence supports authentic

    The update is scaled by the agent's confidence.

    Returns the posterior probability of misinformation ∈ [0, 1].
    """
    log_odds = _PRIOR_LOG_ODDS

    for sig in signals:
        if sig.confidence <= 0:
            continue
        if sig.risk_score > 0.5:
            # Likelihood ratio > 1 (evidence supports misinfo)
            lr = 1.0 + (sig.risk_score - 0.5) * 2.0 * sig.confidence
        elif sig.risk_score < 0.5:
            # Likelihood ratio < 1 (evidence supports authentic)
            lr = 1.0 - (0.5 - sig.risk_score) * 2.0 * sig.confidence
        else:
            lr = 1.0  # neutral

        # Clamp LR to reasonable range [0.05, 20]
        lr = max(0.05, min(20.0, lr))
        log_odds += math.log(lr)

    return round(_from_log_odds(log_odds), 4)


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3 — Meta-model combiner
# ══════════════════════════════════════════════════════════════════════════════

def _meta_combine(ensemble: float, bayesian: float, alpha: float = _ALPHA) -> float:
    """
    Blend Stage 1 and Stage 2 outputs.

    risk_score = α · ensemble + (1 - α) · bayesian

    The Bayesian score acts as a regulariser: when many agents are neutral
    but one agent fires strongly, the Bayesian stage pulls the risk up/down
    faster than the weighted average alone.
    """
    return round(alpha * ensemble + (1.0 - alpha) * bayesian, 4)


# ══════════════════════════════════════════════════════════════════════════════
# Risk band classification
# ══════════════════════════════════════════════════════════════════════════════

def _risk_band(score: float) -> str:
    if score >= 0.80:
        return "RED"
    if score >= 0.55:
        return "ORANGE"
    if score >= 0.25:
        return "AMBER"
    return "GREEN"


# ══════════════════════════════════════════════════════════════════════════════
# Public API — fuse_evidence()
# ══════════════════════════════════════════════════════════════════════════════

def fuse_evidence(
    nfo:                NormalizedFeatureObject,
    claim_extraction:   ClaimExtractionResult,
    claim_verification: ClaimVerifyResult,
    source_cred:        SourceCredibilityResult,
    image_forensics:    Optional[dict],
    video_forensics:    Optional[dict],
    context:            ContextAgentResult,
    network:            NetworkAnalysisResult,
    linguistic:         LinguisticAnalysisResult,
    alpha:              float = _ALPHA,
) -> FusionResult:
    """
    Three-stage evidence fusion.

    Parameters
    ----------
    nfo                 : NormalizedFeatureObject from preprocessing
    claim_extraction    : output of ClaimExtractor
    claim_verification  : output of ClaimVerifier / RAGAgent
    source_cred         : output of SourceCredibilityAgent
    image_forensics     : dict from agent_image_forensics.process() or None
    video_forensics     : dict from agent_video_forensics.process() or None
    context             : output of ContextAgent
    network             : output of analyse_network()
    linguistic          : output of analyse_linguistics()
    alpha               : ensemble blend weight (default 0.60)

    Returns
    -------
    FusionResult
    """
    # ── Extract per-agent signals ──────────────────────────────────────────
    signals: list[AgentSignal] = [
        _signal_from_claim_extract(claim_extraction),
        _signal_from_claim_verify(claim_verification),
        _signal_from_source_cred(source_cred),
        _signal_from_image_forensics(image_forensics),
        _signal_from_video_forensics(video_forensics),
        _signal_from_context(context),
        _signal_from_network(network),
        _signal_from_linguistic(linguistic),
    ]

    logger.debug(
        "Agent signals: %s",
        {s.agent_name: f"risk={s.risk_score:.2f} conf={s.confidence:.2f}" for s in signals},
    )

    # ── Stage 1 : Weighted ensemble ────────────────────────────────────────
    ensemble_score, aggregate_conf = _weighted_ensemble(signals)

    # ── Stage 2 : Bayesian inference ───────────────────────────────────────
    bayesian_score = _bayesian_update(signals)

    # ── Stage 3 : Meta-model ──────────────────────────────────────────────
    risk_score = _meta_combine(ensemble_score, bayesian_score, alpha=alpha)

    # ── Aggregate flags & reasoning ────────────────────────────────────────
    all_flags: list[str] = []
    key_reasoning: list[str] = []

    for sig in signals:
        all_flags.extend(sig.red_flags)
        if sig.confidence > 0:
            key_reasoning.append(f"[{sig.agent_name}] {sig.reasoning}")

    # Deduplicate flags while preserving order
    seen: set[str] = set()
    dedup_flags: list[str] = []
    for f in all_flags:
        if f not in seen:
            dedup_flags.append(f)
            seen.add(f)

    return FusionResult(
        risk_score=risk_score,
        risk_band=_risk_band(risk_score),
        meta_confidence=aggregate_conf,
        ensemble_score=ensemble_score,
        bayesian_score=bayesian_score,
        alpha=alpha,
        signals=signals,
        red_flags=dedup_flags,
        key_reasoning=key_reasoning,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Decision engine
# ══════════════════════════════════════════════════════════════════════════════

# Decision thresholds
_THRESHOLD_ALLOW  = 0.25
_THRESHOLD_REVIEW = 0.80

# Minimum confidence for automated decisions
_MIN_AUTO_CONF = 0.40


class DecisionEngine:
    """
    Maps a FusionResult to a final action and human-readable verdict.

    Actions
    -------
    auto-allow      GREEN band, high confidence → content is likely authentic
    flag-review     AMBER / ORANGE band, or low confidence → human review
    auto-block      RED band, high confidence → content is likely misinformation
    """

    def decide(self, fusion: FusionResult) -> PipelineResult:
        score = fusion.risk_score
        conf  = fusion.meta_confidence
        band  = fusion.risk_band

        # Low confidence override → always escalate to human review
        if conf < _MIN_AUTO_CONF:
            return self._make_result(
                action="flag-review",
                label="LOW_CONFIDENCE",
                fusion=fusion,
                explanation=(
                    f"Insufficient signal confidence ({conf:.2f}) to make an automated decision. "
                    "Escalating to human review."
                ),
                requires_human_review=True,
            )

        if score < _THRESHOLD_ALLOW:
            return self._make_result(
                action="auto-allow",
                label="LIKELY_AUTHENTIC",
                fusion=fusion,
                explanation=(
                    f"Risk score {score:.3f} is below the allow threshold ({_THRESHOLD_ALLOW}). "
                    "Content appears authentic across all agent signals."
                ),
                requires_human_review=False,
            )

        if score >= _THRESHOLD_REVIEW:
            top_flags = fusion.red_flags[:5]
            return self._make_result(
                action="auto-block",
                label="LIKELY_MISINFORMATION",
                fusion=fusion,
                explanation=(
                    f"Risk score {score:.3f} exceeds the block threshold ({_THRESHOLD_REVIEW}). "
                    f"Key signals: {'; '.join(top_flags) or 'see audit trail'}."
                ),
                requires_human_review=False,
            )

        # AMBER or ORANGE → flag for human review
        return self._make_result(
            action="flag-review",
            label=f"UNCERTAIN_{band}",
            fusion=fusion,
            explanation=(
                f"Risk score {score:.3f} falls in the {band} review band. "
                "Content requires human verification before a final decision."
            ),
            requires_human_review=True,
        )

    @staticmethod
    def _make_result(
        action:               str,
        label:                str,
        fusion:               FusionResult,
        explanation:          str,
        requires_human_review: bool,
    ) -> PipelineResult:
        audit: dict = {
            "risk_score":     fusion.risk_score,
            "ensemble_score": fusion.ensemble_score,
            "bayesian_score": fusion.bayesian_score,
            "alpha":          fusion.alpha,
            "meta_confidence": fusion.meta_confidence,
            "risk_band":      fusion.risk_band,
            "red_flags":      fusion.red_flags,
            "key_reasoning":  fusion.key_reasoning,
            "per_agent": {
                sig.agent_name: {
                    "risk_score": sig.risk_score,
                    "confidence": sig.confidence,
                    "weight":     sig.weight,
                    "red_flags":  sig.red_flags,
                    "reasoning":  sig.reasoning,
                }
                for sig in fusion.signals
            },
        }

        return PipelineResult(
            action=action,
            label=label,
            risk_score=fusion.risk_score,
            risk_band=fusion.risk_band,
            confidence=fusion.meta_confidence,
            explanation=explanation,
            requires_human_review=requires_human_review,
            audit_trail=audit,
        )