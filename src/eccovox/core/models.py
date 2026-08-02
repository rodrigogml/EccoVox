"""Internal data contracts for EccoVox runtime operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class CapabilityEnum(StrEnum):
    """Voice capability handled by the runtime."""

    STT = "stt"
    TTS = "tts"


class CapabilityStatusEnum(StrEnum):
    """Public health state for a capability or the full runtime."""

    READY = "ready"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class OperationModeEnum(StrEnum):
    """Public surface that initiated a speech operation."""

    HTTP = "http"
    CLI = "cli"


class OperationStatusEnum(StrEnum):
    """Internal result state for diagnostics."""

    SUCCESS = "success"
    FUNCTIONAL_ERROR = "functional_error"
    TECHNICAL_ERROR = "technical_error"
    TIMEOUT = "timeout"
    CAPACITY_EXCEEDED = "capacity_exceeded"


@dataclass(frozen=True)
class ServerConfig:
    """HTTP server binding configuration."""

    host: str = "127.0.0.1"
    port: int = 8870


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime-wide configuration shared by STT and TTS."""

    temp_dir: Path = Path(".eccovox/tmp")
    model_cache_dir: Path = Path(".eccovox/models")
    state_dir: Path = Path(".eccovox/state")
    log_dir: Path = Path(".eccovox/logs")
    request_timeout_seconds: int = 120
    profiles: tuple[str, ...] = ("default", "balanced", "premium", "diagnostic", "process")
    default_profile: str = "balanced"


@dataclass(frozen=True)
class SttConfig:
    """Default configuration for speech-to-text operations."""

    enabled: bool = True
    engine: str = "faster-whisper"
    profile: str = "balanced"
    model: str = "medium"
    device: str = "cpu"
    compute_type: str = "int8"
    max_audio_bytes: int = 10_485_760
    short_audio_budget_millis: int = 5_000
    max_concurrent: int = 1
    queue_size: int = 0


@dataclass(frozen=True)
class TtsConfig:
    """Default configuration for text-to-speech operations."""

    enabled: bool = True
    engine: str = "kokoro"
    profile: str = "balanced"
    voice: str = "pf_dora"
    language: str = "pt-BR"
    response_format: str = "mp3"
    max_text_chars: int = 4_000
    short_text_start_budget_millis: int = 2_000
    max_concurrent: int = 1
    queue_size: int = 0


@dataclass(frozen=True)
class RuntimeConfiguration:
    """Full effective runtime configuration."""

    server: ServerConfig = field(default_factory=ServerConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    stt: SttConfig = field(default_factory=SttConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)


@dataclass(frozen=True)
class RuntimeProfile:
    """Effective profile for a single STT or TTS operation."""

    name: str
    capability: CapabilityEnum
    engine: str
    model: str | None = None
    voice: str | None = None
    language: str | None = None
    device: str | None = None
    compute_type: str | None = None
    response_format: str | None = None
    speed: float | None = None


@dataclass(frozen=True)
class CapabilityHealth:
    """Public health payload for a single voice capability."""

    status: CapabilityStatusEnum
    engine: str | None = None
    model: str | None = None
    device: str | None = None
    formats: tuple[str, ...] = ()
    safe_message: str | None = None


@dataclass(frozen=True)
class RuntimeHealth:
    """Public health payload for the full runtime."""

    status: CapabilityStatusEnum
    version: str
    capabilities: dict[str, CapabilityHealth]


@dataclass(frozen=True)
class SpeechError:
    """Stable error payload shared by HTTP and CLI surfaces."""

    code: str
    message: str
    retryable: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SttRequest:
    """Normalized STT request used by runtime and adapters."""

    audio: bytes
    audio_format: str | None = None
    profile: str | None = None
    language: str | None = None
    response_format: str = "json"
    model: str | None = None
    device: str | None = None
    compute_type: str | None = None
    prompt: str | None = None
    context_terms: tuple[str, ...] = ()
    normalization_aliases: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SttResult:
    """Normalized STT result."""

    text: str
    raw_text: str | None = None
    language: str | None = None
    confidence: float | None = None
    duration_millis: int | None = None
    normalization_changes: tuple[dict[str, str], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TtsRequest:
    """Normalized TTS request used by runtime and adapters."""

    input_text: str
    voice: str | None = None
    language: str | None = None
    profile: str | None = None
    response_format: str | None = None
    speed: float | None = None


@dataclass(frozen=True)
class TtsResult:
    """Normalized TTS result."""

    audio: bytes
    content_type: str
    response_format: str
    metadata: dict[str, Any] = field(default_factory=dict)
