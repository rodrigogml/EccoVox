"""Install and manage a local EccoVox server or operating-system service."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "Scripts" / "python.exe" if os.name == "nt" else VENV / "bin" / "python"
CONFIG = ROOT / "eccovox.toml"
CONFIG_MODEL = ROOT / "eccovox.toml.model"
DEFAULT_STATE_DIR = ROOT / ".eccovox" / "state"
STATE_FILE = DEFAULT_STATE_DIR / "server.json"
LOG_DIR = ROOT / ".eccovox" / "logs"
SYSTEMD_UNIT = Path("/etc/systemd/system/eccovox.service")
SERVICE_NAME = "EccoVox"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "install", "start", "stop", "kill", "restart", "status", "run",
        "service-install", "service-remove", "service-start", "service-stop",
        "service-restart", "service-status",
    ))
    parser.add_argument("--extras", default="stt-gpu,tts,service", help="Optional dependency groups used by install.")
    parser.add_argument(
        "--service-user",
        help="Linux account that will run the systemd service (defaults to SUDO_USER/current user).",
    )
    args = parser.parse_args()
    actions = {
        "install": lambda: install(args.extras),
        "start": start,
        "stop": lambda: stop(force=False),
        "kill": lambda: stop(force=True),
        "restart": restart,
        "status": status,
        "run": run,
        "service-install": lambda: service_install(args.service_user),
        "service-remove": service_remove,
        "service-start": lambda: service_control("start"),
        "service-stop": lambda: service_control("stop"),
        "service-restart": lambda: service_control("restart"),
        "service-status": service_status,
    }
    try:
        return int(actions[args.command]() or 0)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


def install(extras: str) -> int:
    if not VENV_PYTHON.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    target = f".[{extras}]" if extras.strip() else "."
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT, check=True)
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-e", target], cwd=ROOT, check=True)
    if not CONFIG.exists():
        shutil.copyfile(CONFIG_MODEL, CONFIG)
    print(json.dumps({"ok": True, "python": str(VENV_PYTHON), "config": str(CONFIG)}, ensure_ascii=False))
    return 0


def start() -> int:
    existing = read_state()
    if existing and is_owned_process(existing):
        print(json.dumps({"ok": True, "status": "running", "pid": existing["pid"]}))
        return 0
    require_installation()
    DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    stdout = (LOG_DIR / "server.log").open("ab")
    stderr = (LOG_DIR / "server-error.log").open("ab")
    process = subprocess.Popen(
        command(), cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
        creationflags=creation_flags, close_fds=True,
    )
    state = {"pid": process.pid, "created": process_create_time(process.pid), "command": command()}
    write_state(state)
    if not wait_health(30):
        raise RuntimeError(f"Servidor não ficou saudável; consulte {LOG_DIR}.")
    time.sleep(0.5)
    if process.poll() is not None or not is_owned_process(state):
        STATE_FILE.unlink(missing_ok=True)
        raise RuntimeError(
            "O endpoint respondeu, mas o processo EccoVox recém-iniciado não permaneceu ativo; "
            "verifique se a porta já está ocupada."
        )
    print(json.dumps({"ok": True, "status": "running", "pid": process.pid}))
    return 0


def stop(force: bool) -> int:
    state = read_state()
    if not state or not is_owned_process(state):
        STATE_FILE.unlink(missing_ok=True)
        print(json.dumps({"ok": True, "status": "stopped"}))
        return 0
    import psutil
    process = psutil.Process(int(state["pid"]))
    descendants = process.children(recursive=True)
    targets = descendants + [process]
    for target in reversed(targets):
        try:
            target.kill() if force else target.terminate()
        except psutil.NoSuchProcess:
            pass
    _gone, alive = psutil.wait_procs(targets, timeout=15)
    if alive and not force:
        for target in alive:
            try:
                target.kill()
            except psutil.NoSuchProcess:
                pass
        _gone, alive = psutil.wait_procs(alive, timeout=5)
    if alive:
        raise RuntimeError("A árvore do processo não encerrou completamente.")
    STATE_FILE.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "status": "stopped", "forced": force}))
    return 0


def restart() -> int:
    stop(force=False)
    return start()


def status() -> int:
    state = read_state()
    running = bool(state and is_owned_process(state))
    payload = {"ok": True, "status": "running" if running else "stopped"}
    if running:
        payload["pid"] = state["pid"]
    print(json.dumps(payload))
    return 0 if running else 3


def run() -> int:
    require_installation()
    return subprocess.run(command(), cwd=ROOT).returncode


def service_platform() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    raise RuntimeError("Serviços são suportados somente no Windows e no Linux com systemd.")


def service_install(service_user: str | None = None) -> int:
    require_installation()
    if service_platform() == "linux":
        return systemd_install(service_user)
    if service_user:
        raise RuntimeError("--service-user é aplicável somente ao Linux.")
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "eccovox.windows_service", "--startup", "auto", "install"],
        cwd=ROOT,
    )
    if result.returncode:
        raise RuntimeError("O serviço EccoVox não foi instalado; execute em um PowerShell elevado.")
    configure_windows_service_environment()
    if not service_exists():
        raise RuntimeError("O serviço EccoVox não foi localizado após a instalação.")
    return 0


def service_remove() -> int:
    if service_platform() == "linux":
        return systemd_remove()
    service_control("stop", check=False)
    result = subprocess.run([str(VENV_PYTHON), "-m", "eccovox.windows_service", "remove"], cwd=ROOT)
    if result.returncode or service_exists():
        raise RuntimeError("O serviço EccoVox não foi removido; execute em um PowerShell elevado.")
    return 0


def service_exists() -> bool:
    if service_platform() == "linux":
        return SYSTEMD_UNIT.exists()
    import psutil
    try:
        psutil.win_service_get("EccoVox").as_dict()
        return True
    except psutil.NoSuchProcess:
        return False


def windows_service_python_path() -> str:
    site_packages = VENV / "Lib" / "site-packages"
    candidates = (
        site_packages,
        site_packages / "win32",
        site_packages / "win32" / "lib",
        site_packages / "pythonwin",
        ROOT / "src",
    )
    return ";".join(str(path.resolve()) for path in candidates if path.is_dir())


def configure_windows_service_environment() -> None:
    if service_platform() != "windows":
        raise RuntimeError("O ambiente pywin32 é aplicável somente ao Windows.")
    import winreg

    key_path = rf"SYSTEM\CurrentControlSet\Services\{SERVICE_NAME}"
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
    ) as key:
        try:
            existing, _kind = winreg.QueryValueEx(key, "Environment")
        except FileNotFoundError:
            existing = []
        preserved = [
            value for value in existing
            if not str(value).upper().startswith("PYTHONPATH=")
        ]
        winreg.SetValueEx(
            key,
            "Environment",
            0,
            winreg.REG_MULTI_SZ,
            [*preserved, f"PYTHONPATH={windows_service_python_path()}"],
        )


def service_control(action: str, check: bool = True) -> int:
    platform = service_platform()
    if platform == "linux":
        result = subprocess.run(["systemctl", action, "eccovox.service"])
    elif action == "restart":
        service_control("stop", check=False)
        return service_control("start", check=check)
    else:
        result = subprocess.run(["sc.exe", action, SERVICE_NAME])
    if check and result.returncode:
        raise RuntimeError(f"O comando de serviço '{action}' falhou com código {result.returncode}.")
    return result.returncode


def service_status() -> int:
    platform = service_platform()
    if platform == "linux":
        active = subprocess.run(
            ["systemctl", "is-active", "--quiet", "eccovox.service"]
        ).returncode == 0
        enabled = subprocess.run(
            ["systemctl", "is-enabled", "--quiet", "eccovox.service"]
        ).returncode == 0
        installed = SYSTEMD_UNIT.exists()
    else:
        installed = service_exists()
        active = False
        enabled = installed
        if installed:
            import psutil
            service = psutil.win_service_get(SERVICE_NAME).as_dict()
            active = service.get("status") == "running"
            enabled = service.get("start_type") == "automatic"
    print(json.dumps({
        "ok": True,
        "platform": platform,
        "installed": installed,
        "enabled": enabled,
        "status": "running" if active else "stopped",
    }))
    return 0 if active else 3


def require_root() -> None:
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        raise RuntimeError("Execute esta operação com sudo/root.")


def resolve_service_identity(service_user: str | None) -> tuple[str, str]:
    import pwd

    username = (
        service_user
        or os.environ.get("SUDO_USER")
        or pwd.getpwuid(os.getuid()).pw_name
    )
    try:
        account = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"Usuário Linux inexistente: {username}") from exc
    return account.pw_name, _group_name(account.pw_gid)


def _group_name(group_id: int) -> str:
    import grp

    return grp.getgrgid(group_id).gr_name


def systemd_quote(value: Path | str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def systemd_unit(service_user: str, service_group: str) -> str:
    return "\n".join((
        "[Unit]",
        "Description=EccoVox Local Voice Runtime",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
        f"User={service_user}",
        f"Group={service_group}",
        f"WorkingDirectory={systemd_quote(ROOT)}",
        f"ExecStart={systemd_quote(VENV_PYTHON)} -m eccovox.cli serve --config {systemd_quote(CONFIG)}",
        "Restart=on-failure",
        "RestartSec=5",
        "Environment=PYTHONUNBUFFERED=1",
        "NoNewPrivileges=true",
        "PrivateTmp=true",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ))


def systemd_install(service_user: str | None) -> int:
    require_root()
    user, group = resolve_service_identity(service_user)
    temporary = SYSTEMD_UNIT.with_suffix(".service.tmp")
    temporary.write_text(systemd_unit(user, group), encoding="utf-8")
    temporary.replace(SYSTEMD_UNIT)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "eccovox.service"], check=True)
    print(json.dumps({
        "ok": True,
        "platform": "linux",
        "installed": True,
        "enabled": True,
        "user": user,
        "unit": str(SYSTEMD_UNIT),
    }))
    return 0


def systemd_remove() -> int:
    require_root()
    service_control("stop", check=False)
    subprocess.run(["systemctl", "disable", "eccovox.service"], check=False)
    SYSTEMD_UNIT.unlink(missing_ok=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "reset-failed", "eccovox.service"], check=False)
    print(json.dumps({"ok": True, "platform": "linux", "installed": False}))
    return 0


def command() -> list[str]:
    return [str(VENV_PYTHON), "-m", "eccovox.cli", "serve", "--config", str(CONFIG)]


def require_installation() -> None:
    if not VENV_PYTHON.exists() or not CONFIG.exists():
        raise RuntimeError("Execute 'eccovox.ps1 install' antes desta operação.")


def read_state() -> dict | None:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_state(state: dict) -> None:
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.replace(STATE_FILE)


def process_create_time(pid: int) -> float:
    import psutil
    return psutil.Process(pid).create_time()


def is_owned_process(state: dict) -> bool:
    try:
        import psutil
        process = psutil.Process(int(state["pid"]))
        if abs(process.create_time() - float(state["created"])) > 1:
            return False
        command_line = " ".join(process.cmdline()).casefold()
        return "eccovox.cli" in command_line and str(CONFIG).casefold() in command_line
    except (KeyError, ValueError, OSError, psutil.Error):
        return False


def wait_health(timeout: int) -> bool:
    data = tomllib.loads(CONFIG.read_text(encoding="utf-8-sig"))
    server = data.get("server", {})
    host = str(server.get("host", "127.0.0.1"))
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    port = int(server.get("port", 8870))
    endpoint = f"http://{host}:{port}/v1/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(endpoint, timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
