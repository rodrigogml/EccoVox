"""Typed, atomic configuration helpers used by the EccoVox manager."""

from __future__ import annotations

import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class ConfigurationError(RuntimeError):
    """Raised when a manager setting is unknown or unsafe."""


@dataclass(frozen=True)
class Setting:
    section: str
    key: str
    parser: Callable[[str], object]
    serializer: Callable[[object], str]

    @property
    def name(self) -> str:
        return f"{self.section}.{self.key}"


def _string(value: str) -> str:
    text = value.strip()
    if not text or any(character in text for character in "\r\n\0"):
        raise ConfigurationError("O valor textual não pode ficar vazio.")
    return text


def _identifier(value: str) -> str:
    text = _string(value)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", text):
        raise ConfigurationError("Use somente letras, números, ponto, hífen e sublinhado.")
    return text


def _host(value: str) -> str:
    text = _string(value)
    if "://" in text or not re.fullmatch(r"[A-Za-z0-9:._-]{1,255}", text):
        raise ConfigurationError("Host inválido; informe somente endereço ou nome local.")
    return text


def _integer(minimum: int, maximum: int) -> Callable[[str], int]:
    def parse(value: str) -> int:
        try:
            number = int(value.strip())
        except ValueError as exc:
            raise ConfigurationError("O valor deve ser inteiro.") from exc
        if not minimum <= number <= maximum:
            raise ConfigurationError(f"O valor deve ficar entre {minimum} e {maximum}.")
        return number

    return parse


def _boolean(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "sim", "s", "yes", "y"}:
        return True
    if normalized in {"0", "false", "não", "nao", "n", "no"}:
        return False
    raise ConfigurationError("Use sim/não ou true/false.")


def _choice(*values: str) -> Callable[[str], str]:
    allowed = {value.casefold(): value for value in values}

    def parse(value: str) -> str:
        normalized = value.strip().casefold()
        try:
            return allowed[normalized]
        except KeyError as exc:
            raise ConfigurationError(
                "Valor inválido. Opções: " + ", ".join(values) + "."
            ) from exc

    return parse


def _path(value: str) -> str:
    text = value.strip()
    if any(character in text for character in "\r\n\0"):
        raise ConfigurationError("O caminho contém caracteres inválidos.")
    return text


def _toml_string(value: object) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return _toml_string(value)


SETTINGS = {
    item.name: item
    for item in (
        Setting("server", "host", _host, _toml_scalar),
        Setting("server", "port", _integer(1, 65_535), _toml_scalar),
        Setting("runtime", "request_timeout_seconds", _integer(1, 3_600), _toml_scalar),
        Setting("runtime", "default_profile", _identifier, _toml_scalar),
        Setting("stt", "enabled", _boolean, _toml_scalar),
        Setting("stt", "profile", _identifier, _toml_scalar),
        Setting("stt", "model", _identifier, _toml_scalar),
        Setting("stt", "device", _choice("cpu", "cuda"), _toml_scalar),
        Setting(
            "stt",
            "compute_type",
            _choice("int8", "int8_float16", "float16", "float32"),
            _toml_scalar,
        ),
        Setting("tts", "enabled", _boolean, _toml_scalar),
        Setting("tts", "profile", _identifier, _toml_scalar),
        Setting("tts", "voice", _identifier, _toml_scalar),
        Setting("tts", "language", _identifier, _toml_scalar),
        Setting("tts", "response_format", _choice("wav", "flac", "ogg", "mp3"), _toml_scalar),
        Setting("tts", "device", _choice("cpu", "cuda"), _toml_scalar),
        Setting("tts", "model", _identifier, _toml_scalar),
        Setting("tts", "encoder_path", _path, _toml_scalar),
        Setting("tts", "warmup", _boolean, _toml_scalar),
        Setting("tts", "max_segment_chars", _integer(50, 4_000), _toml_scalar),
        Setting("tts", "max_text_chars", _integer(1, 100_000), _toml_scalar),
    )
}


def known_setting_names() -> tuple[str, ...]:
    return tuple(sorted(SETTINGS))


def parse_assignment(value: str) -> tuple[str, object]:
    name, separator, raw = value.partition("=")
    normalized = name.strip().casefold()
    if not separator or normalized not in SETTINGS:
        raise ConfigurationError(
            "Configuração desconhecida. Use uma chave listada pelo comando configure --list."
        )
    return normalized, SETTINGS[normalized].parser(raw)


def read_configuration(path: Path) -> dict[str, object]:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ConfigurationError("eccovox.toml não existe; execute install primeiro.") from exc
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError("eccovox.toml não pôde ser lido como TOML válido.") from exc
    result: dict[str, object] = {}
    for name, setting in SETTINGS.items():
        section = document.get(setting.section, {})
        if isinstance(section, dict) and setting.key in section:
            result[name] = section[setting.key]
    return result


def update_configuration(
    path: Path,
    assignments: dict[str, object],
    *,
    state_dir: Path,
) -> Path:
    if not assignments:
        raise ConfigurationError("Nenhuma alteração foi informada.")
    unknown = set(assignments).difference(SETTINGS)
    if unknown:
        raise ConfigurationError("Configuração desconhecida: " + ", ".join(sorted(unknown)))
    try:
        original = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise ConfigurationError("eccovox.toml não existe; execute install primeiro.") from exc
    updated = original
    for name, value in assignments.items():
        setting = SETTINGS[name]
        updated = _replace_setting(updated, setting, value)
    try:
        tomllib.loads(updated)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError("A alteração produziria um TOML inválido.") from exc

    backup_dir = state_dir / "config-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = backup_dir / f"eccovox-{stamp}.toml"
    shutil.copy2(path, backup)
    _purge_backups(backup_dir, keep=5)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=".eccovox-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(updated)
            stream.flush()
        temporary_path.replace(path)
    except OSError as exc:
        raise ConfigurationError("Não foi possível atualizar eccovox.toml.") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return backup


def _replace_setting(content: str, setting: Setting, value: object) -> str:
    lines = content.splitlines()
    section_line = f"[{setting.section}]"
    start = next((index for index, line in enumerate(lines) if line.strip() == section_line), None)
    rendered = f"{setting.key} = {setting.serializer(value)}"
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend((section_line, rendered))
        return "\n".join(lines) + "\n"
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith("[")),
        len(lines),
    )
    key_pattern = re.compile(rf"^\s*{re.escape(setting.key)}\s*=")
    existing = next(
        (index for index in range(start + 1, end) if key_pattern.match(lines[index])),
        None,
    )
    if existing is None:
        lines.insert(end, rendered)
    else:
        comment = ""
        if " #" in lines[existing]:
            comment = " #" + lines[existing].split(" #", 1)[1]
        lines[existing] = rendered + comment
    return "\n".join(lines) + "\n"


def _purge_backups(directory: Path, *, keep: int) -> None:
    backups = sorted(directory.glob("eccovox-*.toml"), reverse=True)
    for stale in backups[keep:]:
        stale.unlink(missing_ok=True)
