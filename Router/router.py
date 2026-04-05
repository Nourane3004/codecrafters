# router/router.py
# -----------------
# THE MAIN ROUTER — this is the only file your team needs to call.
#
# It wires together all three layers and returns a clean RoutingDecision.
# Think of it like a traffic controller: content comes in, the router
# decides which analysis "lanes" (pipelines) it should go into.
#
# HOW TO USE (from anywhere in the codebase):
#
#   from router.router import route
#   from router.models import SubmissionContext
#
#   context = SubmissionContext(
#       file_bytes=uploaded_file_bytes,
#       file_name="photo.jpg",
#       originating_url="https://twitter.com/user/status/123",
#       user_agent=request.headers.get("user-agent"),
#   )
#   decision = route(context)
#
#   # decision.active_pipelines = {Pipeline.VISION, Pipeline.TEXT, Pipeline.URL}
#   # decision.routing_notes    = ["Image from social platform...", ...]
#   # decision.pipeline_scores  = {Pipeline.VISION: 0.9, Pipeline.TEXT: 0.65, ...}

from .models import SubmissionContext, RoutingDecision, Pipeline
from .layer1magic import detect_mime
from .layer2sniff import sniff_content
from .layer3classifier import classify, ACTIVATION_THRESHOLD


def route(context: SubmissionContext) -> RoutingDecision:
    """
    Run all three detection layers and return a RoutingDecision.

    This function:
      1. Detects the file type via magic bytes (Layer 1)
      2. Sniffs the text content for additional hints (Layer 2)
      3. Scores each pipeline using all signals (Layer 3)
      4. Activates any pipeline above the threshold
      5. Collects plain-English notes explaining every decision

    CONTRACT FOR YOUR TEAM:
    - This is the ONLY function the rest of the app should call.
    - It never raises exceptions — failures degrade gracefully.
    - The RoutingDecision it returns is the input to your pipeline orchestrator.
    - routing_notes is your explainability feed: pass it to the reasoning engine.
    """

    all_notes: list[str] = []

    # ── Layer 1: Magic bytes ──────────────────────────────────────────────────
    mime = detect_mime(context.file_bytes)
    all_notes.append(f"Layer 1 — MIME detected: {mime}")

    # ── Layer 2: Content sniffing ─────────────────────────────────────────────
    hint = sniff_content(context.file_bytes, context.originating_url)
    all_notes.append(f"Layer 2 — Content hint: {hint.value}")

    # ── Layer 3: Scoring ──────────────────────────────────────────────────────
    scores, classifier_notes = classify(context, mime, hint)
    all_notes.extend(classifier_notes)

    # ── Threshold gate: which pipelines actually activate? ────────────────────
    active: set[Pipeline] = {
        pipeline
        for pipeline, score in scores.items()
        if score >= ACTIVATION_THRESHOLD
    }

    # Explain the activation decisions in plain English
    for pipeline, score in scores.items():
        status = "ACTIVATED" if pipeline in active else "skipped"
        all_notes.append(
            f"Pipeline {pipeline.value}: score={score:.2f} → {status} "
            f"(threshold={ACTIVATION_THRESHOLD})"
        )

    # ── Fallback: if nothing activated, default to TEXT ───────────────────────
    # This should rarely happen, but we never want to return empty pipelines.
    if not active:
        active.add(Pipeline.TEXT)
        all_notes.append(
            "No pipeline scored above threshold — defaulting to TEXT pipeline as fallback."
        )

    return RoutingDecision(
        active_pipelines=active,
        pipeline_scores=scores,
        routing_notes=all_notes,
        raw_mime=mime,
        content_hint=hint,
    )