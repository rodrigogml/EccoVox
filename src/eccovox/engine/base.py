"""Base classes and fake adapters for speech engines."""

from __future__ import annotations

from abc import ABC, abstractmethod

from eccovox.core.models import CapabilityHealth, CapabilityStatusEnum, RuntimeProfile, SttRequest, SttResult, TtsRequest, TtsResult


class SttEngineAdapter(ABC):
    """Adapter interface for STT engines."""

    engine_name: str = "unknown"
    supported_formats: tuple[str, ...] = ("wav", "mp3", "m4a", "mp4", "ogg", "opus", "webm", "flac")

    def health(self, profile: RuntimeProfile) -> CapabilityHealth:
        """Return health for this adapter without transcribing audio."""

        return CapabilityHealth(
            status=CapabilityStatusEnum.READY,
            engine=self.engine_name,
            model=profile.model,
            device=profile.device,
            formats=self.supported_formats,
        )

    @abstractmethod
    def transcribe(self, request: SttRequest, profile: RuntimeProfile) -> SttResult:
        """Transcribe audio bytes into text."""


class TtsEngineAdapter(ABC):
    """Adapter interface for TTS engines."""

    engine_name: str = "unknown"
    supported_formats: tuple[str, ...] = ("mp3", "wav", "opus", "flac")

    def health(self, profile: RuntimeProfile) -> CapabilityHealth:
        """Return health for this adapter without synthesizing speech."""

        return CapabilityHealth(
            status=CapabilityStatusEnum.READY,
            engine=self.engine_name,
            model=profile.model,
            formats=self.supported_formats,
        )

    @abstractmethod
    def synthesize(self, request: TtsRequest, profile: RuntimeProfile) -> TtsResult:
        """Synthesize text into playable audio bytes."""


class FakeSttEngineAdapter(SttEngineAdapter):
    """Deterministic STT adapter for contract tests and development without heavy engines."""

    engine_name = "fake-stt"

    def transcribe(self, request: SttRequest, profile: RuntimeProfile) -> SttResult:
        return SttResult(text="texto transcrito", language=request.language or "pt-BR", metadata={"engine": self.engine_name})


class FakeTtsEngineAdapter(TtsEngineAdapter):
    """Deterministic TTS adapter for contract tests and development without heavy engines."""

    engine_name = "fake-tts"

    def synthesize(self, request: TtsRequest, profile: RuntimeProfile) -> TtsResult:
        response_format = profile.response_format or "mp3"
        return TtsResult(audio=b"FAKEAUDIO", content_type=f"audio/{response_format}", response_format=response_format)
