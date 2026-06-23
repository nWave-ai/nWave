"""Walking skeleton: the nWave DES extension loads into real pi end-to-end.

Driving port = pi loading the rendered extension. No layer is mocked: real pi,
the real rendered extension, the real Python DES adapter subprocess. The test
skips when the `pi` binary is unavailable (e.g. CI without pi installed) per the
SPIKE-0 CI caveat -- a live run still exercises the full path.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when


scenarios("../walking-skeleton.feature")

_REPO_ROOT = Path(__file__).resolve().parents[5]
_TEMPLATE = _REPO_ROOT / "nWave" / "templates" / "pi-des-extension.ts.template"
_HEALTH_LINE = "[nWave DES] enforcement active for pi"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return tmp_path / "proj"


@given("an nWave-activated project")
def _activated_project(project: Path) -> None:
    (project / ".nwave").mkdir(parents=True)
    (project / ".nwave" / "local-config.json").write_text(
        '{"enabled_for_repo": true}', encoding="utf-8"
    )


@given("the nWave pi DES extension rendered for that project")
def _rendered_extension(project: Path) -> Path:
    rendered = (
        _TEMPLATE.read_text(encoding="utf-8")
        .replace("{{PYTHON_PATH}}", sys.executable)
        .replace("{{PYTHONPATH}}", str(_REPO_ROOT / "src"))
    )
    ext_path = project / "des-enforce.ts"
    ext_path.write_text(rendered, encoding="utf-8")
    return ext_path


@when("I start pi with the extension loaded", target_fixture="pi_output")
def _start_pi(project: Path) -> str:
    pi_bin = shutil.which("pi")
    if pi_bin is None:
        pytest.skip("pi binary not available in this environment")
    ext_path = project / "des-enforce.ts"
    result = subprocess.run(
        [
            pi_bin,
            "--no-extensions",
            "-e",
            str(ext_path),
            "--offline",
            "--no-session",
            "--no-tools",
            "-p",
            "noop",
        ],
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout + result.stderr


@then("pi reports that DES enforcement is active for pi")
def _enforcement_active(pi_output: str) -> None:
    assert _HEALTH_LINE in pi_output, (
        f"expected health line {_HEALTH_LINE!r} in pi output, got:\n{pi_output}"
    )
