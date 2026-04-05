# router/layer3_classifier.py
# ----------------------------
# Layer 3: Routing Classifier
#
# WHY THIS EXISTS:
# Layers 1 and 2 give us facts: "this is a PNG" or "this looks like a URL".
# But routing isn't a simple if/else — a screenshot of a tweet is technically
# a PNG, but it should activate the TEXT pipeline (for OCR) AND the URL pipeline
# (to check the source), not just the VISION pipeline.
#
# Layer 3 uses ALL available signals and outputs a SCORE per pipeline.
# Any pipeline scoring above the threshold (ACTIVATION_THRESHOLD) gets activated.
# Multiple pipelines can activate at once — that's intentional.
#
# FOR THE HACKATHON:
# This is a rule-based scorer, not a trained ML model.
# In production you'd replace the scoring rules with a trained classifier,
# but the interface (inputs → score dict) stays identical.
# Your team can swap it out without touching anything else.

from .models import ContentHint, Pipeline, SubmissionContext
from .layer2sniff import is_social_url


# ── Threshold ─────────────────────────────────────────────────────────────────
# Any pipeline scoring AT OR ABOVE this value gets activated.
# 0.35 means "35% confident this pipeline is relevant — activate it".
# Lower = more pipelines activate (broader but noisier).
# Higher = fewer pipelines activate (focused but risks missing signals).
# Tune this during testing. 0.35 is a reasonable hackathon starting point.
ACTIVATION_THRESHOLD = 0.35


def classify(context: SubmissionContext, mime: str, hint: ContentHint) -> dict[Pipeline, float]:
    """
    Score each pipeline based on all available signals.
    Returns a dict: { Pipeline.VISION: 0.9, Pipeline.TEXT: 0.6, ... }

    HOW SCORES ACCUMULATE:
    - Each rule adds to a pipeline's score
    - Scores are clamped to 1.0 at the end
    - Rules are additive — a video from Twitter scores high on VIDEO *and* URL

    CONTRACT FOR YOUR TEAM:
    - Always returns all four pipelines with a score (even if 0.0)
    - Scores are floats between 0.0 and 1.0
    - This function is pure — no side effects, no I/O
    """
    scores: dict[Pipeline, float] = {
        Pipeline.VISION: 0.0,
        Pipeline.TEXT:   0.0,
        Pipeline.VIDEO:  0.0,
        Pipeline.URL:    0.0,
    }
    notes: list[str] = []

    # ── MIME-based rules ──────────────────────────────────────────────────────

    if mime.startswith("image/"):
        scores[Pipeline.VISION] += 0.9
        notes.append(f"Image file detected ({mime}) → Vision pipeline")

    if mime.startswith("video/"):
        scores[Pipeline.VIDEO] += 0.9
        scores[Pipeline.VISION] += 0.3   # video frames can be checked visually too
        notes.append(f"Video file detected ({mime}) → Video + partial Vision")

    if mime.startswith("audio/"):
        scores[Pipeline.VIDEO] += 0.6    # VIDEO pipeline handles ASR (speech-to-text)
        notes.append(f"Audio file detected ({mime}) → Video/ASR pipeline")

    if mime == "application/pdf":
        scores[Pipeline.TEXT] += 0.85
        notes.append("PDF document → Text/NLP pipeline")

    if mime in ("text/plain", "text/html", "application/json"):
        scores[Pipeline.TEXT] += 0.8
        notes.append(f"Text-based file ({mime}) → Text/NLP pipeline")

    # ── Content hint rules ────────────────────────────────────────────────────

    if hint == ContentHint.URL:
        scores[Pipeline.URL] += 0.85
        notes.append("Content is a URL → Source credibility pipeline")

    if hint == ContentHint.PROSE:
        scores[Pipeline.TEXT] += 0.5
        notes.append("Content looks like prose → Text/NLP pipeline")

    if hint == ContentHint.HTML:
        scores[Pipeline.TEXT] += 0.4
        scores[Pipeline.URL]  += 0.3
        notes.append("HTML content detected → Text + URL pipelines")

    # ── Originating URL rules (EXTRA SIGNALS) ────────────────────────────────
    # This is the insight: the URL context around a file is separate signal
    # from the file itself. Never discard it.

    if context.originating_url:
        scores[Pipeline.URL] += 0.4
        notes.append("Originating URL present → URL pipeline gets bonus signal")

    if is_social_url(context.originating_url):
        scores[Pipeline.URL] += 0.25
        notes.append("Originating URL is a social platform → stronger URL signal")

    # ── EDGE CASE: Screenshot of a tweet / news article ──────────────────────
    # Magic bytes say "PNG" but correct routing is Vision + OCR (Text) + URL.
    # We detect this by combining: image MIME + social originating URL.
    # Without Layer 3, this case would only activate VISION — wrong.

    if mime.startswith("image/") and is_social_url(context.originating_url):
        scores[Pipeline.TEXT] += 0.65   # activate OCR on the image text
        scores[Pipeline.URL]  += 0.50   # check the source account too
        notes.append(
            "IMAGE from social platform → likely screenshot of post. "
            "Activating OCR (Text) + Source check (URL) alongside Vision."
        )

    # ── EDGE CASE: Video without context ─────────────────────────────────────
    # A raw video has no metadata. If it came with a social URL, we gain
    # who-posted-it and when — that's a separate rich signal.

    if mime.startswith("video/") and context.originating_url:
        scores[Pipeline.URL] += 0.45
        notes.append(
            "Video + originating URL present → "
            "URL pipeline can extract posting metadata."
        )

    # ── Clamp all scores to [0.0, 1.0] ───────────────────────────────────────
    for pipeline in scores:
        scores[pipeline] = min(scores[pipeline], 1.0)

    return scores, notes