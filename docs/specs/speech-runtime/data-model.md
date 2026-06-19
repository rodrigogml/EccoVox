# Data Model: Speech Runtime

## Entity: RuntimeConfiguration

Configuração carregada de `eccovox.toml` e combinada com argumentos CLI ou parâmetros HTTP por chamada.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| server.host | string | default `127.0.0.1` | Host do server mode. |
| server.port | integer | default `8870` | Porta do server mode. |
| runtime.tempDir | path | required/default | Diretório de temporários. |
| runtime.requestTimeoutSeconds | integer | min 1 | Timeout default de operação. |
| stt.enabled | boolean | default false | Habilita capacidade STT. |
| stt.engine | string | default `faster-whisper` | Engine STT inicial. |
| stt.model | string | optional | Modelo default. |
| stt.device | string | optional | `cpu`, `cuda`, `rocm`, `mps` ou engine-specific. |
| stt.computeType | string | optional | Perfil de inferência. |
| stt.maxAudioBytes | integer | min 1 | Limite de áudio de entrada. |
| stt.maxConcurrent | integer | min 1 | Concorrência server mode. |
| stt.queueSize | integer | min 0 | Fila server mode. |
| tts.enabled | boolean | default false | Habilita capacidade TTS. |
| tts.engine | string | default `kokoro` | Engine TTS inicial. |
| tts.voice | string | optional | Voz default. |
| tts.language | string | optional | Idioma default. |
| tts.responseFormat | string | default `mp3` | Formato default. |
| tts.maxTextChars | integer | min 1 | Limite de texto. |
| tts.maxConcurrent | integer | min 1 | Concorrência server mode. |
| tts.queueSize | integer | min 0 | Fila server mode. |

### Relationships

- `RuntimeConfiguration` cria `RuntimeProfile` efetivo por capacidade.
- Parâmetros HTTP/CLI válidos sobrescrevem campos por operação, sem alterar o arquivo.

## Entity: RuntimeProfile

Perfil efetivo usado por uma chamada STT ou TTS.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| name | string | optional | Identificador lógico do profile. |
| capability | enum | stt, tts | Capacidade aplicável. |
| engine | string | required | Engine efetiva. |
| model | string | optional | Modelo efetivo. |
| voice | string | optional | Voz efetiva para TTS. |
| language | string | optional | Idioma efetivo. |
| device | string | optional | Device efetivo. |
| responseFormat | string | optional | Formato de saída TTS. |
| speed | number | optional | Velocidade TTS. |

### Relationships

- `RuntimeProfile` é derivado de `RuntimeConfiguration` + override por chamada.
- `EngineAdapter` recebe um `RuntimeProfile` validado.

## Entity: CapabilityHealth

Estado público de uma capacidade no health.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| status | enum | ready, disabled, degraded, unavailable | Estado funcional. |
| engine | string | optional | Engine efetiva. |
| model | string | optional | Modelo efetivo. |
| device | string | optional | Device efetivo. |
| formats | array[string] | optional | Formatos aceitos/emitidos. |
| safeMessage | string | optional | Diagnóstico sem segredos. |

### State Transitions

```text
disabled -> ready
disabled -> unavailable
ready -> degraded -> ready
ready -> unavailable -> ready
```

## Entity: SpeechOperation

Representa uma operação transitória de STT ou TTS.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| operationId | string | generated | Identificador de diagnóstico. |
| capability | enum | stt, tts | Capacidade executada. |
| mode | enum | http, cli | Superfície de entrada. |
| profile | RuntimeProfile | required | Perfil efetivo. |
| status | enum | success, functional_error, technical_error, timeout, capacity_exceeded | Resultado. |
| errorCode | string | optional | Código público. |
| startedAt | datetime | required | Início. |
| finishedAt | datetime | optional | Fim. |
| durationMillis | integer | optional | Duração. |

## Entity: EngineAdapter

Adaptador interno para uma engine concreta.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| capability | enum | stt, tts | Capacidade suportada. |
| engineName | string | required | Nome público seguro. |
| supportsHealth | boolean | required | Indica health próprio. |
| supportedFormats | array[string] | optional | Formatos suportados. |

## Entity: TemporaryArtifact

Arquivo transitório necessário para engines ou resposta TTS.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| path | path | required | Caminho local transitório. |
| type | enum | input_audio, output_audio, intermediate | Tipo. |
| ownerOperationId | string | required | Operação dona. |
| expiresAt | datetime | required | Limite de retenção. |
| cleaned | boolean | required | Indica limpeza. |
