"""Expandable interactive menus for EccoVox installation and operation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


PORTUGUESE_VOICES = (
    ("pf_dora", "Dora — feminina"),
    ("pm_alex", "Alex — masculina"),
    ("pm_santa", "Santa — masculina"),
)


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    action: Callable[[], Any]


class MenuApplication:
    """Small menu router; backend operations remain testable and non-interactive."""

    def __init__(
        self,
        backend: Any,
        *,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
    ) -> None:
        self.backend = backend
        self.read = read
        self.write = write

    def run(self) -> int:
        while True:
            selected = self._choose(
                "EccoVox — Instalação e configuração",
                (
                    MenuItem("1", "Instalação e dependências", self.installation_menu),
                    MenuItem("2", "Processo local", self.process_menu),
                    MenuItem("3", "Serviço do sistema", self.service_menu),
                    MenuItem("4", "Servidor e rede", self.server_menu),
                    MenuItem("5", "Reconhecimento de voz (STT)", self.stt_menu),
                    MenuItem("6", "Síntese e vozes (TTS)", self.tts_menu),
                    MenuItem("7", "FFmpeg e formatos de áudio", self.ffmpeg_menu),
                    MenuItem("8", "Diagnóstico", self.diagnostics_menu),
                ),
                exit_label="Sair",
            )
            if selected is None:
                return 0
            self._execute(selected.action)

    def installation_menu(self) -> None:
        while True:
            selected = self._choose(
                "Instalação e dependências",
                (
                    MenuItem("1", "Instalação completa NVIDIA", lambda: self.backend.install("stt-gpu,tts,service")),
                    MenuItem("2", "Instalação completa CPU", lambda: self.backend.install("stt,tts,service")),
                    MenuItem("3", "Runtime mínimo", lambda: self.backend.install("service")),
                    MenuItem("4", "Atualizar instalação atual", self._update_installation),
                ),
            )
            if selected is None:
                return
            self._execute(selected.action)

    def process_menu(self) -> None:
        self._action_menu(
            "Processo local",
            (
                MenuItem("1", "Status", self.backend.status),
                MenuItem("2", "Iniciar", self.backend.start),
                MenuItem("3", "Finalizar", lambda: self.backend.stop(force=False)),
                MenuItem("4", "Reiniciar", self.backend.restart),
                MenuItem("5", "Finalização forçada", self._force_stop),
                MenuItem("6", "Executar no console", self.backend.run),
            ),
        )

    def service_menu(self) -> None:
        self._action_menu(
            "Serviço do sistema",
            (
                MenuItem("1", "Status", self.backend.service_status),
                MenuItem("2", "Instalar", self._install_service),
                MenuItem("3", "Iniciar", lambda: self.backend.service_action("start")),
                MenuItem("4", "Finalizar", lambda: self.backend.service_action("stop")),
                MenuItem("5", "Reiniciar", lambda: self.backend.service_action("restart")),
                MenuItem("6", "Desinstalar", self._remove_service),
            ),
        )

    def server_menu(self) -> None:
        self._action_menu(
            "Servidor e rede",
            (
                MenuItem("1", "Mostrar configuração", self.backend.show_configuration),
                MenuItem("2", "Usar somente esta máquina (127.0.0.1)", lambda: self._set("server.host", "127.0.0.1")),
                MenuItem("3", "Ouvir na rede local (0.0.0.0)", self._enable_network),
                MenuItem("4", "Definir host", lambda: self._prompt_setting("server.host", "Host")),
                MenuItem("5", "Definir porta", lambda: self._prompt_setting("server.port", "Porta")),
                MenuItem("6", "Definir timeout", lambda: self._prompt_setting("runtime.request_timeout_seconds", "Timeout em segundos")),
            ),
        )

    def stt_menu(self) -> None:
        self._action_menu(
            "Reconhecimento de voz (STT)",
            (
                MenuItem("1", "Habilitar", lambda: self._set("stt.enabled", "true")),
                MenuItem("2", "Desabilitar", lambda: self._set("stt.enabled", "false")),
                MenuItem("3", "Definir modelo", lambda: self._prompt_setting("stt.model", "Modelo Whisper")),
                MenuItem("4", "Usar CPU", lambda: self._set_many({"stt.device": "cpu", "stt.compute_type": "int8"})),
                MenuItem("5", "Usar NVIDIA CUDA", lambda: self._set_many({"stt.device": "cuda", "stt.compute_type": "int8_float16"})),
                MenuItem("6", "Definir compute type", lambda: self._prompt_setting("stt.compute_type", "Compute type")),
            ),
        )

    def tts_menu(self) -> None:
        items = [
            MenuItem("1", "Habilitar", lambda: self._set("tts.enabled", "true")),
            MenuItem("2", "Desabilitar", lambda: self._set("tts.enabled", "false")),
            MenuItem("3", "Escolher voz em português", self._choose_portuguese_voice),
            MenuItem("4", "Definir voz manualmente", lambda: self._prompt_setting("tts.voice", "Identificador da voz")),
            MenuItem("5", "Usar CPU", lambda: self._set("tts.device", "cpu")),
            MenuItem("6", "Usar NVIDIA CUDA", lambda: self._set("tts.device", "cuda")),
            MenuItem("7", "Definir formato de saída", lambda: self._prompt_setting("tts.response_format", "Formato (wav/flac/ogg/mp3)")),
            MenuItem("8", "Alternar warm-up", self._toggle_warmup),
        ]
        self._action_menu("Síntese e vozes (TTS)", tuple(items))

    def ffmpeg_menu(self) -> None:
        self._action_menu(
            "FFmpeg e formatos de áudio",
            (
                MenuItem("1", "Diagnosticar FFmpeg", self.backend.ffmpeg_status),
                MenuItem("2", "Detectar e configurar automaticamente", self.backend.configure_detected_ffmpeg),
                MenuItem("3", "Informar executável local", lambda: self._prompt_setting("tts.encoder_path", "Caminho do ffmpeg")),
                MenuItem("4", "Limpar caminho configurado e usar PATH", lambda: self._set("tts.encoder_path", "")),
                MenuItem("5", "Usar WAV sem encoder externo", lambda: self._set("tts.response_format", "wav")),
                MenuItem("6", "Usar MP3", lambda: self._set("tts.response_format", "mp3")),
            ),
        )

    def diagnostics_menu(self) -> None:
        self._action_menu(
            "Diagnóstico",
            (
                MenuItem("1", "Diagnóstico completo", self.backend.doctor),
                MenuItem("2", "Status do processo", self.backend.status),
                MenuItem("3", "Status do serviço", self.backend.service_status),
                MenuItem("4", "Status do FFmpeg", self.backend.ffmpeg_status),
                MenuItem("5", "Mostrar configuração efetiva", self.backend.show_configuration),
                MenuItem("6", "Listar vozes em português", self._print_voices),
            ),
        )

    def _action_menu(self, title: str, items: tuple[MenuItem, ...]) -> None:
        while True:
            selected = self._choose(title, items)
            if selected is None:
                return
            self._execute(selected.action)

    def _choose(
        self,
        title: str,
        items: tuple[MenuItem, ...],
        *,
        exit_label: str = "Voltar",
    ) -> MenuItem | None:
        self.write(f"\n{title}")
        self.write("=" * len(title))
        for item in items:
            self.write(f"{item.key}. {item.label}")
        self.write(f"0. {exit_label}")
        answer = self.read("Escolha: ").strip()
        if answer == "0":
            return None
        return next((item for item in items if item.key == answer), MenuItem("", "", lambda: self.write("Opção inválida.")))

    def _execute(self, action: Callable[[], Any]) -> None:
        try:
            result = action()
            if isinstance(result, dict):
                self.write(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:
            self.write(f"Falha: {exc}")

    def _set(self, name: str, value: str) -> Any:
        return self.backend.configure_assignments((f"{name}={value}",))

    def _set_many(self, values: dict[str, str]) -> Any:
        return self.backend.configure_assignments(tuple(f"{key}={value}" for key, value in values.items()))

    def _prompt_setting(self, name: str, label: str) -> Any:
        value = self.read(f"{label}: ")
        return self._set(name, value)

    def _confirm(self, prompt: str) -> bool:
        return self.read(f"{prompt} [digite SIM]: ").strip().casefold() == "sim"

    def _enable_network(self) -> Any:
        if not self._confirm("A API não possui autenticação própria. Expor na rede local mesmo assim?"):
            return {"ok": False, "cancelled": True}
        return self._set("server.host", "0.0.0.0")

    def _force_stop(self) -> Any:
        if not self._confirm("Forçar encerramento da árvore do processo?"):
            return {"ok": False, "cancelled": True}
        return self.backend.stop(force=True)

    def _install_service(self) -> Any:
        if not self._confirm("Instalar serviço do sistema com inicialização automática?"):
            return {"ok": False, "cancelled": True}
        user = None
        if self.backend.service_platform() == "linux":
            user = self.read("Usuário do serviço (vazio = usuário detectado): ").strip() or None
        return self.backend.service_install(user)

    def _remove_service(self) -> Any:
        if not self._confirm("Desinstalar o serviço do sistema?"):
            return {"ok": False, "cancelled": True}
        return self.backend.service_remove()

    def _update_installation(self) -> Any:
        extras = self.read("Extras (stt-gpu,tts,service): ").strip() or "stt-gpu,tts,service"
        return self.backend.install(extras)

    def _choose_portuguese_voice(self) -> Any:
        items = tuple(
            MenuItem(str(index), label, lambda voice=voice: self._set("tts.voice", voice))
            for index, (voice, label) in enumerate(PORTUGUESE_VOICES, start=1)
        )
        selected = self._choose("Vozes Kokoro — Português brasileiro", items)
        return None if selected is None else selected.action()

    def _toggle_warmup(self) -> Any:
        current = self.backend.configuration_values().get("tts.warmup", True)
        return self._set("tts.warmup", "false" if current else "true")

    def _print_voices(self) -> dict[str, object]:
        return {
            "ok": True,
            "language": "pt-BR",
            "voices": [
                {"id": voice, "label": label} for voice, label in PORTUGUESE_VOICES
            ],
        }
