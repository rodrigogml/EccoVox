# Research: Speech Runtime

Documento produzido no Phase 0 do plan. Resolve decisões técnicas do runtime STT/TTS do EccoVox.

## Decision 1: HTTP API com FastAPI

**Decision**: Usar FastAPI como framework HTTP do EccoVox.
**Rationale**: FastAPI oferece suporte direto a APIs tipadas, multipart upload, responses binárias, validação de payloads e documentação OpenAPI. Isso se alinha ao princípio Contract-First Runtime e reduz trabalho manual para expor health, STT e TTS.
**Alternatives considered**: Flask é simples, mas exigiria mais validação manual; Starlette é mais baixo nível e aumentaria boilerplate; implementar HTTP puro seria custo desnecessário.

**Source**: [FastAPI documentation](https://fastapi.tiangolo.com/)

## Decision 2: ASGI server com Uvicorn

**Decision**: Usar Uvicorn para rodar o server mode.
**Rationale**: Uvicorn é servidor ASGI para Python e suporta HTTP/1.1 e WebSockets. Mesmo sem streaming no MVP, ASGI deixa uma base compatível com capacidades futuras de streaming/live sem trocar a camada de servidor.
**Alternatives considered**: Gunicorn com workers pode ser útil em Linux, mas adiciona complexidade inicial; servidor síncrono simples reduziria flexibilidade futura.

**Source**: [Uvicorn documentation](https://uvicorn.dev/)

## Decision 3: CLI com Typer

**Decision**: Usar Typer para implementar `eccovox serve`, `eccovox transcribe` e `eccovox synthesize`.
**Rationale**: Typer é baseado em type hints, favorece comandos claros e integra bem com empacotamento Python via console script. Isso preserva contrato público de CLI sem parser manual extenso.
**Alternatives considered**: `argparse` evita dependência nova, mas cresce pior com subcomandos e validações; Click é maduro, mas Typer reduz boilerplate para o estilo pretendido.

**Source**: [Typer documentation](https://typer.tiangolo.com/)

## Decision 4: Configuração TOML com tomllib

**Decision**: Ler `eccovox.toml` com `tomllib`, disponível na biblioteca padrão a partir do Python 3.11.
**Rationale**: O projeto já exige Python 3.11+. `tomllib` elimina dependência para leitura de TOML e atende ao uso de configuração local. Escrita de TOML não é necessária no MVP.
**Alternatives considered**: YAML exigiria dependência extra e maior superfície de parsing; JSON é menos legível para configuração operacional; `tomli` seria redundante em Python 3.11+.

**Source**: [Python tomllib documentation](https://docs.python.org/3/library/tomllib.html)

## Decision 5: Testes com pytest e TestClient

**Decision**: Usar pytest para testes unitários, CLI e contratos HTTP; para API, usar o test client compatível com FastAPI/Starlette.
**Rationale**: pytest é padrão maduro para Python, facilita fixtures de arquivos temporários, monkeypatch de engines e validação de CLI/API sem subir processo externo em todos os testes.
**Alternatives considered**: `unittest` evita dependência, mas torna fixtures e parametrização mais verbosas; testes só manuais não atendem o contrato da constitution.

**Source**: [pytest documentation](https://docs.pytest.org/)

## Decision 6: Engines iniciais como extras opcionais

**Decision**: Declarar FastAPI/Typer/testes como dependências do projeto e tratar engines pesadas (`faster-whisper`, Kokoro, soundfile) como extras opcionais no `pyproject.toml`.
**Rationale**: Isso permite instalar EccoVox core para desenvolver contratos e testes sem baixar modelos ou dependências nativas pesadas. Deploy real escolhe extras `stt`, `tts` ou `voice`.
**Alternatives considered**: Colocar todas as engines em dependencies simplifica instalação completa, mas torna setup de desenvolvimento pesado; deixar tudo sem declarar prejudica reprodutibilidade.

## Decision 7: Concorrência conservadora no MVP

**Decision**: Defaults de `max_concurrent=1` por capacidade e `queue_size=0`, rejeitando excesso com `capacity_exceeded`.
**Rationale**: STT/TTS podem consumir CPU/RAM/VRAM intensamente. Sem medição real, rejeição explícita é mais previsível que filas longas e latência escondida.
**Alternatives considered**: Fila ilimitada arrisca saturação; concorrência maior pode ser ótima em hardware forte, mas deve ser ajuste operacional posterior.

## Decision 8: TTS CLI grava em arquivo no MVP

**Decision**: `eccovox synthesize` deve exigir ou aceitar `--output` e gravar áudio em arquivo no MVP; stdout fica reservado para resultados textuais/JSON futuros.
**Rationale**: Bytes de áudio em stdout complicam diagnóstico, logs, shell e integração no Windows. Arquivo explícito é mais simples e seguro para o MVP.
**Alternatives considered**: Stdout binário é útil para pipes Unix, mas aumenta risco de misturar áudio com logs; retornar JSON com base64 amplia payload sem necessidade inicial.
