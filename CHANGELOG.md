# Changelog

## Não lançado

- Instalador e gerenciador de serviço systemd para Linux.
- Comandos uniformes de status e reinício do serviço no Windows e no Linux.
- Script `eccovox.sh` para instalação e operação em distribuições Linux.
- Bootstrap explícito do pywin32 para serviços executados em ambiente virtual.
- Loop assíncrono compatível com a thread de serviço do pywin32 no Windows.
- Registro automático do `PYTHONPATH` privado da venv no serviço Windows.
- Descoberta das DLLs NVIDIA pela venv mesmo sob o interpretador incorporado do serviço.
- Diagnóstico preciso quando uma dependência transitiva do STT não pode ser carregada.
- Serviço Windows convertido em supervisor do Python da própria venv, eliminando
  diferenças de runtime entre serviço e execução interativa.

## 1.0.0 - 2026-08-02

- Primeiro lançamento autônomo do EccoVox.
- API HTTP e CLI para STT e TTS locais.
- Transcrição `faster-whisper` em CPU ou NVIDIA CUDA.
- Contexto, vocabulário e normalização explícita de termos.
- Cache persistente de modelos e reutilização em servidor aquecido.
- Gerenciamento de processo e serviço Windows.
## Unreleased

- Elevado o TTS local com cache persistente de pipelines Kokoro, warm-up no modo servidor e segmentação de textos longos.
- Adicionado suporte consistente a WAV/FLAC/OGG e MP3 por encoder FFmpeg local, com health degradado quando o encoder não está disponível.
- Adicionados device CUDA/CPU, modelo, caminho do encoder e limites de segmento à configuração pública.
- Adicionado configurador modular com menus para instalação, processo, serviço, rede, STT, TTS, vozes, FFmpeg e diagnóstico.
- Adicionada edição TOML tipada, atômica e recuperável, preservando campos desconhecidos e limitando backups locais.
