from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest


def test_start_shouldRejectHealthFromAnotherProcess(tmp_path: Path, monkeypatch) -> None:
    import scripts.manage as manage

    state_file = tmp_path / "state" / "server.json"
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(manage, "STATE_FILE", state_file)
    monkeypatch.setattr(manage, "DEFAULT_STATE_DIR", state_file.parent)
    monkeypatch.setattr(manage, "LOG_DIR", log_dir)
    monkeypatch.setattr(manage, "require_installation", lambda: None)
    monkeypatch.setattr(manage, "wait_health", lambda _timeout: True)
    monkeypatch.setattr(manage, "process_create_time", lambda _pid: 1.0)
    monkeypatch.setattr(manage.time, "sleep", lambda _seconds: None)
    process = type("Process", (), {"pid": 123, "poll": lambda self: 1})()

    with patch.object(subprocess, "Popen", return_value=process):
        with pytest.raises(RuntimeError, match="não permaneceu ativo"):
            manage.start()

    assert not state_file.exists()
