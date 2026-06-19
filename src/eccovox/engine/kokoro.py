"""Optional Kokoro TTS adapter."""

from __future__ import annotations

import io

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import RuntimeProfile, TtsRequest, TtsResult
from eccovox.engine.base import TtsEngineAdapter


class KokoroTtsEngineAdapter(TtsEngineAdapter):
    """Adapter for Kokoro, loaded only when optional TTS dependencies are installed."""

    engine_name = "kokoro"

    def synthesize(self, request: TtsRequest, profile: RuntimeProfile) -> TtsResult:
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
            pipeline = KPipeline(lang_code=lang_code)
            generator = pipeline(request.input_text, voice=profile.voice, speed=profile.speed or 1.0)
            audio_chunks = [item[-1] for item in generator]
            if not audio_chunks:
                raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine returned no audio.")
            buffer = io.BytesIO()
            sf.write(buffer, audio_chunks[0], 24000, format=response_format.upper())
        except EccoVoxError:
            raise
        except Exception as exc:
            raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "TTS engine failed to synthesize text.") from exc

        return TtsResult(audio=buffer.getvalue(), content_type=f"audio/{response_format}", response_format=response_format)
