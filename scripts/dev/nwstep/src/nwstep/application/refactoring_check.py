"""The refactor receipt: behaviour-preserving refactor commits touch no test file, and the same check command exits 0
on each commit's parent and on the commit itself. Two commit fields share it: `refactor_commits` (craft) comes before
the feature commits, `post_refactor_commits` (the refactor step) comes after them.

Whether a prefactoring refactor is needed is the design's decision (`prefactoring`, yes or no); the recorder enforces that
craft names refactor commits exactly when the decision is yes. This class reads what git says about the commits
and runs the check on their trees; the receipt it returns is stored in the record and shown in the brief.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nwstep.domain.baseline import Baseline
from nwstep.domain.document_paths import is_document_only
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.journal import Journal
from nwstep.domain.step import Step
from nwstep.infrastructure.command_runner import CommandRunner
from nwstep.infrastructure.git_diff import GitDiffError
from nwstep.infrastructure.git_refs import GitRefs
from nwstep.infrastructure.workspace import Workspace


@dataclass(frozen=True)
class _Pairing:
    """A commit field, the check that runs on its commits, and whether those commits precede the feature commits."""

    commits: str
    check: str
    before_feature: bool


PAIRINGS = (
    _Pairing("refactor_commits", "refactor_check", before_feature=True),
    _Pairing("post_refactor_commits", "post_refactor_check", before_feature=False),
)


class Refactoring:
    def __init__(
        self, runner: CommandRunner, workspace: Workspace, baseline: Baseline
    ) -> None:
        self._runner = runner
        self._workspace = workspace
        self._baseline = baseline

    def check_pairing(
        self,
        step: Step,
        values: dict[str, Any],
        commands: list[tuple[Field, list[str]]],
    ) -> None:
        """Refactor commits and their check are given together: neither one is accepted alone."""
        given = {field.name for field, _argv in commands}
        for pairing in PAIRINGS:
            commits = step.field(pairing.commits)
            if commits is None:
                continue
            has_check = pairing.check in given
            if pairing.commits in values and not has_check:
                raise commits.refuse(
                    f"'{pairing.commits}' names refactor commits but no refactor check command is given",
                    fault=Fault.MISSING,
                )
            if has_check and pairing.commits not in values:
                raise commits.refuse(
                    f"the refactor check command needs '{pairing.commits}' given in the same record",
                    fault=Fault.MISSING,
                )

    def receipts(
        self,
        field: Field,
        argv: list[str],
        values: dict[str, Any],
        root: Path,
        journal: Journal,
    ) -> dict[str, object]:
        """The check run on the parent and on each refactor commit; every run must exit 0 on both."""
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            raise field.refuse(
                f"'{field.name}' cannot be checked against git history: {reason}",
                fault=Fault.COMMAND,
            )
        git = GitRefs(str(self._baseline.top), str(self._baseline.sha))
        pairing = self._pairing_of(field)
        commits = self._ordered(
            field, git, values.get(pairing.commits) or [], pairing.before_feature
        )
        if not pairing.before_feature:
            self._refuse_prefactored(field, commits, journal)
        receipts: list[dict[str, object]] = []
        for commit in commits:
            receipts.append(self._receipt(field, git, commit, argv))
        return {"commits": receipts}

    def _ordered(
        self,
        field: Field,
        git: GitRefs,
        revisions: list[str],
        before_feature: bool,
    ) -> list[str]:
        resolved: list[str] = []
        for revision in revisions:
            commit = git.resolve(str(revision))
            if commit is None:
                raise field.refuse(
                    f"'{revision}' names no commit of the repository",
                    fault=Fault.COMMAND,
                )
            resolved.append(commit)
        try:
            history = git.commits()
            code = (
                []
                if before_feature
                else [
                    commit
                    for commit in history
                    if not is_document_only(git.files(commit))
                ]
            )
        except GitDiffError as error:
            raise field.refuse(
                f"'{field.name}' cannot read the commits from BASE: {error}",
                fault=Fault.COMMAND,
            ) from None
        if before_feature:
            edge = history[: len(resolved)]
            if edge != resolved:
                raise field.refuse(
                    "refactor commits must be the first commits from BASE to HEAD, oldest first, before any feature commit; "
                    f"the history starts with {', '.join(commit[:12] for commit in edge) or 'nothing'}",
                    fault=Fault.COMMAND,
                )
        else:
            edge = code[-len(resolved) :] if resolved else []
            if edge != resolved:
                raise field.refuse(
                    "post-feature refactor commits must be the last commits from BASE to HEAD, oldest first, after every feature commit; "
                    f"the history ends with {', '.join(commit[:12] for commit in edge) or 'nothing'}",
                    fault=Fault.COMMAND,
                )
        return resolved

    @staticmethod
    def _pairing_of(check: Field) -> _Pairing:
        return next(pairing for pairing in PAIRINGS if pairing.check == check.name)

    @staticmethod
    def _refuse_prefactored(field: Field, commits: list[str], journal: Journal) -> None:
        """A commit refactored after the feature is not one that craft already named as a prefactoring commit."""
        before = next(pairing for pairing in PAIRINGS if pairing.before_feature)
        prefactored = {
            receipt["commit"]
            for record in journal.records
            for receipt in (record.values.get(before.check) or {}).get("commits", [])
        }
        shared = [commit for commit in commits if commit in prefactored]
        if shared:
            raise field.refuse(
                f"refactor commit {shared[0][:12]} is already a prefactoring commit in '{before.commits}': "
                "a commit is refactored once, before the feature commits or after them",
                fault=Fault.COMMAND,
            )

    def _receipt(
        self, field: Field, git: GitRefs, commit: str, argv: list[str]
    ) -> dict[str, object]:
        try:
            parent = git.parent(commit)
            files = git.files(commit)
        except GitDiffError as error:
            raise field.refuse(
                f"'{field.name}' cannot read {commit[:12]}: {error}",
                fault=Fault.COMMAND,
            ) from None
        if parent is None:
            raise field.refuse(
                f"refactor commit {commit[:12]} is a root commit: it has no pre-change tree to compare with",
                fault=Fault.COMMAND,
            )
        tests = [name for name in files if self._is_test(name)]
        if tests:
            raise field.refuse(
                f"refactor commit {commit[:12]} edits test files ({', '.join(tests)}): a behaviour-preserving refactor leaves the oracle unchanged",
                fault=Fault.COMMAND,
            )
        before = self._run_on(field, git, parent, "before", commit, argv)
        after = self._run_on(field, git, commit, "after", commit, argv)
        if before["exit_code"] != 0 or after["exit_code"] != 0:
            raise field.refuse(
                f"refactor commit {commit[:12]}: the check exited {before['exit_code']} before and "
                f"{after['exit_code']} after; a refactor holds the same tests green before and after",
                fault=Fault.COMMAND,
            )
        return {
            "commit": commit,
            "parent": parent,
            "subject": git.subject(commit),
            "before": before,
            "after": after,
        }

    def _run_on(
        self,
        field: Field,
        git: GitRefs,
        tree: str,
        label: str,
        commit: str,
        argv: list[str],
    ) -> dict[str, Any]:
        target = self._workspace.directory / "refactor" / f"{commit[:12]}-{label}"
        try:
            directory = git.export(tree, target)
        except GitDiffError as error:
            raise field.refuse(
                f"'{field.name}' cannot export {tree[:12]}: {error}",
                fault=Fault.COMMAND,
            ) from None
        return dict(self._runner.run(argv, directory).as_value())

    @staticmethod
    def _is_test(path: str) -> bool:
        pure = Path(path)
        return pure.suffix == ".py" and (
            pure.name.startswith("test_") or "tests" in pure.parts
        )
