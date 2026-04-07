from __future__ import annotations

import json
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from .models import AppSettings, DisguisedExtensionRule

DEFAULT_PASSWORD_LIBRARY: list[str] = []

DEFAULT_DISGUISED_EXTENSIONS = [
    DisguisedExtensionRule(".jpg", True),
    DisguisedExtensionRule(".jpeg", True),
    DisguisedExtensionRule(".psd", True),
]


class SettingsPermissionError(PermissionError):
    def __init__(self, path: Path, operation: str) -> None:
        self.path = path
        self.operation = operation
        super().__init__(f"无法{operation}配置文件：{path}")


def app_install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def normalize_extension(value: str) -> str | None:
    candidate = value.strip().lower()
    if not candidate:
        return None
    if not candidate.startswith("."):
        candidate = f".{candidate}"
    if candidate == ".":
        return None
    return candidate


def normalize_password_library(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        candidate = item.strip()
        if not candidate:
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        normalized.append(candidate)
        seen.add(key)
    return normalized


def normalize_disguised_extensions(
    values: list[DisguisedExtensionRule | dict[str, object] | str],
) -> list[DisguisedExtensionRule]:
    normalized: list[DisguisedExtensionRule] = []
    seen: set[str] = set()
    for item in values:
        if isinstance(item, DisguisedExtensionRule):
            suffix = normalize_extension(item.suffix)
            enabled = item.enabled
        elif isinstance(item, dict):
            suffix = normalize_extension(str(item.get("suffix", "")))
            enabled = bool(item.get("enabled", True))
        else:
            suffix = normalize_extension(str(item))
            enabled = True
        if suffix is None or suffix in seen:
            continue
        normalized.append(DisguisedExtensionRule(suffix=suffix, enabled=enabled))
        seen.add(suffix)
    return normalized


class AppSettingsStore:
    def __init__(self, config_dir: Path | None = None) -> None:
        base_dir = config_dir or self._default_config_dir()
        self.config_dir = base_dir
        self.settings_path = self.config_dir / "settings.json"
        self._lock = threading.Lock()

    def _default_config_dir(self) -> Path:
        return app_install_dir()

    def load(self) -> AppSettings:
        with self._lock:
            self._ensure_config_dir()
            if not self.settings_path.exists():
                settings = self._default_settings()
                self._write(settings)
                return settings
            try:
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            except PermissionError as exc:
                raise SettingsPermissionError(self.settings_path, "读取") from exc
            settings = AppSettings(
                password_library=normalize_password_library(
                    list(data.get("password_library", DEFAULT_PASSWORD_LIBRARY))
                ),
                disguised_extensions=normalize_disguised_extensions(
                    list(data.get("disguised_extensions", DEFAULT_DISGUISED_EXTENSIONS))
                ),
                default_output_dir=data.get("default_output_dir"),
                cleanup_policy=str(data.get("cleanup_policy", "temporary_only")),
                recent_inputs=list(data.get("recent_inputs", [])),
            )
            settings = self._merge_defaults(settings)
            self._write(settings)
            return settings

    def save(self, settings: AppSettings) -> AppSettings:
        with self._lock:
            normalized = self._merge_defaults(settings)
            self._write(normalized)
            return normalized

    def add_password(self, password: str) -> AppSettings:
        settings = self.load()
        settings.password_library = normalize_password_library(
            [password, *settings.password_library]
        )
        return self.save(settings)

    def add_recent_input(self, path: str) -> AppSettings:
        settings = self.load()
        deduped = [path, *[item for item in settings.recent_inputs if item != path]]
        settings.recent_inputs = deduped[:10]
        return self.save(settings)

    def _default_settings(self) -> AppSettings:
        return AppSettings(
            password_library=DEFAULT_PASSWORD_LIBRARY.copy(),
            disguised_extensions=[
                DisguisedExtensionRule(rule.suffix, rule.enabled)
                for rule in DEFAULT_DISGUISED_EXTENSIONS
            ],
            default_output_dir=None,
            cleanup_policy="temporary_only",
            recent_inputs=[],
        )

    def _merge_defaults(self, settings: AppSettings) -> AppSettings:
        merged = AppSettings(
            password_library=normalize_password_library(settings.password_library),
            disguised_extensions=normalize_disguised_extensions(
                [*settings.disguised_extensions, *DEFAULT_DISGUISED_EXTENSIONS]
            ),
            default_output_dir=settings.default_output_dir,
            cleanup_policy=settings.cleanup_policy or "temporary_only",
            recent_inputs=list(dict.fromkeys(settings.recent_inputs))[:10],
        )
        return merged

    def _write(self, settings: AppSettings) -> None:
        payload = asdict(settings)
        try:
            self.settings_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except PermissionError as exc:
            raise SettingsPermissionError(self.settings_path, "写入") from exc

    def _ensure_config_dir(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise SettingsPermissionError(self.config_dir, "创建") from exc
