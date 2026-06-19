# Requirements Checklist: Speech Runtime

**Purpose**: Validar clareza, completude, consistencia, mensurabilidade e rastreabilidade dos requisitos do EccoVox como runtime independente de STT/TTS via HTTP e CLI.
**Created**: 2026-06-18
**Feature**: [spec.md](../spec.md)

## Completude Funcional

- [x] CHK001 - Os requisitos definem HTTP health, HTTP STT e HTTP TTS como capacidades publicas do MVP? [Completude, Spec §FR-001..FR-003, Contract §HTTP Health, Contract §HTTP STT, Contract §HTTP TTS] {auto}
- [x] CHK002 - Os requisitos definem CLI STT e CLI TTS como contrato publico, sem exigir servidor HTTP ativo? [Completude, Spec §FR-004, Spec §FR-012, Spec §SC-006, Contract §CLI] {auto}
- [x] CHK003 - Os requisitos definem que HTTP e CLI compartilham contratos internos e semantica consistente de erro? [Consistencia, Spec §FR-004..FR-006, Plan §Structure Decision, Constitution §Dual Execution Mode] {auto}
- [x] CHK004 - Os requisitos mantem EccoVox independente de Jarvis, AIChat ou qualquer consumidor especifico? [Completude, Plan §Summary, Constitution §Host Independence] {auto}
- [x] CHK005 - Os requisitos cobrem disponibilidade independente de STT e TTS, incluindo capacidade desabilitada por configuracao? [Completude, Spec §FR-007, Spec §FR-015..FR-018, Contract §Status Semantics] {auto}
- [x] CHK006 - Os requisitos excluem live conversation e streaming do MVP enquanto preservam extensao futura separada? [Clareza, Spec §FR-014, Plan §Summary] {auto}

## Configuracao e Overrides

- [x] CHK007 - Os requisitos definem arquivo de configuracao com defaults de host, porta, capacidades, engines, modelos, vozes, formatos, limites, temporarios e concorrencia? [Completude, Spec §FR-019, Contract §Configuration File, Data Model §Runtime Configuration] {auto}
- [x] CHK008 - Os requisitos definem que parametros HTTP/CLI validos podem sobrescrever defaults apenas durante a chamada corrente? [Clareza, Spec §FR-020, Contract §Configuration File, Spec §SC-009] {auto}
- [x] CHK009 - Os requisitos definem rejeicao estavel para overrides invalidos ou nao suportados? [Completude, Spec §FR-021, Contract §Error Codes, Plan §Validation Scenarios] {auto}
- [x] CHK010 - O contrato lista parametros STT e TTS suficientes para idioma, profile/modelo, device/compute type, voz, formato e velocidade quando aplicavel? [Completude, Contract §HTTP STT, Contract §HTTP TTS, Contract §CLI] {auto}

## Contratos, Erros e Diagnostico

- [x] CHK011 - O health define semantica de `ready`, `disabled`, `degraded` e `unavailable` para status global e de capacidade? [Clareza, Spec §FR-015..FR-018, Contract §Status Semantics] {auto}
- [x] CHK012 - Os requisitos distinguem `disabled` como configuracao intencional, e nao falha operacional? [Clareza, Spec §FR-016, Contract §Status Semantics] {auto}
- [x] CHK013 - O contrato define formato de erro HTTP com codigo funcional estavel e mensagem segura? [Completude, Spec §FR-006, Spec §FR-025, Contract §Error Response, Contract §Error Codes] {auto}
- [x] CHK014 - O contrato define exit codes CLI equivalentes para consumidores que nao usam HTTP? [Completude, Spec §FR-005, Spec §FR-025, Contract §Exit Codes] {auto}
- [x] CHK015 - Os requisitos definem stdout como resultado e stderr como diagnostico seguro para CLI? [Clareza, Spec §FR-022, Spec §SC-010, Contract §CLI] {auto}
- [x] CHK016 - Os requisitos proíbem vazamento de audio, texto sensivel integral e segredos em logs/diagnosticos? [Seguranca, Spec §FR-009, Spec §SC-005, Constitution §Privacy by Default] {auto}

## Operacao e Edge Cases

- [x] CHK017 - Os requisitos cobrem artefatos temporarios quando engines exigirem arquivos intermediarios? [Completude, Spec §FR-010, Constitution §Architecture Boundaries] {auto}
- [x] CHK018 - Os requisitos definem concorrencia em server mode, incluindo fila ou rejeicao de excesso? [Completude, Spec §FR-024, Spec §SC-011, Plan §Technical Context, Contract §Configuration File] {auto}
- [x] CHK019 - Os requisitos cobrem cold start de CLI como custo operacional esperado, distinto do server mode quente? [Clareza, Spec §FR-013, Constitution §Dual Execution Mode, Constitution §Quality Standards] {auto}
- [x] CHK020 - Os cenarios cobrem modelo ausente, entrada invalida, capacidade desabilitada, excesso de concorrencia e chamadas CLI simultaneas? [Cobertura, Spec §Edge Cases, Plan §Validation Scenarios] {auto}
- [x] CHK021 - A estrutura planejada separa API, CLI, core e engine para evitar que superficies publicas conhecam detalhes de engine? [Consistencia, Plan §Project Structure, Plan §Structure Decision] {auto}

## Mensurabilidade

- [x] CHK022 - Os success criteria cobrem resultados objetivamente verificaveis para health, STT, TTS, erros, logs, CLI, overrides e concorrencia? [Mensurabilidade, Spec §Success Criteria] {auto}
- [x] CHK023 - As metas de latencia foram definidas como budgets configuraveis por modo, perfil, operacao e tamanho da solicitacao, preservando suporte a audios/textos longos via limites e politica configuravel? [Mensurabilidade, Spec §Clarifications, Spec §FR-026..FR-027, Contract §Configuration File] {auto}
- [ ] CHK024 - [Deferred] A especificacao define criterio objetivo para qualidade minima de transcricao e naturalidade de voz por idioma/perfil suportado? [Mensurabilidade, Spec §User Story 1, Spec §User Story 2, Decisao: perfis por roles ficam para fase futura] {auto}

## Decisoes Humanas

- [x] CHK025 - O dono do projeto definiu a licenca final do EccoVox considerando dependencias e distribuicao futura? [Decisao: Apache-2.0 para EccoVox; dependencias/modelos mantem licencas proprias e devem ser auditados pelos distribuidores, Constitution §Governance] {humano}
- [x] CHK026 - O dono do projeto definiu politica final de empacotamento/distribuicao para uso incubado e uso independente? [Decisao: Python package independente com CLI `eccovox` e extras opcionais, Plan §Technical Context] {humano}
- [x] CHK027 - O dono do projeto aceita `max_concurrent=1` e `queue_size=0` como default conservador do MVP? [Decisao: aceito em 2026-06-18, Contract §Configuration File] {humano}
- [x] CHK028 - O dono do projeto validou que perfis por roles e baseline premium detalhado serao definidos em fase futura, mantendo perfis centralizados/configuraveis desde o MVP? [Decisao: deferido para fase futura, Spec §Clarifications] {humano}

## Notes

- Itens `{auto}` foram resolvidos contra spec, plan, contrato e constitution.
- Itens `{humano}` desta rodada foram resolvidos pelo dono do produto em 2026-06-18.
- CHK024 permanece diferido para fase futura de perfis por roles e baseline premium detalhado.
