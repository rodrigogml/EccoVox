"""Windows Service supervisor for the EccoVox HTTP runtime."""

from __future__ import annotations

from pathlib import Path
import socket
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
CONFIG = ROOT / "eccovox.toml"
LOG_DIR = ROOT / ".eccovox" / "logs"


def _bootstrap_pywin32() -> None:
    """Expose pywin32 subdirectories when pythonservice skips virtualenv .pth files."""
    site_packages = ROOT / ".venv" / "Lib" / "site-packages"
    for relative in ("", "win32", "win32/lib", "pythonwin"):
        candidate = site_packages / relative
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


_bootstrap_pywin32()

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError as exc:  # pragma: no cover - platform/optional dependency
    raise SystemExit("Instale o extra 'service' para administrar o serviço Windows.") from exc


class EccoVoxService(win32serviceutil.ServiceFramework):
    _svc_name_ = "EccoVox"
    _svc_display_name_ = "EccoVox Local Speech Runtime"
    _svc_description_ = "Local HTTP speech transcription and synthesis service."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process: subprocess.Popen[bytes] | None = None
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        if not VENV_PYTHON.is_file() or not CONFIG.is_file():
            raise RuntimeError("A venv ou o eccovox.toml não foi encontrado.")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (
            (LOG_DIR / "windows-service.log").open("ab") as stdout,
            (LOG_DIR / "windows-service-error.log").open("ab") as stderr,
        ):
            self.process = subprocess.Popen(
                [
                    str(VENV_PYTHON),
                    "-m",
                    "eccovox.cli",
                    "serve",
                    "--config",
                    str(CONFIG),
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW,
                close_fds=True,
            )
            servicemanager.LogInfoMsg(
                f"EccoVox service started child process {self.process.pid}"
            )
            stop_requested = False
            while self.process.poll() is None:
                result = win32event.WaitForSingleObject(self.stop_event, 1_000)
                if result == win32event.WAIT_OBJECT_0:
                    stop_requested = True
                    self._stop_child()
                    break
            return_code = self.process.poll()
            if return_code not in (None, 0) and not stop_requested:
                raise RuntimeError(
                    f"O processo EccoVox encerrou inesperadamente com código {return_code}."
                )

    def _stop_child(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(EccoVoxService)
