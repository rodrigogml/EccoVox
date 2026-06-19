"""Functional errors exposed by EccoVox."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus


class ErrorCodeEnum(StrEnum):
    """Stable public error codes for HTTP and CLI callers."""

    INVALID_AUDIO = "invalid_audio"
    INVALID_TEXT = "invalid_text"
    INVALID_OVERRIDE = "invalid_override"
    CAPABILITY_DISABLED = "capability_disabled"
    CAPACITY_EXCEEDED = "capacity_exceeded"
    TIMEOUT = "timeout"
    EMPTY_TRANSCRIPTION = "empty_transcription"
    UNSUPPORTED_AUDIO_FORMAT = "unsupported_audio_format"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    ENGINE_FUNCTIONAL_ERROR = "engine_functional_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ErrorMapping:
    """HTTP/CLI mapping for a functional error."""

    http_status: int
    cli_exit_code: int
    retryable: bool = False


ERROR_MAPPINGS: dict[ErrorCodeEnum, ErrorMapping] = {
    ErrorCodeEnum.INVALID_AUDIO: ErrorMapping(HTTPStatus.BAD_REQUEST, 2),
    ErrorCodeEnum.INVALID_TEXT: ErrorMapping(HTTPStatus.BAD_REQUEST, 2),
    ErrorCodeEnum.INVALID_OVERRIDE: ErrorMapping(HTTPStatus.BAD_REQUEST, 2),
    ErrorCodeEnum.CAPABILITY_DISABLED: ErrorMapping(HTTPStatus.NOT_FOUND, 3),
    ErrorCodeEnum.RUNTIME_UNAVAILABLE: ErrorMapping(HTTPStatus.SERVICE_UNAVAILABLE, 3, True),
    ErrorCodeEnum.TIMEOUT: ErrorMapping(HTTPStatus.REQUEST_TIMEOUT, 4, True),
    ErrorCodeEnum.EMPTY_TRANSCRIPTION: ErrorMapping(HTTPStatus.UNPROCESSABLE_ENTITY, 5),
    ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT: ErrorMapping(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, 5),
    ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR: ErrorMapping(HTTPStatus.INTERNAL_SERVER_ERROR, 5),
    ErrorCodeEnum.CAPACITY_EXCEEDED: ErrorMapping(HTTPStatus.CONFLICT, 6, True),
    ErrorCodeEnum.INTERNAL_ERROR: ErrorMapping(HTTPStatus.INTERNAL_SERVER_ERROR, 10),
}


class EccoVoxError(Exception):
    """Base exception for safe public EccoVox errors."""

    def __init__(self, code: ErrorCodeEnum, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @property
    def mapping(self) -> ErrorMapping:
        """Return the public protocol mapping for this error."""

        return ERROR_MAPPINGS[self.code]


def to_error_payload(error: EccoVoxError) -> dict[str, object]:
    """Convert a safe functional exception into the public error payload."""

    mapping = error.mapping
    return {
        "code": error.code.value,
        "message": error.message,
        "retryable": mapping.retryable,
        "details": error.details,
    }
