from dataclasses import replace

from eccovox.core.models import CapabilityStatusEnum, RuntimeConfiguration, SttConfig, TtsConfig
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter


def test_health_shouldReturnReady_whenBothCapabilitiesAreReady() -> None:
    config = RuntimeConfiguration(
        stt=SttConfig(engine="fake-stt"),
        tts=TtsConfig(engine="fake-tts"),
    )

    health = SpeechRuntime(config, FakeSttEngineAdapter(), FakeTtsEngineAdapter()).health()

    assert health.status == CapabilityStatusEnum.READY
    assert health.capabilities["stt"].status == CapabilityStatusEnum.READY
    assert health.capabilities["tts"].status == CapabilityStatusEnum.READY


def test_health_shouldReturnDisabled_whenBothCapabilitiesAreDisabled() -> None:
    config = RuntimeConfiguration(
        stt=SttConfig(enabled=False),
        tts=TtsConfig(enabled=False),
    )

    health = SpeechRuntime(config, FakeSttEngineAdapter(), FakeTtsEngineAdapter()).health()

    assert health.status == CapabilityStatusEnum.DISABLED


def test_health_shouldReturnDegraded_whenOneCapabilityIsDisabledAndOtherReady() -> None:
    config = RuntimeConfiguration(
        stt=SttConfig(engine="fake-stt"),
        tts=TtsConfig(enabled=False),
    )

    health = SpeechRuntime(config, FakeSttEngineAdapter(), FakeTtsEngineAdapter()).health()

    assert health.status == CapabilityStatusEnum.READY
    assert health.capabilities["tts"].status == CapabilityStatusEnum.DISABLED
