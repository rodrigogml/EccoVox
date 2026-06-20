"""Optional faster-whisper STT adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import RuntimeProfile, SttRequest, SttResult
from eccovox.engine.base import SttEngineAdapter


class FasterWhisperSttEngineAdapter(SttEngineAdapter):
    """Adapter for `faster-whisper`, loaded only when the optional dependency is installed."""

    engine_name = "faster-whisper"

    def transcribe(self, request: SttRequest, profile: RuntimeProfile) -> SttResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "faster-whisper extra is not installed.") from exc

        model_name = profile.model or "large-v3"
        try:
            model = WhisperModel(model_name, device=profile.device or "cpu", compute_type=profile.compute_type or "int8")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(request.audio)
                temp_path = Path(temp_file.name)
            try:
                segments, info = model.transcribe(str(temp_path), language=_whisper_language(request.language), initial_prompt=request.prompt)
                text = " ".join(segment.text.strip() for segment in segments).strip()
            finally:
                temp_path.unlink(missing_ok=True)
        except EccoVoxError:
            raise
        except Exception as exc:
            raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "STT engine failed to transcribe audio.") from exc

        if not text:
            raise EccoVoxError(ErrorCodeEnum.EMPTY_TRANSCRIPTION, "STT did not identify useful text.")
        language = getattr(info, "language", None) or request.language
        probability = getattr(info, "language_probability", None)
        return SttResult(text=text, language=language, confidence=probability, metadata={"engine": self.engine_name})


def _whisper_language(language: str | None) -> str | None:
    """Convert BCP 47 language tags to the base code accepted by faster-whisper."""

    if language is None or not language.strip():
        return None
    return language.split("-", maxsplit=1)[0].lower()
