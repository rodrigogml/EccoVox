"""Optional, cached Kokoro TTS adapter."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import threading
from importlib.util import find_spec
from pathlib import Path
from time import perf_counter
from typing import Any

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import CapabilityHealth, CapabilityStatusEnum, RuntimeProfile, TtsRequest, TtsResult
from eccovox.engine.base import TtsEngineAdapter


class KokoroTtsEngineAdapter(TtsEngineAdapter):
    """Kokoro adapter with process-lifetime pipeline reuse and local encoding."""

    engine_name = "kokoro"
    sample_rate = 24_000

    def __init__(self, model_cache_dir: Path | None = None, encoder_path: str | None = None, max_segment_chars: int = 500) -> None:
        self._model_cache_dir = model_cache_dir
        self._encoder_path = encoder_path
        self._max_segment_chars = max_segment_chars
        self._pipelines: dict[tuple[str, str, str], Any] = {}
        self._pipeline_lock = threading.Lock()
        self._encode_lock = threading.Lock()
        if model_cache_dir is not None:
            cache_dir = model_cache_dir / "huggingface"
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("HF_HOME", str(cache_dir))

    def health(self, profile: RuntimeProfile) -> CapabilityHealth:
        if find_spec("kokoro") is None or find_spec("soundfile") is None:
            return CapabilityHealth(
                status=CapabilityStatusEnum.UNAVAILABLE,
                engine=self.engine_name,
                model=profile.model,
                device=profile.device,
                formats=self.supported_formats,
                safe_message="Kokoro TTS extra is not installed.",
            )
        if "mp3" in self.supported_formats and not self._ffmpeg():
            return CapabilityHealth(
                status=CapabilityStatusEnum.DEGRADED,
                engine=self.engine_name,
                model=profile.model,
                device=profile.device,
                formats=("wav", "flac", "ogg"),
                safe_message="WAV/FLAC are available; local FFmpeg was not found for MP3.",
            )
        if profile.device == "cuda" and self._effective_device(profile) != "cuda":
            return CapabilityHealth(
                status=CapabilityStatusEnum.DEGRADED,
                engine=self.engine_name,
                model=profile.model,
                device="cpu",
                formats=self.supported_formats,
                safe_message="CUDA is configured but the installed PyTorch runtime has no CUDA support; using CPU.",
            )
        return super().health(profile)

    def warmup(self, profile: RuntimeProfile) -> None:
        self._pipeline_for(profile)

    def synthesize(self, request: TtsRequest, profile: RuntimeProfile) -> TtsResult:
        started = perf_counter()
        response_format = (profile.response_format or "wav").lower()
        if response_format not in {"wav", "flac", "ogg", "mp3"}:
            raise EccoVoxError(ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT, "Requested TTS format is not supported.")
        if response_format == "mp3" and not self._ffmpeg():
            raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Local FFmpeg is required for MP3 output.")

        try:
            import numpy as np
            import soundfile as sf

            pipeline = self._pipeline_for(profile)
            chunks: list[Any] = []
            segments = _split_text(request.input_text, self._max_segment_chars)
            for segment in segments:
                generator = pipeline(segment, voice=profile.voice, speed=profile.speed or 1.0)
                chunks.extend(item[-1] for item in generator)
            if not chunks:
                raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine returned no audio.")
            audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
            buffer = io.BytesIO()
            sf.write(buffer, audio, self.sample_rate, format=response_format.upper() if response_format != "mp3" else "WAV")
            native_audio = buffer.getvalue()
            encoded = native_audio if response_format != "mp3" else self._encode(native_audio, response_format)
        except EccoVoxError:
            raise
        except ImportError as exc:
            raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Kokoro TTS extra is not installed.") from exc
        except Exception as exc:
            raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine failed to synthesize text.") from exc

        processing_millis = round((perf_counter() - started) * 1_000)
        return TtsResult(
            audio=encoded,
            content_type=f"audio/{response_format}",
            response_format=response_format,
            metadata={
                "engine": self.engine_name,
                "model": profile.model or "kokoro-v1.0",
                "voice": profile.voice,
                "language": profile.language,
                "device": self._effective_device(profile),
                "processingMillis": processing_millis,
                "segmentCount": len(segments),
            },
        )

    def _pipeline_for(self, profile: RuntimeProfile) -> Any:
        language = profile.language or "pt-BR"
        lang_code = "p" if language.lower().startswith("pt") else language[:1].lower()
        device = self._effective_device(profile)
        key = (lang_code, profile.voice or "", device)
        with self._pipeline_lock:
            if key in self._pipelines:
                return self._pipelines[key]
            try:
                from kokoro import KPipeline
                options: dict[str, object] = {"lang_code": lang_code}
                # Older Kokoro releases do not expose device in KPipeline.
                try:
                    import inspect
                    if "device" in inspect.signature(KPipeline).parameters:
                        options["device"] = device
                except (TypeError, ValueError):
                    pass
                pipeline = KPipeline(**options)
            except ImportError as exc:
                raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Kokoro TTS extra is not installed.") from exc
            self._pipelines[key] = pipeline
            return pipeline

    @staticmethod
    def _effective_device(profile: RuntimeProfile) -> str:
        requested = profile.device or "cpu"
        if requested != "cuda":
            return requested
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except (ImportError, AttributeError):
            return "cpu"

    def _ffmpeg(self) -> str | None:
        if self._encoder_path:
            path = Path(self._encoder_path).expanduser()
            if path.is_file():
                return str(path)
        return shutil.which("ffmpeg")

    def _encode(self, wav_audio: bytes, response_format: str) -> bytes:
        executable = self._ffmpeg()
        if not executable:
            raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Local FFmpeg is required for compressed audio output.")
        codec = "libmp3lame" if response_format == "mp3" else "libvorbis"
        with self._encode_lock:
            try:
                completed = subprocess.run(
                    [executable, "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-f", response_format, "-acodec", codec, "pipe:1"],
                    input=wav_audio,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "Local audio encoder failed.") from exc
        return completed.stdout


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split on sentence boundaries while keeping segments bounded."""
    words = text.strip().split()
    segments: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            segments.append(current)
            current = word
        else:
            current = candidate
        if current.endswith((".", "!", "?", ":")) and len(current) >= max_chars // 2:
            segments.append(current)
            current = ""
    if current:
        segments.append(current)
    return segments or [""]
