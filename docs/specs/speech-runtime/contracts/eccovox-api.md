# Contract: EccoVox API and CLI

## HTTP Health

**Method**: `GET /v1/health`

### Response 200

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | yes | `ready`, `degraded`, `disabled` ou `unavailable`. |
| version | string | yes | Versão do EccoVox. |
| capabilities | object | yes | Status por capacidade. |

### Status Semantics

| Status | Scope | Meaning |
|--------|-------|---------|
| `ready` | global/capability | Tudo que está habilitado e necessário para a capacidade está pronto. |
| `disabled` | global/capability | Capacidade desabilitada intencionalmente por configuração; não é falha. |
| `degraded` | global | Ao menos uma capacidade habilitada está pronta e ao menos uma capacidade habilitada não está pronta. |
| `degraded` | capability | Capacidade aceita chamadas, mas com limitação conhecida, como fallback de device ou formato. |
| `unavailable` | global/capability | Capacidade habilitada não pode atender por falha/configuração/modelo/engine indisponível. |

### Capability Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | yes | `ready`, `degraded`, `disabled` ou `unavailable`. |
| engine | string | no | Engine efetiva, quando configurada. |
| model | string | no | Modelo efetivo, quando conhecido. |
| device | string | no | `cpu`, `cuda`, `rocm`, `mps` ou equivalente. |
| formats | array[string] | no | Formatos aceitos/emitidos. |
| safeMessage | string | no | Diagnóstico seguro. |

### Example

```json
{
  "status": "degraded",
  "version": "0.1.0",
  "capabilities": {
    "stt": {
      "status": "ready",
      "engine": "faster-whisper",
      "model": "large-v3",
      "device": "cpu",
      "formats": ["wav", "mp3", "webm"]
    },
    "tts": {
      "status": "disabled",
      "safeMessage": "TTS capability is disabled by configuration."
    }
  }
}
```

## HTTP STT

**Method**: `POST /v1/audio/transcriptions`

**Content-Type**: `multipart/form-data`

### Request

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| file | binary | yes | Áudio de entrada. |
| language | string | no | Idioma preferencial. |
| profile | string | no | Perfil de runtime. |
| responseFormat | string | no | `json` no MVP. |
| model | string | no | Override de modelo quando permitido pelo profile. |
| device | string | no | Override de device quando permitido pelo profile. |
| computeType | string | no | Override de compute type quando permitido pelo profile. |

### Response 200

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | string | yes | Texto transcrito normalizado. |
| language | string | no | Idioma detectado ou configurado. |
| confidence | number | no | Confiança quando disponível. |
| durationMillis | number | no | Duração de processamento. |
| metadata | object | no | Metadados seguros. |

## HTTP TTS

**Method**: `POST /v1/audio/speech`

**Content-Type**: `application/json`

### Request

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| input | string | yes | Texto para síntese. |
| voice | string | no | Voz preferencial. |
| language | string | no | Idioma preferencial. |
| profile | string | no | Perfil de runtime. |
| responseFormat | string | no | `mp3`, `wav`, `opus`, `flac` ou formato adicional suportado e anunciado pelo runtime. |
| speed | number | no | Velocidade quando suportada. |

### Response 200

Retorna bytes de áudio. `Content-Type` deve refletir o formato efetivo.

## Error Response

Aplicável aos endpoints HTTP.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | yes | Código funcional estável. |
| message | string | yes | Mensagem segura para consumidor. |
| retryable | boolean | yes | Indica se retry pode fazer sentido. |
| details | object | no | Diagnóstico seguro e limitado. |

### Error Codes

| HTTP | Code | Description |
|------|------|-------------|
| 400 | invalid_audio | Áudio ausente, vazio ou inválido. |
| 400 | invalid_text | Texto ausente, vazio ou inválido. |
| 400 | invalid_override | Parâmetro por chamada não é aceito pelo profile/capacidade. |
| 404 | capability_disabled | Capacidade não habilitada. |
| 415 | unsupported_audio_format | Formato de áudio de entrada ou saída não suportado pela capacidade. |
| 409 | capacity_exceeded | Limite de concorrência ou fila atingido. |
| 408 | timeout | Operação excedeu timeout. |
| 422 | empty_transcription | STT não identificou texto útil. |
| 500 | engine_functional_error | Engine retornou erro funcional previsto, mas não mapeado para código mais específico. |
| 503 | runtime_unavailable | Engine/modelo indisponível. |
| 500 | internal_error | Falha técnica inesperada. |

## Configuration File

O arquivo `eccovox.toml` define defaults operacionais. Parâmetros HTTP/CLI válidos podem sobrescrever esses defaults apenas na chamada corrente.

```toml
[server]
host = "127.0.0.1"
port = 8870

[runtime]
temp_dir = ".eccovox/tmp"
request_timeout_seconds = 120
profiles = ["default", "balanced", "premium", "diagnostic", "process"]
default_profile = "balanced"

[stt]
enabled = true
engine = "faster-whisper"
profile = "balanced"
model = "large-v3"
device = "cpu"
compute_type = "int8"
max_audio_bytes = 10485760
short_audio_budget_millis = 5000
max_concurrent = 1
queue_size = 0

[tts]
enabled = true
engine = "kokoro"
profile = "balanced"
voice = "pf_dora"
language = "pt-BR"
response_format = "mp3"
max_text_chars = 4000
short_text_start_budget_millis = 2000
max_concurrent = 1
queue_size = 0
```

Budgets de latência são metas operacionais por perfil, modo, operação e tamanho de solicitação. Eles não limitam universalmente áudio ou texto longo; nesses casos prevalecem `request_timeout_seconds`, limites de tamanho e políticas de divisão ou recusa funcional.

## CLI

### Server Mode

```powershell
eccovox serve --host 127.0.0.1 --port 8870 --config eccovox.toml
```

### STT Mode

```powershell
eccovox transcribe --file input.wav --language pt-BR --format json
```

Saída JSON esperada:

```json
{
  "text": "texto transcrito",
  "language": "pt-BR",
  "metadata": {}
}
```

Regras:

- `stdout` deve conter apenas o JSON de resultado quando `--format json`.
- `stderr` deve conter apenas diagnóstico/log seguro.
- `--profile`, `--model`, `--device`, `--compute-type` e `--language` podem sobrescrever defaults quando aceitos.

### TTS Mode

```powershell
eccovox synthesize --text "Olá" --voice pf_dora --output output.mp3 --format mp3
```

Regras:

- MVP deve suportar `--output <path>` para gravar o áudio.
- `stdout` deve ficar vazio em sucesso com `--output`, salvo quando formato de saída textual/JSON for explicitamente solicitado em versão futura.
- `stderr` deve conter apenas diagnóstico/log seguro.
- `--profile`, `--voice`, `--language`, `--format` e `--speed` podem sobrescrever defaults quando aceitos.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Sucesso. |
| 2 | Entrada inválida. |
| 3 | Capacidade desabilitada ou indisponível. |
| 4 | Timeout. |
| 5 | Erro funcional da engine, incluindo `empty_transcription`, `unsupported_audio_format` ou `engine_functional_error` quando aplicável. |
| 6 | Capacidade excedida por concorrência/fila. |
| 10 | Erro técnico inesperado. |
