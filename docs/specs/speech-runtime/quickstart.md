# Quickstart: Speech Runtime

Cenários de teste que validam a implementação end-to-end do EccoVox.

## Setup Rapido

```powershell
cd modules/eccovox
python -m pip install -e .[dev]
python -m compileall -q src tests
python -m pytest -q
```

Para validar contrato sem baixar modelos pesados, use engines fake:

```toml
[stt]
engine = "fake-stt"

[tts]
engine = "fake-tts"
```

As engines reais ficam em extras opcionais:

```powershell
python -m pip install -e .[stt]
python -m pip install -e .[tts]
python -m pip install -e .[voice]
```

## Scenario 1: Server Health

1. Instalar EccoVox em ambiente local.
2. Criar `eccovox.toml` com STT e TTS habilitados.
3. Executar `eccovox serve --host 127.0.0.1 --port 8870 --config eccovox.toml`.
4. Chamar `GET http://127.0.0.1:8870/v1/health`.
5. **Expected**: resposta contém `status`, `version`, `capabilities.stt` e `capabilities.tts` conforme contrato.

## Scenario 2: HTTP STT Success

1. Subir server mode com STT habilitado.
2. Enviar áudio curto para `POST /v1/audio/transcriptions`.
3. **Expected**: resposta 200 com `text` não vazio e metadados seguros.

## Scenario 3: HTTP TTS Success

1. Subir server mode com TTS habilitado.
2. Enviar texto curto para `POST /v1/audio/speech`.
3. **Expected**: resposta 200 com bytes de áudio e `Content-Type` compatível com o formato efetivo.

## Scenario 4: CLI STT Success

1. Executar `python -m eccovox.cli transcribe --file input.wav --language pt-BR --format json`.
2. **Expected**: stdout contém JSON de transcrição; stderr não contém áudio, segredo ou texto sensível integral; exit code `0`.

## Scenario 5: CLI TTS Success

1. Executar `python -m eccovox.cli synthesize --text "Olá" --voice pf_dora --output output.mp3 --format mp3`.
2. **Expected**: arquivo `output.mp3` é criado; stdout fica vazio; stderr contém apenas diagnóstico seguro; exit code `0`.

## Scenario 6: Disabled Capability

1. Configurar `stt.enabled=false`.
2. Chamar `POST /v1/audio/transcriptions`.
3. **Expected**: resposta funcional `capability_disabled`; health mostra `capabilities.stt.status=disabled`.

## Scenario 7: Capacity Exceeded

1. Configurar `stt.max_concurrent=1` e `stt.queue_size=0`.
2. Simular duas chamadas STT simultâneas.
3. **Expected**: uma chamada executa; a excedente retorna `capacity_exceeded`.

## Scenario 8: Invalid Override

1. Enviar override de `device` ou `profile` não aceito pelo runtime.
2. **Expected**: resposta `invalid_override` sem chamar engine concreta.

## Scenario 9: Roundtrip End-to-End

1. Subir o server mode real.
2. Chamar `GET /v1/health`.
3. Chamar `POST /v1/audio/transcriptions` com áudio real curto.
4. Chamar `POST /v1/audio/speech` com texto curto.
5. Comparar os payloads e headers reais com [contracts/eccovox-api.md](./contracts/eccovox-api.md).
6. **Expected**: zero divergência de campos obrigatórios, tipos, códigos de erro e `Content-Type`.
