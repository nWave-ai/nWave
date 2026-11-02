"""Emit a pinned, host-specific offline dependency closure beside a public wheel.

The public ``nwave-ai`` wheel deliberately retains normal ``Requires-Dist``
metadata. This Hatch hook complements that metadata at build time with the
same resolver closure as install-time pip/pipx uses, so an operator can pass
the candidate and its adjacent ``offline-wheelhouse`` to an air-gapped host.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _distribution_name(name: str) -> str:
    """Return the PEP 503 comparison form used by pip's resolver."""
    return name.replace("_", "-").lower()


def _runtime_requirements(requirements: list[str]) -> list[str]:
    """Keep every direct runtime requirement while removing environment markers.

    A candidate handoff carries all declared runtime wheels, including a
    marker-gated dependency such as ``tomli``. Pip still honours the marker in
    the wheel metadata when the candidate is installed; fetching the wheel now
    makes the handoff portable across the supported Python floors.
    """
    return sorted(
        requirement.split(";", maxsplit=1)[0].strip() for requirement in requirements
    )


def _wheel_distribution(wheel: Path) -> tuple[str, str]:
    """Read the canonical distribution name and exact version from *wheel*."""
    with zipfile.ZipFile(wheel) as archive:
        metadata_member = next(
            member
            for member in archive.namelist()
            if member.endswith(".dist-info/METADATA")
        )
        metadata = BytesParser(policy=default).parsebytes(archive.read(metadata_member))
    name = metadata["Name"]
    version = metadata["Version"]
    if not name or not version:
        raise RuntimeError(
            "WHAT: an offline-wheelhouse artifact has incomplete package metadata. "
            f"WHY: {wheel.name} lacks Name or Version in .dist-info/METADATA. "
            "HOW: rebuild the public candidate with a valid wheel-producing resolver."
        )
    return _distribution_name(name), version


def _write_lock(wheelhouse: Path, candidate: Path) -> None:
    """Write a reproducible requirements file from the downloaded wheel bytes."""
    entries: list[tuple[str, str, str]] = []
    for wheel in sorted(wheelhouse.glob("*.whl")):
        name, version = _wheel_distribution(wheel)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        entries.append((name, version, digest))

    if not entries:
        raise RuntimeError(
            "WHAT: the public candidate offline wheelhouse is empty. "
            "WHY: pip did not download the bootstrap or runtime distributions. "
            "HOW: restore pip download access during candidate assembly and rebuild."
        )

    lines = [
        "# Generated from the exact public candidate's runtime metadata.",
        "# Install only with: pip install --no-index --find-links . -r requirements.lock",
    ]
    lines.extend(
        f"{name}=={version} --hash=sha256:{digest}"
        for name, version, digest in sorted(entries)
    )
    candidate_digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    candidate_reference = (Path("..") / candidate.name).as_posix()
    lines.append(f"{candidate_reference} --hash=sha256:{candidate_digest}")
    (wheelhouse / "requirements.lock").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


class CustomBuildHook(BuildHookInterface):
    """Build a normal pip/pipx-compatible closure after the public wheel exists."""

    PLUGIN_NAME = "custom"

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Download and lock pip plus the complete runtime dependency graph."""
        del version, build_data
        if self.target_name != "wheel":
            return

        candidate = Path(artifact_path).resolve()
        wheelhouse = candidate.parent / "offline-wheelhouse"
        if wheelhouse.exists():
            shutil.rmtree(wheelhouse)
        wheelhouse.mkdir(parents=True, exist_ok=True)
        requirements = _runtime_requirements(self.metadata.core.dependencies)
        command = [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--dest",
            str(wheelhouse),
            "pip",
            *requirements,
        ]
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=900,
        )
        if result.returncode:
            raise RuntimeError(
                "WHAT: the public candidate has no complete offline dependency closure. "
                "WHY: pip could not download the bootstrap pip and all runtime wheels. "
                "HOW: make the release builder's package index reachable, then rebuild the candidate. "
                f"pip output: {(result.stdout + result.stderr).strip()}"
            )

        _write_lock(wheelhouse, candidate)
