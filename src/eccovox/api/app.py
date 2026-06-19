"""FastAPI application factory for EccoVox."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from eccovox.api.routes import router
from eccovox.core.config import load_configuration
from eccovox.core.errors import EccoVoxError, ErrorCodeEnum, to_error_payload
from eccovox.core.runtime import SpeechRuntime


def create_app(runtime: SpeechRuntime | None = None) -> FastAPI:
    """Create the HTTP app with a configurable runtime instance."""

    app = FastAPI(title="EccoVox", version="0.1.0")
    app.state.runtime = runtime or SpeechRuntime(load_configuration())
    app.include_router(router)

    @app.exception_handler(EccoVoxError)
    async def ecco_vox_error_handler(_request, exc: EccoVoxError) -> JSONResponse:
        return JSONResponse(status_code=exc.mapping.http_status, content=to_error_payload(exc))

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=to_error_payload(EccoVoxError(ErrorCodeEnum.INTERNAL_ERROR, "HTTP request failed.")),
        )

    return app


app = create_app()
