import os
from pathlib import Path

import pytest

from eccovox.core.models import RuntimeProfile, CapabilityEnum, SttRequest, TtsRequest
from eccovox.engine.faster_whisper import FasterWhisperSttEngineAdapter
from eccovox.engine.kokoro import KokoroTtsEngineAdapter


RUN_ENGINE_TESTS = os.getenv("ECCOVOX_RUN_ENGINE_TESTS") == "1"


@pytest.mark.skipif(not RUN_ENGINE_TESTS, reason="requires optional STT engine dependency and local model availability")
def test_fasterWhisperAdapter_shouldExposeOperationalPath_whenEngineExtraIsAvailable() -> None:
    sample_path = os.getenv("ECCOVOX_STT_SAMPLE")
    if not sample_path or not Path(sample_path).exists():
        pytest.skip("ECCOVOX_STT_SAMPLE must point to a local audio sample")
    adapter = FasterWhisperSttEngineAdapter()
    profile = RuntimeProfile(
        name="diagnostic",
        capability=CapabilityEnum.STT,
        engine="faster-whisper",
        model=os.getenv("ECCOVOX_STT_MODEL", "tiny"),
        device=os.getenv("ECCOVOX_STT_DEVICE", "cpu"),
        compute_type=os.getenv("ECCOVOX_STT_COMPUTE_TYPE", "int8"),
    )

    result = adapter.transcribe(SttRequest(audio=Path(sample_path).read_bytes(), language="pt-BR"), profile)

    assert result.text


@pytest.mark.skipif(not RUN_ENGINE_TESTS, reason="requires optional TTS engine dependency and local model availability")
def test_kokoroAdapter_shouldExposeOperationalPath_whenEngineExtraIsAvailable() -> None:
    adapter = KokoroTtsEngineAdapter()
    profile = RuntimeProfile(
        name="diagnostic",
        capability=CapabilityEnum.TTS,
        engine="kokoro",
        voice="pf_dora",
        language="pt-BR",
        response_format="wav",
    )

    result = adapter.synthesize(TtsRequest(input_text="Ola"), profile)

    assert result.audio
