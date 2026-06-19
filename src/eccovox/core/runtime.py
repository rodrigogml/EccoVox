"""Core EccoVox runtime orchestration."""

from __future__ import annotations

from eccovox import __version__
from eccovox.core.concurrency import CapacityLimiter
from eccovox.core.config import stt_profile, tts_profile
from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import (
    CapabilityHealth,
    CapabilityStatusEnum,
    RuntimeConfiguration,
    RuntimeHealth,
    SttRequest,
    SttResult,
    TtsRequest,
    TtsResult,
)
from eccovox.engine.base import SttEngineAdapter, TtsEngineAdapter
from eccovox.engine.registry import stt_adapter, tts_adapter


class SpeechRuntime:
    """Runtime service shared by HTTP and CLI entrypoints."""

    def __init__(
        self,
        config: RuntimeConfiguration,
        stt_engine: SttEngineAdapter | None = None,
        tts_engine: TtsEngineAdapter | None = None,
    ) -> None:
        self.config = config
        self._stt_engine = stt_engine or stt_adapter(config)
        self._tts_engine = tts_engine or tts_adapter(config)
        self._stt_limiter = CapacityLimiter(config.stt.max_concurrent, config.stt.queue_size)
        self._tts_limiter = CapacityLimiter(config.tts.max_concurrent, config.tts.queue_size)

    def health(self) -> RuntimeHealth:
        """Return idempotent runtime health without executing STT or TTS work."""

        stt = self._stt_health()
        tts = self._tts_health()
        status = self._global_status(stt, tts)
        return RuntimeHealth(status=status, version=__version__, capabilities={"stt": stt, "tts": tts})

    def transcribe(self, request: SttRequest) -> SttResult:
        """Execute one STT operation."""

        if not self.config.stt.enabled:
            raise EccoVoxError(ErrorCodeEnum.CAPABILITY_DISABLED, "STT capability is disabled by configuration.")
        if not request.audio:
            raise EccoVoxError(ErrorCodeEnum.INVALID_AUDIO, "Audio input is required.")
        if len(request.audio) > self.config.stt.max_audio_bytes:
            raise EccoVoxError(ErrorCodeEnum.INVALID_AUDIO, "Audio input exceeds configured size limit.")
        profile = stt_profile(self.config, request)
        with self._stt_limiter.acquire():
            return self._stt_engine.transcribe(request, profile)

    def synthesize(self, request: TtsRequest) -> TtsResult:
        """Execute one TTS operation."""

        if not self.config.tts.enabled:
            raise EccoVoxError(ErrorCodeEnum.CAPABILITY_DISABLED, "TTS capability is disabled by configuration.")
        if not request.input_text.strip():
            raise EccoVoxError(ErrorCodeEnum.INVALID_TEXT, "Text input is required.")
        if len(request.input_text) > self.config.tts.max_text_chars:
            raise EccoVoxError(ErrorCodeEnum.INVALID_TEXT, "Text input exceeds configured size limit.")
        profile = tts_profile(self.config, request)
        with self._tts_limiter.acquire():
            return self._tts_engine.synthesize(request, profile)

    def _stt_health(self) -> CapabilityHealth:
        if not self.config.stt.enabled:
            return CapabilityHealth(status=CapabilityStatusEnum.DISABLED, safe_message="STT capability is disabled by configuration.")
        try:
            return self._stt_engine.health(stt_profile(self.config, SttRequest(audio=b"x")))
        except Exception:
            return CapabilityHealth(status=CapabilityStatusEnum.UNAVAILABLE, engine=self.config.stt.engine, safe_message="STT engine is unavailable.")

    def _tts_health(self) -> CapabilityHealth:
        if not self.config.tts.enabled:
            return CapabilityHealth(status=CapabilityStatusEnum.DISABLED, safe_message="TTS capability is disabled by configuration.")
        try:
            return self._tts_engine.health(tts_profile(self.config, TtsRequest(input_text="health")))
        except Exception:
            return CapabilityHealth(status=CapabilityStatusEnum.UNAVAILABLE, engine=self.config.tts.engine, safe_message="TTS engine is unavailable.")

    def _global_status(self, stt: CapabilityHealth, tts: CapabilityHealth) -> CapabilityStatusEnum:
        statuses = [stt.status, tts.status]
        enabled_statuses = [status for status in statuses if status != CapabilityStatusEnum.DISABLED]
        if not enabled_statuses:
            return CapabilityStatusEnum.DISABLED
        if all(status == CapabilityStatusEnum.READY for status in enabled_statuses):
            return CapabilityStatusEnum.READY
        if any(status == CapabilityStatusEnum.READY for status in enabled_statuses):
            return CapabilityStatusEnum.DEGRADED
        return CapabilityStatusEnum.UNAVAILABLE
