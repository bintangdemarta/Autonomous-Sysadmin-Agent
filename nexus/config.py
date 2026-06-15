"""Configuration loading helpers for Nexus-CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMMANDS_PATH = PROJECT_ROOT / "config" / "commands.json"
DEFAULT_AUDIT_LOG_PATH = PROJECT_ROOT / "data" / "audit_log.jsonl"


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class SSHSettings:
    """SSH connection settings loaded from environment variables."""

    host: str
    user: str
    port: int = 22
    password: str | None = None
    key_path: str | None = None
    timeout: int = 15

    @property
    def uses_password(self) -> bool:
        return bool(self.password)

    @property
    def uses_key(self) -> bool:
        return bool(self.key_path)


def load_environment() -> None:
    """Load .env from project root if present."""

    load_dotenv(PROJECT_ROOT / ".env")


def get_commands_path() -> Path:
    """Return the configured command mapping path."""

    return Path(os.getenv("NEXUS_COMMANDS_PATH", DEFAULT_COMMANDS_PATH)).expanduser().resolve()


def load_commands(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load command mappings from JSON."""

    command_path = path or get_commands_path()
    try:
        with command_path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"Command configuration not found: {command_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Command configuration is not valid JSON: {command_path}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Command configuration must be an object keyed by category.")

    for category, commands in data.items():
        if not isinstance(commands, list):
            raise ConfigError(f"Command category '{category}' must contain a list.")
        for command in commands:
            if not isinstance(command, dict) or "command" not in command:
                raise ConfigError(f"Invalid command entry in category '{category}'.")

    return data


def save_commands(config: dict[str, list[dict[str, Any]]], path: Path | None = None) -> None:
    """Persist command mappings to JSON after validating the structure."""

    # Reuse validation by dumping/loading through simple structure checks.
    if not isinstance(config, dict):
        raise ConfigError("Command configuration must be an object keyed by category.")

    for category, commands in config.items():
        if not isinstance(commands, list):
            raise ConfigError(f"Command category '{category}' must contain a list.")
        for command in commands:
            if not isinstance(command, dict) or "command" not in command:
                raise ConfigError(f"Invalid command entry in category '{category}'.")

    command_path = path or get_commands_path()
    command_path.parent.mkdir(parents=True, exist_ok=True)
    with command_path.open("w", encoding="utf-8") as file_handle:
        json.dump(config, file_handle, indent=2, ensure_ascii=False)
        file_handle.write("\n")


def get_ssh_settings(require_auth: bool = True) -> SSHSettings:
    """Load SSH settings from environment variables without hardcoded secrets."""

    load_environment()

    host = os.getenv("NEXUS_SSH_HOST") or os.getenv("SSH_HOST")
    user = os.getenv("NEXUS_SSH_USER") or os.getenv("SSH_USER")
    password = os.getenv("NEXUS_SSH_PASSWORD") or os.getenv("SSH_PASSWORD")
    key_path = os.getenv("NEXUS_SSH_KEY_PATH") or os.getenv("SSH_KEY_PATH")
    port_value = os.getenv("NEXUS_SSH_PORT") or os.getenv("SSH_PORT") or "22"
    timeout_value = os.getenv("NEXUS_SSH_TIMEOUT", "15")

    missing = []
    if not host:
        missing.append("NEXUS_SSH_HOST")
    if not user:
        missing.append("NEXUS_SSH_USER")
    if require_auth and not password and not key_path:
        missing.append("NEXUS_SSH_PASSWORD or NEXUS_SSH_KEY_PATH")
    if missing:
        raise ConfigError("Missing required SSH configuration: " + ", ".join(missing))

    try:
        port = int(port_value)
        timeout = int(timeout_value)
    except ValueError as exc:
        raise ConfigError("NEXUS_SSH_PORT and NEXUS_SSH_TIMEOUT must be integers.") from exc

    return SSHSettings(
        host=host or "",
        user=user or "",
        port=port,
        password=password,
        key_path=key_path,
        timeout=timeout,
    )


def get_web_auth_credentials() -> tuple[str | None, str | None]:
    """Return optional web basic-auth credentials from environment."""

    load_environment()
    return os.getenv("NEXUS_WEB_USERNAME"), os.getenv("NEXUS_WEB_PASSWORD")


def get_audit_log_path() -> Path:
    """Return audit log path, defaulting to data/audit_log.jsonl."""

    return Path(os.getenv("NEXUS_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH)).expanduser().resolve()
