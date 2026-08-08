from pathlib import Path, PurePosixPath
import importlib.util
import os
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


def test_systemd_unit_uses_installed_runtime_and_restart_policy(monkeypatch) -> None:
    import scripts.manage as manage

    root = PurePosixPath("/opt/Ecco Vox")
    monkeypatch.setattr(manage, "ROOT", root)
    monkeypatch.setattr(manage, "VENV_PYTHON", root / ".venv" / "bin" / "python")
    monkeypatch.setattr(manage, "CONFIG", root / "eccovox.toml")

    unit = manage.systemd_unit("voice", "voice")

    assert "User=voice" in unit
    assert "Group=voice" in unit
    assert f'WorkingDirectory="{root}"' in unit
    assert f'ExecStart="{root / ".venv" / "bin" / "python"}" -m eccovox.cli serve' in unit
    assert f'--config "{root / "eccovox.toml"}"' in unit
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_systemd_install_writes_unit_enables_but_does_not_start(
    tmp_path: Path, monkeypatch
) -> None:
    import scripts.manage as manage

    unit_path = tmp_path / "eccovox.service"
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(manage, "SYSTEMD_UNIT", unit_path)
    monkeypatch.setattr(manage, "require_root", lambda: None)
    monkeypatch.setattr(manage, "resolve_service_identity", lambda _user: ("voice", "audio"))
    monkeypatch.setattr(manage.subprocess, "run", fake_run)

    assert manage.systemd_install("voice") == 0
    assert unit_path.exists()
    assert "User=voice" in unit_path.read_text(encoding="utf-8")
    assert ["systemctl", "daemon-reload"] in calls
    assert ["systemctl", "enable", "eccovox.service"] in calls
    assert not any("start" in command for command in calls)


def test_service_control_dispatches_to_systemd(monkeypatch) -> None:
    import scripts.manage as manage

    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(manage, "service_platform", lambda: "linux")
    monkeypatch.setattr(manage.subprocess, "run", fake_run)

    assert manage.service_control("restart") == 0
    assert calls == [["systemctl", "restart", "eccovox.service"]]


@pytest.mark.skipif(
    os.name != "nt" or importlib.util.find_spec("servicemanager") is None,
    reason="Windows service dependencies unavailable",
)
def test_windows_service_bootstraps_pywin32_from_virtualenv() -> None:
    import eccovox.windows_service as service

    assert service.servicemanager is not None
    assert service.win32serviceutil is not None
