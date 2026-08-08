"""Windows Service wrapper for the EccoVox HTTP runtime."""

from __future__ import annotations

from pathlib import Path
import socket
import sys


def _bootstrap_pywin32() -> None:
    """Expose pywin32 subdirectories when pythonservice skips virtualenv .pth files."""
    site_packages = Path(__file__).resolve().parents[2] / ".venv" / "Lib" / "site-packages"
    for relative in ("", "win32", "win32/lib", "pythonwin"):
        candidate = site_packages / relative
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


_bootstrap_pywin32()

from eccovox.core.config import load_configuration
from eccovox.core.runtime import SpeechRuntime
from eccovox.api.app import create_app


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
        self.server = None
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.server is not None:
            self.server.should_exit = True
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        import asyncio
        from contextlib import contextmanager
        import uvicorn

        class WindowsServiceServer(uvicorn.Server):
            @contextmanager
            def capture_signals(self):
                # Service control events replace console signal handlers.
                yield

        root = Path(__file__).resolve().parents[2]
        config = load_configuration(root / "eccovox.toml")
        self.server = WindowsServiceServer(
            uvicorn.Config(
                create_app(SpeechRuntime(config)),
                host=config.server.host,
                port=config.server.port,
                log_config=None,
            )
        )
        servicemanager.LogInfoMsg("EccoVox service started")
        # pywin32 executes SvcDoRun outside the main interpreter thread. The
        # default Windows proactor loop calls signal.set_wakeup_fd() and fails
        # in that context, so the service owns an explicit selector loop.
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.server.serve())
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            asyncio.set_event_loop(None)
            loop.close()


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(EccoVoxService)
