"""Command-line adapter: parses arguments, calls the application and prints WHAT, WHY and HOW on refusal."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import ClassVar

from nwexpress.application import jev_protocol, refactor_currency, review_lines, rework
from nwexpress.application.answer_recorder import AnswerRecorder
from nwexpress.application.briefer import Briefer
from nwexpress.application.commit_hooks import HookReport, ensure_hooks
from nwexpress.application.delivery_root import require_delivery_root
from nwexpress.application.delivery_worktree import make_delivery_worktree
from nwexpress.application.feature_publication import FeaturePlan, FeaturePublication
from nwexpress.application.how_line import HowLine
from nwexpress.application.initializer import Initializer
from nwexpress.application.next_block import NextKind, next_block, next_state
from nwexpress.application.progress import Progress
from nwexpress.application.prompt import Prompt
from nwexpress.application.reclaim import reclaim_delivery
from nwexpress.application.request_writer import RequestWriter
from nwexpress.application.recorded import Recorded
from nwexpress.application.recorder import Recorder
from nwexpress.application.step_status import StepStatus
from nwexpress.application.storage_guard import admit_directory
from nwexpress.domain import examine_level, review, run_mode
from nwexpress.domain.baseline import Baseline
from nwexpress.domain.commit_hooks import HookOutcome
from nwexpress.domain.feature_id import FeatureId
from nwexpress.domain.jev_consent import JevConsent
from nwexpress.domain.journal import Journal
from nwexpress.domain.kit import UnknownKit, compare_trees
from nwexpress.domain.person_answer import Pause
from nwexpress.domain.refusal import Refusal
from nwexpress.domain.request_sentences import RequestSentences
from nwexpress.domain.retired_schema import is_retired_name, retired_refusal
from nwexpress.domain.run_mode import CHOICES
from nwexpress.domain.schema import Schema
from nwexpress.domain.request_sections import RequestSections
from nwexpress.domain.size import Size
from nwexpress.domain.size_declaration import SizeDeclaration
from nwexpress.domain.step import Step
from nwexpress.infrastructure import consent_tiers, examine_level_tiers, review_store
from nwexpress.infrastructure.baseline_store import BaselineStore
from nwexpress.infrastructure.checkout_commit import CheckoutCommit
from nwexpress.infrastructure.command_runner import CommandRunner
from nwexpress.infrastructure.configuration_files import read_tiers
from nwexpress.infrastructure.current_schema_reader import shipped_current_schema
from nwexpress.infrastructure.request_files import RequestFiles
from nwexpress.infrastructure.examine_level_binding import ExamineLevelBinding
from nwexpress.infrastructure.feature_publisher import FeaturePublisher
from nwexpress.infrastructure.section_reader import SectionReader
from nwexpress.infrastructure.feature_store import DeclaredFeature, FeatureStore
from nwexpress.infrastructure.git_refs import GitRefs
from nwexpress.infrastructure.invocation_line import InvocationLine
from nwexpress.infrastructure.jsonl_journal import JsonlJournal
from nwexpress.infrastructure.kit_store import KitStore
from nwexpress.infrastructure.package_paths import PackagePaths
from nwexpress.infrastructure.person_answer_store import PersonAnswerStore
from nwexpress.infrastructure.rebuildable_caches import load_cache_names
from nwexpress.infrastructure.record_arguments import RecordArguments
from nwexpress.infrastructure.refusing_parser import RefusingParser
from nwexpress.infrastructure.size_store import SizeStore
from nwexpress.infrastructure.skill_tree_reader import SkillTreeReader
from nwexpress.infrastructure.skills_root import SkillsRoot
from nwexpress.infrastructure.storage_settings import read_storage_policy
from nwexpress.infrastructure.template_manifest_reader import read_template_manifest
from nwexpress.infrastructure.toml_schema_reader import TomlSchemaReader
from nwexpress.infrastructure.workspace import Workspace
from nwexpress.infrastructure.workspace_mode import WorkspaceMode


BRIEF_KINDS = ("summary", "decisions", "trace")

SHARED_INSTALL_OUTCOMES = (HookOutcome.INSTALLED, HookOutcome.INSTALLED_KEEPING_FOREIGN)
HOOK_STATUS: dict[HookOutcome, str] = {
    HookOutcome.ALREADY_INSTALLED: "hooks: {root} already has the commit-msg and pre-commit hooks",
    HookOutcome.INSTALLED: "hooks: installed the commit-msg and pre-commit hooks in {root}",
    HookOutcome.INSTALLED_KEEPING_FOREIGN: "hooks: installed the commit-msg and pre-commit hooks in {root}; a hook already there was moved to its .legacy name by pre-commit",
    HookOutcome.NOT_DECLARED: "WARNING: no commit hooks installed in {root}: it has no .pre-commit-config.yaml, so it declares no commit hooks and its commits are not checked by them",
    HookOutcome.GIT_UNAVAILABLE: "WARNING: no commit hooks checked in {root}: git cannot be run here, so no commit can be made from it in this environment",
    HookOutcome.OWN_HOOKS_PRESENT: "hooks: {root} already has its own commit hooks and no .pre-commit-config.yaml; they check its commits, and nwexpress installs none there",
    HookOutcome.IN_PLACE_HOOKS_PRESENT: "hooks: {root} already has its own commit hooks in {hooks_dir}; nothing was installed or moved",
}
WORKSPACE_ENVIRONMENT = "NWEXPRESS_HOME"
RECORD_USAGE = (
    "usage: nwexpress record STEP --workspace DIR --root DIR "
    "(--FIELD VALUE | --item FIELD=VALUE ...)"
)


class Cli:
    def __init__(self) -> None:
        self._how = HowLine()
        self._directory: Path | None = None

    def run(self, argv: list[str]) -> int:
        try:
            return self._dispatch(argv)
        except Refusal as refusal:
            self._report(
                refusal if refusal.how else refusal.with_how(self._status_how())
            )
            return 2
        except (
            Exception
        ) as error:  # the last line of defence: report the failure, never hide it
            self._report(
                Refusal(
                    what=f"unexpected failure: {error}",
                    why="the command stopped before finishing; a record is written only after every check has passed",
                    how=self._status_how(),
                )
            )
            return 1

    def _dispatch(self, argv: list[str]) -> int:
        if argv[:1] == ["record"]:
            if any(token in ("--help", "-h") for token in argv[1:]):
                return self._record_help(argv[1:])
            return self._record(argv[1:])
        arguments = self._parser().parse_args(argv)
        if arguments.command == "sentences":
            return self._sentences(arguments.file)
        if arguments.command == "kit":
            return self._kit_status()
        if arguments.command == "clone":
            return self._clone(arguments.source, arguments.base, arguments.dest)
        if arguments.command == "reclaim":
            return self._reclaim(arguments.workspace, arguments.trunk)
        directory = self._directory_of(arguments.workspace)
        # fmt: off
        if arguments.command == "init":
            return self._init(
                arguments.schema,
                directory,
                arguments.base,
                arguments.mode,
                arguments.skills,
            )
        # fmt: on
        if arguments.command == "request":
            return self._request(arguments, directory)
        workspace = self._initialized(directory)
        schema = TomlSchemaReader().read(workspace.schema_path)
        journal = JsonlJournal(workspace).snapshot()
        if arguments.command == "replay":
            return self._replay(workspace, arguments.root, schema, journal)
        if arguments.command == "prompt":
            return self._prompt(arguments, workspace, schema)
        if arguments.command in ("finding", "packet", "verdict", "withdraw"):
            return self._review(arguments, workspace)
        if arguments.command == "size":
            return self._size(arguments, workspace, schema)
        if arguments.command == "answer":
            return self._answer(arguments, workspace)
        if arguments.command == "next":
            return self._next(schema, journal, arguments.request, workspace)
        if arguments.command == "status":
            return self._status(workspace, schema, journal)
        if arguments.command == "feature":
            return self._feature(arguments, workspace)
        if arguments.command == "brief":
            briefer = Briefer(
                schema,
                BaselineStore(workspace).read(),
                KitStore(workspace).state(),
                review_store.read(workspace),
            )
            if arguments.publish and arguments.out:
                raise Refusal(
                    what="brief --publish and --out name two destinations",
                    why="one run writes one destination: the feature folder for --publish, or the directory named by --out",
                    how=self._how.command(
                        "brief", "--workspace", str(workspace.directory), "--publish"
                    ),
                )
            if arguments.publish:
                return self._publish(briefer, journal, workspace)
            if arguments.out:
                return self._write_briefs(briefer, journal, Path(arguments.out))
            if arguments.kind is None:
                return self._close(briefer, journal, workspace)
            print(briefer.render(arguments.kind, journal), end="")
            return 0
        print(json.dumps(journal.to_list(), indent=2, sort_keys=True))
        return 0

    BRIEF_FILES: ClassVar[dict[str, str]] = {
        "summary": "SUMMARY.md",
        "decisions": "DECISIONS.md",
        "trace": "TRACE.md",
    }

    @classmethod
    def _write_briefs(cls, briefer: Briefer, journal: Journal, target: Path) -> int:
        target.mkdir(parents=True, exist_ok=True)
        for kind, name in cls.BRIEF_FILES.items():
            (target / name).write_text(briefer.render(kind, journal), encoding="utf-8")
        print(f"wrote {', '.join(cls.BRIEF_FILES.values())} to {target}")
        return 0

    def _feature(self, arguments, workspace: Workspace) -> int:
        """Declares the feature id and the repository root its folder lies in; one declaration per workspace."""
        try:
            feature = FeatureId.of(arguments.id)
        except Refusal as refusal:
            raise refusal.with_how(
                self._how.command(
                    "feature",
                    "--workspace",
                    str(workspace.directory),
                    "--id",
                    "<feature-id>",
                )
            ) from None
        root = Path(arguments.root or Path.cwd()).resolve()
        store = FeatureStore(workspace)
        declared = store.current()
        if declared is not None and declared.feature != feature:
            raise Refusal(
                what=f"this workspace already declares the feature {declared.feature.text!r}, so it cannot declare {feature.text!r}",
                why="the feature folder of a run is fixed by its first declaration; a second folder would split the record of one delivery",
                how=self._how.command(
                    "init",
                    "--schema",
                    "<schema.toml>",
                    "--workspace",
                    "<new workspace directory>",
                ),
            )
        if declared is not None and declared.root != root:
            raise Refusal(
                what=f"this workspace already declares the feature {feature.text!r} in {declared.root}, so it cannot declare it in {root}",
                why="the feature folder of a run lies in the repository its first declaration names, and a second root would split the documents of one delivery between two repositories; another repository needs a workspace of its own, made with nwexpress init",
                how=self._how.command(
                    "feature",
                    "--workspace",
                    str(workspace.directory),
                    "--id",
                    feature.text,
                    "--root",
                    str(declared.root),
                ),
            )
        if declared is None:
            store.declare(DeclaredFeature(feature, root))
            print(f"feature: {feature.text}")
        else:
            print(
                f"feature: {feature.text} already declared in {declared.root}; nothing changed"
            )
        return 0

    def _close(self, briefer: Briefer, journal: Journal, workspace: Workspace) -> int:
        """The bare brief: prints the summary as before and, when a feature is declared, writes its documents too."""
        publication = self._plan_publication(briefer, journal, workspace)
        print(briefer.render("summary", journal), end="")
        if publication is not None:
            self._write_publication(*publication)
        return 0

    def _publish(self, briefer: Briefer, journal: Journal, workspace: Workspace) -> int:
        """Writes the feature documents into the declared feature folder; every refusal comes before the first write."""
        publication = self._plan_publication(briefer, journal, workspace)
        if publication is None:
            raise Refusal(
                what="no feature id is declared in this workspace",
                why="the feature documents are written into the feature folder named by the declared id, and no id is guessed from the request, the branch or the clone name",
                how=self._how.command(
                    "feature",
                    "--workspace",
                    str(workspace.directory),
                    "--id",
                    "<feature-id>",
                ),
            )
        self._write_publication(*publication)
        return 0

    @staticmethod
    def _plan_publication(
        briefer: Briefer, journal: Journal, workspace: Workspace
    ) -> tuple[Path, FeaturePlan] | None:
        """The declared repository root and the plan of the feature documents; None when no feature is declared."""
        declared = FeatureStore(workspace).current()
        if declared is None:
            return None
        plan = FeaturePublication.plan(
            declared.feature,
            read_tiers(declared.root, declared.feature.text, Path.home()),
            briefer,
            journal,
        )
        return declared.root, plan

    @staticmethod
    def _write_publication(root: Path, plan: FeaturePlan) -> None:
        for path in FeaturePublisher(root).publish(plan):
            print(f"wrote {path}", file=sys.stderr)

    def _parser(self) -> RefusingParser:
        parser = RefusingParser(
            prog="nwexpress", description="Record one step of a delivery at a time."
        )
        commands = parser.add_subparsers(
            dest="command", required=True, metavar="COMMAND"
        )
        init = commands.add_parser(
            "init",
            help="create a workspace from a schema and its pre-feature baseline; run it in a delivery clone made by nwexpress clone or in a git linked worktree",
        )
        init.add_argument(
            "--schema",
            help="the name of a shipped schema or the path of a schema file; without it the shipped current schema is used",
        )
        init.add_argument("--workspace")
        init.add_argument(
            "--mode",
            choices=CHOICES,
            help="record the run mode at init; a later prompt with the other mode is refused (default: the first prompt records it)",
        )
        init.add_argument(
            "--base",
            default="HEAD",
            metavar="REV",
            help="the pre-feature commit: its tree is exported into the workspace as a git repository holding one commit of it (default HEAD)",
        )
        init.add_argument(
            "--skills",
            metavar="DIR",
            help=f"copy the skills the run reads from DIR into the workspace kit (default: the skills of the checkout that holds this tool, {SkillsRoot.CHECKOUT})",
        )
        commands.add_parser(
            "record", help="record one step: nwexpress record STEP --FIELD VALUE"
        )
        sentences = commands.add_parser(
            "sentences", help="print the numbered sentences of a request file"
        )
        sentences.add_argument("--file", required=True)
        request = commands.add_parser(
            "request",
            help="write REQUEST.md in the workspace from the standing-block template and the sections given; refuses when a part is missing",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=(
                "Writes REQUEST.md in the workspace. The standing rules come from the one template file of the checkout;\n"
                "the sections come from the options. The first line is the card line the board reads.\n"
                "It checks that every card id is in board form, that the card, title, problem, acceptance and scratch folder\n"
                "are given, that each section file is readable text, that stdin is read by one section at most, and that an\n"
                "existing REQUEST.md is replaced only with --force.\n"
                "The verb cannot judge the quality of the sections; it checks that they are present and readable."
            ),
        )
        request.add_argument(
            "--workspace",
            help="the workspace folder the request is written into; created when missing (default: NWEXPRESS_HOME)",
        )
        request.add_argument(
            "--card",
            help="the card id or ids of the delivery, for example t-0556 or t-0554, t-0555; the first line of the request",
        )
        request.add_argument("--title", help="the title of the request, one line")
        request.add_argument(
            "--problem", help="file with the problem; - reads it from stdin"
        )
        request.add_argument(
            "--deliver",
            help="file with what to deliver, optional; - reads it from stdin",
        )
        request.add_argument(
            "--decisions",
            help="file with the owner's decisions, optional; - reads it from stdin",
        )
        request.add_argument(
            "--acceptance", help="file with the acceptance; - reads it from stdin"
        )
        request.add_argument(
            "--scratch",
            help="the scratch folder the executor may write under, for example /tmp/lane-7/scratch",
        )
        request.add_argument(
            "--force",
            action="store_true",
            help="replace a REQUEST.md that already exists in the workspace",
        )
        clone = commands.add_parser(
            "clone",
            help="make a delivery worktree: a git linked worktree on a new branch at the base commit, with the commit-msg and pre-commit hooks active and the trunk guard installed; refuses a RAM-backed or nearly full target",
            description=(
                "Makes the delivery as a git linked worktree, not a full clone: the worktree shares the repository's objects, "
                "its hook directory and its config. Its branch is nwexpress/<destination folder name>. The trunk guard refuses "
                "updates of lanes.trunk from a worktree: it stops ACCIDENTS only; a process that sets core.hooksPath or skips "
                "hooks is not stopped, and the recovery is the reflog of the trunk and the single-writer rule. Storage keys "
                "(min_free_gib, forbidden_filesystems, forbidden_sources) live under nwexpress storage in .nwave/config.json; "
                "NWEXPRESS_MIN_FREE_GIB overrides the threshold for one command."
            ),
        )
        clone.add_argument(
            "--source",
            required=True,
            help="the path of a git checkout on this machine; the worktree is added to its repository",
        )
        clone.add_argument(
            "--base",
            required=True,
            help="the revision the delivery starts at, declared by you and never guessed; for example HEAD",
        )
        clone.add_argument(
            "--dest", required=True, help="the new folder the worktree is made in"
        )
        reclaim = commands.add_parser(
            "reclaim",
            help="remove one finished delivery: its worktree, its branch and its workspace folder, only when nothing in it would be lost",
            description=(
                "Removes one delivery. Refuses, naming every blocker with what, why and how, when the worktree holds uncommitted "
                "or untracked files, when a commit of its branch is not integrated into the trunk by patch equivalence "
                "(git cherry; a cherry-picked commit counts as integrated), when a merge commit is not held by the trunk, or when "
                "an ignored path is not a rebuildable cache (the closed list of cache folder names the tool ships). A clean, "
                "integrated delivery is removed completely; the repository's object store is not touched. The trunk is an argument: "
                "reclaim never assumes it."
            ),
        )
        reclaim.add_argument(
            "--workspace", required=True, help="the workspace folder of one delivery"
        )
        reclaim.add_argument(
            "--trunk",
            required=True,
            help="the trunk branch that the delivery must be integrated into, for example master",
        )
        kit = commands.add_parser(
            "kit", help="compare the installed skill copies with the checkout"
        )
        kit_commands = kit.add_subparsers(
            dest="kit_command", required=True, metavar="SUBCOMMAND"
        )
        kit_commands.add_parser(
            "status",
            help="compare the installed skill copies with the checkout",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=(
                f"Compares the installed skill copies in\n  {SkillsRoot.INSTALLED}\n"
                f"with the skills of the checkout in\n  {SkillsRoot.CHECKOUT}\n"
                "Prints each file that differs, is missing from the installed copies or\n"
                "exists only in them, then a verdict.\n"
                "Exit 0 when the two folders are identical, exit 1 when they differ,\n"
                "exit 2 when either folder cannot be read."
            ),
        )
        prompt = commands.add_parser(
            "prompt",
            help="print the express mode prompt for a workspace, a clone and a request",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=(
                "Prints the executor prompt for the workspace, the clone and the request.\n"
                "The printed text is given to the executor UNCHANGED, as one block.\n"
                "Giving the executor the path of the file that holds the printed text is allowed,\n"
                "because the bytes stay identical. Any other change is not allowed: no summary,\n"
                "no shortened line, no replaced block and no added note, because the executor's\n"
                "work and its quality can be relied on only for the exact text the template renders."
            ),
        )
        prompt.add_argument("--workspace")
        prompt.add_argument(
            "--root", required=True, help="the clone the executor works in"
        )
        prompt.add_argument(
            "--mode",
            choices=CHOICES,
            help="auto prints the plain delivery prompt; interactive adds the interactive protocol that stops for the owner",
        )
        prompt.add_argument(
            "--request", required=True, help="the request file, read verbatim"
        )
        prompt.add_argument(
            "--authority", help="authority the executor reads first, as text"
        )
        prompt.add_argument("--baseline", help="known baseline failures, as text")
        prompt.add_argument(
            "--template",
            default=None,
            help="shipped template name (a file in templates/ without .tmpl); the default is the manifest's default template",
        )
        prompt.add_argument(
            "--jev",
            help='Jev consent for this run: authorized or unauthorized; optional, and authorized when neither the flag nor a configuration file declares "jev" (repository .nwave/config.json over global ~/.nwave/config.json); the flag wins, and every declared value must be one of the two',
        )
        next_step = commands.add_parser("next", help="print the next step to record")
        next_step.add_argument("--workspace")
        size_command = commands.add_parser(
            "size",
            help="declare the delivery's size, S, M or L: the steps it makes due; lowering needs the owner's note and id",
        )
        size_command.add_argument("--workspace")
        size_command.add_argument("--size", required=True, help="S, M or L")
        size_command.add_argument(
            "--why", required=True, help="one sentence: why this size"
        )
        size_command.add_argument(
            "--owner-note", help="the owner's note; required to lower the size"
        )
        size_command.add_argument(
            "--author", help="the owner's id; required to lower the size"
        )
        answer_command = commands.add_parser(
            "answer",
            help="answer the question that interactive mode asks after a pause step",
        )
        answer_command.add_argument("--workspace")
        answer_command.add_argument(
            "--author", required=True, help="the id of the person who answers"
        )
        feature_command = commands.add_parser(
            "feature",
            help="declare the feature whose folder the feature documents go to: its id and the repository root it lies in; one declaration per workspace, and the same id and root may be given again",
        )
        feature_command.add_argument("--workspace")
        feature_command.add_argument(
            "--id", required=True, help="the feature id: the feature folder name"
        )
        feature_command.add_argument(
            "--root",
            help="the repository the feature folder lies in (default: the current directory)",
        )
        answer_command.add_argument(
            "--text", required=True, help="the answer, in the person's words"
        )
        replay = commands.add_parser(
            "replay",
            help="record again every stale step, in schema order, from the submission its latest record kept",
        )
        replay.add_argument("--workspace")
        replay.add_argument("--root", help="the clone the steps run in (default: cwd)")
        finding = commands.add_parser(
            "finding",
            help="record a review finding with the case that proves it: the tool runs the case and it must fail on the candidate",
        )
        finding.add_argument("--workspace")
        finding.add_argument(
            "--root", help="the project the case runs in (default: cwd)"
        )
        finding.add_argument(
            "--author", required=True, help="who wrote the finding, as an id"
        )
        finding.add_argument("--text", required=True, help="what the finding says")
        finding.add_argument(
            "--red",
            required=True,
            help="the case that proves the finding: one command, run without a shell, that fails now and must pass after the fix",
        )
        packet = commands.add_parser(
            "packet",
            help="print the reviewer's packet and freeze the identity of the candidate it names",
        )
        packet.add_argument("--workspace")
        packet.add_argument(
            "--root", help="the project whose candidate is frozen (default: cwd)"
        )
        verdict = commands.add_parser(
            "verdict",
            help="record a reviewer's verdict for the candidate the packet froze; a verdict for a changed candidate is refused",
        )
        verdict.add_argument("--workspace")
        verdict.add_argument(
            "--root", help="the project whose candidate was judged (default: cwd)"
        )
        verdict.add_argument(
            "--reviewer", required=True, help="who gives the verdict, as an id"
        )
        verdict.add_argument(
            "--candidate",
            required=True,
            help="the candidate identity the reviewer judged, as the packet prints it",
        )
        verdict.add_argument(
            "--outcome", required=True, help="the verdict: accepted or rejected"
        )
        withdraw = commands.add_parser(
            "withdraw",
            help="withdraw a recorded finding whose case was wrong, with its reason on record: its case is no longer run and it no longer holds the packet; only its author may withdraw it",
        )
        withdraw.add_argument("--workspace")
        withdraw.add_argument(
            "--root", help="the project the withdrawal is made in (default: cwd)"
        )
        withdraw.add_argument(
            "--finding",
            required=True,
            help="the finding to withdraw, by the identifier the status prints, such as F1",
        )
        withdraw.add_argument(
            "--author", required=True, help="who wrote the finding, as an id"
        )
        withdraw.add_argument(
            "--reason",
            help="why the case was wrong: a withdrawal needs a reason that is not blank",
        )
        next_step.add_argument(
            "--request",
            help="the request file; its numbered sentences are shown with a step that maps them",
        )
        for name, summary in (
            ("status", "print every step with its revisions"),
            ("export", "print the journal as a JSON array"),
        ):
            commands.add_parser(name, help=summary).add_argument("--workspace")
        brief = commands.add_parser(
            "brief",
            help="render Markdown from the journal; the bare form also writes the feature documents when a feature is declared",
        )
        brief.add_argument("--workspace")
        brief.add_argument(
            "--kind",
            choices=BRIEF_KINDS,
            help="print this document (default: summary); a named kind only prints and writes no feature documents",
        )
        brief.add_argument(
            "--out",
            help="write SUMMARY.md, DECISIONS.md and TRACE.md into this directory (inside the clone) instead of printing one",
        )
        brief.add_argument(
            "--publish",
            action="store_true",
            help="write brief.md, architecture.md, acceptance.md and TRACE.md into the feature folder the workspace declares, under the repository's configured feature directory; refused without a declared feature id",
        )
        return parser

    def _directory_of(self, option: str | None) -> Path:
        value = option or os.environ.get(WORKSPACE_ENVIRONMENT)
        if not value:
            raise Refusal(
                what="no workspace given",
                why=f"every command reads or writes one workspace directory; pass --workspace or set {WORKSPACE_ENVIRONMENT}",
                how=self._how.command("status", "--workspace", "<workspace directory>"),
            )
        self._directory = Path(value).resolve()
        return self._directory

    def _initialized(self, directory: Path) -> Workspace:
        workspace = Workspace(directory)
        if not workspace.is_initialized():
            raise Refusal(
                what=f"workspace {directory} is not initialized",
                why="init copies the schema in and opens the journal; nothing can be recorded before that",
                how=self._how.command(
                    "init", "--schema", "<schema.toml>", "--workspace", str(directory)
                ),
            )
        return workspace

    @staticmethod
    def _schema_source(value: str | None) -> Path:
        """No value is the shipped current schema; a shipped schema named without a folder (its file name, with or without the extension) is that file; any other value is a path."""
        if value is None:
            return shipped_current_schema()
        if "/" not in value and "\\" not in value:
            name = value if value.endswith(".toml") else f"{value}.toml"
            if (PackagePaths.SCHEMAS / name).is_file():
                return PackagePaths.SCHEMAS / name
        return Path(value).resolve()

    # fmt: off
    def _init(
        self,
        schema_path: str | None,
        directory: Path,
        base: str,
        mode: str | None,
        skills: str | None,
    ) -> int:
        initializer = Initializer(self._how)
        if schema_path is not None and is_retired_name(schema_path):
            current = shipped_current_schema().name
            command = self._how.command("init", "--workspace", str(directory))
            raise retired_refusal(
                schema_path,
                how=f"{command}  # creates the workspace from the shipped current schema {current}",
            )
        schema_source = self._schema_source(schema_path)
        workspace = Workspace(directory)
        self._admit_root(Path.cwd(), "init")
        policy = read_storage_policy(Path.cwd(), Path.home(), dict(os.environ))
        for warning in admit_directory(
            directory,
            policy=policy,
            command="init",
            configuration=Path.cwd() / ".nwave" / "config.json",
        ):
            print(warning, file=sys.stderr)
        prepared = initializer.prepare(
            schema_source,
            workspace,
            skills_source=Path(skills).resolve() if skills else SkillsRoot.CHECKOUT,
            commit=CheckoutCommit.read(),
        )
        self._guard_hooks(Path.cwd())
        created = initializer.write(
            prepared,
            schema_source,
            workspace,
            Path.cwd(),
            base,
            mode=mode,
        )
        print(f"initialized workspace {directory} with {len(created.steps)} steps")
        self._report_baseline(BaselineStore(Workspace(directory)).read())
        return 0
    # fmt: on

    @staticmethod
    def _report_baseline(baseline: Baseline) -> None:
        if baseline.is_available:
            print(
                f"baseline: pre-feature base {baseline.sha} recorded for {baseline.top}; its tree is read from git while a RED or probe run needs it"
            )
            return
        print(
            f"WARNING: no pre-feature baseline: {baseline.reason}; every probe case will be recorded as could-not-verify against it, not as differing",
            file=sys.stderr,
        )

    def _record(self, tokens: list[str]) -> int:
        arguments = RecordArguments(tokens)
        workspace = self._initialized(self._directory_of(arguments.workspace))
        if arguments.step is None:
            raise Refusal(
                what="record needs a step id as its first argument",
                why="a record is one named step with its fields",
                how=self._how.command("next", "--workspace", str(workspace.directory)),
            )
        root = Path(arguments.root).resolve() if arguments.root else Path.cwd()
        self._admit_root(root, "record", workspace)
        result = Recorder(workspace).record(arguments.step, arguments.submission, root)
        print(f"recorded {result.record.step} revision {result.record.revision}")
        self._print_closed(result)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        self._print_stale_names(result.stale)
        for replayed in result.replayed:
            print(
                f"replayed {replayed.record.step} revision {replayed.record.revision}"
            )
            self._print_closed(replayed)
            for warning in replayed.warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
        last = result.replayed[-1] if result.replayed else result
        self._print_next(last, workspace)
        return 0

    def _record_help(self, tokens: list[str]) -> int:
        """Help never refuses: it prints the usage, and the schema's steps or the named step when a workspace is known."""
        print(RECORD_USAGE)
        directory = self._option_value(tokens, "--workspace") or os.environ.get(
            WORKSPACE_ENVIRONMENT
        )
        if not directory:
            print(
                "give --workspace DIR (or set NWEXPRESS_HOME) to list the steps and their fields"
            )
            return 0
        workspace = Workspace(Path(directory).resolve())
        if not workspace.is_initialized():
            print(f"workspace {workspace.directory} is not initialized: run init first")
            return 0
        schema = TomlSchemaReader().read(workspace.schema_path)
        step_id = tokens[0] if tokens and not tokens[0].startswith("-") else None
        if step_id is None:
            print(f"steps: {', '.join(schema.ids)}")
            return 0
        step = schema.find(step_id)
        if step is None:
            print(f"unknown step '{step_id}'; steps: {', '.join(schema.ids)}")
            return 0
        print(self._describe(step, None, self._help_skills_root(workspace)))
        return 0

    @staticmethod
    def _help_skills_root(workspace: Workspace) -> Path | None:
        """The skill folder the help names, or None with a warning when the kit record cannot be read: help never refuses."""
        try:
            return KitStore(workspace).skills_root()
        except Refusal as refusal:
            print(
                f"WARNING: skill paths are not shown: {refusal.what}", file=sys.stderr
            )
            return None

    @staticmethod
    def _option_value(tokens: list[str], option: str) -> str | None:
        if option in tokens and tokens.index(option) + 1 < len(tokens):
            return tokens[tokens.index(option) + 1]
        return None

    def _sentences(self, file: str) -> int:
        for line in self._read_sentences(file).to_values():
            print(line)
        return 0

    def _request(self, arguments, directory: Path) -> int:
        how = self._how
        read = SectionReader(how, str(directory)).read(
            {
                "problem": arguments.problem,
                "deliver": arguments.deliver,
                "decisions": arguments.decisions,
                "acceptance": arguments.acceptance,
            }
        )
        sections = RequestSections(
            title=arguments.title,
            problem=read["problem"],
            deliver=read["deliver"],
            decisions=read["decisions"],
            acceptance=read["acceptance"],
            scratch=arguments.scratch,
        )
        files = RequestFiles()
        path = RequestFiles.path_of(directory)
        text = RequestWriter(how).plan(
            card=arguments.card,
            sections=sections,
            template=files.read_template(),
            request_path=str(path),
            request_exists=path.is_file(),
            force=arguments.force,
        )
        written = RequestFiles.write(directory, text)
        sentences = len(RequestSentences.from_text(text).sentences)
        print(f"wrote {written} with {sentences} numbered sentences")
        print(
            f"RED evidence: the oracle step keeps its RED values in {directory / 'journal.jsonl'}; "
            "the raw report is removed when the step is recorded, so the committed record names the base and candidate commits"
        )
        return 0

    def _kit_status(self) -> int:
        installed = SkillsRoot.INSTALLED
        checkout = SkillsRoot.CHECKOUT
        try:
            installed_files = (
                SkillTreeReader().read(installed) if installed.is_dir() else {}
            )
            checkout_files = SkillTreeReader().read(checkout)
        except Refusal as refusal:
            raise refusal.with_how(self._how.command("kit", "status", "--help"))
        comparison = compare_trees(installed_files, checkout_files)
        print(f"installed: {installed}")
        print(f"checkout: {checkout}")
        for label, names in (
            ("differs", comparison.differs),
            ("missing", comparison.missing),
            ("extra", comparison.extra),
        ):
            for name in names:
                print(f"{label}: {name}")
        print(f"verdict: {'match' if comparison.same else 'differ'}")
        return 0 if comparison.same else 1

    def _read_sentences(self, file: str) -> RequestSentences:
        try:
            text = Path(file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(
                what=f"{file} cannot be read as text: {error}",
                why="the sentences of a request are numbered from a text file",
                how=self._how.command("sentences", "--file", "<request file>"),
            ) from None
        sentences = RequestSentences.from_text(text)
        if not sentences.sentences:
            raise Refusal(
                what=f"{file} holds no sentence",
                why="a request needs at least one sentence for its sentence map to cover",
                how=self._how.command("sentences", "--file", "<request file>"),
            )
        return sentences

    def _prompt(self, arguments, workspace: Workspace, schema: Schema) -> int:
        template = self._template_file(arguments, workspace)
        root = Path(arguments.root).resolve()
        self._admit_root(root, "prompt", workspace)
        consent = self._consent(arguments.jev, root)
        examine = ExamineLevelBinding(workspace.directory).bound_to(
            self._examine_level(root)
        )
        requested = run_mode.requested(arguments.mode)
        request = self._read_prompt_request(arguments.request)
        self._guard_hooks(root)
        recorded = WorkspaceMode(workspace).read()
        mode = run_mode.bind(recorded, requested)
        prompt = Prompt(template, InvocationLine().text())
        text = prompt.render(
            root=root,
            workspace=workspace.directory,
            steps=tuple(step.id for step in schema.steps),
            request=request,
            authority=arguments.authority,
            baseline=arguments.baseline,
            mode=mode,
            consent=consent,
            skill=PackagePaths.jev_skill(),
            pauses=schema.has_pauses,
        )
        # Every refusal that can happen has happened: only now the workspace is written.
        if mode != recorded:
            WorkspaceMode(workspace).write(mode)
        ExamineLevelBinding(workspace.directory).record(examine)
        print(text + examine.section(), end="")
        return 0

    def _template_file(self, arguments, workspace: Workspace) -> Path:
        """The shipped template the prompt renders; any other name is refused before anything is read or written."""
        manifest = read_template_manifest(PackagePaths.MANIFEST)
        name = arguments.template or manifest.default
        listed = [
            template
            for template in manifest.in_use(PackagePaths.shipped_schema_versions())
            if (PackagePaths.TEMPLATES / f"{template}.tmpl").is_file()
        ]
        if name in listed:
            return PackagePaths.TEMPLATES / f"{name}.tmpl"
        how = self._how.command(
            "prompt",
            "--workspace",
            str(workspace.directory),
            "--root",
            arguments.root,
            "--request",
            arguments.request,
            "--mode",
            arguments.mode or "auto",
            "--template",
            manifest.default,
        )
        if manifest.is_retired(name):
            raise Refusal(
                what=f"the template {name} is no longer distributed",
                why=f"no shipped schema uses it: the shipped schemas are {PackagePaths.shipped_schemas()} and none names a template; {name} was removed from the checkout and git history keeps it; the shipped templates are {listed}",
                how=how,
            )
        raise Refusal(
            what=f"no template named {name!r}: the shipped templates are {listed}",
            why="the prompt renders one shipped template, and a name that is not one of them has no text to render",
            how=how,
        )

    @staticmethod
    def _examine_level(root: Path) -> examine_level.Resolved:
        """Resolved before anything is written, so a refused level leaves the workspace as it was."""
        return examine_level.resolve(
            examine_level_tiers.read_declared(root / ".nwave" / "config.json"),
            examine_level_tiers.read_declared(Path.home() / ".nwave" / "config.json"),
        )

    @staticmethod
    def _consent(flag: str | None, root: Path) -> JevConsent:
        """Resolved before anything is written, so a refused consent leaves the workspace as it was."""
        repository = root / ".nwave" / "config.json"
        global_config = Path.home() / ".nwave" / "config.json"
        return jev_protocol.resolve(
            (
                jev_protocol.Declaration("--jev", () if flag is None else (flag,)),
                jev_protocol.Declaration(
                    str(repository), consent_tiers.read_declared(repository)
                ),
                jev_protocol.Declaration(
                    str(global_config), consent_tiers.read_declared(global_config)
                ),
            )
        )

    def _read_prompt_request(self, file: str) -> str:
        try:
            return Path(file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(
                what=f"{file} cannot be read as text: {error}",
                why="the prompt carries the request verbatim, so the request file must be readable text",
                how=self._how.command(
                    "prompt",
                    "--workspace",
                    str(self._directory),
                    "--root",
                    "<clone>",
                    "--request",
                    "<request file>",
                ),
            ) from None

    def _clone(self, source: str, base: str, dest: str) -> int:
        made = make_delivery_worktree(
            source,
            base,
            Path(dest),
            environ=dict(os.environ),
            home=Path.home(),
        )
        for warning in made.warnings:
            print(warning, file=sys.stderr)
        print(
            f"created delivery worktree {made.dest} on branch {made.branch} at {made.commit}"
        )
        self._report_hooks(made.dest, made.hooks)
        return 0

    def _reclaim(self, workspace: str, trunk: str) -> int:
        outcome = reclaim_delivery(
            Path(workspace).resolve(), trunk, load_cache_names(), Path.home()
        )
        for refusal in outcome.refusals:
            self._report(refusal)
        if outcome.refusals:
            return 2
        for removed in outcome.removed:
            print(f"removed {removed}")
        return 0

    def _admit_root(
        self, root: Path, command: str, workspace: Workspace | None = None
    ) -> None:
        """Refuses a root the delivery may not write in, before any write, hook installation or record."""
        anchor = None if workspace is None else BaselineStore(workspace).read().top
        require_delivery_root(root, anchor=anchor, command=command)

    def _guard_hooks(self, root: Path) -> None:
        self._report_hooks(root, ensure_hooks(root))

    @staticmethod
    def _report_hooks(root: Path, report: HookReport) -> None:
        text = HOOK_STATUS.get(report.outcome)
        if text is None:
            return
        line = text.format(root=root, hooks_dir=report.hooks_dir)
        if report.shared and report.outcome in SHARED_INSTALL_OUTCOMES:
            line += (
                f"; the hook directory {report.hooks_dir} is shared with the other worktrees of this repository, "
                f"and these files in it changed: {', '.join(report.changed)}"
            )
        print(line, file=sys.stderr)

    def _replay(
        self,
        workspace: Workspace,
        root_option: str | None,
        schema: Schema,
        journal: Journal,
    ) -> int:
        root = Path(root_option).resolve() if root_option else Path.cwd()
        self._admit_root(root, "replay", workspace)
        replayed = Recorder(workspace).replay(root)
        held = rework.stale_steps(
            schema, JsonlJournal(workspace).snapshot(), review_store.read(workspace)
        )
        if not replayed:
            print(
                "no stale step can be replayed from its kept submission"
                if held
                else "nothing is stale: no step needs replaying"
            )
            self._print_held(held)
            progress = Progress(schema, self._declared_size(schema, workspace))
            self._print_block(
                progress.next_ready(journal), progress.remaining(journal), workspace
            )
            return 0
        for result in replayed:
            print(f"replayed {result.record.step} revision {result.record.revision}")
            self._print_closed(result)
            for warning in result.warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
        self._print_held(held)
        self._print_next(replayed[-1], workspace)
        return 0

    @staticmethod
    def _print_held(held: tuple[str, ...]) -> None:
        """The stale steps a replay leaves alone: a verdict, and what relies on one."""
        if held:
            print(f"not replayed ({review_lines.VERDICT_STEP_NOTE}): {', '.join(held)}")

    @staticmethod
    def _print_closed(result: Recorded) -> None:
        for receipt in result.record.values.get(review.CLOSED_KEY, ()):
            print(
                f"finding {receipt['finding']}: its case passed; closed by "
                f"{result.record.step} revision {result.record.revision}"
            )

    def _review(self, arguments, workspace: Workspace) -> int:
        root = Path(arguments.root).resolve() if arguments.root else Path.cwd()
        self._admit_root(root, arguments.command, workspace)
        desk = rework.Desk(workspace, root, self._how)
        if arguments.command == "finding":
            return self._finding(desk, arguments)
        if arguments.command == "packet":
            return self._packet(desk)
        if arguments.command == "withdraw":
            return self._withdraw(desk, arguments)
        return self._verdict(desk, arguments)

    @staticmethod
    def _withdraw(desk: rework.Desk, arguments) -> int:
        report = rework.report_withdrawal(
            desk, arguments.finding, arguments.author, arguments.reason
        )
        withdrawal = report.withdrawal
        print(
            f"withdrew finding {withdrawal.identifier} by {withdrawal.author}: "
            "its case is no longer run and it no longer holds the packet"
        )
        line = review_lines.stale_line(report.stale, report.waiting)
        if line is not None:
            print(line)
        return 0

    @staticmethod
    def _finding(desk: rework.Desk, arguments) -> int:
        report = rework.report_finding(
            desk, CommandRunner(), arguments.author, arguments.text, arguments.red
        )
        finding = report.finding
        if report.repeated:
            print(
                f"finding {finding.identifier} by {finding.author} is already recorded and open: nothing new was written"
            )
        else:
            print(f"recorded finding {finding.identifier} by {finding.author}")
            print(
                f"red: `{finding.command}` exited {finding.red.get('exit_code')} on the candidate"
            )
            if report.corrects is not None:
                print(
                    f"corrected case: the earlier case `{report.corrects.command}` stays in the record "
                    "and no longer has to pass"
                )
        print(
            f"closed by: the record of step '{report.closing_step}' that sees the case pass"
        )
        line = review_lines.stale_line(report.stale, report.waiting)
        if line is not None:
            print(line)
            print(
                f"when the case passes, record the delta with: {desk.line(review.Remedy.REPLAY)}"
            )
        return 0

    @staticmethod
    def _packet(desk: rework.Desk) -> int:
        report = rework.freeze_candidate(desk)
        Cli._print_notes(report.notes)
        baseline = BaselineStore(desk.workspace).read()
        base = (
            f"{baseline.sha} (the pre-feature commit recorded at init)"
            if baseline.is_available
            else f"none recorded ({baseline.reason})"
        )
        for line in review_lines.packet_lines(
            report.packet,
            report.log,
            root=str(desk.root),
            workspace=str(desk.workspace.directory),
            base=base,
            stale=report.stale,
            verdict_command=desk.verdict_line(report.packet.candidate),
        ):
            print(line)
        return 0

    @staticmethod
    def _verdict(desk: rework.Desk, arguments) -> int:
        report = rework.record_verdict(
            desk, arguments.reviewer, arguments.candidate, arguments.outcome
        )
        Cli._print_notes(report.notes)
        if report.repeated:
            print(
                f"verdict {report.verdict.describe()} is already recorded: nothing new was written"
            )
        else:
            print(f"recorded verdict {report.verdict.describe()}")
        for withdrawal in report.withdrawn:
            print(review_lines.withdrawal_line(withdrawal))
        return 0

    @staticmethod
    def _print_notes(notes: tuple[str, ...]) -> None:
        for note in notes:
            print(f"WARNING: {note}", file=sys.stderr)

    def _next(
        self,
        schema: Schema,
        journal: Journal,
        request: str | None,
        workspace: Workspace,
    ) -> int:
        progress = Progress(schema, self._declared_size(schema, workspace))
        step = progress.next_ready(journal)
        remaining = progress.remaining(journal)
        kind = next_state(step.id if step is not None else None, remaining).kind
        kit = KitStore(workspace).state()
        if isinstance(kit, UnknownKit):
            print(
                f"WARNING: {kit.describe()}: this workspace was created before the kit existed; its skill paths are not a fixed copy. Create a new workspace with init to fix the kit.",
                file=sys.stderr,
            )
        pause = progress.pending_pause(
            journal,
            PersonAnswerStore(workspace).read(),
            interactive=WorkspaceMode(workspace).read() == run_mode.INTERACTIVE,
        )
        if pause is not None:
            print(self._awaiting_line(pause, workspace))
            return 0
        if kind is NextKind.READY:
            sentences = self._read_sentences(request) if request else None
            print(self._describe(step, sentences, KitStore(workspace).skills_root()))
            self._print_stale(schema, journal, workspace)
            return 0
        if kind is NextKind.COMPLETE:
            print("all steps recorded")
        else:
            blocked = [
                status for status in progress.statuses(journal) if status.label != "ok"
            ]
            waiting = ", ".join(
                f"{status.step_id} ({status.label})" for status in blocked
            )
            print(f"no step is ready; waiting on: {waiting}")
        self._print_stale(schema, journal, workspace)
        return 0

    @staticmethod
    def _print_stale(schema: Schema, journal: Journal, workspace: Workspace) -> None:
        log = review_store.read(workspace)
        line = review_lines.stale_line(
            rework.stale_steps(schema, journal, log),
            review.open_findings(log, journal, rework.green_id(schema)),
        )
        if line is not None:
            print(line)

    @staticmethod
    def _print_stale_names(stale: tuple[str, ...]) -> None:
        line = review_lines.stale_line(stale, ())
        if line is not None:
            print(line)

    def _status(self, workspace: Workspace, schema: Schema, journal: Journal) -> int:
        recorded = WorkspaceMode(workspace).read()
        print(f"mode: {recorded if recorded else 'not set'}")
        if schema.sized:
            print(self._size_line(workspace))
        print(KitStore(workspace).state().describe())
        size = self._declared_size(schema, workspace)
        progress = Progress(schema, size)
        for status in progress.statuses(journal):
            label = self._refactor_label(status, journal, workspace)
            print(f"{status.step_id:<14} revisions={status.revisions} {label}")
        if progress.not_due():
            print(f"not due for size {size}: {', '.join(progress.not_due())}")
        answers = PersonAnswerStore(workspace).read()
        pause = progress.pending_pause(
            journal, answers, interactive=recorded == run_mode.INTERACTIVE
        )
        if pause is not None:
            print(self._awaiting_line(pause, workspace))
        for answer in answers:
            print(
                f"answer after '{answer.after_step}' by {answer.author}: {answer.text}"
            )
        self._print_stale(schema, journal, workspace)
        for line in review_lines.status_lines(
            review_store.read(workspace), journal, rework.green_id(schema)
        ):
            print(line)
        return 0

    @staticmethod
    def _size_line(workspace: Workspace) -> str:
        declaration = SizeStore(workspace).current()
        if declaration is None:
            return "size: not declared"
        return f"size: {declaration.describe()}"

    @staticmethod
    def _declared_size(schema: Schema, workspace: Workspace) -> Size | None:
        if not schema.sized:
            return None
        declaration = SizeStore(workspace).current()
        return None if declaration is None else declaration.size

    @staticmethod
    def _refactor_label(
        status: StepStatus, journal: Journal, workspace: Workspace
    ) -> str:
        names = refactor_currency.named_refactor_commits(journal.records)
        if (
            status.step_id != refactor_currency.REFACTOR_STEP
            or not status.revisions
            or names is None
        ):
            return status.label
        baseline = BaselineStore(workspace).read()
        currency = refactor_currency.check(
            GitRefs(str(baseline.top), str(baseline.sha)), names
        )
        return currency.label

    def _awaiting_line(self, pause: Pause, workspace: Workspace) -> str:
        answer = self._how.command(
            "answer",
            "--workspace",
            str(workspace.directory),
            "--author",
            "<the person's id>",
            "--text",
            "<the answer>",
        )
        return f"awaiting person after '{pause.after_step}': {pause.question} Answer with: {answer}"

    def _size(self, arguments, workspace: Workspace, schema: Schema) -> int:
        if not schema.sized:
            raise Refusal(
                what="this schema declares no sizes, so every step is due and there is no size to declare",
                why="a size decides which steps are due; a delivery made from this schema runs every step",
                how=self._how.command("next", "--workspace", str(workspace.directory)),
            )
        size = Size.parse(arguments.size)
        if not arguments.why.strip():
            raise Refusal(
                what="the size is given no motivation",
                why="the declared size is kept with the sentence that motivates it, so the record says why this size",
                how=self._how.command(
                    "size",
                    "--workspace",
                    str(workspace.directory),
                    "--size",
                    size.label,
                    "--why",
                    "<one sentence>",
                ),
            )
        store = SizeStore(workspace)
        current = store.current()
        declaration = SizeDeclaration.declare(
            current,
            size,
            arguments.why,
            owner_note=arguments.owner_note,
            author=arguments.author,
        )
        if declaration is current:
            print(f"size {size} is already declared: nothing new was written")
            return 0
        store.append(declaration)
        if current is None:
            verb = "declared"
        elif size.outranks(current.size):
            verb = "raised"
        else:
            verb = "lowered"
        print(f"{verb} size: {declaration.describe()}")
        return 0

    def _answer(self, arguments, workspace: Workspace) -> int:
        answer = AnswerRecorder(workspace).answer(arguments.author, arguments.text)
        print(f"answer recorded after '{answer.after_step}' by {answer.author}")
        return 0

    @staticmethod
    def _describe(
        step: Step,
        sentences: RequestSentences | None,
        skills_root: Path | None,
    ) -> str:
        lines = [f"step: {step.id} - {step.title}", f"help: {step.help}"]
        if skills_root is not None:
            lines += Cli._skill_lines(step, skills_root)
        lines.append("fields:")
        lines += [f"  - {field.describe()}" for field in step.fields]
        maps_sentences = any(field.covers_sentences for field in step.fields)
        if sentences is not None and maps_sentences:
            lines.append("request sentences:")
            lines += [f"  {line}" for line in sentences.to_values()]
        return "\n".join(lines)

    @staticmethod
    def _skill_lines(step: Step, skills_root: Path) -> list[str]:
        if not step.skills:
            return []
        return ["read before this step:"] + [
            f"  - {skill}: {skill.file_under(skills_root)}" for skill in step.skills
        ]

    @staticmethod
    def _next_line(result: Recorded) -> str:
        step = result.next_step
        kind = next_state(step.id if step is not None else None, result.remaining).kind
        if kind is NextKind.READY and step is not None:
            return f"next: {step.id} - {step.title}"
        if kind is NextKind.COMPLETE:
            return "next: all steps recorded"
        return f"next: none ready; waiting on {', '.join(result.remaining)}"

    def _print_next(self, result: Recorded, workspace: Workspace) -> None:
        print(self._next_line(result))
        self._print_block(result.next_step, result.remaining, workspace)

    def _print_block(
        self, next_step: Step | None, remaining: tuple[str, ...], workspace: Workspace
    ) -> None:
        command = self._how.command("next", "--workspace", str(workspace.directory))
        next_id = next_step.id if next_step is not None else None
        for line in next_block(next_id, remaining, command):
            print(line)

    def _status_how(self) -> str:
        if self._directory is None:
            return self._how.command("--help")
        return self._how.command("status", "--workspace", str(self._directory))

    @staticmethod
    def _report(refusal: Refusal) -> None:
        how = refusal.how or "<no command line available>"
        for label, text in (("WHAT", refusal.what), ("WHY", refusal.why), ("HOW", how)):
            print(f"{label}: {' '.join(text.split())}", file=sys.stderr)
