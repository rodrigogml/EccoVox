# EccoVox

EccoVox é um runtime autônomo e local para transcrição de voz (STT) e síntese de
fala (TTS). Ele expõe uma API HTTP e um CLI, mantém os áudios na própria máquina e
pode ser consumido por Coworker, Jarvis ou qualquer outro cliente sem dependência
direta entre os projetos.

## Recursos

- STT com `faster-whisper` em CPU ou NVIDIA CUDA;
- TTS com Kokoro;
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
```

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
```

`stop` tenta encerramento cooperativo; `kill` é a alternativa forçada. O PID é aceito
somente quando horário de criação e linha de comando correspondem ao processo que o
EccoVox registrou, evitando finalizar um PID reciclado pelo Windows.

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
