# router/layer1_magic.py
# ----------------------
# Layer 1: Magic Byte Inspection
#
# WHY THIS EXISTS:
# You can never trust the file extension a user gives you.
# Someone can rename "virus.exe" to "report.pdf" and upload it.
# The first few bytes of every real file contain a "signature" that
# reveals what it actually is — that's what we read here.
#
# INSTALL REQUIREMENT:
# This uses the 'python-magic' library which wraps a system tool called libmagic.
# On Ubuntu/Debian run:  sudo apt-get install libmagic1
# On Mac run:            brew install libmagic
# Then:                  pip install python-magic


import magic   # pip install python-magic


# A human-friendly map of MIME types to plain labels.
# We use this in routing_notes so the explainability layer can say
# "File detected as: PNG image" instead of "image/png".
MIME_LABELS: dict[str, str] = {
    "image/png":       "PNG image",
    "image/jpeg":      "JPEG image",
    "image/gif":       "GIF image",
    "image/webp":      "WebP image",
    "video/mp4":       "MP4 video",
    "video/webm":      "WebM video",
    "video/quicktime": "QuickTime video",
    "application/pdf": "PDF document",
    "text/plain":      "plain text",
    "text/html":       "HTML document",
    "application/json":"JSON data",
    "audio/mpeg":      "MP3 audio",
    "audio/wav":       "WAV audio",
}


def detect_mime(file_bytes: bytes | None) -> str:
    """
    Read the magic bytes of a file and return its MIME type.

    Examples:
        b'\\x89PNG...'  ->  'image/png'
        b'%PDF-...'    ->  'application/pdf'
        None           ->  'unknown'

    CONTRACT FOR YOUR TEAM:
    - Always returns a string. Never raises an exception.
    - Returns 'unknown' if bytes are None or unrecognizable.
    - The API layer should pass raw bytes — do NOT decode to string first.
    """
    if not file_bytes:
        return "unknown"

    try:
        # mime=True tells python-magic to return the MIME type string
        # e.g. "image/png" not "PNG image data, 800 x 600"
        return magic.from_buffer(file_bytes, mime=True)
    except Exception:
        # If libmagic itself fails (corrupted file, etc.) we fall through gracefully
        return "unknown"


def mime_label(mime: str) -> str:
    """
    Convert a raw MIME string to a readable label for logging/explainability.
    Falls back to the raw MIME string if we don't have a label for it.
    """
    return MIME_LABELS.get(mime, mime)