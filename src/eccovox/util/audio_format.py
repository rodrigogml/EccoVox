"""Audio container detection for safe engine interoperability."""

from __future__ import annotations

from pathlib import Path


SUPPORTED_AUDIO_FORMATS: tuple[str, ...] = ("wav", "mp3", "m4a", "mp4", "ogg", "opus", "webm", "flac")

_CONTENT_TYPE_FORMATS = {
    "audio/flac": "flac",
    "audio/m4a": "m4a",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "audio/x-m4a": "m4a",
    "audio/x-wav": "wav",
}


def audio_format_hint(filename: str | None = None, content_type: str | None = None) -> str | None:
    """Return a normalized format hint from untrusted upload metadata."""

    if filename:
        suffix = Path(filename).suffix.removeprefix(".").lower()
        if suffix in SUPPORTED_AUDIO_FORMATS:
            return suffix
    if content_type:
        return _CONTENT_TYPE_FORMATS.get(content_type.split(";", maxsplit=1)[0].strip().lower())
    return None


def detect_audio_format(audio: bytes, declared_format: str | None = None) -> str | None:
    """Detect a supported container from bytes, using a normalized hint only as fallback."""

    hint = _normalize_hint(declared_format)
    if audio.startswith(b"OggS"):
        return "opus" if hint == "opus" else "ogg"
    if len(audio) >= 12 and audio.startswith(b"RIFF") and audio[8:12] == b"WAVE":
        return "wav"
    if audio.startswith(b"fLaC"):
        return "flac"
    if audio.startswith(b"\x1aE\xdf\xa3"):
        return "webm"
    if len(audio) >= 8 and audio[4:8] == b"ftyp":
        return hint if hint in {"m4a", "mp4"} else "m4a"
    if audio.startswith(b"ID3") or (len(audio) >= 2 and audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0):
        return "mp3"
    return hint


def audio_suffix(audio: bytes, declared_format: str | None = None) -> str:
    """Return a safe suffix for a temporary audio artifact."""

    detected_format = detect_audio_format(audio, declared_format)
    return f".{detected_format}" if detected_format else ".bin"


def _normalize_hint(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().removeprefix(".")
    return normalized if normalized in SUPPORTED_AUDIO_FORMATS else None
