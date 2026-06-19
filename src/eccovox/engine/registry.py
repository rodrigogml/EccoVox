"""Engine registry and adapter selection."""

from __future__ import annotations

from eccovox.core.models import RuntimeConfiguration
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter, SttEngineAdapter, TtsEngineAdapter
from eccovox.engine.faster_whisper import FasterWhisperSttEngineAdapter
from eccovox.engine.kokoro import KokoroTtsEngineAdapter


def stt_adapter(config: RuntimeConfiguration) -> SttEngineAdapter:
    """Return the configured STT adapter."""

    if config.stt.engine == "fake-stt":
        return FakeSttEngineAdapter()
    return FasterWhisperSttEngineAdapter()


def tts_adapter(config: RuntimeConfiguration) -> TtsEngineAdapter:
    """Return the configured TTS adapter."""

    if config.tts.engine == "fake-tts":
        return FakeTtsEngineAdapter()
    return KokoroTtsEngineAdapter()
