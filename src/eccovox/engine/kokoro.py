"""Optional Kokoro TTS adapter."""

from __future__ import annotations

import io
from importlib.util import find_spec
import os
from pathlib import Path

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import CapabilityHealth, CapabilityStatusEnum, RuntimeProfile, TtsRequest, TtsResult
from eccovox.engine.base import TtsEngineAdapter


class KokoroTtsEngineAdapter(TtsEngineAdapter):
    """Adapter for Kokoro, loaded only when optional TTS dependencies are installed."""

    engine_name = "kokoro"

    def __init__(self, model_cache_dir: Path | None = None) -> None:
        self._model_cache_dir = model_cache_dir

    def health(self, profile: RuntimeProfile) -> CapabilityHealth:
        if find_spec("kokoro") is None or find_spec("soundfile") is None:
            return CapabilityHealth(
                status=CapabilityStatusEnum.UNAVAILABLE,
                engine=self.engine_name,
                formats=self.supported_formats,
                safe_message="Kokoro TTS extra is not installed.",
            )
        return super().health(profile)

    def synthesize(self, request: TtsRequest, profile: RuntimeProfile) -> TtsResult:
        if self._model_cache_dir is not None:
            cache_dir = self._model_cache_dir / "huggingface"
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("HF_HOME", str(cache_dir))
        try:
            import soundfile as sf
            from kokoro import KPipeline
        except ImportError as exc:
            raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Kokoro TTS extra is not installed.") from exc

        language = profile.language or request.language or "pt-BR"
        lang_code = "p" if language.lower().startswith("pt") else language[:1].lower()
        response_format = profile.response_format or "mp3"
        if response_format not in self.supported_formats:
            raise EccoVoxError(ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT, "Requested TTS format is not supported.")

        try:
            import numpy as np
            pipeline = KPipeline(lang_code=lang_code)
            generator = pipeline(request.input_text, voice=profile.voice, speed=profile.speed or 1.0)
            audio_chunks = [item[-1] for item in generator]
            if not audio_chunks:
                raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine returned no audio.")
            audio = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
            buffer = io.BytesIO()
            sf.write(buffer, audio, 24000, format=response_format.upper())
        except EccoVoxError:
            raise
        except Exception as exc:
            raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine failed to synthesize text.") from exc

        return TtsResult(audio=buffer.getvalue(), content_type=f"audio/{response_format}", response_format=response_format)
