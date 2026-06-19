# EccoVox

EccoVox is an independent local voice runtime incubated in this repository.

It provides speech capabilities through two execution modes:

- HTTP server mode for long-running API integration.
- CLI mode for direct one-shot transcription or synthesis.

The initial scope is limited to:

- STT: audio to text.
- TTS: text to audio.

EccoVox does not know Jarvis, AIChat or any host application. Consumers integrate through documented HTTP and CLI contracts.

## Development

Install the lightweight development/runtime dependencies:

```powershell
python -m pip install -e .[dev]
```

If the local Python certificate store blocks PyPI, use the host-approved certificate fix or a trusted internal mirror. During local troubleshooting only, this workspace was validated with:

```powershell
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -e .[dev]
```

Run validation:

```powershell
python -m compileall -q src tests
python -m pytest -q
python -m eccovox.cli --help
python -m eccovox.cli serve --help
python -m eccovox.cli transcribe --help
python -m eccovox.cli synthesize --help
```

For contract tests without heavy STT/TTS dependencies, configure fake engines:

```toml
[stt]
engine = "fake-stt"

[tts]
engine = "fake-tts"
```

Install optional real engines separately when needed:

```powershell
python -m pip install -e .[stt]
python -m pip install -e .[tts]
python -m pip install -e .[voice]
```

## Documentation

- [Briefing](docs/briefing/20260618-briefing.md)
- [Constitution](docs/constitution.md)
- [Architecture](docs/architecture.md)
- [Licenses](docs/licenses.md)
- [Speech Runtime Spec](docs/specs/speech-runtime/spec.md)
- [API and CLI Contract](docs/specs/speech-runtime/contracts/eccovox-api.md)
- [Quickstart](docs/specs/speech-runtime/quickstart.md)
