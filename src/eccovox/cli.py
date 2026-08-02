"""Command-line interface for EccoVox."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from eccovox.api.app import create_app
from eccovox.api.routes import _parse_aliases
from eccovox.core.config import load_configuration, with_server_overrides
from eccovox.core.errors import EccoVoxError, ErrorCodeEnum, to_error_payload
from eccovox.core.models import SttRequest, TtsRequest
from eccovox.core.runtime import SpeechRuntime

app = typer.Typer(help="Independent local voice runtime for STT and TTS.")


@app.command()
def serve(
    host: Annotated[str | None, typer.Option("--host")] = None,
    port: Annotated[int | None, typer.Option("--port")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Start EccoVox HTTP server mode."""

    try:
        runtime_config = with_server_overrides(load_configuration(config), host=host, port=port)
    except EccoVoxError as exc:
        _exit_with_error(exc)
    uvicorn.run(create_app(SpeechRuntime(runtime_config)), host=runtime_config.server.host, port=runtime_config.server.port)


@app.command()
def transcribe(
    file: Annotated[Path, typer.Option("--file", exists=True, readable=True)],
    language: Annotated[str | None, typer.Option("--language")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    model: Annotated[str | None, typer.Option("--model")] = None,
    device: Annotated[str | None, typer.Option("--device")] = None,
    compute_type: Annotated[str | None, typer.Option("--compute-type")] = None,
    prompt: Annotated[str | None, typer.Option("--prompt")] = None,
    term: Annotated[list[str] | None, typer.Option("--term")] = None,
    alias: Annotated[list[str] | None, typer.Option("--alias")] = None,
    format: Annotated[str, typer.Option("--format")] = "json",
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Execute one STT conversion and write result JSON to stdout."""

    try:
        runtime = SpeechRuntime(load_configuration(config))
        result = runtime.transcribe(
            SttRequest(
                audio=file.read_bytes(),
                audio_format=file.suffix,
                language=language,
                profile=profile,
                response_format=format,
                model=model,
                device=device,
                compute_type=compute_type,
                prompt=prompt,
                context_terms=tuple(term or ()),
                normalization_aliases=_parse_aliases(alias or ()),
            )
        )
        typer.echo(
            json.dumps(
                {
                    "text": result.text,
                    "rawText": result.raw_text,
                    "language": result.language,
                    "confidence": result.confidence,
                    "durationMillis": result.duration_millis,
                    "normalizationChanges": list(result.normalization_changes),
                    "metadata": result.metadata,
                },
                ensure_ascii=False,
            )
        )
    except EccoVoxError as exc:
        _exit_with_error(exc)


@app.command()
def synthesize(
    text: Annotated[str, typer.Option("--text")],
    output: Annotated[Path, typer.Option("--output")],
    voice: Annotated[str | None, typer.Option("--voice")] = None,
    format: Annotated[str, typer.Option("--format")] = "mp3",
    language: Annotated[str | None, typer.Option("--language")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    speed: Annotated[float | None, typer.Option("--speed")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Execute one TTS conversion and write audio bytes to a file."""

    try:
        runtime = SpeechRuntime(load_configuration(config))
        result = runtime.synthesize(
            TtsRequest(
                input_text=text,
                voice=voice,
                language=language,
                profile=profile,
                response_format=format,
                speed=speed,
            )
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result.audio)
    except EccoVoxError as exc:
        _exit_with_error(exc)


def _exit_with_error(error: EccoVoxError) -> None:
    typer.echo(json.dumps(to_error_payload(error), ensure_ascii=False), err=True)
    raise typer.Exit(code=error.mapping.cli_exit_code)


def main() -> None:
    """Run the Typer command application."""

    app()


if __name__ == "__main__":
    main()
