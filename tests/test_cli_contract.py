from pathlib import Path

from typer.testing import CliRunner

from eccovox.cli import app


def test_cli_shouldShowRootHelp() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "serve" in result.stdout
    assert "transcribe" in result.stdout
    assert "synthesize" in result.stdout


def test_transcribe_shouldWriteJsonToStdout_whenUsingFakeEngine(tmp_path: Path) -> None:
    audio = tmp_path / "input.wav"
    audio.write_bytes(b"audio")
    config = _fake_config(tmp_path)

    result = CliRunner().invoke(app, ["transcribe", "--file", str(audio), "--config", str(config)])

    assert result.exit_code == 0
    assert "texto transcrito" in result.stdout
    assert result.stderr == ""


def test_synthesize_shouldWriteAudioFileAndKeepStdoutEmpty_whenUsingFakeEngine(tmp_path: Path) -> None:
    output = tmp_path / "out.mp3"
    config = _fake_config(tmp_path)

    result = CliRunner().invoke(
        app,
        ["synthesize", "--text", "hello", "--output", str(output), "--config", str(config)],
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert output.read_bytes() == b"FAKEAUDIO"


def _fake_config(tmp_path: Path) -> Path:
    config = tmp_path / "eccovox.toml"
    config.write_text(
        """
[stt]
engine = "fake-stt"

[tts]
engine = "fake-tts"
""",
        encoding="utf-8",
    )
    return config
