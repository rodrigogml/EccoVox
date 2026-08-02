"""Windows Service wrapper for the EccoVox HTTP runtime."""

from __future__ import annotations

from pathlib import Path
import socket

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
        import uvicorn

        root = Path(__file__).resolve().parents[2]
        config = load_configuration(root / "eccovox.toml")
        self.server = uvicorn.Server(
            uvicorn.Config(
                create_app(SpeechRuntime(config)),
                host=config.server.host,
                port=config.server.port,
                log_config=None,
            )
        )
        servicemanager.LogInfoMsg("EccoVox service started")
        self.server.run()


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(EccoVoxService)
