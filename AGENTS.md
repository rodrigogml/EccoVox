# EccoVox — Instruções do Agente

EccoVox é um projeto autônomo de processamento local de voz. Preserve essa
independência: integrações consumidoras pertencem aos seus próprios repositórios.

## Contratos

- Mantenha compatibilidade da API pública sob `/v1` e do CLI `eccovox`.
- Não envie áudio, transcrições ou vocabulário para serviços externos.
- Nunca versione `eccovox.toml`, modelos, áudios, logs ou estado operacional.
- Acrescente configuração pública a `eccovox.toml.model` e mantenha valores locais
  somente em `eccovox.toml`.
- Alterações de comportamento exigem testes. Execute `pytest`, `compileall` e a
  construção de wheel/sdist antes de uma release.
- Atualize `CHANGELOG.md`, `pyproject.toml`, `src/eccovox/__init__.py` e a tag juntos.

## Operação

Use `eccovox.ps1` no Windows ou `eccovox.sh` no Linux para instalar, iniciar, parar,
reiniciar, consultar e administrar o serviço. No Linux, a integração suportada é um
serviço systemd de sistema; não improvise unidades ou comandos paralelos. O arquivo
real de configuração é resolvido a partir da raiz do projeto. Não finalize PIDs sem
validar que pertencem a uma instância EccoVox registrada.

Sem argumentos, os wrappers abrem o menu modular. Mantenha operações automatizáveis
em `scripts/manage.py`, edição tipada e atômica em `scripts/manager_config.py` e apenas
navegação/interação em `scripts/manager_menu.py`. Toda nova seção de menu deve possuir
uma operação não interativa equivalente e testes próprios.
