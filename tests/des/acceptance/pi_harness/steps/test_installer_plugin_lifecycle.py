"""Acceptance steps: the nWave installer wires DES into the pi agent.

Driving port = the production ``PiDESPlugin`` lifecycle
(``validate_prerequisites`` / ``install`` / ``verify`` / ``uninstall``) over a real
``InstallContext`` with real filesystem I/O on ``tmp_path``. No model, no pi
binary, no mocks beyond the logger -- this exercises the installer adapter
deterministically (layer 3, ``@real-io @adapter-integration``).

State-mutating steps assert via ``assert_state_delta`` over a port-exposed universe
(extension presence, manifest presence, operator-file presence, rendered content)
-- Mandate 8. Sad paths are example-based (Mandate 11); no PBT at this layer
(Mandate 9).

RED until DELIVER implements ``scripts/install/plugins/pi_des_plugin.py``: the
scaffold's lifecycle methods raise AssertionError, so these scenarios fail for
MISSING_FUNCTIONALITY, not import/collection error.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to
from pytest_bdd import given, scenarios, then, when

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_des_plugin import (
    _EXTENSION_FILENAME,
    _MANIFEST_FILENAME,
    PiDESPlugin,
)


scenarios("../installer-plugin-lifecycle.feature")

_REPO_ROOT = Path(__file__).resolve().parents[5]
_TEMPLATE_SRC = _REPO_ROOT / "nWave" / "templates" / "pi-des-extension.ts.template"
_OPERATOR_FILE = "my-own-extension.ts"


# --------------------------------------------------------------------------- #
# State capture helpers (port-exposed universe — Mandate 8)
# --------------------------------------------------------------------------- #


def _pi_filesystem_state(pi_dir: Path) -> dict[str, object]:
    """Port-exposed observable state of the pi config dir."""
    ext = pi_dir / _EXTENSION_FILENAME
    manifest = pi_dir / _MANIFEST_FILENAME
    operator = pi_dir / _OPERATOR_FILE
    return {
        "extension.present": ext.exists(),
        "extension.content": ext.read_text(encoding="utf-8") if ext.exists() else None,
        "manifest.present": manifest.exists(),
        "operator_file.present": operator.exists(),
        "operator_file.content": (
            operator.read_text(encoding="utf-8") if operator.exists() else None
        ),
    }


@pytest.fixture
def world() -> dict[str, object]:
    return {}


@pytest.fixture
def plugin() -> PiDESPlugin:
    return PiDESPlugin()


def _build_context(
    tmp_path: Path, *, des_installed: bool, template_available: bool
) -> InstallContext:
    framework_source = tmp_path / "framework"
    (framework_source / "templates").mkdir(parents=True)
    if template_available:
        (framework_source / "templates" / "pi-des-extension.ts.template").write_text(
            _TEMPLATE_SRC.read_text(encoding="utf-8"), encoding="utf-8"
        )

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    if des_installed:
        des_module = claude_dir / "lib" / "python" / "des"
        des_module.mkdir(parents=True)
        (des_module / "__init__.py").write_text("", encoding="utf-8")

    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=tmp_path / "scripts",
        templates_dir=framework_source / "templates",
        logger=MagicMock(),
        project_root=tmp_path / "project",
        framework_source=framework_source,
    )


# --------------------------------------------------------------------------- #
# Given (preconditions only — never the expected output)
# --------------------------------------------------------------------------- #


@given("the DES Python library is installed")
def _des_installed(world: dict) -> None:
    world["des_installed"] = True


@given("the DES Python library is not installed")
def _des_not_installed(world: dict) -> None:
    world["des_installed"] = False


@given("the pi DES extension template is available to the installer")
def _template_available(world: dict) -> None:
    world["template_available"] = True


@given("a pi config directory exists")
def _pi_dir_exists(world: dict, tmp_path: Path, monkeypatch) -> None:
    pi_dir = tmp_path / "pi-config"
    pi_dir.mkdir(parents=True)
    monkeypatch.setenv("PI_CONFIG_DIR", str(pi_dir))
    world["pi_dir"] = pi_dir


@given("no pi config directory exists")
def _pi_dir_absent(world: dict, tmp_path: Path, monkeypatch) -> None:
    pi_dir = tmp_path / "pi-config-absent"
    monkeypatch.setenv("PI_CONFIG_DIR", str(pi_dir))
    world["pi_dir"] = pi_dir


@given("the operator keeps their own file in the pi config directory")
def _operator_file(world: dict) -> None:
    pi_dir: Path = world["pi_dir"]
    (pi_dir / _OPERATOR_FILE).write_text("// operator's own pi file", encoding="utf-8")


@given("the pi DES target has been installed")
@given("the pi DES target has been installed once")
def _already_installed(world: dict, plugin: PiDESPlugin, tmp_path: Path) -> None:
    context = _build_context(
        tmp_path,
        des_installed=world.get("des_installed", True),
        template_available=world.get("template_available", True),
    )
    world["context"] = context
    plugin.install(context)


# --------------------------------------------------------------------------- #
# When (single action through the driving port)
# --------------------------------------------------------------------------- #


@when("the operator installs the pi DES target")
def _install(world: dict, plugin: PiDESPlugin, tmp_path: Path) -> None:
    context = world.get("context") or _build_context(
        tmp_path,
        des_installed=world.get("des_installed", True),
        template_available=world.get("template_available", True),
    )
    world["context"] = context
    world["before"] = _pi_filesystem_state(world["pi_dir"])
    world["result"] = plugin.install(context)
    world["after"] = _pi_filesystem_state(world["pi_dir"])


@when("the operator installs the pi DES target again")
def _reinstall(world: dict, plugin: PiDESPlugin) -> None:
    world["before"] = _pi_filesystem_state(world["pi_dir"])
    world["result"] = plugin.install(world["context"])
    world["after"] = _pi_filesystem_state(world["pi_dir"])


@when("the operator checks pi DES prerequisites")
def _check_prereqs(world: dict, plugin: PiDESPlugin, tmp_path: Path) -> None:
    context = _build_context(
        tmp_path,
        des_installed=world.get("des_installed", True),
        template_available=world.get("template_available", True),
    )
    world["result"] = plugin.validate_prerequisites(context)


@when("the operator verifies the pi DES install")
def _verify(world: dict, plugin: PiDESPlugin, tmp_path: Path) -> None:
    context = world.get("context") or _build_context(
        tmp_path,
        des_installed=world.get("des_installed", True),
        template_available=world.get("template_available", True),
    )
    world["result"] = plugin.verify(context)


@when("the operator uninstalls the pi DES target")
def _uninstall(world: dict, plugin: PiDESPlugin, tmp_path: Path) -> None:
    context = world.get("context") or _build_context(
        tmp_path,
        des_installed=world.get("des_installed", True),
        template_available=world.get("template_available", True),
    )
    world["context"] = context
    world["before"] = _pi_filesystem_state(world["pi_dir"])
    world["result"] = plugin.uninstall(context)
    world["after"] = _pi_filesystem_state(world["pi_dir"])


# --------------------------------------------------------------------------- #
# Then (observable outcomes — universe-bound deltas where state mutates)
# --------------------------------------------------------------------------- #


@then("the rendered pi DES extension is present in the pi config directory")
def _extension_present(world: dict) -> None:
    before, after = world["before"], world["after"]
    assert_state_delta(
        before=before,
        after=after,
        universe=set(before) | set(after),
        expected={
            "extension.present": set_to(True),
            "manifest.present": set_to(True),
            "extension.content": _is_rendered,
        },
    )


@then("the extension records the resolved python interpreter and DES library path")
def _extension_rendered(world: dict) -> None:
    content = world["after"]["extension.content"]
    assert content is not None and "{{" not in content, (
        f"expected fully-rendered extension, got placeholders or empty:\n{content}"
    )


@then("an install manifest records the placed artifacts")
def _manifest_records(world: dict) -> None:
    manifest_path = world["pi_dir"] / _MANIFEST_FILENAME
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data, "manifest is empty; expected it to record the placed artifacts"


@then("no unrelated pi config files are disturbed")
def _nothing_unrelated_disturbed(world: dict) -> None:
    # operator_file.present is in the universe but absent from the install
    # expected map -> implicit-unchanged already enforced it stays as-was.
    before, after = world["before"], world["after"]
    assert_state_delta(
        before=before,
        after=after,
        universe=set(before) | set(after),
        expected={
            "extension.present": set_to(True),
            "manifest.present": set_to(True),
            "extension.content": _is_rendered,
        },
    )


@then("the installation reports success")
@then("the uninstallation reports success")
def _reports_success(world: dict) -> None:
    assert world["result"].success is True, world["result"].message


@then("the operator is told the pi target was skipped because pi was not detected")
def _skip_message(world: dict) -> None:
    msg = world["result"].message.lower()
    assert "skip" in msg or "not detected" in msg, world["result"].message


@then("the prerequisite check fails naming the missing DES library")
def _prereq_fails_des(world: dict) -> None:
    result = world["result"]
    assert result.success is False
    assert "des" in result.message.lower()


@then("the verification reports the extension and manifest are present")
def _verify_passes(world: dict) -> None:
    assert world["result"].success is True, world["result"].message


@then("the verification reports the pi DES extension is missing")
def _verify_fails_missing(world: dict) -> None:
    result = world["result"]
    assert result.success is False
    assert (
        "extension" in result.message.lower()
        or _EXTENSION_FILENAME in result.message
        or "missing" in result.message.lower()
    )


@then("the rendered pi DES extension reflects the current template")
def _extension_refreshed(world: dict) -> None:
    content = world["after"]["extension.content"]
    expected = _TEMPLATE_SRC.read_text(encoding="utf-8")
    marker = "[nWave DES] enforcement active for pi"
    assert content is not None and marker in content and marker in expected


@then("the operator's own pi file is left untouched")
def _operator_file_untouched(world: dict) -> None:
    before, after = world["before"], world["after"]
    assert after["operator_file.present"] is True
    assert after["operator_file.content"] == before["operator_file.content"]


@then("the rendered pi DES extension is gone")
def _extension_gone(world: dict) -> None:
    before, after = world["before"], world["after"]
    assert_state_delta(
        before=before,
        after=after,
        universe=set(before) | set(after),
        expected={
            "extension.present": set_to(False),
            "extension.content": set_to(None),
            "manifest.present": set_to(False),
        },
    )


@then("the install manifest is gone")
def _manifest_gone(world: dict) -> None:
    assert world["after"]["manifest.present"] is False


def _is_rendered(_old: object, new: object) -> bool:
    return isinstance(new, str) and "{{" not in new and len(new) > 0
