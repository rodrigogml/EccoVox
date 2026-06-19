import pytest

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import RuntimeConfiguration, SttConfig, SttRequest, TtsConfig
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter


def test_transcribe_shouldReturnText_whenAudioIsValid() -> None:
    runtime = SpeechRuntime(
        RuntimeConfiguration(stt=SttConfig(engine="fake-stt"), tts=TtsConfig(engine="fake-tts")),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )

    result = runtime.transcribe(SttRequest(audio=b"audio", language="pt-BR"))

    assert result.text == "texto transcrito"
    assert result.language == "pt-BR"


def test_transcribe_shouldRaiseInvalidAudio_whenAudioIsEmpty() -> None:
    runtime = SpeechRuntime(RuntimeConfiguration(), FakeSttEngineAdapter(), FakeTtsEngineAdapter())

    with pytest.raises(EccoVoxError) as error:
        runtime.transcribe(SttRequest(audio=b""))

    assert error.value.code == ErrorCodeEnum.INVALID_AUDIO


def test_transcribe_shouldRaiseCapabilityDisabled_whenSttIsDisabled() -> None:
    runtime = SpeechRuntime(
        RuntimeConfiguration(stt=SttConfig(enabled=False)),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )

    with pytest.raises(EccoVoxError) as error:
        runtime.transcribe(SttRequest(audio=b"audio"))

    assert error.value.code == ErrorCodeEnum.CAPABILITY_DISABLED
