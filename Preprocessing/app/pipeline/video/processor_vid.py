"""
Video Preprocessing Branch
-----------------------------
Steps  (matches diagram Image 1):
  1. Frame extract    – FFmpeg keyframe extraction
  2. ASR transcription – Whisper (with timestamps)
  3. Video metadata   – codec, duration, resolution, timestamps
"""

from __future__ import annotations
import hashlib
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from models.feature_object import (
    ASRResult,
    InputType,
    NormalizedFeatureObject,
    VideoData,
    VideoMetadata,
)

logger = logging.getLogger(__name__)

# Max keyframes to extract (keeps processing time bounded)
MAX_KEYFRAMES = 10


# ══════════════════════════════════════════════════════
# 1.  Frame extraction
# ══════════════════════════════════════════════════════

def extract_keyframes(video_path: str, output_dir: str) -> list[str]:
    """
    Extract keyframes from a video file using FFmpeg.
    Returns a list of saved frame file paths.
    """
    frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        # Extract only I-frames (keyframes), up to MAX_KEYFRAMES
        "-vf", f"select='eq(pict_type,I)',scale=640:-1",
        "-vsync", "vfr",
        "-frames:v", str(MAX_KEYFRAMES),
        "-q:v", "3",
        frame_pattern,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning(f"FFmpeg keyframe extraction error: {result.stderr[:200]}")

        frames = sorted(Path(output_dir).glob("frame_*.jpg"))
        return [str(f) for f in frames]

    except FileNotFoundError:
        logger.warning("FFmpeg not found — keyframe extraction skipped")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg keyframe extraction timed out")
        return []
    except Exception as e:
        logger.warning(f"Keyframe extraction failed: {e}")
        return []


# ══════════════════════════════════════════════════════
# 2.  ASR transcription
# ══════════════════════════════════════════════════════

def transcribe_audio(video_path: str) -> ASRResult:
    """
    Transcribe audio from a video file using OpenAI Whisper.
    Returns ASRResult with raw transcript and word-level timestamps.
    """
    try:
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(
            video_path,
            word_timestamps=True,
            verbose=False,
        )

        # Flatten word-level timestamps from all segments
        words_with_timestamps: list[dict] = []
        for segment in result.get("segments", []):
            for word in segment.get("words", []):
                words_with_timestamps.append({
                    "word":  word.get("word", "").strip(),
                    "start": round(word.get("start", 0.0), 2),
                    "end":   round(word.get("end",   0.0), 2),
                })

        # Segment-level timestamps (less granular but always available)
        segments: list[dict] = [
            {
                "text":  seg.get("text", "").strip(),
                "start": round(seg.get("start", 0.0), 2),
                "end":   round(seg.get("end",   0.0), 2),
            }
            for seg in result.get("segments", [])
        ]

        return ASRResult(
            raw_text            = result.get("text", "").strip(),
            language            = result.get("language"),
            segments            = segments,
            word_timestamps     = words_with_timestamps,
            model               = "whisper-base",
        )

    except ImportError:
        logger.warning("openai-whisper not installed — ASR skipped")
        return ASRResult(raw_text="", model="unavailable")
    except Exception as e:
        logger.warning(f"Whisper transcription failed: {e}")
        return ASRResult(raw_text="", model="whisper-base")


# ══════════════════════════════════════════════════════
# 3.  Video metadata
# ══════════════════════════════════════════════════════

def extract_video_metadata(video_path: str) -> VideoMetadata:
    """
    Use FFprobe to extract codec, duration, resolution, and frame rate.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning(f"FFprobe error: {result.stderr[:200]}")
            return VideoMetadata()

        probe = json.loads(result.stdout)
        fmt   = probe.get("format", {})

        # Find video and audio streams
        video_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        audio_stream = next(
            (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"),
            {},
        )

        # Parse frame rate (can be "30000/1001" fraction)
        fps: float | None = None
        fps_raw = video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate")
        if fps_raw and "/" in fps_raw:
            num, den = fps_raw.split("/")
            if int(den) > 0:
                fps = round(int(num) / int(den), 2)

        duration = None
        raw_dur  = fmt.get("duration") or video_stream.get("duration")
        if raw_dur:
            try:
                duration = round(float(raw_dur), 2)
            except ValueError:
                pass

        return VideoMetadata(
            duration_seconds = duration,
            width            = video_stream.get("width"),
            height           = video_stream.get("height"),
            video_codec      = video_stream.get("codec_name"),
            audio_codec      = audio_stream.get("codec_name"),
            fps              = fps,
            bit_rate         = int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
            format_name      = fmt.get("format_name"),
            has_audio        = bool(audio_stream),
        )

    except FileNotFoundError:
        logger.warning("FFprobe not found — video metadata extraction skipped")
        return VideoMetadata()
    except subprocess.TimeoutExpired:
        logger.warning("FFprobe timed out")
        return VideoMetadata()
    except Exception as e:
        logger.warning(f"Video metadata extraction failed: {e}")
        return VideoMetadata()


# ══════════════════════════════════════════════════════
# Pipeline entry point
# ══════════════════════════════════════════════════════

def preprocess_video(
    file_bytes: bytes,
    source_ref: str = "uploaded_video",
) -> NormalizedFeatureObject:
    """
    Full video preprocessing pipeline.
    Returns a NormalizedFeatureObject ready for the agent committee.
    """
    errors: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Write video bytes to temp file so FFmpeg/FFprobe/Whisper can read it
        ext       = Path(source_ref).suffix or ".mp4"
        video_path = os.path.join(tmp_dir, f"input{ext}")
        frames_dir = os.path.join(tmp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        with open(video_path, "wb") as f:
            f.write(file_bytes)

        # ── Step 1: Frame extraction ──
        frame_paths = extract_keyframes(video_path, frames_dir)
        if not frame_paths:
            errors.append("Keyframe extraction failed or FFmpeg unavailable")

        # ── Step 2: ASR transcription ──
        asr = transcribe_audio(video_path)
        if not asr.raw_text:
            errors.append("ASR produced no transcript")

        # ── Step 3: Video metadata ──
        video_meta = extract_video_metadata(video_path)

        # ── Dedup hash (SHA-256 of raw bytes; video files can be large) ──
        dedup_hash = hashlib.sha256(file_bytes[:2_000_000]).hexdigest()  # first 2 MB

        # ── Language from ASR ──
        language = asr.language or "unknown"

        # ── Assemble VideoData ──
        video_data = VideoData(
            metadata       = video_meta,
            asr            = asr,
            keyframe_count = len(frame_paths),
            file_size_bytes= len(file_bytes),
        )

        # ── Quality gate ──
        quality_passed, quality_reason = _quality_gate(video_meta, asr, errors)

        # ── Primary text: transcript ──
        primary_text = asr.raw_text.strip()

        return NormalizedFeatureObject(
            input_type     = InputType.VIDEO,
            source_ref     = source_ref,
            text           = primary_text,
            language       = language,
            video_data     = video_data,
            quality_passed = quality_passed,
            quality_reason = quality_reason,
            dedup_hash     = dedup_hash,
            errors         = errors,
        )


def _quality_gate(
    video_meta: VideoMetadata,
    asr: ASRResult,
    errors: list[str],
) -> tuple[bool, str]:
    # Reject if we couldn't even read the file's metadata
    if video_meta.duration_seconds is None and video_meta.video_codec is None:
        return False, "Could not read video metadata (FFprobe unavailable or corrupt file)"
    if video_meta.duration_seconds is not None and video_meta.duration_seconds < 0.5:
        return False, "Video too short"
    return True, "OK"