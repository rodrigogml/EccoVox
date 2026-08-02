"""Install and manage a local EccoVox server or Windows service."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "install", "start", "stop", "kill", "restart", "status", "run",
        "service-install", "service-remove", "service-start", "service-stop",
    ))
    parser.add_argument("--extras", default="stt-gpu,service", help="Optional dependency groups used by install.")
    args = parser.parse_args()
    actions = {
        "install": lambda: install(args.extras),
        "start": start,
        "stop": lambda: stop(force=False),
        "kill": lambda: stop(force=True),
        "restart": restart,
        "status": status,
        "run": run,
        "service-install": service_install,
        "service-remove": service_remove,
        "service-start": lambda: service_control("start"),
        "service-stop": lambda: service_control("stop"),
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


def service_install() -> int:
    require_installation()
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "eccovox.windows_service", "--startup", "auto", "install"],
        cwd=ROOT,
    )
    if result.returncode or not service_exists():
        raise RuntimeError("O serviço EccoVox não foi instalado; execute em um PowerShell elevado.")
    return 0


def service_remove() -> int:
    service_control("stop", check=False)
    result = subprocess.run([str(VENV_PYTHON), "-m", "eccovox.windows_service", "remove"], cwd=ROOT)
    if result.returncode or service_exists():
        raise RuntimeError("O serviço EccoVox não foi removido; execute em um PowerShell elevado.")
    return 0


def service_exists() -> bool:
    if os.name != "nt":
        return False
    import psutil
    try:
        psutil.win_service_get("EccoVox").as_dict()
        return True
    except psutil.NoSuchProcess:
        return False


def service_control(action: str, check: bool = True) -> int:
    if os.name != "nt":
        raise RuntimeError("Gerenciamento de serviço está disponível somente no Windows.")
    result = subprocess.run(["sc.exe", action, "EccoVox"])
    if check and result.returncode:
        raise RuntimeError(f"sc.exe {action} falhou com código {result.returncode}.")
    return result.returncode


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
