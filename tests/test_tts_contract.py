import pytest

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import RuntimeConfiguration, SttConfig, TtsConfig, TtsRequest
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter


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
