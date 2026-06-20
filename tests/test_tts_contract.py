import sys
import types

import pytest

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import CapabilityEnum, RuntimeConfiguration, RuntimeProfile, SttConfig, TtsConfig, TtsRequest
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter
from eccovox.engine.kokoro import KokoroTtsEngineAdapter


def test_synthesize_shouldReturnAudio_whenTextIsValid() -> None:
    runtime = SpeechRuntime(
        RuntimeConfiguration(stt=SttConfig(engine="fake-stt"), tts=TtsConfig(engine="fake-tts")),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )

    result = runtime.synthesize(TtsRequest(input_text="hello", response_format="mp3"))

    assert result.audio == b"FAKEAUDIO"
    assert result.content_type == "audio/mp3"


def test_synthesize_shouldRaiseInvalidText_whenTextIsBlank() -> None:
    runtime = SpeechRuntime(RuntimeConfiguration(), FakeSttEngineAdapter(), FakeTtsEngineAdapter())

    with pytest.raises(EccoVoxError) as error:
        runtime.synthesize(TtsRequest(input_text=" "))

    assert error.value.code == ErrorCodeEnum.INVALID_TEXT


def test_synthesize_shouldRaiseCapabilityDisabled_whenTtsIsDisabled() -> None:
    runtime = SpeechRuntime(
        RuntimeConfiguration(tts=TtsConfig(enabled=False)),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )

    with pytest.raises(EccoVoxError) as error:
        runtime.synthesize(TtsRequest(input_text="hello"))

    assert error.value.code == ErrorCodeEnum.CAPABILITY_DISABLED


def test_kokoroAdapter_shouldWriteAllGeneratedAudioChunks(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakePipeline:
        def __init__(self, lang_code: str) -> None:
            captured["lang_code"] = lang_code

        def __call__(self, text: str, voice: str | None, speed: float) -> list[tuple[str, str, list[int]]]:
            captured["text"] = text
            captured["voice"] = voice
            captured["speed"] = speed
            return [("part", "one", [1, 2]), ("part", "two", [3, 4])]

    def fake_concatenate(chunks: list[list[int]]) -> list[int]:
        captured["chunks"] = chunks
        return [sample for chunk in chunks for sample in chunk]

    def fake_write(buffer, audio: list[int], samplerate: int, format: str) -> None:
        captured["audio"] = audio
        captured["samplerate"] = samplerate
        captured["format"] = format
        buffer.write(bytes(audio))

    monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakePipeline))
    monkeypatch.setitem(sys.modules, "numpy", types.SimpleNamespace(concatenate=fake_concatenate))
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=fake_write))

    result = KokoroTtsEngineAdapter().synthesize(
        TtsRequest(input_text="linha um\nlinha dois"),
        RuntimeProfile(
            name="diagnostic",
            capability=CapabilityEnum.TTS,
            engine="kokoro",
            voice="pf_dora",
            language="pt-BR",
            response_format="wav",
        ),
    )

    assert captured["chunks"] == [[1, 2], [3, 4]]
    assert captured["audio"] == [1, 2, 3, 4]
    assert captured["samplerate"] == 24000
    assert captured["format"] == "WAV"
    assert result.audio == b"\x01\x02\x03\x04"
    assert result.content_type == "audio/wav"
