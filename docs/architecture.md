# EccoVox Architecture

EccoVox é um runtime de voz independente. Ele não conhece aplicações consumidoras; expõe contratos HTTP e CLI para que qualquer host consuma STT e TTS.

## Contexto

```text
Consumer application
  |-- HTTP -> EccoVox server
  `-- CLI  -> eccovox command

EccoVox
  |-- API layer
  |-- CLI layer
  |-- Core speech contracts
  |-- Engine adapters
  |   |-- STT: faster-whisper
  |   `-- TTS: Kokoro
  `-- Runtime diagnostics
```

## Modos de Execução

### Server Mode

`eccovox serve` inicia um processo persistente com endpoints HTTP. Esse modo é adequado para baixa latência, uso frequente e engines carregadas em memória.

### CLI Mode

`eccovox transcribe` e `eccovox synthesize` executam conversões pontuais. Esse modo é adequado para diagnóstico, automações simples e ambientes onde memória residente deve ser evitada.

CLI mode pode ter cold start maior porque carrega runtime e modelos por execução.

## Contratos Públicos

| Superfície | Contrato | Responsabilidade |
|------------|----------|------------------|
| HTTP health | `GET /v1/health` | Expor disponibilidade de STT/TTS. |
| HTTP STT | `POST /v1/audio/transcriptions` | Converter áudio em texto. |
| HTTP TTS | `POST /v1/audio/speech` | Converter texto em áudio. |
| CLI serve | `eccovox serve` | Iniciar API HTTP. |
| CLI STT | `eccovox transcribe` | Converter áudio em texto sob demanda. |
| CLI TTS | `eccovox synthesize` | Converter texto em áudio sob demanda. |

## Camadas Internas

| Camada | Responsabilidade |
|--------|------------------|
| API | Parsear HTTP, validar payload, serializar resposta e erro. |
| CLI | Parsear argumentos, chamar contratos internos e definir exit codes. |
| Core | Definir requests, responses, erros e contratos de STT/TTS. |
| Engine adapters | Isolar detalhes de faster-whisper, Kokoro e futuras engines. |
| Runtime diagnostics | Health, capacidade efetiva, tempos e mensagens seguras. |
| Temporary artifacts | Criar e limpar arquivos transitórios quando necessários. |

## Extensão Futura

Streaming e conversação live ficam fora do MVP. A arquitetura deve reservar nomes e camadas para futuras capacidades sem quebrar STT/TTS síncronos:

- `POST /v1/audio/transcriptions` permanece síncrono.
- `POST /v1/audio/speech` permanece síncrono.
- Streaming futuro deve usar endpoints ou protocolos próprios.
- Conversação live futura deve ser uma capability nova, não uma extensão implícita de STT/TTS.
- Qualquer API live futura deve declarar lifecycle, streaming transport, cancelamento, buffering e política de privacidade próprios.

## Diretrizes

- API e CLI compartilham os mesmos contratos internos.
- Engines nunca vazam erro bruto para consumidor.
- Logs não registram áudio, texto sensível integral ou segredos.
- Modo servidor e modo CLI têm expectativas de performance separadas.
- Consumidores cuidam de autenticação, autorização, sessão, UI e histórico.
