# EccoVox

EccoVox é um runtime autônomo e local para transcrição de voz (STT) e síntese de
fala (TTS). Ele expõe uma API HTTP e um CLI, mantém os áudios na própria máquina e
pode ser consumido por Coworker, Jarvis ou qualquer outro cliente sem dependência
direta entre os projetos.

## Recursos

- STT com `faster-whisper` em CPU ou NVIDIA CUDA;
- TTS local com Kokoro, cache persistente de pipeline e suporte a CPU/CUDA;
- API FastAPI versionada em `/v1` e CLI `eccovox`;
- vocabulário contextual, prompt e aliases explícitos de normalização;
- cache local de modelos e reutilização do modelo enquanto o servidor está ativo;
- configuração TOML, gerenciador de processo e serviço nativo no Windows ou Linux.

## Requisitos

- Windows 10/11, Windows Server ou Linux com systemd e Python 3.11+;
- para GPU, placa NVIDIA compatível; as DLLs CUDA necessárias são instaladas pelo
  extra `stt-gpu`, sem exigir o CUDA Toolkit completo;
- privilégios administrativos somente para instalar/remover/controlar o serviço do
  sistema.

## Instalação rápida

No Windows, executar `.\eccovox.ps1` sem argumentos abre o configurador interativo.
No Linux, use `./eccovox.sh`. O menu é dividido em seções independentes para crescer
sem misturar instalação, operação e configuração:

1. instalação e dependências;
2. processo local;
3. serviço do sistema;
4. servidor e rede;
5. reconhecimento de voz (STT);
6. síntese e vozes (TTS);
7. FFmpeg e formatos de áudio;
8. diagnóstico.

O menu oferece presets completos para NVIDIA ou CPU e um runtime mínimo. Instalar,
remover ou controlar serviços continua exigindo os privilégios do sistema operacional;
o configurador não tenta elevar permissões escondido.

```powershell
git clone git@github.com:rodrigogml/EccoVox.git C:\opt\EccoVox
Set-Location C:\opt\EccoVox
.\eccovox.ps1 install
.\eccovox.ps1 start
.\eccovox.ps1 status
```

O instalador cria `.venv`, instala os extras `stt-gpu,tts,service` e copia
`eccovox.toml.model` para `eccovox.toml` quando a configuração real ainda não
existe. O arquivo real, modelos, logs e estado são ignorados pelo Git.

Para CPU ou uma instalação mínima:

```powershell
.\eccovox.ps1 install --extras stt
```

No Linux:

```bash
git clone git@github.com:rodrigogml/EccoVox.git /opt/EccoVox
cd /opt/EccoVox
./eccovox.sh install --extras stt,tts
./eccovox.sh start
./eccovox.sh status
```

`start` executa um processo independente gerenciado pelo próprio EccoVox. Para uma
instalação permanente, inicializada junto com o sistema e reiniciada em caso de
falha, prefira o serviço descrito abaixo.

## Configuração

Edite `eccovox.toml`. Caminhos relativos são resolvidos a partir da pasta que contém
esse arquivo, portanto a execução não depende do diretório atual.

Também é possível alterar campos públicos conhecidos pelo configurador ou por CLI:

```powershell
.\eccovox.ps1 configure --list
.\eccovox.ps1 configure --set server.port=8871 `
  --set tts.voice=pm_alex --set tts.response_format=wav
```

As alterações são tipadas, preservam campos e comentários desconhecidos, validam o
TOML efetivo e criam backup em `.eccovox/state/config-backups/`. Somente os cinco
backups mais recentes são mantidos. Se a validação falhar, o arquivo anterior é
restaurado. Mudanças de runtime entram em vigor após reiniciar o processo ou serviço.

```toml
[server]
host = "127.0.0.1"
port = 8870

[runtime]
temp_dir = ".eccovox/tmp"
model_cache_dir = ".eccovox/models"
state_dir = ".eccovox/state"
log_dir = ".eccovox/logs"

[stt]
model = "medium"
device = "cuda"
compute_type = "int8_float16"

[tts]
engine = "kokoro"
profile = "premium"
voice = "pf_dora"
language = "pt-BR"
response_format = "mp3"
device = "cuda"
warmup = true
max_segment_chars = 500
# Opcional: caminho absoluto para o FFmpeg local usado na saída MP3.
encoder_path = ""
```

O TTS mantém o pipeline aquecido no modo servidor, divide textos longos em
segmentos controlados e usa somente dependências locais. WAV não exige encoder
externo; MP3 requer FFmpeg instalado localmente ou informado em `encoder_path`.

### FFmpeg portátil no Windows

Para uma instalação independente, mantenha uma build estática portátil em:

```text
C:\opt\EccoVox\tools\ffmpeg\bin\ffmpeg.exe
```

Esse diretório é ignorado pelo Git. No `eccovox.toml` da instalação, configure:

```toml
[tts]
encoder_path = "tools/ffmpeg/bin/ffmpeg.exe"
```

O caminho relativo é resolvido a partir da pasta que contém o arquivo de
configuração. O executável pode ser validado com:

```powershell
.\tools\ffmpeg\bin\ffmpeg.exe -version
```

O gerenciador procura primeiro o caminho configurado, depois a instalação portátil e
por fim o `PATH`. Ele não baixa nem executa instaladores automaticamente:

```powershell
.\eccovox.ps1 ffmpeg-status
.\eccovox.ps1 ffmpeg-detect
```

`ffmpeg-detect` registra o executável já existente. Pelo menu também é possível
informar outro caminho, limpar a configuração ou selecionar WAV, que não depende de
encoder externo.

As vozes Kokoro disponíveis para português brasileiro podem ser consultadas com
`.\eccovox.ps1 voices`: `pf_dora`, `pm_alex` e `pm_santa`.

Use `127.0.0.1` quando só processos da máquina devem acessar o runtime. Para atender
outras máquinas, associe a uma interface apropriada e proteja rede, firewall e TLS no
proxy; a API não implementa autenticação por conta própria.

## Gerenciamento

```powershell
.\eccovox.ps1 start
.\eccovox.ps1 stop
.\eccovox.ps1 kill
.\eccovox.ps1 restart
.\eccovox.ps1 status
.\eccovox.ps1 run
.\eccovox.ps1 doctor
```

`stop` tenta encerramento cooperativo; `kill` é a alternativa forçada. O PID é aceito
somente quando horário de criação e linha de comando correspondem ao processo que o
EccoVox registrou, evitando finalizar um PID reciclado pelo Windows.

O gerenciador impede iniciar processo local e serviço simultaneamente. `doctor`
consolida instalação, configuração, dependências, processo, serviço, FFmpeg e saúde
HTTP em JSON, sem carregar modelos ou enviar áudio.

### Serviço do sistema

Não mantenha simultaneamente o processo criado por `start` e o serviço: ambos usam a
mesma porta. Antes da primeira inicialização do serviço, execute `stop` caso o runtime
esteja rodando como processo.

#### Windows

Em um PowerShell elevado:

```powershell
.\eccovox.ps1 service-install
.\eccovox.ps1 service-start
.\eccovox.ps1 service-status
.\eccovox.ps1 service-restart
.\eccovox.ps1 service-stop
.\eccovox.ps1 service-remove
```

O serviço é instalado com inicialização automática e usa o mesmo `eccovox.toml`.

#### Linux (systemd)

Instale primeiro como usuário normal. Depois administre a unidade com `sudo`:

```bash
./eccovox.sh install --extras stt,tts
./eccovox.sh stop
sudo ./eccovox.sh service-install --service-user "$USER"
sudo ./eccovox.sh service-start
sudo ./eccovox.sh service-status
```

O comando cria `/etc/systemd/system/eccovox.service`, habilita a inicialização no
boot e configura reinício automático após falhas. A instalação não inicia o serviço
automaticamente, evitando tomar a porta sem uma decisão explícita. Para manutenção:

```bash
sudo ./eccovox.sh service-restart
sudo ./eccovox.sh service-stop
sudo ./eccovox.sh service-remove
```

Quando `--service-user` não é informado, o instalador usa `SUDO_USER`; em uma sessão
root sem esse contexto, usa o usuário atual. É recomendável informar explicitamente
uma conta sem privilégios que tenha leitura do projeto e escrita nos diretórios de
estado, logs, temporários e cache configurados.

## API e CLI

Saúde:

```powershell
Invoke-RestMethod http://127.0.0.1:8870/v1/health
```

Transcrição avulsa:

```powershell
.\.venv\Scripts\eccovox.exe transcribe --file voice.ogg --config eccovox.toml `
  --language pt-BR --term EccoVox --term backup --alias becapi=backup
```

Síntese de fala:

```powershell
.\.venv\Scripts\eccovox.exe synthesize --text "Olá, EccoVox." `
  --voice pf_dora --format mp3 --output resposta.mp3 --config eccovox.toml
```

Servidor sem o gerenciador:

```powershell
.\.venv\Scripts\eccovox.exe serve --config eccovox.toml
```

A documentação interativa fica em `http://127.0.0.1:8870/docs`.

## Desenvolvimento e release

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m build
```

Versão, changelog e tag devem ser atualizados juntos. O CI repete testes, compilação
e construção do wheel/sdist a cada push e pull request.

## Licença

Apache-2.0. Consulte [LICENSE](LICENSE).
