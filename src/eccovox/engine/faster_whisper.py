"""Optional faster-whisper STT adapter."""

from __future__ import annotations

from importlib.util import find_spec
from math import exp
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum
from eccovox.core.models import CapabilityHealth, CapabilityStatusEnum, RuntimeProfile, SttRequest, SttResult
from eccovox.engine.base import SttEngineAdapter
from eccovox.util.audio_format import audio_suffix
from eccovox.util.nvidia_runtime import configure_nvidia_dll_directories
from eccovox.util.temp_artifact import temporary_artifact


class FasterWhisperSttEngineAdapter(SttEngineAdapter):
    """Adapter for `faster-whisper`, loaded only when the optional dependency is installed."""

    engine_name = "faster-whisper"

    def __init__(self, temp_dir: Path | None = None, model_cache_dir: Path | None = None) -> None:
        self._temp_dir = temp_dir or Path(".eccovox/tmp")
        self._model_cache_dir = model_cache_dir
        self._models: dict[tuple[str, str, str], Any] = {}
        self._model_lock = Lock()

    def health(self, profile: RuntimeProfile) -> CapabilityHealth:
        """Report dependency availability without downloading or loading a model."""

        if find_spec("faster_whisper") is None:
            return CapabilityHealth(
                status=CapabilityStatusEnum.UNAVAILABLE,
                engine=self.engine_name,
                model=profile.model,
                device=profile.device,
                formats=self.supported_formats,
                safe_message="faster-whisper extra is not installed.",
            )
        if profile.device == "cuda":
            try:
                configure_nvidia_dll_directories()
                import ctranslate2

                if ctranslate2.get_cuda_device_count() < 1:
                    raise RuntimeError("no CUDA device")
            except Exception:
                return CapabilityHealth(
                    status=CapabilityStatusEnum.UNAVAILABLE,
                    engine=self.engine_name,
                    model=profile.model,
                    device=profile.device,
                    formats=self.supported_formats,
                    safe_message="CUDA runtime or a compatible NVIDIA device is unavailable.",
                )
        return super().health(profile)

    def transcribe(self, request: SttRequest, profile: RuntimeProfile) -> SttResult:
        started_at = perf_counter()
        try:
            model = self._model_for(profile)
            suffix = audio_suffix(request.audio, request.audio_format)
            with temporary_artifact(self._temp_dir, suffix=suffix) as temp_path:
                temp_path.write_bytes(request.audio)
                segments, info = model.transcribe(
                    str(temp_path),
                    language=_whisper_language(request.language),
                    initial_prompt=_initial_prompt(request),
                )
                segment_list = list(segments)
                text = " ".join(segment.text.strip() for segment in segment_list).strip()
        except EccoVoxError:
            raise
        except Exception as exc:
            raise EccoVoxError(ErrorCodeEnum.ENGINE_FUNCTIONAL_ERROR, "STT engine failed to transcribe audio.") from exc

        if not text:
            raise EccoVoxError(ErrorCodeEnum.EMPTY_TRANSCRIPTION, "STT did not identify useful text.")
        language = getattr(info, "language", None) or request.language
        language_probability = getattr(info, "language_probability", None)
        confidence = _transcription_confidence(segment_list)
        processing_millis = round((perf_counter() - started_at) * 1_000)
        audio_duration = getattr(info, "duration", None)
        metadata: dict[str, object] = {
            "engine": self.engine_name,
            "model": profile.model or "medium",
            "device": profile.device or "cpu",
            "computeType": profile.compute_type or "int8",
            "audioFormat": suffix.removeprefix("."),
            "segmentCount": len(segment_list),
            "contextTermCount": len(request.context_terms),
        }
        if language_probability is not None:
            metadata["languageProbability"] = float(language_probability)
        if audio_duration is not None:
            metadata["audioDurationMillis"] = round(float(audio_duration) * 1_000)
        return SttResult(
            text=text,
            language=language,
            confidence=confidence,
            duration_millis=processing_millis,
            metadata=metadata,
        )

    def _model_for(self, profile: RuntimeProfile) -> Any:
        """Load each effective model once and reuse it for warm requests."""

        model_name = profile.model or "medium"
        device = profile.device or "cpu"
        compute_type = profile.compute_type or "int8"
        cache_key = (model_name, device, compute_type)
        with self._model_lock:
            cached_model = self._models.get(cache_key)
            if cached_model is not None:
                return cached_model
            try:
                if device == "cuda":
                    configure_nvidia_dll_directories()
                from faster_whisper import WhisperModel
            except ImportError as exc:
                missing_module = getattr(exc, "name", None)
                raise EccoVoxError(
                    ErrorCodeEnum.RUNTIME_UNAVAILABLE,
                    "faster-whisper or one of its runtime dependencies could not be loaded.",
                    {
                        "exceptionType": type(exc).__name__,
                        **({"module": missing_module} if missing_module else {}),
                    },
                ) from exc
            options: dict[str, object] = {"device": device, "compute_type": compute_type}
            if self._model_cache_dir is not None:
                options["download_root"] = str(self._model_cache_dir)
            model = WhisperModel(model_name, **options)
            self._models[cache_key] = model
            return model


def _whisper_language(language: str | None) -> str | None:
    """Convert BCP 47 language tags to the base code accepted by faster-whisper."""

    if language is None or not language.strip():
        return None
    return language.split("-", maxsplit=1)[0].lower()


def _initial_prompt(request: SttRequest) -> str | None:
    """Combine free context and deduplicated vocabulary without exposing it in metadata."""

    prompt = request.prompt.strip() if request.prompt else ""
    unique_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in request.context_terms:
        normalized_term = term.strip()
        deduplication_key = normalized_term.casefold()
        if deduplication_key not in seen_terms:
            seen_terms.add(deduplication_key)
            unique_terms.append(normalized_term)
    vocabulary = f"Context vocabulary: {', '.join(unique_terms)}." if unique_terms else ""
    combined_prompt = "\n".join(part for part in (prompt, vocabulary) if part)
    return combined_prompt or None


def _transcription_confidence(segments: list[Any]) -> float | None:
    """Estimate transcript confidence from duration-weighted segment log probabilities."""

    weighted_log_probability = 0.0
    total_weight = 0.0
    for segment in segments:
        average_log_probability = getattr(segment, "avg_logprob", None)
        if average_log_probability is None:
            continue
        start = float(getattr(segment, "start", 0.0))
        end = float(getattr(segment, "end", start))
        weight = max(end - start, 0.001)
        weighted_log_probability += float(average_log_probability) * weight
        total_weight += weight
    if not total_weight:
        return None
    return max(0.0, min(1.0, exp(weighted_log_probability / total_weight)))
