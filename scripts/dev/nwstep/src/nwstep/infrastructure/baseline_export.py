"""Exports the committed tree at REV into the workspace's baseline directory as a git repository of one commit.

The commit steps and the identity are domain data; this adapter only runs them. Every failure is returned as an
unavailable Baseline with its reason; nothing is passed silently.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from collections.abc import Mapping
from pathlib import Path

from nwstep.domain.baseline import (
    Baseline,
    identity_environment,
    pre_feature_commit_steps,
)
from nwstep.infrastructure.workspace import Workspace


class BaselineExport:
    def create(self, root: Path, rev: str, workspace: Workspace) -> Baseline:
        if rev.startswith("-"):
            return Baseline.unavailable(f"'{rev}' is not a revision")
        try:
            top_result = self._git(root, "rev-parse", "--show-toplevel")
            if top_result.returncode != 0:
                return Baseline.unavailable(f"{root} is not inside a git repository")
            top = Path(top_result.stdout.decode("utf-8").strip()).resolve()
            commit = self._git(
                top, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"
            )
            if commit.returncode != 0:
                return Baseline.unavailable(f"'{rev}' is not a commit of {top}")
            sha = commit.stdout.decode("utf-8").strip()
            listed = self._git(top, "ls-tree", "-r", "--name-only", sha)
            if listed.returncode != 0:
                detail = listed.stderr.decode("utf-8", errors="replace").strip()
                return Baseline.unavailable(f"git ls-tree of {sha} failed: {detail}")
            archive_data = b""
            if listed.stdout.strip():
                archive = self._git(top, "archive", "--format=tar", sha)
                if archive.returncode != 0:
                    detail = archive.stderr.decode("utf-8", errors="replace").strip()
                    return Baseline.unavailable(
                        f"git archive of {sha} failed: {detail}"
                    )
                archive_data = archive.stdout
            self._unpack(archive_data, workspace.baseline_directory)
            refusal = self._commit_pre_feature_tree(workspace.baseline_directory, sha)
        except OSError as error:
            return Baseline.unavailable(f"git cannot be run: {error.strerror or error}")
        except tarfile.TarError as error:
            return Baseline.unavailable(
                f"the archive of {sha} could not be unpacked: {error}"
            )
        if refusal is not None:
            return Baseline.unavailable(refusal)
        return Baseline.available(
            top=str(top), sha=sha, directory=str(workspace.baseline_directory)
        )

    def _commit_pre_feature_tree(self, target: Path, sha: str) -> str | None:
        environment = identity_environment()
        for step in pre_feature_commit_steps(sha):
            completed = self._git(target, *step, environment=environment)
            if completed.returncode != 0:
                detail = completed.stderr.decode("utf-8", errors="replace").strip()
                return f"git failed in {target} while making the pre-feature commit of {sha}: {detail}"
        return None

    @staticmethod
    def _git(
        cwd: Path,
        *args: str,
        environment: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=None if environment is None else {**os.environ, **environment},
            timeout=300,
            check=False,
        )

    @staticmethod
    def _unpack(data: bytes, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        if not data:
            # A tree without files has no archive to unpack: the export is that empty tree.
            return
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(target, filter="data")
