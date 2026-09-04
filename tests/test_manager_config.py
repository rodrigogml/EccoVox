from pathlib import Path

import pytest

from scripts.manager_config import (
    ConfigurationError,
    parse_assignment,
    read_configuration,
    update_configuration,
)


MODEL = """# local config
[server]
host = "127.0.0.1" # keep
port = 8870

[tts]
voice = "pf_dora"
enabled = true

[custom]
preserve = "yes"
"""


def test_configuration_update_is_typed_atomic_and_preserves_unknown_sections(tmp_path: Path) -> None:
    config = tmp_path / "eccovox.toml"
    state = tmp_path / ".eccovox" / "state"
    config.write_text(MODEL, encoding="utf-8")

    backup = update_configuration(
        config,
        {
            "server.port": 9000,
            "tts.voice": "pm_alex",
            "tts.response_format": "wav",
        },
        state_dir=state,
    )
    content = config.read_text(encoding="utf-8")
    values = read_configuration(config)

    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == MODEL
    assert values["server.port"] == 9000
    assert values["tts.voice"] == "pm_alex"
    assert values["tts.response_format"] == "wav"
    assert 'preserve = "yes"' in content
    assert 'host = "127.0.0.1" # keep' in content


@pytest.mark.parametrize(
    ("assignment", "expected"),
    (
        ("server.port=9001", ("server.port", 9001)),
        ("tts.enabled=não", ("tts.enabled", False)),
        ("tts.encoder_path=C:/tools/ffmpeg.exe", ("tts.encoder_path", "C:/tools/ffmpeg.exe")),
    ),
)
def test_assignment_parser_accepts_only_known_typed_values(assignment: str, expected: tuple[str, object]) -> None:
    assert parse_assignment(assignment) == expected


def test_assignment_parser_rejects_unknown_key_and_unsafe_port() -> None:
    with pytest.raises(ConfigurationError):
        parse_assignment("unknown.value=x")
    with pytest.raises(ConfigurationError):
        parse_assignment("server.port=70000")


def test_configuration_keeps_only_five_recoverable_backups(tmp_path: Path) -> None:
    config = tmp_path / "eccovox.toml"
    state = tmp_path / ".eccovox" / "state"
    config.write_text(MODEL, encoding="utf-8")

    for port in range(9000, 9007):
        update_configuration(config, {"server.port": port}, state_dir=state)

    assert len(list((state / "config-backups").glob("eccovox-*.toml"))) == 5
