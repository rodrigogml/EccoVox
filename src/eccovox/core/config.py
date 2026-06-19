"""Configuration loading and per-call override handling."""

from __future__ import annotations

import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import (
    CapabilityEnum,
    RuntimeConfig,
    RuntimeConfiguration,
    RuntimeProfile,
    ServerConfig,
    SttConfig,
    SttRequest,
    TtsConfig,
    TtsRequest,
)


def load_configuration(config_path: Path | str | None = None) -> RuntimeConfiguration:
    """Load runtime configuration from TOML or return validated defaults."""

    if config_path is None:
        return validate_configuration(RuntimeConfiguration())

    path = Path(config_path)
    if not path.exists():
        raise EccoVoxError(ErrorCodeEnum.RUNTIME_UNAVAILABLE, "Configuration file was not found.")

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, "Configuration file is not valid TOML.") from exc
    server = _server_config(data.get("server", {}))
    runtime = _runtime_config(data.get("runtime", {}))
    stt = _stt_config(data.get("stt", {}))
    tts = _tts_config(data.get("tts", {}))
    return validate_configuration(RuntimeConfiguration(server=server, runtime=runtime, stt=stt, tts=tts))


def validate_configuration(config: RuntimeConfiguration) -> RuntimeConfiguration:
    """Validate configuration values that would make runtime behavior unsafe or undefined."""

    _require_positive("server.port", config.server.port)
    _require_positive("runtime.request_timeout_seconds", config.runtime.request_timeout_seconds)
    _require_non_empty("runtime.default_profile", config.runtime.default_profile)
    if config.runtime.default_profile not in config.runtime.profiles:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, "Default profile is not listed in configured profiles.")
    _validate_capability_limits("stt", config.stt.max_audio_bytes, config.stt.max_concurrent, config.stt.queue_size)
    _validate_capability_limits("tts", config.tts.max_text_chars, config.tts.max_concurrent, config.tts.queue_size)
    return config


def stt_profile(config: RuntimeConfiguration, request: SttRequest) -> RuntimeProfile:
    """Build an effective STT profile for one operation without mutating defaults."""

    profile_name = _resolve_profile(config, request.profile or config.stt.profile)
    _validate_override(config, request.model, "model")
    _validate_override(config, request.device, "device")
    _validate_override(config, request.compute_type, "computeType")
    return RuntimeProfile(
        name=profile_name,
        capability=CapabilityEnum.STT,
        engine=config.stt.engine,
        model=request.model or config.stt.model,
        language=request.language,
        device=request.device or config.stt.device,
        compute_type=request.compute_type or config.stt.compute_type,
        response_format=request.response_format,
    )


def tts_profile(config: RuntimeConfiguration, request: TtsRequest) -> RuntimeProfile:
    """Build an effective TTS profile for one operation without mutating defaults."""

    profile_name = _resolve_profile(config, request.profile or config.tts.profile)
    _validate_override(config, request.voice, "voice")
    _validate_override(config, request.response_format, "responseFormat")
    if request.speed is not None and request.speed <= 0:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, "TTS speed override must be positive.")
    return RuntimeProfile(
        name=profile_name,
        capability=CapabilityEnum.TTS,
        engine=config.tts.engine,
        voice=request.voice or config.tts.voice,
        language=request.language or config.tts.language,
        response_format=request.response_format or config.tts.response_format,
        speed=request.speed,
    )


def with_server_overrides(
    config: RuntimeConfiguration,
    host: str | None = None,
    port: int | None = None,
) -> RuntimeConfiguration:
    """Return a copy of the configuration with CLI server overrides applied."""

    server = replace(config.server, host=host or config.server.host, port=port or config.server.port)
    return validate_configuration(replace(config, server=server))


def _server_config(data: dict[str, Any]) -> ServerConfig:
    return ServerConfig(host=str(data.get("host", "127.0.0.1")), port=int(data.get("port", 8870)))


def _runtime_config(data: dict[str, Any]) -> RuntimeConfig:
    profiles = tuple(str(item) for item in data.get("profiles", ["default", "balanced", "premium", "diagnostic", "process"]))
    return RuntimeConfig(
        temp_dir=Path(str(data.get("temp_dir", ".eccovox/tmp"))),
        request_timeout_seconds=int(data.get("request_timeout_seconds", 120)),
        profiles=profiles,
        default_profile=str(data.get("default_profile", "balanced")),
    )


def _stt_config(data: dict[str, Any]) -> SttConfig:
    return SttConfig(
        enabled=bool(data.get("enabled", True)),
        engine=str(data.get("engine", "faster-whisper")),
        profile=str(data.get("profile", "balanced")),
        model=str(data.get("model", "large-v3")),
        device=str(data.get("device", "cpu")),
        compute_type=str(data.get("compute_type", "int8")),
        max_audio_bytes=int(data.get("max_audio_bytes", 10_485_760)),
        short_audio_budget_millis=int(data.get("short_audio_budget_millis", 5_000)),
        max_concurrent=int(data.get("max_concurrent", 1)),
        queue_size=int(data.get("queue_size", 0)),
    )


def _tts_config(data: dict[str, Any]) -> TtsConfig:
    return TtsConfig(
        enabled=bool(data.get("enabled", True)),
        engine=str(data.get("engine", "kokoro")),
        profile=str(data.get("profile", "balanced")),
        voice=str(data.get("voice", "pf_dora")),
        language=str(data.get("language", "pt-BR")),
        response_format=str(data.get("response_format", "mp3")),
        max_text_chars=int(data.get("max_text_chars", 4_000)),
        short_text_start_budget_millis=int(data.get("short_text_start_budget_millis", 2_000)),
        max_concurrent=int(data.get("max_concurrent", 1)),
        queue_size=int(data.get("queue_size", 0)),
    )


def _resolve_profile(config: RuntimeConfiguration, profile_name: str) -> str:
    if profile_name == "default":
        return config.runtime.default_profile
    if profile_name not in config.runtime.profiles:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, "Profile override is not configured.")
    return profile_name


def _validate_override(config: RuntimeConfiguration, value: object | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, f"{field_name} override cannot be blank.")
    if field_name == "responseFormat" and str(value) not in {"json", "mp3", "wav", "opus", "flac"}:
        raise EccoVoxError(ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT, "Requested response format is not supported.")


def _validate_capability_limits(name: str, max_size: int, max_concurrent: int, queue_size: int) -> None:
    _require_positive(f"{name}.max_size", max_size)
    _require_positive(f"{name}.max_concurrent", max_concurrent)
    if queue_size < 0:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, f"{name}.queue_size must be zero or positive.")


def _require_positive(name: str, value: int) -> None:
    if value < 1:
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, f"{name} must be positive.")


def _require_non_empty(name: str, value: str) -> None:
    if not value.strip():
        raise EccoVoxError(ErrorCodeEnum.INVALID_OVERRIDE, f"{name} cannot be blank.")
