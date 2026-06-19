# Feature Specification: Speech Runtime

**Feature**: `speech-runtime`
**Created**: 2026-06-18
**Status**: Draft

## Clarifications

### Session 2026-06-18

- Q: EccoVox deve depender de configuração fixa ou aceitar parâmetros por chamada? -> A: EccoVox deve ter defaults por configuração própria, mas deve aceitar overrides por chamada quando o contrato permitir.
- Q: `disabled` é estado funcional? -> A: Sim. Capacidade desabilitada intencionalmente deve ser representada por estado funcional `disabled`, separado de erro técnico ou engine indisponível.
- Q: Quem controla concorrência em server mode? -> A: EccoVox controla concorrência, fila e rejeição em server mode; consumidores só observam erros/status documentados.
- Q: CLI deve ser contrato público de integração? -> A: Sim. CLI STT/TTS deve ter stdout/stderr, exit codes, arquivos de entrada/saída e erros documentados.
- Q: Live/streaming entra no MVP? -> A: Não. Deve ser reservado para capacidade futura separada, sem alterar os endpoints síncronos.
- Q: Qual licença governa o projeto EccoVox? -> A: EccoVox deve usar Apache-2.0 como licença do projeto. Dependências, modelos e assets de terceiros mantêm suas próprias licenças e devem ser auditados pelo usuário/distribuidor.
- Q: Como EccoVox deve ser empacotado? -> A: Como Python package independente com CLI `eccovox` e extras opcionais (`dev`, `stt`, `tts`, `voice`), mesmo enquanto estiver incubado no monorepo.
- Q: Quais defaults de concorrência valem no MVP? -> A: `max_concurrent=1` e `queue_size=0` para STT e TTS, mantendo esses valores configuráveis.
- Q: Como tratar latência sem limitar áudio/texto grande? -> A: Latência deve ser budget operacional configurável por modo, perfil, operação e tamanho da solicitação. Timeouts, limites de tamanho e políticas de processamento devem ficar no arquivo de configuração ou em parâmetros por chamada quando suportado.
- Q: Perfis premium por roles entram no MVP? -> A: Não. O MVP deve manter perfis centralizados e configuráveis, mas a associação de perfil/modelo/voz a roles fica para fase futura.

## User Scenarios & Testing

### User Story 1 - Transcrever áudio por API HTTP (Priority: P1)

Como aplicação consumidora, quero enviar áudio ao EccoVox por API HTTP e receber texto transcrito, para usar STT local sem integrar diretamente a engine de transcrição.

**Why this priority**: STT é uma das duas capacidades iniciais do projeto. O modo servidor atende integrações que precisam de baixa latência e modelo carregado.

**Independent Test**: Subir o EccoVox em modo servidor, enviar um arquivo de áudio curto ao endpoint de transcrição e validar resposta com texto ou erro funcional.

**Acceptance Scenarios**:

1. **Given** EccoVox em modo servidor com STT configurado, **When** uma aplicação enviar áudio válido, **Then** a API deve retornar texto transcrito e metadados seguros.
2. **Given** áudio vazio ou inválido, **When** uma aplicação solicitar transcrição, **Then** a API deve retornar erro funcional estável.
3. **Given** engine STT indisponível, **When** uma aplicação solicitar transcrição, **Then** a API deve retornar indisponibilidade sem expor erro bruto da engine.
4. **Given** STT desabilitado por configuração, **When** uma aplicação solicitar transcrição, **Then** a API deve retornar erro funcional de capacidade desabilitada.
5. **Given** STT configurado com modelo default, **When** uma aplicação enviar `profile`, `language` ou parâmetros suportados por chamada, **Then** EccoVox deve usar os overrides válidos e aplicar defaults aos campos ausentes.

---

### User Story 2 - Gerar áudio por API HTTP (Priority: P1)

Como aplicação consumidora, quero enviar texto ao EccoVox por API HTTP e receber áudio sintetizado, para usar TTS local sem integrar diretamente a engine de síntese.

**Why this priority**: TTS completa o escopo inicial e permite que consumidores ofereçam saída por voz com runtime local.

**Independent Test**: Subir o EccoVox em modo servidor, enviar texto curto ao endpoint de síntese e validar bytes de áudio com `Content-Type` reproduzível.

**Acceptance Scenarios**:

1. **Given** EccoVox em modo servidor com TTS configurado, **When** uma aplicação enviar texto válido, **Then** a API deve retornar áudio no formato solicitado ou default.
2. **Given** texto vazio ou acima do limite, **When** uma aplicação solicitar síntese, **Then** a API deve retornar erro funcional estável.
3. **Given** engine TTS indisponível, **When** uma aplicação solicitar síntese, **Then** a API deve retornar indisponibilidade sem expor erro bruto da engine.
4. **Given** TTS desabilitado por configuração, **When** uma aplicação solicitar síntese, **Then** a API deve retornar erro funcional de capacidade desabilitada.
5. **Given** TTS configurado com voz default, **When** uma aplicação enviar `voice`, `responseFormat`, `speed`, `language` ou `profile`, **Then** EccoVox deve usar os overrides válidos e aplicar defaults aos campos ausentes.

---

### User Story 3 - Executar conversões por CLI (Priority: P2)

Como operador ou aplicação local, quero executar STT e TTS pelo comando `eccovox`, para realizar conversões sob demanda sem manter servidor persistente.

**Why this priority**: CLI reduz custo operacional em ambientes de baixo uso, facilita diagnóstico e permite automações simples.

**Independent Test**: Executar `eccovox transcribe` com um arquivo de áudio e `eccovox synthesize` com texto curto, validando arquivo/saída gerada e exit code.

**Acceptance Scenarios**:

1. **Given** EccoVox instalado com STT configurado, **When** o operador executar `eccovox transcribe`, **Then** o comando deve emitir transcrição em formato documentado.
2. **Given** EccoVox instalado com TTS configurado, **When** o operador executar `eccovox synthesize`, **Then** o comando deve gravar ou emitir áudio no formato solicitado.
3. **Given** erro funcional ou técnico, **When** o comando falhar, **Then** deve retornar exit code e erro estruturado previsíveis.
4. **Given** o comando STT ou TTS recebe parâmetros opcionais, **When** a execução iniciar, **Then** parâmetros CLI válidos devem sobrescrever os defaults do arquivo de configuração apenas naquela chamada.
5. **Given** a execução CLI gera logs ou diagnósticos, **When** o comando terminar, **Then** stdout deve conter apenas o resultado documentado e stderr deve conter diagnósticos seguros.

---

### User Story 4 - Validar disponibilidade do runtime (Priority: P2)

Como aplicação consumidora ou operador, quero consultar health e capacidades efetivas do EccoVox, para saber se STT/TTS estão prontos antes de enviar requisições reais.

**Why this priority**: Engines de voz dependem de modelos, dispositivo, memória e configuração. Consumidores precisam diferenciar indisponibilidade de STT e TTS.

**Independent Test**: Subir EccoVox com STT e TTS completos, parciais e ausentes, chamando health em cada cenário.

**Acceptance Scenarios**:

1. **Given** STT e TTS prontos, **When** consumidor consultar health, **Then** a resposta deve indicar disponibilidade de ambas as capacidades.
2. **Given** apenas STT pronto, **When** consumidor consultar health, **Then** TTS deve aparecer indisponível sem afetar STT.
3. **Given** modelo ausente, **When** consumidor consultar health, **Then** resposta deve indicar configuração incompleta ou engine indisponível.
4. **Given** STT ou TTS desabilitado intencionalmente, **When** consumidor consultar health, **Then** a capacidade deve retornar `disabled`.
5. **Given** uma capacidade pronta e outra indisponível, **When** consumidor consultar health, **Then** o status global deve retornar `degraded`.

### Edge Cases

- STT pronto e TTS ausente.
- TTS pronto e STT ausente.
- STT ou TTS desabilitado intencionalmente por configuração.
- Modelo configurado, mas download/cache ausente.
- CLI chamada simultaneamente por múltiplos processos.
- Server mode recebe chamadas concorrentes acima da capacidade do hardware.
- Áudio ou texto contém informação sensível.
- Texto longo demais para síntese em chamada única.
- Runtime precisa usar arquivo temporário para atender exigência da engine.
- Engine troca formato de retorno após upgrade.
- Futuro streaming/live não deve quebrar endpoints síncronos existentes.

## Requirements

### Functional Requirements

- **FR-001**: EccoVox MUST expose an HTTP health endpoint with STT and TTS capability status.
- **FR-002**: EccoVox MUST expose an HTTP STT endpoint that accepts audio and returns normalized transcription result.
- **FR-003**: EccoVox MUST expose an HTTP TTS endpoint that accepts text and returns playable audio bytes.
- **FR-004**: EccoVox MUST expose CLI commands for STT and TTS using the same internal contracts as HTTP mode.
- **FR-005**: EccoVox MUST keep HTTP and CLI error semantics consistent.
- **FR-006**: EccoVox MUST adapt engine-specific failures into stable functional error codes.
- **FR-007**: EccoVox MUST support independent availability of STT and TTS.
- **FR-008**: EccoVox MUST not require consumers to know whether Whisper, faster-whisper, Kokoro or another engine is used.
- **FR-009**: EccoVox MUST not log raw audio, generated audio, full sensitive transcripts or secrets.
- **FR-010**: EccoVox MUST document temporary artifact lifecycle when files are required by engines.
- **FR-011**: EccoVox MUST allow server mode startup with configured host, port, engines and model profiles.
- **FR-012**: EccoVox MUST allow CLI mode execution without starting the HTTP server.
- **FR-013**: EccoVox MUST document concurrency limits for server mode and expected cold-start cost for CLI mode.
- **FR-014**: EccoVox MUST leave live conversation and streaming out of the first implementation while preserving extension points for future contracts.
- **FR-015**: EccoVox MUST support capability status values `ready`, `disabled`, `degraded` and `unavailable` where applicable.
- **FR-016**: EccoVox MUST define `disabled` as intentional configuration state, not as runtime failure.
- **FR-017**: EccoVox MUST define global `degraded` as partial readiness where at least one enabled capability is ready and at least one enabled capability is not ready.
- **FR-018**: EccoVox MUST define global `unavailable` as no enabled capability ready because of configuration, model, engine or runtime failure.
- **FR-019**: EccoVox MUST support a configuration file with default values for host, port, enabled capabilities, engine profiles, models, voices, formats, limits, temporary directory and concurrency.
- **FR-020**: EccoVox MUST allow supported per-call HTTP and CLI parameters to override defaults for that operation only.
- **FR-021**: EccoVox MUST reject unsupported or invalid overrides with stable functional errors.
- **FR-022**: EccoVox MUST define CLI stdout as result-only output and CLI stderr as diagnostic-only output.
- **FR-023**: EccoVox MUST define whether TTS CLI writes audio to a file, stdout or both; MVP MUST support file output.
- **FR-024**: EccoVox MUST define server-mode concurrency limits for STT and TTS, including whether excess work is queued or rejected.
- **FR-025**: EccoVox MUST return stable HTTP error codes and CLI exit codes that consumers can map without parsing engine messages.
- **FR-026**: EccoVox MUST centralize runtime profile names and defaults in configuration, allowing initial profiles `default`, `balanced`, `premium`, `diagnostic` and `process` to evolve without changing public contracts.
- **FR-027**: EccoVox MUST treat latency targets as configurable operational budgets by mode, profile, operation and request size, not as fixed limits for all audio or text.
- **FR-028**: EccoVox MUST expose configurable size, timeout and concurrency controls for STT and TTS in its configuration file, with per-call overrides only where explicitly supported by contract.

> Decisões de infraestrutura: EccoVox introduces a long-running server mode and one-shot CLI mode. Scheduling, token refresh, key rotation and distributed lock are N/A in the initial scope. Runtime health checks are idempotent. Backup/restore applies only to installed models/configuration managed by deployment, not to request audio or generated audio.

### Key Entities

- **Speech Runtime**: Processo EccoVox capaz de executar STT/TTS em modo servidor ou CLI.
- **STT Capability**: Capacidade de converter áudio em texto por engine configurada.
- **TTS Capability**: Capacidade de converter texto em áudio por engine configurada.
- **Engine Adapter**: Adaptador interno que isola uma engine concreta do contrato público.
- **Runtime Profile**: Configuração de modelo, dispositivo, qualidade, limites e formato.
- **Runtime Health**: Estado efetivo de disponibilidade e diagnóstico seguro.
- **Temporary Artifact**: Arquivo transitório usado durante processamento e descartado conforme política.
- **Capability Status**: Estado funcional de cada capacidade, podendo ser `ready`, `disabled`, `degraded` ou `unavailable`.
- **Runtime Configuration**: Arquivo de configuração do EccoVox com defaults de engines, modelos, limites e concorrência.
- **Per-call Override**: Parâmetro recebido via HTTP ou CLI que substitui o default apenas durante a operação atual.
- **Concurrency Policy**: Regra de server mode que define quantas operações simultâneas são aceitas por capacidade e como excedentes são tratados.
- **Latency Budget**: Meta operacional configurável por modo, perfil, operação e tamanho da solicitação. Não limita a duração máxima de qualquer áudio/texto; orienta diagnóstico, timeouts e validação por cenário.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das chamadas HTTP de health retornam status separado para STT e TTS.
- **SC-002**: 100% das transcrições válidas retornam texto em formato documentado.
- **SC-003**: 100% das sínteses válidas retornam áudio com `Content-Type` documentado.
- **SC-004**: 100% dos erros funcionais testados retornam código estável em HTTP e CLI.
- **SC-005**: 100% dos logs revisados em cenários de erro não expõem áudio, texto sensível integral ou segredos.
- **SC-006**: CLI STT e CLI TTS funcionam sem iniciar servidor HTTP.
- **SC-007**: Server mode aceita STT e TTS sem exigir conhecimento do consumidor sobre engines internas.
- **SC-008**: 100% dos estados `disabled`, `degraded` e `unavailable` são distinguíveis no health.
- **SC-009**: 100% dos overrides válidos testados substituem defaults apenas na chamada corrente.
- **SC-010**: 100% dos comandos CLI testados mantêm resultado em stdout e diagnóstico em stderr.
- **SC-011**: 100% dos excessos de concorrência em server mode seguem a política documentada de fila ou rejeição.
