# router/layer2_sniff.py
# ----------------------
# Layer 2: Content Sniffing
#
# WHY THIS EXISTS:
# Magic bytes only work on binary files. But what if the user pastes
# a URL into a text box? Or uploads a .txt file? Or submits a JSON blob?
# There are no magic bytes for "this is a URL" — we have to look at the
# actual content and make an educated guess.
#
# We only look at the first 512 bytes — fast and cheap.
# The result is a ContentHint (see models.py), not a final decision.
# Layer 3 uses this hint alongside the MIME type.

import re
from .models import ContentHint


# ── Patterns we scan for ──────────────────────────────────────────────────────

# A URL typically starts with http:// or https://
_URL_PATTERN = re.compile(r'^https?://', re.IGNORECASE)

# HTML usually has tags like <html>, <div>, <p>, <head>
_HTML_PATTERN = re.compile(r'<\s*(html|head|body|div|p|span|script)', re.IGNORECASE)

# JSON starts with { or [ (after optional whitespace)
_JSON_PATTERN = re.compile(r'^\s*[\[{]')

# Social platform URLs — these carry extra metadata signals
_SOCIAL_DOMAINS = ("twitter.com", "x.com", "facebook.com", "instagram.com",
                   "tiktok.com", "youtube.com", "reddit.com", "t.co")


def sniff_content(file_bytes: bytes | None, originating_url: str | None) -> ContentHint:
    """
    Inspect the first 512 bytes of content (or the originating URL) to get
    a content hint when magic bytes are ambiguous.

    Logic order:
      1. If there are no file bytes but there IS a URL → it's a URL submission
      2. If the file bytes decode to a URL string → URL
      3. If content looks like HTML → HTML
      4. If content looks like JSON → JSON
      5. If it's readable text → PROSE
      6. Everything else → AMBIGUOUS

    CONTRACT FOR YOUR TEAM:
    - Call this AFTER layer1. If layer1 returned a clear binary MIME
      (image/png, video/mp4), you can skip this layer — it adds nothing.
    - This is most useful when mime == 'text/plain' or 'unknown'.
    - Returns a ContentHint enum value, never None.
    """

    # ── Case 1: No file, but a URL was provided ───────────────────────────────
    if not file_bytes and originating_url:
        return ContentHint.URL

    if not file_bytes:
        return ContentHint.AMBIGUOUS

    # ── Try to decode the first 512 bytes as UTF-8 text ──────────────────────
    # Many binary files will fail here — that's fine, we catch it below
    snippet = file_bytes[:512]
    try:
        text = snippet.decode("utf-8").strip()
    except UnicodeDecodeError:
        # Can't decode as text → it's binary content, not prose
        return ContentHint.AMBIGUOUS

    # ── Case 2: The text content IS a URL ─────────────────────────────────────
    if _URL_PATTERN.match(text):
        return ContentHint.URL

    # ── Case 3: HTML tags detected ────────────────────────────────────────────
    if _HTML_PATTERN.search(text):
        return ContentHint.HTML

    # ── Case 4: JSON structure detected ──────────────────────────────────────
    if _JSON_PATTERN.match(text):
        return ContentHint.JSON

    # ── Case 5: Readable prose ────────────────────────────────────────────────
    # We define "readable" as: mostly printable ASCII/unicode, no binary garbage
    printable_ratio = sum(1 for c in text if c.isprintable()) / max(len(text), 1)
    if printable_ratio > 0.85:
        return ContentHint.PROSE

    # ── Fallback ──────────────────────────────────────────────────────────────
    return ContentHint.AMBIGUOUS


def is_social_url(url: str | None) -> bool:
    """
    Returns True if the originating URL is from a known social platform.

    WHY THIS MATTERS:
    A social URL means: the content was *shared* somewhere. That means
    we can check who shared it, when, how many times, and cross-reference
    the original source. This is extra signal for the URL pipeline.
    The Layer 3 classifier uses this as a scoring bonus.
    """
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in _SOCIAL_DOMAINS)