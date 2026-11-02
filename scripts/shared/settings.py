"""Shared JSON settings file loading.

Provides a single implementation for loading Claude Code ``settings.json``
files, used by DES plugin installation and uninstallation scripts.

Semantics:
  - Missing file: returns ``{}``.
  - Corrupt JSON: raises ``ValueError`` (callers that need silent fallback
    should catch explicitly).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


_TODO_TOOLS_ENV = "CLAUDE_CODE_ENABLE_TODO_TOOLS"


@dataclass(frozen=True)
class TodoToolsEnvReceipt:
    written: str
    before: str | None


@dataclass(frozen=True)
class EnvPlan:
    settings: Mapping[str, object]
    receipt: TodoToolsEnvReceipt


def _immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _immutable(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_immutable(child) for child in value)
    return value


def _json_data(value):
    if isinstance(value, Mapping):
        return {key: _json_data(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_json_data(child) for child in value]
    return value


def plan_enable_todo_tools(
    settings: Mapping[str, object], existing: TodoToolsEnvReceipt | None
) -> EnvPlan:
    env = settings.get("env", {})
    receipt = (
        existing
        if existing is not None
        else TodoToolsEnvReceipt(written="1", before=env.get(_TODO_TOOLS_ENV))
    )
    return EnvPlan(
        _immutable({**settings, "env": {**env, _TODO_TOOLS_ENV: "1"}}),
        receipt,
    )


def plan_restore_todo_tools(
    settings: Mapping[str, object], receipt: TodoToolsEnvReceipt
) -> Mapping[str, object]:
    env = settings.get("env", {})
    if env.get(_TODO_TOOLS_ENV) != receipt.written:
        return settings
    restored_env = {
        **{key: value for key, value in env.items() if key != _TODO_TOOLS_ENV},
        **({_TODO_TOOLS_ENV: receipt.before} if receipt.before is not None else {}),
    }
    return _immutable(
        {
            **{key: value for key, value in settings.items() if key != "env"},
            **({"env": restored_env} if restored_env else {}),
        }
    )


def todo_tools_receipt_path(claude_dir: Path) -> Path:
    digest = hashlib.sha256(str(claude_dir.resolve()).encode()).hexdigest()[:16]
    return (
        claude_dir.parent / ".nwave" / "install-receipts" / f"claude-env-{digest}.json"
    )


def enable_todo_tools_env(settings_file: Path, receipt_file: Path) -> None:
    settings = load_settings(settings_file)
    existing = (
        TodoToolsEnvReceipt(**json.loads(receipt_file.read_text(encoding="utf-8")))
        if receipt_file.exists()
        else None
    )
    plan = plan_enable_todo_tools(settings, existing)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps(_json_data(plan.settings), indent=2) + "\n", encoding="utf-8"
    )
    receipt_file.write_text(
        json.dumps(asdict(plan.receipt), indent=2) + "\n", encoding="utf-8"
    )


def restore_todo_tools_env(settings_file: Path, receipt_file: Path) -> None:
    if not receipt_file.exists():
        return
    settings = load_settings(settings_file)
    receipt = TodoToolsEnvReceipt(
        **json.loads(receipt_file.read_text(encoding="utf-8"))
    )
    restored = plan_restore_todo_tools(settings, receipt)
    if restored != settings:
        settings_file.write_text(
            json.dumps(_json_data(restored), indent=2) + "\n", encoding="utf-8"
        )
    receipt_file.unlink()


def load_settings(settings_file: Path) -> dict:
    """Load settings from a JSON file.

    Returns an empty dict when *settings_file* does not exist.
    Raises ``ValueError`` when the file exists but contains invalid JSON,
    ensuring corrupt configuration is never silently ignored.
    """
    if not settings_file.exists():
        return {}

    try:
        with open(settings_file, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {settings_file}: {e}") from e
