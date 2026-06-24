"""Regression: the pi extension surfaces the crafter skill via resources_discover.

ROOT CAUSE this guards (fix-pi-kata-phase-recording, step 01-01): in a live pi
kata run, phases were never recorded -> ``execution-log.json`` stayed empty -> DoD
not met. The defect: ``pi-des-extension.ts.template`` had NO ``resources_discover``
handler, so the ``software-crafter/SKILL.md`` the plugin places on disk was never
surfaced to pi. The model therefore never received the ``des-log-phase`` recording
contract. ADR-PI-003 mandated this handler; it was never implemented.

Driving port = the production ``PiDESPlugin`` rendering the extension into a tmp
``PI_CONFIG_DIR`` (real filesystem I/O on ``tmp_path``). Model-free: discoverability
is asserted by inspecting the RENDERED extension source (the registered
``resources_discover`` handler + its ``skillPaths`` result), mirroring the
rendered-source inspection pattern in ``test_extension_translation_contract.py``.
No node runtime needed. Plugin ``verify`` is also asserted to check
discoverability, not just ``skill_path.exists()``.

Layer 3 (``@real-io`` / ``@adapter-integration``): example-only (Mandate 11), no
PBT (Mandate 9) -- this is a wiring contract, not an input-equivalence-class claim.
Engine reused UNCHANGED (K2): zero ``src/des/**`` change. All test state stays
under ``tmp_path``.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_des_plugin import (
    _EXTENSION_FILENAME,
    _SKILL_DIRNAME,
    _SKILL_FILENAME,
    PiDESPlugin,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]
_TEMPLATE_SRC = _REPO_ROOT / "nWave" / "templates" / "pi-des-extension.ts.template"


def _build_context(tmp_path: Path) -> InstallContext:
    framework_source = tmp_path / "framework"
    (framework_source / "templates").mkdir(parents=True)
    (framework_source / "templates" / "pi-des-extension.ts.template").write_text(
        _TEMPLATE_SRC.read_text(encoding="utf-8"), encoding="utf-8"
    )

    claude_dir = tmp_path / ".claude"
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


@pytest.fixture
def installed_pi(tmp_path: Path, monkeypatch) -> dict:
    pi_dir = tmp_path / "pi-config"
    pi_dir.mkdir(parents=True)
    monkeypatch.setenv("PI_CONFIG_DIR", str(pi_dir))

    plugin = PiDESPlugin()
    context = _build_context(tmp_path)
    result = plugin.install(context)
    assert result.success, result.message

    extension = pi_dir / _EXTENSION_FILENAME
    return {
        "plugin": plugin,
        "context": context,
        "pi_dir": pi_dir,
        "rendered": extension.read_text(encoding="utf-8"),
    }


def test_extension_registers_resources_discover_handler(installed_pi: dict) -> None:
    rendered = installed_pi["rendered"]
    assert 'pi.on("resources_discover"' in rendered, (
        "extension must register a resources_discover handler so pi loads the "
        "crafter skill (ADR-PI-003); without it the des-log-phase recording "
        "contract never reaches the model and execution-log.json stays empty"
    )


def test_resources_discover_returns_installed_skill_dir_in_skill_paths(
    installed_pi: dict,
) -> None:
    rendered = installed_pi["rendered"]

    # The handler's result must use the pi ResourcesDiscoverResult shape: the
    # field pi reads skill directories from is `skillPaths` (pi 0.79.9 types).
    assert "skillPaths" in rendered, (
        "resources_discover result must populate `skillPaths` (the pi field of "
        "absolute skill directories) -- ResourcesDiscoverResult, pi 0.79.9"
    )

    # The skill dir that pi must load is the one the plugin placed:
    # <pi-config>/software-crafter/. The handler resolves it relative to the
    # extension's own location (the extension lives in <pi-config>), so the
    # rendered source must reference the placed skill dir name.
    assert _SKILL_DIRNAME in rendered, (
        f"resources_discover must surface the placed skill dir '{_SKILL_DIRNAME}' "
        f"in skillPaths -- this is the dir the plugin writes "
        f"'{_SKILL_DIRNAME}/{_SKILL_FILENAME}' into"
    )

    # The skill dir must actually be wired INTO the skillPaths result, not merely
    # mentioned in a comment. Strip comments, then assert the skill dir name and
    # skillPaths co-occur in the handler body.
    code_only = re.sub(r"/\*.*?\*/", "", rendered, flags=re.S)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "resources_discover" in code_only and "skillPaths" in code_only, (
        "the resources_discover -> skillPaths wiring must be code, not prose"
    )
    assert _SKILL_DIRNAME in code_only, (
        f"the skill dir '{_SKILL_DIRNAME}' must be wired into the handler body, "
        f"not just documented in a comment"
    )


def test_placed_skill_is_actually_discoverable_on_disk(installed_pi: dict) -> None:
    # The dir name the handler surfaces must match the dir the plugin placed --
    # otherwise the wire points at a non-existent path and pi loads nothing.
    skill_dir = installed_pi["pi_dir"] / _SKILL_DIRNAME
    skill_file = skill_dir / _SKILL_FILENAME
    assert skill_file.exists(), (
        "plugin must place the crafter skill so the resources_discover skillPaths "
        "entry resolves to a real directory"
    )


def test_verify_asserts_skill_is_discoverable_not_just_present(
    installed_pi: dict,
) -> None:
    # A passing verify must require the resources_discover wire, not merely the
    # skill file's existence. Sabotage the wire (remove the resources_discover
    # handler from the rendered extension) and confirm verify FAILS -- proving it
    # checks discoverability, not just skill_path.exists().
    plugin: PiDESPlugin = installed_pi["plugin"]
    context: InstallContext = installed_pi["context"]
    pi_dir: Path = installed_pi["pi_dir"]

    healthy = plugin.verify(context)
    assert healthy.success, healthy.message

    extension = pi_dir / _EXTENSION_FILENAME
    sabotaged = extension.read_text(encoding="utf-8").replace(
        'pi.on("resources_discover"', 'pi.on("__disabled_resources_discover__"'
    )
    extension.write_text(sabotaged, encoding="utf-8")

    broken = plugin.verify(context)
    assert broken.success is False, (
        "verify must reject an extension that does not expose resources_discover "
        "even when the skill file still exists on disk -- discoverability is the "
        "contract, not mere file presence"
    )
