"""Wiring regression — the REAL uninstall entry point removes the managed payload.

RCA: ``fix-uninstall-attribution-residue``. The green milestone-2 ATs drove
``AttributionPlugin.uninstall()`` DIRECTLY, bypassing ``uninstall_nwave.py``.
That left the wiring untested: the bespoke ``NWaveUninstaller`` never called the
plugin / ``remove_settings_attribution``, so the nWave-managed ``attribution``
payload survived a real uninstall.

This test closes that blind spot. It drives the REAL command entry point —
``NWaveUninstaller.main()`` — inside a ``CLAUDE_CONFIG_DIR``-isolated sandbox and
asserts the managed payload is gone, neighbours are intact and in order, a
user-modified value is preserved, and an empty uninstall is a no-op.

Litmus (port-to-port at the command layer): delete the ``remove_attribution()``
call-site in ``main()`` and this test goes RED.

# bypass: acceptance-level WIRING test — single-example by nature (it verifies
# the real ``main()`` actually invokes removal on the isolated CLAUDE_CONFIG_DIR
# path). PBT would add no detection power here; the state-delta universe is
# exercised by the plugin-level AC4/AC5 unit ATs, which this test does NOT touch.
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.install.attribution_utils import (
    NWAVE_MANAGED_COMMIT,
    NWAVE_MANAGED_PR,
)
from scripts.install.uninstall_nwave import main as uninstall_main


# The DES PreToolUse registration written at install time; seeding it lets
# ``check_installation()`` recognise an installation so ``main()`` proceeds.
_DES_HOOK_COMMAND = (
    "# des-hook:pre-commit-attribution\n"
    "PYTHONPATH=$HOME/.claude/lib/python python3 -m "
    "des.adapters.drivers.hooks.claude_code_hook_adapter pre-tool-use"
)


def _settings_with_managed_payload() -> OrderedDict:
    """settings.json with the managed attribution payload plus ordered neighbours.

    Neighbour keys (env, model, hooks, theme) bracket the attribution block to
    pin both their survival AND their insertion order through the uninstall.
    """
    return OrderedDict(
        [
            ("env", {"NWAVE": "1"}),
            ("model", "claude-opus-4"),
            (
                "attribution",
                {"commit": NWAVE_MANAGED_COMMIT, "pr": NWAVE_MANAGED_PR},
            ),
            (
                "hooks",
                {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {"type": "command", "command": _DES_HOOK_COMMAND}
                            ],
                        }
                    ]
                },
            ),
            ("theme", "dark"),
        ]
    )


@pytest.fixture
def claude_sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated ``CLAUDE_CONFIG_DIR`` — the real uninstaller's isolation seam.

    ``NWaveUninstaller`` resolves ``self.claude_config_dir`` via
    ``PathUtils.get_claude_config_dir()``, which honours ``CLAUDE_CONFIG_DIR``.
    Setting it here points the REAL command at the sandbox, never the live
    ``~/.claude``.
    """
    claude_dir = tmp_path / "claude-config"
    claude_dir.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_dir))
    # A recognisable installation so check_installation() lets main() proceed.
    (claude_dir / "agents" / "nw").mkdir(parents=True)
    return claude_dir


def _write_settings(claude_dir: Path, data) -> None:
    (claude_dir / "settings.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def _read_settings(claude_dir: Path) -> dict:
    return json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))


def _run_real_uninstall(monkeypatch: pytest.MonkeyPatch) -> int:
    """Invoke the REAL command entry point: NWaveUninstaller.main() --force."""
    monkeypatch.setattr(sys, "argv", ["uninstall_nwave.py", "--force"])
    return uninstall_main()


def test_real_uninstall_removes_managed_attribution_payload(
    claude_sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Managed payload removed; neighbours intact AND in their original order."""
    _write_settings(claude_sandbox, _settings_with_managed_payload())

    exit_code = _run_real_uninstall(monkeypatch)

    after = _read_settings(claude_sandbox)
    # Managed payload gone (the empty attribution dict is dropped entirely).
    assert "attribution" not in after
    # Neighbours survive, with their original relative order preserved.
    assert [k for k in after if k != "attribution"] == [
        "env",
        "model",
        "hooks",
        "theme",
    ]
    assert after["env"] == {"NWAVE": "1"}
    assert after["model"] == "claude-opus-4"
    assert after["theme"] == "dark"
    # main() must not abort on the managed-removal path.
    assert exit_code == 0


def test_real_uninstall_preserves_user_modified_attribution(
    claude_sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A credit the developer rewrote after install survives uninstall."""
    settings = _settings_with_managed_payload()
    settings["attribution"] = {"commit": "my own credit"}
    _write_settings(claude_sandbox, settings)

    _run_real_uninstall(monkeypatch)

    after = _read_settings(claude_sandbox)
    assert after["attribution"] == {"commit": "my own credit"}


def test_real_uninstall_with_no_attribution_is_noop(
    claude_sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No attribution payload present → uninstall is a no-op and never crashes."""
    _write_settings(
        claude_sandbox,
        OrderedDict([("env", {"NWAVE": "1"}), ("theme", "dark")]),
    )

    exit_code = _run_real_uninstall(monkeypatch)

    after = _read_settings(claude_sandbox)
    assert "attribution" not in after
    assert after == {"env": {"NWAVE": "1"}, "theme": "dark"}
    assert exit_code == 0
