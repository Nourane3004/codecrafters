"""
app/agents/linguistic_agent.py
───────────────────────────────────────────────────────────────────────────────
Linguistic Agent — Clickbait Detection · AI-Generated Text Detection
───────────────────────────────────────────────────────────────────────────────
Analyses the *linguistic* signals of a piece of content across two axes:

  1. Clickbait detection
       - Headline / title pattern matching (curiosity gap, listicle bait, etc.)
       - Sensationalism vocabulary scoring
       - Title–body coherence mismatch (promise vs. delivery)
       - Emotional manipulation intensity

  2. AI-generated text detection
       - Perplexity proxy (vocabulary diversity, burstiness)
       - Structural uniformity (sentence length variance, paragraph rhythm)
       - Stylometric fingerprints (hedge-phrase density, transition overuse)
       - Semantic flatness (low specificity, generic assertions)
       - Groq LLM self-reflection pass (LLM evaluating LLM)

Returns a LinguisticAnalysisResult — never raises; always degrades gracefully.

Integration note
────────────────
Wire into each processor after text extraction:

    from app.agents.linguistic_agent import analyse_linguistics
    ling_result = analyse_linguistics(
        extracted_text=extracted_text,
        title=title_or_headline,          # optional — empty string if absent
        source_type="document",
    )
    nfo.agent_results["linguistic_agent"] = ling_result.model_dump()
    # Blend confidence contribution into NFO score (same pattern as network_agent)
    nfo.confidence_score = (
        nfo.confidence_score * 0.70 + ling_result.confidence_contribution * 0.30
    )
    nfo.anomalies_detected += [f"[linguistic] {f}" for f in ling_result.red_flags]
    nfo.reasoning_notes += [f"[LinguisticAgent] {n}" for n in ling_result.reasoning_notes]
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── optional Groq import ───────────────────────────────────────────────────────
try:
    from groq import Groq  # type: ignore
    _groq_available = True
except ImportError:
    _groq_available = False

# ── constants ──────────────────────────────────────────────────────────────────

_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 1500
_TEXT_CHAR_LIMIT = 8000

# ────────────────────────────────────────────────────────────────────────────────
# CLICKBAIT SIGNAL BANKS
# ────────────────────────────────────────────────────────────────────────────────

# Curiosity-gap patterns ("what happened next", "you won't believe", etc.)
_CURIOSITY_GAP_PATTERNS = [
    r"\byou won'?t believe\b",
    r"\bwhat happened next\b",
    r"\bthe result(?:s)? (?:will|might) shock you\b",
    r"\bwhat (?:they|he|she|we) don'?t want you to know\b",
    r"\bthe truth (?:about|behind)\b",
    r"\bthis (?:one )?trick\b",
    r"\bdoctors hate (?:him|her|this)\b",
    r"\b(?:nobody|no one) is talking about\b",
    r"\bthe real reason\b",
    r"\bhere'?s why\b.*\bwon'?t\b",
    r"\bsecret(?:s)? (?:they|that)\b",
]

# Listicle / numeric bait titles
_LISTICLE_PATTERNS = [
    r"^\d+\s+(?:reasons|ways|things|facts|tips|tricks|secrets|signs|mistakes)\b",
    r"\btop\s+\d+\b",
    r"\b\d+\s+(?:amazing|shocking|mind-blowing|unbelievable|incredible)\b",
    r"\bthe\s+\d+\s+best\b",
    r"\bthings\s+(?:only|every)\b",
]

# Sensationalism lexicon — words inflating importance or urgency
_SENSATIONALISM_WORDS = {
    "shocking", "bombshell", "explosive", "outrageous", "stunning", "unbelievable",
    "incredible", "insane", "crazy", "breaking", "urgent", "alert", "warning",
    "destroy", "exposed", "busted", "crushed", "obliterated", "demolished",
    "slammed", "ripped", "torched", "annihilated", "devastating", "catastrophic",
    "epic", "massive", "huge", "enormous", "gigantic", "terrifying", "alarming",
    "heartbreaking", "mind-blowing", "jaw-dropping", "eye-opening", "game-changer",
    "revolutionary", "historic", "unprecedented", "exclusive", "must-see",
    "must-read", "viral", "trending",
}

# Emotional manipulation triggers
_EMOTIONAL_TRIGGERS = {
    "fear": ["threat", "danger", "risk", "terrifying", "deadly", "fatal", "kill",
             "attack", "invasion", "collapse", "crash", "disaster", "emergency"],
    "anger": ["outrage", "disgusting", "sickening", "shameful", "betrayal",
              "scandal", "corrupt", "lie", "fraud", "cheat", "steal", "abuse"],
    "hope": ["miracle", "cure", "solution", "finally", "breakthrough", "hope",
             "save", "rescue", "recover", "heal", "fix", "answer"],
    "envy": ["secret wealth", "hidden trick", "while you sleep", "passive income",
             "they don't tell you", "elite", "exclusive access"],
}

# ────────────────────────────────────────────────────────────────────────────────
# AI-GENERATED TEXT SIGNAL BANKS
# ────────────────────────────────────────────────────────────────────────────────

# Hedge/softener phrases heavily overused by LLMs
_AI_HEDGE_PHRASES = [
    r"\bit'?s (?:important|worth|crucial|essential) to (?:note|remember|consider)\b",
    r"\bin (?:today'?s|the modern|our current|this digital) (?:world|era|society|landscape|age)\b",
    r"\bit is (?:worth noting|important to note|crucial to understand)\b",
    r"\bmoreover[,\s]",
    r"\bfurthermore[,\s]",
    r"\badditionally[,\s]",
    r"\bin conclusion[,\s]",
    r"\bto summarize[,\s]",
    r"\bto sum up[,\s]",
    r"\bin summary[,\s]",
    r"\boverall[,\s]",
    r"\bultimately[,\s].*(?:important|clear|evident)\b",
    r"\bas (?:an AI|a language model)\b",
    r"\bi (?:don'?t|do not) have (?:personal|the ability|access)\b",
    r"\bfeel free to (?:ask|reach out|let me know)\b",
    r"\bhope (?:this|that) helps\b",
    r"\bI'?(?:m| am) here to help\b",
    r"\bcertainly[,!]\s",
    r"\babsolutely[,!]\s",
    r"\bof course[,!]\s",
    r"\bgreat (?:question|point|idea)[,!]",
]

_AI_HEDGE_RE = [re.compile(p, re.IGNORECASE) for p in _AI_HEDGE_PHRASES]

# Transition overuse — LLMs love these as structural scaffolding
_TRANSITION_WORDS = {
    "moreover", "furthermore", "additionally", "consequently", "therefore",
    "nonetheless", "nevertheless", "subsequently", "accordingly", "hence",
    "thus", "thereby", "wherein", "therein", "herein",
}

# Generic filler phrases — low-specificity assertions common in LLM text
_GENERIC_FILLER_PATTERNS = [
    r"\bplays? (?:a|an) (?:crucial|important|vital|key|significant|major) role\b",
    r"\bhas become (?:increasingly|more) (?:important|relevant|common|prevalent)\b",
    r"\bin (?:recent|today'?s|modern) times?\b",
    r"\bthroughout history\b",
    r"\bsince (?:the dawn of|time immemorial)\b",
    r"\bthe (?:world|society|community|industry) (?:as we know it)\b",
    r"\bwhen it comes to\b",
    r"\bone of the most\b",
    r"\bthe fact (?:of the matter|that)\b",
    r"\bit (?:goes without saying|is no secret)\b",
    r"\bneedless to say\b",
    r"\bfor all intents and purposes\b",
    r"\bat the end of the day\b",
    r"\bthe bottom line is\b",
]

_GENERIC_FILLER_RE = [re.compile(p, re.IGNORECASE) for p in _GENERIC_FILLER_PATTERNS]

# ── LLM system prompt ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a forensic linguistic analyst for a misinformation detection system.
You specialise in two tasks:

1. CLICKBAIT DETECTION: identifying manipulative headlines, emotional exploitation,
   curiosity gaps, misleading promises, and sensationalism.

2. AI-GENERATED TEXT DETECTION: identifying text likely written by a large language
   model via stylometric analysis — uniform sentence length, hedge phrase overuse,
   structural templates, low lexical specificity, and absence of genuine human voice.

You will receive:
- source_type: the kind of content
- title: the headline or title (may be empty)
- extracted_text: the content body (may be truncated)
- heuristic_signals: pre-computed linguistic signals as JSON

Your task: synthesise all signals and return a JSON verdict with EXACTLY this structure
(no markdown fences, no extra keys):

{
  "clickbait_score": <float 0.0–1.0>,
  "ai_generated_score": <float 0.0–1.0>,
  "linguistic_risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "dominant_signals": ["<signal1>", "<signal2>", ...],
  "confidence": <float 0.0–1.0>,
  "reasoning": "<one concise paragraph explaining both verdicts>",
  "red_flags": ["<flag1>", "<flag2>", ...]
}

Scoring guidance:
- clickbait_score: 0.0 = clearly informational, 1.0 = pure engagement bait
- ai_generated_score: 0.0 = clearly human-written, 1.0 = almost certainly AI-generated
- linguistic_risk_level: aggregate risk (CRITICAL if either score > 0.80)
- dominant_signals: the 2–5 most decisive signals you used
- red_flags: specific anomalies (e.g. "curiosity gap headline", "LLM hedge phrase density 0.4")
- confidence: your certainty given the available text

Important: short texts (<100 words) reduce your confidence — reflect this.
Never speculate beyond available evidence."""


# ── output schema ──────────────────────────────────────────────────────────────

@dataclass
class LinguisticAnalysisResult:
    success: bool
    # Scores
    clickbait_score: float = 0.0        # 0.0–1.0
    ai_generated_score: float = 0.0     # 0.0–1.0
    linguistic_risk_level: str = "UNKNOWN"  # LOW|MEDIUM|HIGH|CRITICAL
    # Evidence
    dominant_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    # Internal
    heuristic_signals: dict = field(default_factory=dict)
    confidence_contribution: float = 0.0   # fed into quality_gate.py
    analysis_method: str = "heuristic"     # "llm" | "heuristic" | "failed"
    reasoning_notes: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def model_dump(self) -> dict:
        return {
            "success": self.success,
            "clickbait_score": self.clickbait_score,
            "ai_generated_score": self.ai_generated_score,
            "linguistic_risk_level": self.linguistic_risk_level,
            "dominant_signals": self.dominant_signals,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "red_flags": self.red_flags,
            "heuristic_signals": self.heuristic_signals,
            "confidence_contribution": self.confidence_contribution,
            "analysis_method": self.analysis_method,
            "reasoning_notes": self.reasoning_notes,
            "error": self.error,
        }


# ────────────────────────────────────────────────────────────────────────────────
# HEURISTIC ENGINE — CLICKBAIT
# ────────────────────────────────────────────────────────────────────────────────

def _analyse_clickbait(title: str, body: str) -> dict:
    """
    Compute clickbait signals from the title and body text.
    Returns a dict of scored features.
    """
    signals: dict = {
        "has_title": bool(title),
        "curiosity_gap_hits": 0,
        "listicle_hits": 0,
        "sensationalism_density": 0.0,
        "emotional_trigger_counts": {},
        "title_body_mismatch_hint": False,
        "caps_ratio_title": 0.0,
        "question_clickbait": False,
    }

    full_text = f"{title} {body}".strip()
    if not full_text:
        return signals

    # ── curiosity gap patterns ─────────────────────────────────────────────────
    curiosity_re = [re.compile(p, re.IGNORECASE) for p in _CURIOSITY_GAP_PATTERNS]
    signals["curiosity_gap_hits"] = sum(
        1 for r in curiosity_re if r.search(full_text)
    )

    # ── listicle patterns (title-focused) ─────────────────────────────────────
    listicle_re = [re.compile(p, re.IGNORECASE) for p in _LISTICLE_PATTERNS]
    check_text = title if title else full_text[:200]
    signals["listicle_hits"] = sum(
        1 for r in listicle_re if r.search(check_text)
    )

    # ── sensationalism word density ────────────────────────────────────────────
    words = re.findall(r"\b[a-z]+\b", full_text.lower())
    if words:
        sens_count = sum(1 for w in words if w in _SENSATIONALISM_WORDS)
        signals["sensationalism_density"] = round(sens_count / len(words), 4)

    # ── emotional trigger counts ───────────────────────────────────────────────
    for emotion, triggers in _EMOTIONAL_TRIGGERS.items():
        count = sum(1 for t in triggers if t.lower() in full_text.lower())
        signals["emotional_trigger_counts"][emotion] = count

    # ── all-caps ratio in title ────────────────────────────────────────────────
    if title:
        alpha_chars = [c for c in title if c.isalpha()]
        if alpha_chars:
            signals["caps_ratio_title"] = round(
                sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars), 3
            )

    # ── question-bait: title ends with "?" after emotional word ───────────────
    if title and title.strip().endswith("?"):
        question_words = ["really", "actually", "true", "believe", "know", "secret"]
        if any(w in title.lower() for w in question_words):
            signals["question_clickbait"] = True

    # ── title-body mismatch hint ───────────────────────────────────────────────
    # If title has a named entity not in body, it may be misleading
    if title and body:
        title_caps = set(re.findall(r"\b[A-Z][a-z]{2,}\b", title))
        body_caps = set(re.findall(r"\b[A-Z][a-z]{2,}\b", body))
        common_words = {"The", "This", "That", "When", "How", "Why", "What", "Here"}
        title_entities = title_caps - common_words
        if title_entities and not title_entities.intersection(body_caps):
            signals["title_body_mismatch_hint"] = True

    return signals


def _score_clickbait(signals: dict) -> tuple[float, list[str], list[str]]:
    """Convert clickbait signal dict into a 0–1 score."""
    score = 0.0
    key_signals: list[str] = []
    red_flags: list[str] = []

    if signals["curiosity_gap_hits"] >= 1:
        score += 0.30 * min(signals["curiosity_gap_hits"], 2)
        key_signals.append(f"curiosity_gap_patterns={signals['curiosity_gap_hits']}")
        red_flags.append(f"Curiosity-gap phrasing detected ({signals['curiosity_gap_hits']} matches)")

    if signals["listicle_hits"] >= 1:
        score += 0.15
        key_signals.append("listicle_headline")

    sens = signals["sensationalism_density"]
    if sens > 0.01:
        score += min(sens * 15, 0.25)
        key_signals.append(f"sensationalism_density={sens:.3f}")
        if sens > 0.03:
            red_flags.append(f"High sensationalism word density: {sens:.3f}")

    # Sum emotional triggers
    total_triggers = sum(signals["emotional_trigger_counts"].values())
    dominant_emotion = max(
        signals["emotional_trigger_counts"],
        key=lambda k: signals["emotional_trigger_counts"][k],
        default=None,
    )
    if total_triggers >= 2:
        score += min(total_triggers * 0.04, 0.20)
        if dominant_emotion and signals["emotional_trigger_counts"][dominant_emotion] >= 2:
            key_signals.append(f"dominant_emotion={dominant_emotion}")
            red_flags.append(f"Emotional manipulation ({dominant_emotion}) — {signals['emotional_trigger_counts'][dominant_emotion]} triggers")

    if signals["caps_ratio_title"] > 0.50:
        score += 0.10
        red_flags.append(f"Excessive caps in title: {signals['caps_ratio_title']:.0%}")

    if signals["question_clickbait"]:
        score += 0.10
        key_signals.append("question_bait_title")

    if signals["title_body_mismatch_hint"]:
        score += 0.15
        key_signals.append("title_body_entity_mismatch")
        red_flags.append("Title contains named entities absent from body — possible misleading headline")

    return round(min(score, 1.0), 3), key_signals, red_flags


# ────────────────────────────────────────────────────────────────────────────────
# HEURISTIC ENGINE — AI-GENERATED TEXT
# ────────────────────────────────────────────────────────────────────────────────

def _analyse_ai_text(text: str) -> dict:
    """
    Compute AI-generation signals from body text.
    Returns a dict of scored features.
    """
    signals: dict = {
        "word_count": 0,
        "sentence_count": 0,
        "avg_sentence_length": 0.0,
        "sentence_length_variance": 0.0,   # low variance = AI
        "type_token_ratio": 0.0,           # low TTR = repetitive = AI hint
        "hedge_phrase_hits": 0,
        "hedge_phrase_density": 0.0,
        "transition_word_density": 0.0,
        "generic_filler_hits": 0,
        "paragraph_length_variance": 0.0,  # low = AI
        "burstiness_score": 0.0,           # low = AI (uniform sentence length)
    }

    if not text or len(text.strip()) < 20:
        return signals

    # ── tokenise ──────────────────────────────────────────────────────────────
    words = re.findall(r"\b[a-z']+\b", text.lower())
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    signals["word_count"] = len(words)
    signals["sentence_count"] = len(sentences)

    if not words:
        return signals

    # ── sentence length stats ─────────────────────────────────────────────────
    sent_lengths = [len(s.split()) for s in sentences if s.split()]
    if sent_lengths:
        avg = sum(sent_lengths) / len(sent_lengths)
        signals["avg_sentence_length"] = round(avg, 2)
        if len(sent_lengths) > 1:
            variance = sum((l - avg) ** 2 for l in sent_lengths) / len(sent_lengths)
            signals["sentence_length_variance"] = round(variance, 2)
            # Burstiness: coefficient of variation — low means uniform (AI-like)
            if avg > 0:
                cv = math.sqrt(variance) / avg
                signals["burstiness_score"] = round(cv, 3)

    # ── type-token ratio (lexical diversity) ─────────────────────────────────
    # Calculated over first 500 words for comparability
    sample = words[:500]
    if sample:
        signals["type_token_ratio"] = round(len(set(sample)) / len(sample), 4)

    # ── hedge phrase density ──────────────────────────────────────────────────
    hedge_hits = sum(1 for r in _AI_HEDGE_RE if r.search(text))
    signals["hedge_phrase_hits"] = hedge_hits
    signals["hedge_phrase_density"] = round(
        hedge_hits / max(len(sentences), 1), 3
    )

    # ── transition word density ───────────────────────────────────────────────
    trans_count = sum(1 for w in words if w in _TRANSITION_WORDS)
    signals["transition_word_density"] = round(trans_count / max(len(words), 1), 4)

    # ── generic filler hits ───────────────────────────────────────────────────
    signals["generic_filler_hits"] = sum(
        1 for r in _GENERIC_FILLER_RE if r.search(text)
    )

    # ── paragraph length variance ─────────────────────────────────────────────
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 2:
        para_lengths = [len(p.split()) for p in paragraphs]
        avg_p = sum(para_lengths) / len(para_lengths)
        if avg_p > 0:
            para_var = sum((l - avg_p) ** 2 for l in para_lengths) / len(para_lengths)
            signals["paragraph_length_variance"] = round(para_var, 2)

    return signals


def _score_ai_text(signals: dict) -> tuple[float, list[str], list[str]]:
    """Convert AI-text signal dict into a 0–1 score."""
    score = 0.0
    key_signals: list[str] = []
    red_flags: list[str] = []

    word_count = signals.get("word_count", 0)

    # Need enough text to say anything meaningful
    if word_count < 30:
        return 0.0, ["insufficient_text"], []

    # ── burstiness (sentence length uniformity) ───────────────────────────────
    burst = signals.get("burstiness_score", 0.0)
    if burst < 0.20 and signals.get("sentence_count", 0) >= 5:
        score += 0.25
        key_signals.append(f"low_burstiness={burst:.2f}")
        red_flags.append(f"Unusually uniform sentence lengths (burstiness={burst:.2f}) — AI pattern")

    # ── type-token ratio ──────────────────────────────────────────────────────
    ttr = signals.get("type_token_ratio", 0.0)
    if ttr < 0.45 and word_count >= 100:
        score += 0.15
        key_signals.append(f"low_ttr={ttr:.3f}")

    # ── hedge phrase density ──────────────────────────────────────────────────
    hedge = signals.get("hedge_phrase_density", 0.0)
    if hedge > 0.10:
        score += min(hedge * 1.5, 0.30)
        key_signals.append(f"hedge_density={hedge:.3f}")
        if hedge > 0.20:
            red_flags.append(f"High LLM hedge phrase density: {hedge:.3f} per sentence")

    # ── transition overuse ────────────────────────────────────────────────────
    trans = signals.get("transition_word_density", 0.0)
    if trans > 0.015:
        score += min(trans * 8, 0.15)
        key_signals.append(f"transition_overuse={trans:.4f}")
        if trans > 0.025:
            red_flags.append(f"Excessive transition words (density={trans:.4f}) — templated structure")

    # ── generic filler phrases ────────────────────────────────────────────────
    fillers = signals.get("generic_filler_hits", 0)
    if fillers >= 2:
        score += min(fillers * 0.06, 0.20)
        key_signals.append(f"generic_filler_count={fillers}")
        if fillers >= 3:
            red_flags.append(f"Multiple generic filler phrases ({fillers}) — low-specificity AI boilerplate")

    # ── paragraph uniformity ──────────────────────────────────────────────────
    para_var = signals.get("paragraph_length_variance", None)
    if para_var is not None and para_var < 50 and signals.get("sentence_count", 0) >= 10:
        score += 0.10
        key_signals.append(f"low_para_length_variance={para_var:.1f}")

    return round(min(score, 1.0), 3), key_signals, red_flags


# ────────────────────────────────────────────────────────────────────────────────
# HEURISTIC VERDICT COMBINER
# ────────────────────────────────────────────────────────────────────────────────

def _compute_heuristic_verdict(
    clickbait_signals: dict,
    ai_signals: dict,
) -> dict:
    """Combine both sub-scores into a unified verdict dict."""

    cb_score, cb_key_signals, cb_flags = _score_clickbait(clickbait_signals)
    ai_score, ai_key_signals, ai_flags = _score_ai_text(ai_signals)

    all_signals = cb_key_signals + ai_key_signals
    all_flags = cb_flags + ai_flags

    # Combined risk level
    max_score = max(cb_score, ai_score)
    if max_score >= 0.75:
        risk_level = "CRITICAL"
    elif max_score >= 0.50:
        risk_level = "HIGH"
    elif max_score >= 0.25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasoning = (
        f"Heuristic analysis: clickbait_score={cb_score:.2f}, "
        f"ai_generated_score={ai_score:.2f}, "
        f"risk_level={risk_level}."
    )

    return {
        "clickbait_score": cb_score,
        "ai_generated_score": ai_score,
        "linguistic_risk_level": risk_level,
        "dominant_signals": all_signals[:5],  # top 5
        "confidence": 0.55,  # heuristic baseline
        "reasoning": reasoning,
        "red_flags": all_flags,
    }


# ── LLM fusion layer ───────────────────────────────────────────────────────────

def _call_groq_llm(
    source_type: str,
    title: str,
    extracted_text: str,
    heuristic_signals: dict,
) -> Optional[dict]:
    """
    Call Groq LLM to fuse heuristic signals into a richer structured verdict.
    Returns parsed dict on success, None on any failure.
    """
    if not _groq_available:
        logger.debug("groq package not installed — skipping LLM fusion")
        return None

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.debug("GROQ_API_KEY not set — skipping LLM fusion")
        return None

    try:
        client = Groq()

        text_snippet = extracted_text[:_TEXT_CHAR_LIMIT] if extracted_text else ""

        user_content = (
            f"source_type: {source_type}\n"
            f"title: {title or '(none)'}\n"
            f"extracted_text: {text_snippet or '(none)'}\n\n"
            f"heuristic_signals:\n{json.dumps(heuristic_signals, indent=2)}"
        )

        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError as exc:
        logger.warning("Linguistic agent: LLM returned non-JSON: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Linguistic agent: Groq call failed: %s", exc)
        return None


# ── public API ─────────────────────────────────────────────────────────────────

def analyse_linguistics(
    extracted_text: str = "",
    title: str = "",
    source_type: str = "unknown",
) -> LinguisticAnalysisResult:
    """
    Main entry-point for the Linguistic Agent.

    Parameters
    ----------
    extracted_text : str
        The body text extracted from the content by a preprocessor.
        Truncated to 12000 chars before analysis; 8000 chars sent to LLM.
    title : str
        The headline, title, or subject line (empty string if absent).
        If the content is a URL article, pass the <title> tag value here.
    source_type : str
        One of "image", "url", "document", "video", "text".

    Returns
    -------
    LinguisticAnalysisResult
        Always returns a result — never raises.
    """
    reasoning_notes: list[str] = []

    try:
        # Enforce text length limit
        text = extracted_text[:12000] if extracted_text else ""

        # ── Step 1: heuristic signal extraction ───────────────────────────────
        clickbait_signals = _analyse_clickbait(title, text)
        ai_signals = _analyse_ai_text(text)

        heuristic_signals = {
            "clickbait": clickbait_signals,
            "ai_text": ai_signals,
        }

        # ── Step 2: heuristic verdict (always computed) ───────────────────────
        h_verdict = _compute_heuristic_verdict(clickbait_signals, ai_signals)

        reasoning_notes.append(
            f"Heuristic clickbait_score={h_verdict['clickbait_score']:.2f}, "
            f"ai_generated_score={h_verdict['ai_generated_score']:.2f}, "
            f"risk={h_verdict['linguistic_risk_level']}."
        )

        if not text or ai_signals.get("word_count", 0) < 30:
            reasoning_notes.append(
                "Text too short (<30 words) — AI-generation scoring suppressed."
            )

        # ── Step 3: LLM fusion (optional upgrade) ─────────────────────────────
        llm_verdict = _call_groq_llm(
            source_type=source_type,
            title=title,
            extracted_text=text,
            heuristic_signals=heuristic_signals,
        )

        if llm_verdict:
            analysis_method = "llm"
            reasoning_notes.append(
                "LLM fusion layer applied — heuristic signals enriched by "
                f"llama-3.3-70b-versatile (confidence={llm_verdict.get('confidence', 0):.2f})."
            )
            # Merge: LLM verdict takes precedence; heuristic red_flags always kept
            merged_flags = list(
                dict.fromkeys(
                    llm_verdict.get("red_flags", []) + h_verdict["red_flags"]
                )
            )
            final = {**h_verdict, **llm_verdict, "red_flags": merged_flags}
        else:
            analysis_method = "heuristic"
            reasoning_notes.append(
                "LLM fusion unavailable — heuristic-only verdict used."
            )
            final = h_verdict

        # ── Step 4: confidence_contribution for quality_gate ──────────────────
        # Average of both sub-scores weighted inversely:
        # high clickbait or AI score → lower trust → lower confidence contribution
        avg_risk = (final["clickbait_score"] + final["ai_generated_score"]) / 2.0
        confidence_contribution = round(
            final["confidence"] * (1.0 - avg_risk), 3
        )

        return LinguisticAnalysisResult(
            success=True,
            clickbait_score=final.get("clickbait_score", 0.0),
            ai_generated_score=final.get("ai_generated_score", 0.0),
            linguistic_risk_level=final.get("linguistic_risk_level", "UNKNOWN"),
            dominant_signals=final.get("dominant_signals", []),
            confidence=final.get("confidence", 0.5),
            reasoning=final.get("reasoning", ""),
            red_flags=final.get("red_flags", []),
            heuristic_signals=heuristic_signals,
            confidence_contribution=confidence_contribution,
            analysis_method=analysis_method,
            reasoning_notes=reasoning_notes,
        )

    except Exception as exc:
        logger.exception("Linguistic agent unexpected failure: %s", exc)
        return LinguisticAnalysisResult(
            success=False,
            analysis_method="failed",
            error=str(exc),
            reasoning_notes=[f"Linguistic agent failed: {exc}"],
        )