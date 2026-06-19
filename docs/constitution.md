<!--
Sync Impact Report
- Version: none -> 1.0.0
- Princípios modificados: primeira ratificação da constituição do EccoVox
- Seções adicionadas: Core Principles; Quality Standards; Architecture Boundaries; Governance
- Seções removidas: nenhuma
- Artefatos que precisam atualização: docs/briefing/20260618-briefing.md alinhado; specs futuras devem referenciar esta constituição
- TODOs pendentes: nenhum nesta rodada
-->

# EccoVox Constitution

## Core Principles

### Host Independence

EccoVox MUST remain independent from Jarvis, AIChat and any other consuming application. It MAY be incubated inside a larger repository, but its runtime, API contracts, CLI contracts, documentation and configuration MUST NOT depend on host-specific roles, sessions, database schemas, UI flows or domain rules.

Consumers integrate with EccoVox through stable public contracts. Any host-specific mapping, authorization or business policy belongs to the consuming application, not to EccoVox.

### Contract-First Runtime

EccoVox MUST define HTTP and CLI contracts before implementation behavior is considered stable. STT and TTS operations MUST expose predictable inputs, outputs, status codes, exit codes and functional error codes.

Engine-specific details from Whisper, faster-whisper, Kokoro or future providers MUST be adapted behind EccoVox contracts instead of leaking directly to consumers.

### Dual Execution Mode

EccoVox MUST support two first-class execution modes: server mode for persistent HTTP API usage and CLI mode for one-shot local conversions. Both modes MUST share the same internal service contracts so behavior, validation and error semantics remain consistent.

Server mode SHOULD optimize latency by keeping engines warm when configured. CLI mode SHOULD optimize operational simplicity and resource release after execution.

### Engine Replaceability

EccoVox MUST treat STT and TTS engines as replaceable adapters. The initial target engines are Whisper/faster-whisper for STT and Kokoro for TTS, but public contracts MUST NOT require consumers to know or depend on those engines.

Future capabilities such as streaming, live conversation or additional engines MUST be added through explicit contracts, not by breaking existing STT/TTS behavior.

### Privacy by Default

EccoVox MUST minimize retention of audio, generated speech, transcripts and intermediate artifacts. Runtime logs MUST NOT include raw audio, generated audio, full sensitive transcripts or secrets.

Temporary files MAY be used when required by an engine, but they MUST have explicit lifecycle, cleanup behavior and failure handling.

## Quality Standards

Documentation MUST explain what each public command and endpoint does, required inputs, outputs, error behavior, operational limits and deployment assumptions.

Tests SHOULD cover contract-level behavior for HTTP and CLI modes, including valid STT, valid TTS, invalid audio, invalid text, missing model, timeout and engine failure.

Observability MUST distinguish disabled capability, missing configuration, unavailable engine, invalid input, timeout and internal failure without exposing sensitive payloads.

Performance expectations MUST be documented separately for warm server mode and cold CLI mode. EccoVox MUST NOT imply conversational latency for CLI mode unless validated on the target hardware.

## Architecture Boundaries

EccoVox owns voice runtime concerns: loading voice engines, validating voice requests, executing STT/TTS, normalizing errors, exposing HTTP endpoints, exposing CLI commands and managing temporary voice artifacts.

Consuming applications own authentication, authorization, user sessions, UI decisions, business policy, persistence of conversation history and mapping EccoVox results into their own domain.

The initial source layout SHOULD keep API, CLI, engine adapters, core contracts and tests separated so server and CLI modes do not drift.

## Governance

This constitution governs architecture, quality and process decisions for EccoVox. Specs, plans, tasks and implementation decisions MUST align with it.

EccoVox is licensed as Apache-2.0 unless changed by an explicit future governance decision. Third-party libraries, models and voice assets keep their own licenses; users and distributors MUST audit those licenses for their intended use before redistribution or production deployment.

EccoVox packaging policy starts as an independent Python package with the public CLI command `eccovox` and optional extras for development, STT, TTS and full voice runtime. Incubation inside a larger repository MUST NOT make consumers depend on Jarvis-specific packaging.

Amendments MUST update the version, ratification or amendment date, and the Sync Impact Report at the top of this file. Versioning follows SemVer:

- MAJOR for removing or redefining a principle in an incompatible way.
- MINOR for adding a principle or materially expanding governance.
- PATCH for clarifications that do not change meaning.

Exceptions are allowed only when explicitly documented in the affected spec, plan, task or architecture decision, with rationale, risk and validation plan.

**Version**: 1.0.0 | **Ratified**: 2026-06-18 | **Last Amended**: 2026-06-18
