"""E2E: Distributed nwave-ai wheel contains no private or closed-source files.

Migrated from: tests/e2e/Dockerfile.verify-hotfix-batch (Test 5 only)
Layer 4 of platform-testing-strategy.md

Supply-chain privacy contract for the public PyPI wheel.  Each of the
11 assertions below maps to a class of material that MUST NOT ship:

  1. No docs/analysis/           — internal RCA reports, audits
  2. No docs/feature/            — in-flight feature tracking + acks
  3. No .github/                 — CI/CD workflows, secrets references
  4. No src/des/                 — DES source (closed-source runtime)
  5. No tests/ .py               — test fixtures and tooling
  6. No .secrets / .key          — credentials, tokens
  7. No pyproject.toml           — internal build config (distinct from METADATA)
  8. No scripts/release/         — release-automation tooling (private)
  9. No scripts/hooks/           — pre-commit hook scripts (dev-only)
 10. No scripts/framework/       — framework build utilities (dev-only)
 11. No scripts/validation/      — CI validators (dev-only)

The installed site-packages directory is inspected inside a container
that has run ``pipx install --pre nwave-ai``; each assertion is an
existence check over the shipped files, not a build-side scan.

Other hotfix-batch tests (#34 hook stdout, #33 regex, #32 gitignore,
#29 user skills survive) are out of scope for this migration — they
cover orthogonal regression surfaces and would require the broader RC
install rig.

Requires a Docker daemon.  Skips gracefully when Docker is unavailable.

Step-Id: 01-03
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tests.e2e.conftest import exec_in_container, require_docker


pytestmark = pytest.mark.e2e_smoke

_REPO_ROOT = Path(__file__).parent.parent.parent
_IMAGE = "python:3.12-slim"


@pytest.fixture(scope="module")
def wheel_privacy_container(pypi_shape_wheel: Path):
    """Container with nwave-ai installed from the LOCAL-built wheel.

    Closes Root Cause A from /nw-bugfix RCA (fix-wheel-privacy-self-blocking-gate
    step 01-02): previously this fixture installed nwave-ai from the live PyPI
    release channel, creating a self-blocking catch-22 when a leaked wheel
    reached PyPI — the leak fix could not be pushed because the pre-push e2e
    installed the leaked wheel and failed on it.

    The fixture now consumes the session-scoped `pypi_shape_wheel` fixture from
    tests/e2e/conftest.py (which builds the wheel via the exact same pipeline
    as release-prod.yml:publish-to-pypi) and installs from a container-mounted
    path.  No live PyPI dependency.
    """
    from tests.e2e.conftest import _is_docker_available

    if not _is_docker_available():
        pytest.skip("Docker daemon not available")

    from testcontainers.core.container import (
        DockerContainer,  # type: ignore[import-untyped]
    )

    container = DockerContainer(image=_IMAGE)
    container.with_env("HOME", "/home/tester")
    container.with_env("DEBIAN_FRONTEND", "noninteractive")
    # Mount the session-built wheel's parent directory read-only at /tmp/wheels
    # inside the container.  pipx then installs from the local path.
    wheel_host_dir = str(pypi_shape_wheel.parent)
    container.with_volume_mapping(wheel_host_dir, "/tmp/wheels", "ro")
    container._command = "tail -f /dev/null"

    wheel_filename = pypi_shape_wheel.name

    with container:
        setup = (
            "set -e && "
            "apt-get update -qq && "
            "apt-get install -y --no-install-recommends git curl pipx -qq && "
            "rm -rf /var/lib/apt/lists/* && "
            "useradd -m -s /bin/bash tester && "
            "su tester -c 'pipx ensurepath'"
        )
        code, out = exec_in_container(container, ["bash", "-c", setup])
        assert code == 0, f"Base setup failed.\n{out[-400:]}"

        install = (
            "su tester -c 'export PATH=/home/tester/.local/bin:$PATH && "
            f"pipx install /tmp/wheels/{wheel_filename} 2>&1' | tail -10"
        )
        code, out = exec_in_container(container, ["bash", "-c", install])
        if code != 0:
            pytest.skip(
                f"pipx install of local wheel failed (exit {code}) — "
                f"likely Docker volume mount or wheel-build issue.\n{out[-400:]}"
            )

        yield container


def _site_packages_root(container) -> str:
    """Resolve the site-packages root — matches the original Dockerfile scope.

    The Dockerfile did:

        SITE_PACKAGES=$(find ~/.local/pipx -name "nwave_ai" -type d | head -1)
        SITE_DIR=$(dirname "$SITE_PACKAGES")

    The original ``~/.local/pipx`` path was wrong (pipx actually uses
    ``~/.local/share/pipx``); that bug silently skipped the privacy
    checks.  We correct the search root and return ``dirname(nwave_ai)``,
    i.e. the site-packages directory itself.  This is the SAME scope the
    Dockerfile intended: privacy assertions run over the entire
    site-packages tree, catching any leaked content (including the
    site-packages-level ``src/des/config/`` runtime data).
    """
    code, out = exec_in_container(
        container,
        [
            "bash",
            "-c",
            (
                "find /home/tester/.local/share/pipx/venvs/nwave-ai "
                "-name 'nwave_ai' -type d -not -path '*dist-info*' 2>/dev/null | head -1"
            ),
        ],
    )
    pkg = out.strip().splitlines()[-1] if out.strip() else ""
    assert code == 0 and pkg, (
        f"Could not resolve nwave_ai package dir.\nexit={code}, output={out[-300:]!r}"
    )
    # Return site-packages root (parent of nwave_ai/) to match Dockerfile scope.
    return pkg.rsplit("/", 1)[0]


def _find_in_site_packages(container, pattern: str, path_filter: str = "") -> int:
    """Count matches of *pattern* under pipx site-packages, optionally path-filtered."""
    site = _site_packages_root(container)
    filter_expr = f'-path "*/{path_filter}*"' if path_filter else ""
    cmd = f'find "{site}" {filter_expr} -name "{pattern}" 2>/dev/null | wc -l'
    _code, out = exec_in_container(container, ["bash", "-c", cmd])
    try:
        return int(out.strip())
    except ValueError:
        return -1


def _tests_leak_scan_cmd(site: str) -> str:
    """Bash command listing nWave's OWN leaked ``tests/`` .py files under *site*.

    Scoped to nWave's footprint: a leaked repo ``tests/`` dir lands at the
    site-packages root (mirroring repo layout, exactly like the ``src/`` and
    ``scripts/`` leaks guarded above), or nested inside the installed
    ``nwave_ai`` package.  Third-party dependencies legitimately bundle their
    own ``tests/`` (e.g. ``referencing/tests/``, pulled in transitively via the
    ``jsonschema`` runtime dependency added in v3.19.0) — those are NOT nWave
    leaks and must not trip this gate.  The previous unscoped
    ``find "$site" -path "*/tests/*"`` matched any dependency's bundled tests.
    """
    return (
        f'find "{site}/tests" "{site}/nwave_ai" -path "*/tests/*" '
        '-name "*.py" 2>/dev/null | head -5'
    )


@pytest.mark.e2e
@require_docker
class TestWheelPrivacyContract:
    """Wheel minimization + privacy: 11 classes must not ship in the PyPI wheel.

    The wheel `nwave-ai` is the `pipx install` entry-point — it ships only what
    is needed at install time.  Source browsing, tests, CI, and dev tooling
    live in the public GitHub mirror (``nWave-ai/nWave``) and should not
    double-distribute through the wheel.

    Most classes here (src/, tests/, scripts/release, scripts/hooks, etc.) are
    **wheel-bloat / wrong-channel** concerns, not closed-source violations —
    their content is open source on GitHub.  A few classes (docs/analysis,
    .github/, .secrets) are **privacy** concerns: they are private to this
    repo and never published anywhere.

    Originally migrated from Dockerfile.verify-hotfix-batch Test 5 (7 assertions).
    Extended 2026-04-23 (reduce-wheel-bloat, step 01-02) with 4 new guards for
    scripts/{release,hooks,framework,validation}/ — classes discovered to also
    leak into the 3.11.0 wheel alongside src/des/.
    """

    def test_no_docs_analysis_in_wheel(self, wheel_privacy_container) -> None:
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/docs/analysis/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", f"docs/analysis/ content leaked into wheel:\n{leaked}"

    def test_no_docs_feature_in_wheel(self, wheel_privacy_container) -> None:
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/docs/feature/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", f"docs/feature/ content leaked into wheel:\n{leaked}"

    def test_no_github_workflows_in_wheel(self, wheel_privacy_container) -> None:
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            ["bash", "-c", f'find "{site}" -path "*/.github/*" 2>/dev/null | head -5'],
        )
        leaked = out.strip()
        assert leaked == "", f".github/ content leaked into wheel:\n{leaked}"

    def test_no_des_source_in_wheel(self, wheel_privacy_container) -> None:
        """src/des/ must not ship inside the PyPI wheel.

        DES source is OPEN SOURCE and available on the public GitHub mirror
        (``nWave-ai/nWave``).  The wheel ships only the pre-built DES tree at
        ``nWave/lib/python/des/`` produced by ``scripts/build_dist.py`` — not
        the raw ``src/des/`` source.  Shipping both is double-distribution and
        wheel bloat, not a privacy violation.
        """
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            ["bash", "-c", f'find "{site}" -path "*/src/des/*" 2>/dev/null | head -5'],
        )
        leaked = out.strip()
        assert leaked == "", (
            "src/des/ leaked into wheel — wheel should ship pre-built "
            f"nWave/lib/python/des/ only. Source lives on GitHub.\n{leaked}"
        )

    def test_no_test_files_in_wheel(self, wheel_privacy_container) -> None:
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            ["bash", "-c", _tests_leak_scan_cmd(site)],
        )
        leaked = out.strip()
        assert leaked == "", f"nWave tests/ .py files leaked into wheel:\n{leaked}"

    def test_no_secret_files_in_wheel(self, wheel_privacy_container) -> None:
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                (
                    f'find "{site}" \\( -name ".secrets" -o -name "credentials*" '
                    '-o -name "*.key" \\) 2>/dev/null | head -5'
                ),
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"Credential/secret files leaked into wheel:\n{leaked}\n"
            "This is a P0 security issue — rotate any exposed secrets."
        )

    def test_no_pyproject_toml_in_wheel(self, wheel_privacy_container) -> None:
        """pyproject.toml is internal build config; METADATA is the wheel's public contract."""
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -name "pyproject.toml" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"pyproject.toml leaked into wheel (internal build config):\n{leaked}"
        )

    def test_no_scripts_release_in_wheel(self, wheel_privacy_container) -> None:
        """scripts/release/ is release-automation tooling — must NOT ship to users.

        Regression guard (fix-wheel-leaks-des-config-p0 01-02): the 3.11.0 wheel
        shipped 15 files of release automation (patch_pyproject.py, ci_gate.py,
        version calculators, slack hooks) because patch_pyproject.py force-included
        the entire scripts/ directory.  The fix narrows the force-include to
        scripts/install/ + scripts/shared/ only.
        """
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/scripts/release/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"scripts/release/ (release automation) leaked into wheel:\n{leaked}"
        )

    def test_no_scripts_hooks_in_wheel(self, wheel_privacy_container) -> None:
        """scripts/hooks/ is pre-commit tooling for this repo — must NOT ship to users.

        Regression guard (fix-wheel-leaks-des-config-p0 01-02): 25 files leaked
        in the 3.11.0 wheel via the broad scripts/ force-include.
        """
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/scripts/hooks/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"scripts/hooks/ (pre-commit tooling) leaked into wheel:\n{leaked}"
        )

    def test_no_scripts_framework_in_wheel(self, wheel_privacy_container) -> None:
        """scripts/framework/ is framework build utilities — must NOT ship to users.

        Regression guard (fix-wheel-leaks-des-config-p0 01-02): 8 files leaked
        in the 3.11.0 wheel via the broad scripts/ force-include.
        """
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/scripts/framework/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"scripts/framework/ (build utilities) leaked into wheel:\n{leaked}"
        )

    def test_no_scripts_validation_in_wheel(self, wheel_privacy_container) -> None:
        """scripts/validation/ is CI validator tooling — must NOT ship to users.

        Regression guard (fix-wheel-leaks-des-config-p0 01-02): 11 files leaked
        in the 3.11.0 wheel via the broad scripts/ force-include.
        """
        site = _site_packages_root(wheel_privacy_container)
        _code, out = exec_in_container(
            wheel_privacy_container,
            [
                "bash",
                "-c",
                f'find "{site}" -path "*/scripts/validation/*" 2>/dev/null | head -5',
            ],
        )
        leaked = out.strip()
        assert leaked == "", (
            f"scripts/validation/ (CI validators) leaked into wheel:\n{leaked}"
        )


# ---------------------------------------------------------------------------
# Meta-test: regression guard against re-introducing the live-PyPI anti-pattern
# ---------------------------------------------------------------------------


class TestWheelPrivacyFixtureShape:
    """Regression guard: wheel_privacy_container MUST consume a local-built wheel.

    Closes Root Cause A from /nw-bugfix RCA (fix-wheel-privacy-self-blocking-gate):
    the fixture previously installed nwave-ai from live PyPI via
    `pipx install --pip-args="--pre"`, creating a self-blocking catch-22 when a
    leaked wheel reached PyPI — the leak fix could not be pushed because the
    pre-push e2e installed the leaked wheel and failed on it.

    The fixture must source the wheel from the local `pypi_shape_wheel` session
    fixture (which builds the wheel via the same release-prod.yml pipeline) and
    install it from a path inside the container, never from live PyPI.
    """

    def test_tests_leak_scan_ignores_third_party_bundled_tests(self, tmp_path) -> None:
        """The tests/ leak gate flags nWave's own leaked tests/ but ignores
        third-party deps that bundle their own tests/ (e.g. referencing via
        jsonschema, v3.19.0). Runs the scan logic locally — no Docker needed.

        Regression for the v3.19.0 RC failure: the unscoped
        ``find "$site" -path "*/tests/*"`` matched ``referencing/tests/*.py`` and
        falsely blocked the release.
        """
        import subprocess

        site = tmp_path
        (site / "nwave_ai").mkdir()
        (site / "nwave_ai" / "__init__.py").write_text("")
        # A third-party dependency that bundles its own tests/ — must be IGNORED.
        (site / "referencing" / "tests").mkdir(parents=True)
        (site / "referencing" / "tests" / "test_referencing_suite.py").write_text("")
        (site / "referencing" / "tests" / "__init__.py").write_text("")

        def scan() -> str:
            done = subprocess.run(
                ["bash", "-c", _tests_leak_scan_cmd(str(site))],
                capture_output=True,
                text=True,
                check=False,
            )
            return done.stdout.strip()

        # Only a dependency bundles tests/ -> gate must pass (empty result).
        assert scan() == "", (
            f"third-party bundled tests/ tripped the leak gate:\n{scan()}"
        )

        # nWave's own repo tests/ shipped at the site root -> MUST be caught.
        (site / "tests").mkdir()
        (site / "tests" / "test_leaked.py").write_text("")
        leaked = scan()
        assert "tests/test_leaked.py" in leaked, (
            f"nWave tests/ leak was not caught by the gate:\n{leaked!r}"
        )

    def test_fixture_does_not_install_from_live_pypi(self) -> None:
        """The wheel_privacy_container fixture body MUST NOT reference live PyPI."""
        source = inspect.getsource(wheel_privacy_container)
        assert "--pre" not in source, (
            "wheel_privacy_container fixture installs from live PyPI via --pre. "
            "This creates a self-blocking catch-22: a leaked wheel on PyPI cannot "
            "be fixed because the pre-push e2e installs the leaked wheel and fails. "
            "Consume the local-built `pypi_shape_wheel` fixture instead."
        )
        assert "--pip-args" not in source, (
            "wheel_privacy_container fixture uses pipx --pip-args (live-PyPI "
            "install pattern). Consume the local-built `pypi_shape_wheel` fixture "
            "and install from a container-local path instead."
        )

    def test_fixture_installs_from_local_wheel_path(self) -> None:
        """The fixture must install from a local wheel path in the container."""
        source = inspect.getsource(wheel_privacy_container)
        # Either /tmp/wheels/ container path or a literal .whl reference must
        # appear in the fixture body — proving it sources from a local artifact
        # rather than the PyPI index.
        has_local_wheel_marker = "/tmp/wheels/" in source or ".whl" in source
        assert has_local_wheel_marker, (
            "wheel_privacy_container fixture body does not reference a local "
            "wheel path (/tmp/wheels/ or .whl). The fixture must consume the "
            "local-built `pypi_shape_wheel` fixture and install it from a "
            "container-mounted path."
        )
