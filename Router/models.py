# router/models.py
# -----------------
# This file defines the "shape" of data that enters the router.
# Think of it like a form — it lists every piece of info we need to make routing decisions.
# Every other part of the system speaks this language.

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ContentHint(Enum):
    """
    What Layer 2 (content sniffing) thinks the content is.
    Used when magic bytes are missing or ambiguous (e.g. plain text, URLs).
    """
    URL   = "url"       # looks like a web link
    HTML  = "html"      # contains HTML tags
    JSON  = "json"      # structured JSON data
    PROSE = "prose"     # plain human-written text
    AMBIGUOUS = "ambiguous"  # couldn't decide


class Pipeline(Enum):
    """
    The four analysis pipelines that can be activated.
    More than one can run at the same time.
    """
    VISION = "vision"   # image forensics — detects AI-generated or tampered images
    TEXT   = "text"     # NLP — extracts claims, detects AI-written text
    VIDEO  = "video"    # deepfake detection + speech transcription (ASR)
    URL    = "url"      # source credibility — who posted this, is the domain trustworthy


@dataclass
class SubmissionContext:
    """
    Everything the router knows about one user submission.

    IMPORTANT FOR YOUR TEAM:
    - The API layer must populate ALL fields it can before calling the router.
    - Never pass only file_bytes. Even if originating_url is None, say so explicitly.
    - file_bytes can be None if the user pasted a URL (no file uploaded).
    """
    file_bytes:       bytes | None   # raw file content (None if URL-only submission)
    file_name:        str   | None   # original filename, e.g. "clip.mp4"
    originating_url:  str   | None   # where this content came from (tweet URL, news link…)
    user_agent:       str   | None   # browser info — used for basic fraud signals
    timestamp:        datetime = field(default_factory=datetime.utcnow)


@dataclass
class RoutingDecision:
    """
    What the router outputs after analysing a submission.
    This is handed to the pipeline orchestrator which runs the active pipelines.

    IMPORTANT FOR YOUR TEAM:
    - active_pipelines is a SET — iterate it to know which agents to launch.
    - pipeline_scores is a DICT — use it to weight confidence in the aggregator.
    - routing_notes is a plain-English explanation of WHY each pipeline was activated.
      Feed this string into the explainability layer as context.
    """
    active_pipelines: set[Pipeline]
    pipeline_scores:  dict[Pipeline, float]   # 0.0 – 1.0 per pipeline
    routing_notes:    list[str]               # human-readable reasons
    raw_mime:         str                     # what Layer 1 detected
    content_hint:     ContentHint             # what Layer 2 detected