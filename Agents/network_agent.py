"""
app/agents/network_agent.py
───────────────────────────────────────────────────────────────────────────────
Network Agent — Graph ML · Bot Detection
───────────────────────────────────────────────────────────────────────────────
Analyses the *network-level* signals of a piece of content:

  1. URL / domain graph features   (link depth, redirect chains, TLD risk)
  2. Bot-behaviour heuristics      (user-agent-style signals in metadata)
  3. Content propagation patterns  (extracted share counts, forwarding cues)
  4. Linguistic bot markers        (templated phrasing, repetition ratios)
  5. LLM synthesis (Groq)          (fuses signals → structured verdict)

Returns a NetworkAnalysisResult — never raises; always degrades gracefully.

Integration note
────────────────
Call after preprocessing.  Wire into each processor that produces a
NormalizedFeatureObject by adding:

    from app.agents.network_agent import analyse_network
    net_result = analyse_network(nfo)
    nfo.agent_results["network_agent"] = net_result.model_dump()

The quality_gate.py `enrich()` step will pick it up automatically if
agent_results is present on the NormalizedFeatureObject.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

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
_TEXT_CHAR_LIMIT = 8000          # truncate before sending to LLM

# High-risk TLDs associated with spam / phishing campaigns
_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".click", ".loan", ".win", ".gq", ".ml", ".cf", ".tk",
    ".work", ".party", ".science", ".download", ".racing", ".trade", ".men",
    ".date", ".faith", ".stream", ".accountant", ".review", ".bid",
}

# URL shorteners often used to obscure final destinations
_URL_SHORTENERS = {
    "bit.ly", "t.co", "tinyurl.com", "ow.ly", "buff.ly", "goo.gl",
    "short.link", "rb.gy", "cutt.ly", "tiny.cc", "is.gd", "v.gd",
}

# Bot-language fingerprints — phrases that appear in templated / automated posts
_BOT_PHRASE_PATTERNS = [
    r"\bfollow\s+for\s+follow\b",
    r"\blike\s+and\s+share\b",
    r"\brt\s+to\s+win\b",
    r"\bclick\s+the\s+link\s+in\s+(my\s+)?bio\b",
    r"\b\d{1,3}%\s+of\s+people\s+won'?t\b",
    r"\bshare\s+before\s+(?:they\s+)?delete\b",
    r"\bforward\s+this\s+to\s+\d+\s+(?:friends|people|contacts)\b",
    r"\bsend\s+this\s+to\s+everyone\b",
    r"\bthis\s+will\s+be\s+deleted\s+in\b",
    r"\bdouble\s+tap\s+if\b",
    r"\bcomment\s+amen\b",
    r"\bact\s+now[.!]?\s*limited\s+time\b",
    r"\bcongratulations[,!]?\s+you('ve)?\s+(been\s+)?(selected|won|chosen)\b",
]

_BOT_PHRASE_RE = [re.compile(p, re.IGNORECASE) for p in _BOT_PHRASE_PATTERNS]

# Repetition: if any token appears > this fraction of total tokens it's suspicious
_REPETITION_THRESHOLD = 0.15

_SYSTEM_PROMPT = """You are a network-behaviour and bot-detection analyst for a misinformation detection system.

You will receive:
- source_type: the kind of content (image, url, document, video, text)
- url: the URL associated with the content (may be empty)
- extracted_text: the text extracted from the content (may be empty)
- heuristic_signals: a JSON object with pre-computed network and bot signals

Your task: synthesise all signals and return a JSON verdict with EXACTLY this structure
(no markdown fences, no extra keys):

{
  "bot_probability": <float 0.0–1.0>,
  "network_risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "propagation_pattern": "<ORGANIC|COORDINATED|AUTOMATED|UNKNOWN>",
  "key_signals": ["<signal1>", "<signal2>", ...],
  "confidence": <float 0.0–1.0>,
  "reasoning": "<one concise paragraph explaining the verdict>",
  "red_flags": ["<flag1>", "<flag2>", ...]
}

Rules:
- bot_probability reflects how likely the content originates from or is promoted by automated accounts.
- network_risk_level reflects the infrastructure risk (domain, redirects, shorteners).
- propagation_pattern reflects how the content is likely spreading.
- key_signals must list the 2–5 most decisive signals you used.
- red_flags are specific anomalies (e.g. "suspicious TLD .xyz", "chain-letter phrasing detected").
- confidence reflects your certainty given the available signals.
- Be concise. Do not speculate beyond the evidence provided."""


# ── output schema ──────────────────────────────────────────────────────────────

@dataclass
class NetworkAnalysisResult:
    success: bool
    bot_probability: float = 0.0
    network_risk_level: str = "UNKNOWN"        # LOW|MEDIUM|HIGH|CRITICAL
    propagation_pattern: str = "UNKNOWN"       # ORGANIC|COORDINATED|AUTOMATED|UNKNOWN
    key_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    # heuristic mirror (always populated regardless of LLM availability)
    heuristic_signals: dict = field(default_factory=dict)
    confidence_contribution: float = 0.0      # fed into quality_gate.py
    analysis_method: str = "heuristic"        # "llm" | "heuristic" | "failed"
    reasoning_notes: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def model_dump(self) -> dict:
        return {
            "success": self.success,
            "bot_probability": self.bot_probability,
            "network_risk_level": self.network_risk_level,
            "propagation_pattern": self.propagation_pattern,
            "key_signals": self.key_signals,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "red_flags": self.red_flags,
            "heuristic_signals": self.heuristic_signals,
            "confidence_contribution": self.confidence_contribution,
            "analysis_method": self.analysis_method,
            "reasoning_notes": self.reasoning_notes,
            "error": self.error,
        }


# ── heuristic engine ───────────────────────────────────────────────────────────

def _analyse_url(url: str) -> dict:
    """Extract network-level risk signals from a URL string."""
    signals: dict = {
        "url_present": bool(url),
        "uses_shortener": False,
        "suspicious_tld": False,
        "tld": "",
        "redirect_depth_hint": 0,
        "domain": "",
        "has_ip_address": False,
        "excessive_subdomains": False,
        "long_path": False,
    }

    if not url:
        return signals

    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        hostname = parsed.hostname or ""
        path = parsed.path or ""

        signals["domain"] = hostname

        # IP address in hostname → phishing risk
        ip_re = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
        signals["has_ip_address"] = bool(ip_re.match(hostname))

        # TLD extraction
        parts = hostname.split(".")
        tld = f".{parts[-1]}" if parts else ""
        signals["tld"] = tld
        signals["suspicious_tld"] = tld in _SUSPICIOUS_TLDS

        # URL shortener detection
        bare_domain = ".".join(parts[-2:]) if len(parts) >= 2 else hostname
        signals["uses_shortener"] = bare_domain in _URL_SHORTENERS

        # Subdomain depth > 2 levels is suspicious (e.g. a.b.legit.com)
        signals["excessive_subdomains"] = len(parts) > 3

        # Very long paths are sometimes used to hide tracking payloads
        signals["long_path"] = len(path) > 200

        # Redirect hints from path keywords
        if "redirect" in path.lower() or "r=" in parsed.query.lower():
            signals["redirect_depth_hint"] = 1

    except Exception as exc:
        logger.debug("URL parse error: %s", exc)

    return signals


def _analyse_text_for_bot_signals(text: str) -> dict:
    """Detect bot-language and propagation-manipulation patterns in text."""
    signals: dict = {
        "bot_phrase_hits": [],
        "repetition_score": 0.0,
        "chain_letter_score": 0.0,
        "urgency_density": 0.0,
        "all_caps_ratio": 0.0,
        "exclamation_density": 0.0,
    }

    if not text:
        return signals

    # Bot phrase matching
    for pattern in _BOT_PHRASE_RE:
        m = pattern.search(text)
        if m:
            signals["bot_phrase_hits"].append(m.group(0).strip())

    # Token repetition score
    tokens = re.findall(r"\b\w+\b", text.lower())
    if len(tokens) > 10:
        from collections import Counter
        counts = Counter(tokens)
        most_common_freq = counts.most_common(1)[0][1]
        signals["repetition_score"] = round(most_common_freq / len(tokens), 3)

    # Chain-letter cues
    chain_cues = len(re.findall(
        r"\b(forward|share|send|pass)\s+(this|it|on)\b",
        text, re.IGNORECASE
    ))
    signals["chain_letter_score"] = min(chain_cues / max(len(tokens) / 100, 1), 1.0)

    # Urgency density
    urgency_words = len(re.findall(
        r"\b(urgent|immediately|breaking|act\s+now|expires|hurry|limited|deadline)\b",
        text, re.IGNORECASE
    ))
    signals["urgency_density"] = round(urgency_words / max(len(tokens) / 100, 1), 3)

    # ALL-CAPS ratio (normalised by word count)
    cap_words = len(re.findall(r"\b[A-Z]{3,}\b", text))
    word_count = max(len(tokens), 1)
    signals["all_caps_ratio"] = round(cap_words / word_count, 3)

    # Exclamation density
    signals["exclamation_density"] = round(
        text.count("!") / max(len(text) / 100, 1), 3
    )

    return signals


def _compute_heuristic_verdict(url_signals: dict, text_signals: dict) -> dict:
    """
    Combine URL and text signals into a heuristic verdict.
    Returns a dict compatible with NetworkAnalysisResult fields.
    """
    risk_score = 0.0
    red_flags: list[str] = []
    key_signals: list[str] = []

    # ── URL scoring ────────────────────────────────────────────────
    if url_signals.get("has_ip_address"):
        risk_score += 0.30
        red_flags.append("IP address used instead of domain name")
    if url_signals.get("suspicious_tld"):
        risk_score += 0.20
        red_flags.append(f"Suspicious TLD detected: {url_signals.get('tld', '')}")
    if url_signals.get("uses_shortener"):
        risk_score += 0.15
        red_flags.append("URL shortener obscures final destination")
        key_signals.append("URL shortener detected")
    if url_signals.get("excessive_subdomains"):
        risk_score += 0.10
        red_flags.append("Excessive subdomain depth (possible spoofing)")
    if url_signals.get("redirect_depth_hint", 0) > 0:
        risk_score += 0.10
        red_flags.append("Redirect indicator found in URL path")

    # ── Text scoring ───────────────────────────────────────────────
    bot_hits = text_signals.get("bot_phrase_hits", [])
    if bot_hits:
        risk_score += min(0.10 * len(bot_hits), 0.30)
        for hit in bot_hits[:3]:
            red_flags.append(f"Bot-language pattern: '{hit}'")
        key_signals.append(f"{len(bot_hits)} bot-phrase pattern(s) matched")

    rep = text_signals.get("repetition_score", 0.0)
    if rep > _REPETITION_THRESHOLD:
        risk_score += 0.10
        red_flags.append(f"High token repetition score ({rep:.2f})")
        key_signals.append("Abnormal word repetition detected")

    chain = text_signals.get("chain_letter_score", 0.0)
    if chain > 0.5:
        risk_score += 0.15
        red_flags.append("Chain-letter / viral forwarding language detected")
        key_signals.append("Chain-letter propagation pattern")

    urgency = text_signals.get("urgency_density", 0.0)
    if urgency > 0.5:
        risk_score += 0.10
        red_flags.append(f"High urgency language density ({urgency:.2f})")

    caps = text_signals.get("all_caps_ratio", 0.0)
    if caps > 0.20:
        risk_score += 0.05
        red_flags.append(f"Excessive ALL-CAPS usage ({caps:.0%} of words)")

    # ── Normalise ──────────────────────────────────────────────────
    bot_probability = min(risk_score, 1.0)

    if bot_probability >= 0.75:
        network_risk_level = "CRITICAL"
    elif bot_probability >= 0.50:
        network_risk_level = "HIGH"
    elif bot_probability >= 0.25:
        network_risk_level = "MEDIUM"
    else:
        network_risk_level = "LOW"

    if chain > 0.3 or len(bot_hits) >= 2:
        propagation_pattern = "AUTOMATED"
    elif bot_probability >= 0.40:
        propagation_pattern = "COORDINATED"
    elif bot_probability < 0.15:
        propagation_pattern = "ORGANIC"
    else:
        propagation_pattern = "UNKNOWN"

    if not key_signals:
        key_signals.append("No significant network risk signals detected")

    return {
        "bot_probability": round(bot_probability, 3),
        "network_risk_level": network_risk_level,
        "propagation_pattern": propagation_pattern,
        "key_signals": key_signals,
        "confidence": 0.55,   # heuristic baseline confidence
        "reasoning": (
            f"Heuristic analysis: risk_score={risk_score:.2f}, "
            f"bot_hits={len(bot_hits)}, chain_score={chain:.2f}, "
            f"urgency={urgency:.2f}. "
            f"Risk level: {network_risk_level}."
        ),
        "red_flags": red_flags,
    }


# ── LLM fusion layer ───────────────────────────────────────────────────────────

def _call_groq_llm(
    source_type: str,
    url: str,
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

        # Truncate text to avoid token overflow
        text_snippet = extracted_text[:_TEXT_CHAR_LIMIT] if extracted_text else ""

        user_content = (
            f"source_type: {source_type}\n"
            f"url: {url or '(none)'}\n"
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

        # Strip markdown fences if model forgot the instruction
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError as exc:
        logger.warning("Network agent: LLM returned non-JSON: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Network agent: Groq call failed: %s", exc)
        return None


# ── public API ─────────────────────────────────────────────────────────────────

def analyse_network(
    source_type: str = "unknown",
    url: str = "",
    extracted_text: str = "",
    metadata: Optional[dict] = None,
) -> NetworkAnalysisResult:
    """
    Main entry-point for the Network Agent.

    Parameters
    ----------
    source_type : str
        One of "image", "url", "document", "video", "text".
    url : str
        The URL associated with the content (empty string if none).
    extracted_text : str
        Any text extracted from the content by a preprocessor.
    metadata : dict | None
        Optional metadata dict from the preprocessor (domain info, WHOIS, etc.).

    Returns
    -------
    NetworkAnalysisResult
        Always returns a result — never raises.
    """
    reasoning_notes: list[str] = []

    try:
        # ── Step 1: heuristic signal extraction ───────────────────
        url_signals = _analyse_url(url)
        text_signals = _analyse_text_for_bot_signals(extracted_text)

        # Fold in any preprocessor metadata we can use
        if metadata:
            domain_age = metadata.get("domain_age_days")
            if domain_age is not None and int(domain_age) < 30:
                url_signals["young_domain"] = True
                reasoning_notes.append(
                    f"Domain is only {domain_age} days old — elevated phishing risk."
                )
            whois_privacy = metadata.get("whois_privacy_enabled")
            if whois_privacy:
                url_signals["whois_privacy"] = True
                reasoning_notes.append(
                    "WHOIS privacy shield active — registrant identity hidden."
                )

        heuristic_signals = {
            "url": url_signals,
            "text": text_signals,
            "metadata_hints": {
                "domain_age_days": (metadata or {}).get("domain_age_days"),
                "whois_privacy": (metadata or {}).get("whois_privacy_enabled"),
            },
        }

        # ── Step 2: heuristic verdict (always computed) ────────────
        h_verdict = _compute_heuristic_verdict(url_signals, text_signals)

        reasoning_notes.append(
            f"Heuristic bot_probability={h_verdict['bot_probability']:.2f}, "
            f"risk={h_verdict['network_risk_level']}."
        )

        # ── Step 3: LLM fusion (optional upgrade) ─────────────────
        llm_verdict = _call_groq_llm(
            source_type=source_type,
            url=url,
            extracted_text=extracted_text,
            heuristic_signals=heuristic_signals,
        )

        if llm_verdict:
            analysis_method = "llm"
            reasoning_notes.append(
                "LLM fusion layer applied — heuristic signals enriched by "
                f"llama-3.3-70b-versatile (confidence={llm_verdict.get('confidence', 0):.2f})."
            )
            # Merge: LLM verdict takes precedence but we keep heuristic red_flags
            # to ensure no signal is silently dropped.
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

        # ── Step 4: confidence_contribution for quality_gate ──────
        # Higher bot probability → more negative contribution to overall confidence
        confidence_contribution = round(
            final["confidence"] * (1.0 - final["bot_probability"]), 3
        )

        return NetworkAnalysisResult(
            success=True,
            bot_probability=final.get("bot_probability", 0.0),
            network_risk_level=final.get("network_risk_level", "UNKNOWN"),
            propagation_pattern=final.get("propagation_pattern", "UNKNOWN"),
            key_signals=final.get("key_signals", []),
            confidence=final.get("confidence", 0.5),
            reasoning=final.get("reasoning", ""),
            red_flags=final.get("red_flags", []),
            heuristic_signals=heuristic_signals,
            confidence_contribution=confidence_contribution,
            analysis_method=analysis_method,
            reasoning_notes=reasoning_notes,
        )

    except Exception as exc:
        logger.exception("Network agent unexpected failure: %s", exc)
        return NetworkAnalysisResult(
            success=False,
            analysis_method="failed",
            error=str(exc),
            reasoning_notes=[f"Network agent failed: {exc}"],
        )