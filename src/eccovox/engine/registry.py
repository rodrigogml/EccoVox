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
    return FasterWhisperSttEngineAdapter(
        temp_dir=config.runtime.temp_dir,
        model_cache_dir=config.runtime.model_cache_dir,
    )


def tts_adapter(config: RuntimeConfiguration) -> TtsEngineAdapter:
    """Return the configured TTS adapter."""

    if config.tts.engine == "fake-tts":
        return FakeTtsEngineAdapter()
    return KokoroTtsEngineAdapter(
        model_cache_dir=config.runtime.model_cache_dir,
        encoder_path=config.tts.encoder_path,
        max_segment_chars=config.tts.max_segment_chars,
    )
