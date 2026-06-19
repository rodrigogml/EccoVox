"""HTTP routes and protocol mapping for EccoVox."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum, to_error_payload
from eccovox.core.models import CapabilityHealth, RuntimeHealth, SttRequest, TtsRequest
from eccovox.core.runtime import SpeechRuntime

router = APIRouter(prefix="/v1")


class SpeechRequestDTO(BaseModel):
    """HTTP TTS request payload."""

    input: str
    voice: str | None = None
    language: str | None = None
    profile: str | None = None
    response_format: str | None = Field(default=None, alias="responseFormat")
    speed: float | None = None

    model_config = {"populate_by_name": True}


def runtime_from(request: Request) -> SpeechRuntime:
    """Return the runtime attached to the FastAPI app."""

    return request.app.state.runtime


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Return runtime health using the public camelCase contract."""

    return _runtime_health_to_dict(runtime_from(request).health())


@router.post("/audio/transcriptions")
async def transcribe(
    request: Request,
    file: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
    profile: Annotated[str | None, Form()] = None,
    response_format: Annotated[str | None, Form(alias="responseFormat")] = None,
    model: Annotated[str | None, Form()] = None,
    device: Annotated[str | None, Form()] = None,
    compute_type: Annotated[str | None, Form(alias="computeType")] = None,
    prompt: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    """Transcribe uploaded audio and return normalized JSON."""

    try:
        audio = await file.read()
        result = runtime_from(request).transcribe(
            SttRequest(
                audio=audio,
                language=language,
                profile=profile,
                response_format=response_format or "json",
                model=model,
                device=device,
                compute_type=compute_type,
                prompt=prompt,
            )
        )
        return {
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
            "durationMillis": result.duration_millis,
            "metadata": result.metadata,
        }
    except EccoVoxError as exc:
        raise _http_error(exc) from exc


@router.post("/audio/speech")
def synthesize(request: Request, payload: SpeechRequestDTO) -> Response:
    """Synthesize text and return playable audio bytes."""

    try:
        result = runtime_from(request).synthesize(
            TtsRequest(
                input_text=payload.input,
                voice=payload.voice,
                language=payload.language,
                profile=payload.profile,
                response_format=payload.response_format,
                speed=payload.speed,
            )
        )
        return Response(content=result.audio, media_type=result.content_type)
    except EccoVoxError as exc:
        raise _http_error(exc) from exc


def _http_error(error: EccoVoxError) -> HTTPException:
    return HTTPException(status_code=error.mapping.http_status, detail=to_error_payload(error))


def _runtime_health_to_dict(health_payload: RuntimeHealth) -> dict[str, object]:
    return {
        "status": health_payload.status.value,
        "version": health_payload.version,
        "capabilities": {
            name: _capability_health_to_dict(capability)
            for name, capability in health_payload.capabilities.items()
        },
    }


def _capability_health_to_dict(capability: CapabilityHealth) -> dict[str, object]:
    data = {
        "status": capability.status.value,
        "engine": capability.engine,
        "model": capability.model,
        "device": capability.device,
        "formats": list(capability.formats),
        "safeMessage": capability.safe_message,
    }
    return {key: value for key, value in data.items() if value not in (None, [], {})}
