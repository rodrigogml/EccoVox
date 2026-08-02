from pathlib import Path

import pytest

from eccovox.core.config import load_configuration, stt_profile, tts_profile
from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import SttRequest, TtsRequest


def test_load_configuration_shouldReturnDefaults_whenPathIsAbsent() -> None:
    config = load_configuration()

    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8870
    assert config.runtime.default_profile == "balanced"
    assert config.runtime.model_cache_dir.is_absolute()
    assert config.stt.max_concurrent == 1
    assert config.tts.queue_size == 0


def test_load_configuration_shouldReadToml_whenFileIsValid(tmp_path: Path) -> None:
    config_file = tmp_path / "eccovox.toml"
    config_file.write_text(
        """
[server]
host = "0.0.0.0"
port = 9000

[runtime]
temp_dir = ".tmp"
request_timeout_seconds = 30
profiles = ["default", "balanced"]
default_profile = "balanced"

[stt]
enabled = true
engine = "fake-stt"
max_audio_bytes = 64
max_concurrent = 1
queue_size = 0

[tts]
enabled = true
engine = "fake-tts"
max_text_chars = 32
max_concurrent = 1
queue_size = 0
""",
        encoding="utf-8",
    )

    config = load_configuration(config_file)

    assert config.server.host == "0.0.0.0"
    assert config.server.port == 9000
    assert config.stt.engine == "fake-stt"
    assert config.tts.engine == "fake-tts"
    assert config.runtime.temp_dir == (tmp_path / ".tmp").resolve()


def test_loadConfiguration_shouldAcceptUtf8Bom_whenFileComesFromWindowsTooling(tmp_path: Path) -> None:
    config_file = tmp_path / "eccovox.toml"
    config_file.write_text('\ufeff[stt]\nengine = "fake-stt"\n', encoding="utf-8")

    config = load_configuration(config_file)

    assert config.stt.engine == "fake-stt"


def test_loadConfiguration_shouldResolveRuntimePaths_fromConfigDirectory(tmp_path: Path) -> None:
    nested = tmp_path / "config"
    nested.mkdir()
    config_file = nested / "eccovox.toml"
    config_file.write_text(
        '[runtime]\nmodel_cache_dir = "models"\nstate_dir = "state"\nlog_dir = "logs"\n',
        encoding="utf-8",
    )

    config = load_configuration(config_file)

    assert config.runtime.model_cache_dir == (nested / "models").resolve()
    assert config.runtime.state_dir == (nested / "state").resolve()
    assert config.runtime.log_dir == (nested / "logs").resolve()


def test_stt_profile_shouldRejectUnknownProfile_whenOverrideIsInvalid() -> None:
    config = load_configuration()

    with pytest.raises(EccoVoxError) as error:
        stt_profile(config, SttRequest(audio=b"abc", profile="missing"))

    assert error.value.code == ErrorCodeEnum.INVALID_OVERRIDE


def test_tts_profile_shouldRejectUnsupportedFormat_whenFormatIsInvalid() -> None:
    config = load_configuration()

    with pytest.raises(EccoVoxError) as error:
        tts_profile(config, TtsRequest(input_text="hello", response_format="aac"))

    assert error.value.code == ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT
