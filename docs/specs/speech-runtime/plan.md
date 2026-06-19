# Implementation Plan: Speech Runtime

**Feature**: `speech-runtime` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)

## Summary

Implementar o runtime inicial do EccoVox com duas superfícies públicas: API HTTP persistente e CLI sob demanda. O MVP cobre STT e TTS síncronos, usando adapters internos para `faster-whisper` e Kokoro, com contratos estáveis, configuração TOML, overrides por chamada, health, erros funcionais e política conservadora de concorrência.

O desenho mantém EccoVox independente de qualquer host. Jarvis ou outros consumidores integram apenas via contrato HTTP/CLI.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Uvicorn, Typer, pytest; extras opcionais para `faster-whisper`, Kokoro e soundfile  
**Storage**: Arquivos locais para modelos/cache e temporários; sem banco de dados  
**Testing**: pytest, FastAPI/TestClient, testes de CLI com fixtures temporárias  
**Target Platform**: Windows e Linux locais; server mode em loopback por padrão  
**Project Type**: Python package com HTTP service e CLI  
**Performance Goals**: Server mode com engines quentes dentro do budget configurado por perfil/operação/tamanho; CLI mode com cold start documentado  
**Constraints**: Projeto independente, contratos antes de implementação, logs seguros, defaults conservadores, sem streaming/live no MVP  
**Scale/Scope**: MVP local/single-host; concorrência default `1` por capacidade e fila `0`

## Constitution Check

*GATE: Deve passar antes do Phase 0. Rechecar após Phase 1.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| Host Independence | PASS | Contratos não mencionam Jarvis nem exigem regra de host. |
| Contract-First Runtime | PASS | HTTP/CLI e erros estão documentados antes da implementação. |
| Dual Execution Mode | PASS | Server e CLI são modos de primeira classe. |
| Engine Replaceability | PASS | Engines ficam atrás de adapters e profiles. |
| Privacy by Default | PASS | Logs e temporários têm política segura documentada. |

## Project Structure

### Documentation (this feature)

```text
modules/eccovox/docs/specs/speech-runtime/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
`-- contracts/
    `-- eccovox-api.md
```

### Source Code (repository root)

```text
modules/eccovox/
|-- pyproject.toml
|-- README.md
|-- src/eccovox/
|   |-- __init__.py
|   |-- cli.py
|   |-- api/
|   |   |-- __init__.py
|   |   |-- app.py
|   |   `-- routes.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   |-- errors.py
|   |   |-- models.py
|   |   |-- runtime.py
|   |   `-- concurrency.py
|   |-- engine/
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- faster_whisper.py
|   |   `-- kokoro.py
|   `-- util/
|       |-- __init__.py
|       `-- temp_artifact.py
`-- tests/
    |-- test_config.py
    |-- test_health_contract.py
    |-- test_cli_contract.py
    |-- test_stt_contract.py
    `-- test_tts_contract.py
```

**Structure Decision**: Separar `api`, `cli`, `core` e `engine` para impedir que HTTP/CLI conheçam detalhes de engines. `util` é permitido aqui apenas com contexto claro e escopo pequeno para artefatos temporários; se crescer, deve virar pacote de domínio.

## Convenções de Borda

| Camada | Case style | Validação | Fonte da verdade |
|--------|------------|-----------|------------------|
| TOML config | snake_case | loader + tests | `data-model.md` e `eccovox.toml` |
| Python model fields | snake_case | dataclasses/pydantic | `core/models.py` |
| HTTP JSON | camelCase | FastAPI/Pydantic + contract tests | `contracts/eccovox-api.md` |
| CLI options | kebab-case | Typer + CLI tests | `contracts/eccovox-api.md` |
| Public error codes | snake_case | enum/constants + tests | `contracts/eccovox-api.md` |
| Audio content | MIME types | response headers + tests | `contracts/eccovox-api.md` |

**Mapper layer (config/HTTP/CLI <-> core)**: `core.runtime` recebe modelos internos normalizados. API e CLI convertem entrada externa para esses modelos.

**Validação de schema**: requests, responses, exit codes e erros devem ter testes de contrato.

## Phase 0: Research Summary

Pesquisa consolidada em [research.md](./research.md).

Decisões principais:

1. FastAPI para HTTP.
2. Uvicorn para ASGI server.
3. Typer para CLI.
4. `tomllib` para leitura TOML.
5. pytest para testes.
6. Engines pesadas como extras opcionais.
7. Concorrência conservadora no MVP.
8. TTS CLI grava em arquivo no MVP.

## Phase 1: Design Summary

Artefatos de design:

- [data-model.md](./data-model.md): configuração, profiles, health, operações, adapters e temporários.
- [contracts/eccovox-api.md](./contracts/eccovox-api.md): HTTP, CLI, erros, config e exit codes.
- [quickstart.md](./quickstart.md): cenários de validação end-to-end.

## Implementation Approach

1. Atualizar `pyproject.toml` com dependências core, dev extras e extras de engines.
2. Criar modelos internos de config, health, request/result, erro e operação.
3. Implementar loader TOML com defaults e validação.
4. Implementar registry de engine adapters com stubs testáveis.
5. Implementar health por capability.
6. Implementar semáforos/limites por capacidade no server mode.
7. Implementar FastAPI app e rotas `/v1/health`, `/v1/audio/transcriptions`, `/v1/audio/speech`.
8. Implementar CLI Typer com `serve`, `transcribe`, `synthesize`.
9. Implementar adapters reais `faster-whisper` e Kokoro atrás das interfaces.
10. Implementar política de temporários e logs seguros.
11. Validar contratos HTTP e CLI com pytest.

## Validation Scenarios

Gates mínimos:

- `python -m py_compile` para pacote.
- `pytest` para contratos core/API/CLI.
- `eccovox --help`, `eccovox serve --help`, `eccovox transcribe --help`, `eccovox synthesize --help`.
- Testes com engines fake para contratos sem dependências pesadas.
- Teste operacional real com engines instaladas quando extras estiverem disponíveis.

Cobertura focada:

- Health com STT/TTS ready, disabled, degraded e unavailable.
- STT HTTP sucesso e erros.
- TTS HTTP sucesso e erros.
- CLI stdout/stderr/exit code.
- Invalid override sem chamar engine.
- Capacity exceeded.
- Temporários limpos em sucesso e erro.
- Logs sem áudio, transcrição sensível integral ou segredos.

## Re-check da Constitution

| Princípio | Status | Notas |
|-----------|--------|-------|
| Host Independence | PASS | Plano não adiciona regra de host consumidor. |
| Contract-First Runtime | PASS | Contratos e quickstart guiam implementação. |
| Dual Execution Mode | PASS | API e CLI compartilham core runtime. |
| Engine Replaceability | PASS | Adapters isolam engines concretas. |
| Privacy by Default | PASS | Temporários e logs seguros são gates de validação. |

## Complexity Tracking

Não há violações de constitution que exijam justificativa.
