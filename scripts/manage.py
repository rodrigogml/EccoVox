"""Install and manage a local EccoVox server or operating-system service."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
from urllib.request import urlopen

try:
    from scripts.manager_config import (
        ConfigurationError,
        known_setting_names,
        parse_assignment,
        read_configuration,
        update_configuration,
    )
    from scripts.manager_menu import MenuApplication, PORTUGUESE_VOICES
except ModuleNotFoundError:  # Direct execution via python scripts/manage.py.
    from manager_config import (
        ConfigurationError,
        known_setting_names,
        parse_assignment,
        read_configuration,
        update_configuration,
    )
    from manager_menu import MenuApplication, PORTUGUESE_VOICES


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
KNOWN_EXTRAS = {"dev", "service", "stt", "stt-gpu", "tts", "voice"}


def bootstrap_venv_packages() -> None:
    """Allow the bootstrap interpreter to continue the menu after creating .venv."""
    candidates = [VENV / "Lib" / "site-packages"]
    candidates.extend((VENV / "lib").glob("python*/site-packages") if (VENV / "lib").is_dir() else ())
    for candidate in candidates:
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


bootstrap_venv_packages()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="menu", choices=(
        "menu", "doctor", "configure", "config-show", "voices",
        "ffmpeg-status", "ffmpeg-detect",
        "install", "start", "stop", "kill", "restart", "status", "run",
        "service-install", "service-remove", "service-start", "service-stop",
        "service-restart", "service-status",
    ))
    parser.add_argument("--extras", default="stt-gpu,tts,service", help="Optional dependency groups used by install.")
    parser.add_argument(
        "--service-user",
        help="Linux account that will run the systemd service (defaults to SUDO_USER/current user).",
    )
    parser.add_argument(
        "--set",
        dest="assignments",
        action="append",
        default=[],
        metavar="SECAO.CHAVE=VALOR",
        help="Altera uma configuração pública conhecida; pode ser repetido.",
    )
    parser.add_argument(
        "--list",
        dest="list_settings",
        action="store_true",
        help="Lista as chaves aceitas por configure.",
    )
    args = parser.parse_args()
    actions = {
        "menu": run_menu,
        "doctor": doctor,
        "configure": lambda: configure_command(args.assignments, args.list_settings),
        "config-show": show_configuration,
        "voices": list_voices,
        "ffmpeg-status": ffmpeg_status,
        "ffmpeg-detect": configure_detected_ffmpeg,
        "install": lambda: install(args.extras),
        "start": start,
        "stop": lambda: stop(force=False),
        "kill": lambda: stop(force=True),
        "restart": restart,
        "status": status,
        "run": run,
        "service-install": lambda: service_install(args.service_user),
        "service-remove": service_remove,
        "service-start": lambda: service_action("start"),
        "service-stop": lambda: service_action("stop"),
        "service-restart": lambda: service_action("restart"),
        "service-status": service_status,
    }
    try:
        return int(actions[args.command]() or 0)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


def install(extras: str) -> int:
    extras = normalize_extras(extras)
    if not VENV_PYTHON.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    target = f".[{extras}]" if extras.strip() else "."
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT, check=True)
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-e", target], cwd=ROOT, check=True)
    if not CONFIG.exists():
        shutil.copyfile(CONFIG_MODEL, CONFIG)
    bootstrap_venv_packages()
    print(json.dumps({"ok": True, "python": str(VENV_PYTHON), "config": str(CONFIG)}, ensure_ascii=False))
    return 0


def normalize_extras(extras: str) -> str:
    values = tuple(dict.fromkeys(item.strip() for item in extras.split(",") if item.strip()))
    unknown = set(values).difference(KNOWN_EXTRAS)
    if unknown:
        raise RuntimeError("Extras desconhecidos: " + ", ".join(sorted(unknown)) + ".")
    return ",".join(values)


def run_menu() -> int:
    return MenuApplication(sys.modules[__name__]).run()


def configuration_values() -> dict[str, object]:
    return read_configuration(CONFIG)


def configure_assignments(assignments: tuple[str, ...] | list[str]) -> dict[str, object]:
    parsed = dict(parse_assignment(item) for item in assignments)
    backup = update_configuration(
        CONFIG,
        parsed,
        state_dir=DEFAULT_STATE_DIR,
    )
    try:
        validate_runtime_configuration()
    except Exception as exc:
        shutil.copy2(backup, CONFIG)
        raise ConfigurationError(
            f"A configuração foi rejeitada e restaurada: {exc}"
        ) from exc
    return {
        "ok": True,
        "updated": sorted(parsed),
        "backup": str(backup),
        "restart_required": True,
    }


def validate_runtime_configuration() -> None:
    src = ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from eccovox.core.config import load_configuration

    load_configuration(CONFIG)


def configure_command(assignments: list[str], list_settings: bool) -> int:
    if list_settings:
        print(json.dumps({"ok": True, "settings": list(known_setting_names())}, ensure_ascii=False, indent=2))
        return 0
    result = configure_assignments(assignments)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def show_configuration() -> int:
    print(json.dumps({"ok": True, "config": configuration_values()}, ensure_ascii=False, indent=2))
    return 0


def list_voices() -> int:
    print(json.dumps({
        "ok": True,
        "engine": "kokoro",
        "language": "pt-BR",
        "voices": [{"id": voice, "label": label} for voice, label in PORTUGUESE_VOICES],
    }, ensure_ascii=False, indent=2))
    return 0


def ffmpeg_candidates() -> tuple[Path, ...]:
    try:
        values = configuration_values() if CONFIG.exists() else {}
    except ConfigurationError:
        values = {}
    configured = str(values.get("tts.encoder_path") or "").strip()
    raw: list[Path] = []
    if configured:
        path = Path(configured).expanduser()
        raw.append(path if path.is_absolute() else ROOT / path)
    portable = ROOT / "tools" / "ffmpeg" / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    raw.append(portable)
    discovered = shutil.which("ffmpeg")
    if discovered:
        raw.append(Path(discovered))
    result: list[Path] = []
    for candidate in raw:
        resolved = candidate.resolve()
        if resolved not in result:
            result.append(resolved)
    return tuple(result)


def inspect_ffmpeg() -> dict[str, object]:
    for candidate in ffmpeg_candidates():
        if not candidate.is_file():
            continue
        try:
            completed = subprocess.run(
                [str(candidate), "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if completed.returncode == 0:
            first_line = (completed.stdout.splitlines() or ["ffmpeg"])[0][:300]
            return {"available": True, "path": str(candidate), "version": first_line}
    return {
        "available": False,
        "path": None,
        "message": "FFmpeg não localizado; WAV continua disponível sem encoder externo.",
    }


def ffmpeg_status() -> int:
    print(json.dumps({"ok": True, "ffmpeg": inspect_ffmpeg()}, ensure_ascii=False, indent=2))
    return 0


def configure_detected_ffmpeg() -> int:
    result = inspect_ffmpeg()
    if not result["available"]:
        raise RuntimeError(str(result["message"]))
    configured = configure_assignments((f"tts.encoder_path={result['path']}",))
    print(json.dumps({**configured, "ffmpeg": result}, ensure_ascii=False, indent=2))
    return 0


def doctor() -> int:
    configuration: dict[str, object]
    configuration_ok = False
    configuration_error: str | None = None
    try:
        values = configuration_values()
        src = ROOT / "src"
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        from eccovox.core.config import load_configuration

        effective = load_configuration(CONFIG)
        configuration = {
            "valid": True,
            "host": effective.server.host,
            "port": effective.server.port,
            "stt_enabled": effective.stt.enabled,
            "tts_enabled": effective.tts.enabled,
            "tts_voice": effective.tts.voice,
            "tts_format": effective.tts.response_format,
            "configured_fields": len(values),
        }
        configuration_ok = True
    except Exception as exc:
        configuration_error = str(exc)
        configuration = {"valid": False, "error": configuration_error}

    dependencies = {
        "fastapi": importlib.util.find_spec("fastapi") is not None,
        "uvicorn": importlib.util.find_spec("uvicorn") is not None,
        "psutil": importlib.util.find_spec("psutil") is not None,
        "faster_whisper": importlib.util.find_spec("faster_whisper") is not None,
        "kokoro": importlib.util.find_spec("kokoro") is not None,
        "soundfile": importlib.util.find_spec("soundfile") is not None,
    }
    process = process_status_payload()
    service = service_status_payload(safe=True)
    ffmpeg = inspect_ffmpeg()
    health = endpoint_status() if configuration_ok else {"reachable": False}
    payload = {
        "ok": configuration_ok and VENV_PYTHON.is_file(),
        "installation": {
            "venv": VENV_PYTHON.is_file(),
            "python": str(VENV_PYTHON),
            "config": CONFIG.is_file(),
        },
        "configuration": configuration,
        "dependencies": dependencies,
        "process": process,
        "service": service,
        "ffmpeg": ffmpeg,
        "health": health,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def endpoint_status() -> dict[str, object]:
    try:
        values = tomllib.loads(CONFIG.read_text(encoding="utf-8-sig"))
        server = values.get("server", {})
        host = str(server.get("host", "127.0.0.1")) if isinstance(server, dict) else "127.0.0.1"
        port = int(server.get("port", 8870)) if isinstance(server, dict) else 8870
        if host in {"0.0.0.0", "::"}:
            host = "127.0.0.1"
        with urlopen(f"http://{host}:{port}/v1/health", timeout=2) as response:
            return {"reachable": response.status == 200, "status_code": response.status}
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return {"reachable": False}


def start() -> int:
    existing = read_state()
    if existing and is_owned_process(existing):
        print(json.dumps({"ok": True, "status": "running", "pid": existing["pid"]}))
        return 0
    require_installation()
    service = service_status_payload(safe=True)
    if service.get("status") == "running":
        raise RuntimeError("O serviço EccoVox já está ativo; não inicie um segundo processo na mesma porta.")
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
    payload = process_status_payload()
    print(json.dumps(payload))
    return 0 if payload["status"] == "running" else 3


def process_status_payload() -> dict[str, object]:
    state = read_state()
    running = bool(state and is_owned_process(state))
    payload: dict[str, object] = {
        "ok": True,
        "status": "running" if running else "stopped",
        "state_file": str(STATE_FILE),
    }
    if running:
        payload["pid"] = state["pid"]
    return payload


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
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:500]
        raise RuntimeError(
            "O serviço EccoVox não foi instalado; execute em um PowerShell elevado."
            + (f" Detalhe: {detail}" if detail else "")
        )
    configure_windows_service_environment()
    if not service_exists():
        raise RuntimeError("O serviço EccoVox não foi localizado após a instalação.")
    print(json.dumps({"ok": True, "platform": "windows", "installed": True, "startup": "automatic"}))
    return 0


def service_remove() -> int:
    if service_platform() == "linux":
        return systemd_remove()
    service_control("stop", check=False)
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "eccovox.windows_service", "remove"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode or service_exists():
        raise RuntimeError("O serviço EccoVox não foi removido; execute em um PowerShell elevado.")
    print(json.dumps({"ok": True, "platform": "windows", "installed": False}))
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
    if action in {"start", "restart"}:
        process = process_status_payload()
        if process["status"] == "running":
            raise RuntimeError(
                "O processo local EccoVox já está ativo; finalize-o antes de iniciar o serviço."
            )
    platform = service_platform()
    if platform == "linux":
        result = subprocess.run(
            ["systemctl", action, "eccovox.service"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    elif action == "restart":
        service_control("stop", check=False)
        wait_service_state("stopped", timeout=30)
        return service_control("start", check=check)
    else:
        result = subprocess.run(
            ["sc.exe", action, SERVICE_NAME],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()[:500]
        raise RuntimeError(
            f"O comando de serviço '{action}' falhou com código {result.returncode}."
            + (f" Detalhe: {detail}" if detail else "")
        )
    return result.returncode


def service_action(action: str) -> int:
    result = service_control(action)
    expected = "stopped" if action == "stop" else "running"
    payload = wait_service_state(expected, timeout=30)
    print(json.dumps({**payload, "ok": result == 0, "action": action}, ensure_ascii=False))
    return result


def wait_service_state(expected: str, *, timeout: int) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last = service_status_payload(safe=True)
    while time.monotonic() < deadline:
        last = service_status_payload(safe=True)
        if last.get("status") == expected:
            return last
        time.sleep(0.25)
    raise RuntimeError(
        f"O serviço não alcançou o estado '{expected}' em {timeout} segundos."
    )


def service_status() -> int:
    payload = service_status_payload()
    print(json.dumps(payload))
    return 0 if payload["status"] == "running" else 3


def service_status_payload(*, safe: bool = False) -> dict[str, object]:
    try:
        return _service_status_payload()
    except (RuntimeError, ImportError, OSError):
        if safe:
            return {"ok": False, "installed": False, "status": "unsupported"}
        raise


def _service_status_payload() -> dict[str, object]:
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
    return {
        "ok": True,
        "platform": platform,
        "installed": installed,
        "enabled": enabled,
        "status": "running" if active else "stopped",
    }


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
    except ImportError:
        return False
    try:
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
