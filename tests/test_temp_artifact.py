from pathlib import Path

from eccovox.util.temp_artifact import temporary_artifact


def test_temporaryArtifact_shouldDeleteFile_whenContextExits(tmp_path: Path) -> None:
    with temporary_artifact(tmp_path, suffix=".wav") as path:
        path.write_bytes(b"audio")
        assert path.exists()

    assert not path.exists()
