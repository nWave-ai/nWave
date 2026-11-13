"""Command-line adapter: parses arguments, calls the application and prints WHAT, WHY and HOW on refusal."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import ClassVar

from nwstep.application import jev_protocol, refactor_currency, review_lines, rework
from nwstep.application.answer_recorder import AnswerRecorder
from nwstep.application.briefer import Briefer
from nwstep.application.commit_hooks import clone_with_hooks, ensure_hooks
from nwstep.application.how_line import HowLine
from nwstep.application.initializer import Initializer
from nwstep.application.next_block import NextKind, next_block, next_state
from nwstep.application.progress import Progress
from nwstep.application.prompt import Prompt
from nwstep.application.recorded import Recorded
from nwstep.application.recorder import Recorder
from nwstep.application.step_status import StepStatus
from nwstep.domain import examine_level, review, run_mode
from nwstep.domain.baseline import Baseline
from nwstep.domain.commit_hooks import HookOutcome
from nwstep.domain.jev_consent import JevConsent
from nwstep.domain.journal import Journal
from nwstep.domain.kit import UnknownKit, compare_trees
from nwstep.domain.person_answer import Pause
from nwstep.domain.refusal import Refusal
from nwstep.domain.request_sentences import RequestSentences
from nwstep.domain.run_mode import CHOICES
from nwstep.domain.schema import Schema
from nwstep.domain.size import Size
from nwstep.domain.size_declaration import SizeDeclaration
from nwstep.domain.step import Step
from nwstep.infrastructure import consent_tiers, examine_level_tiers, review_store
from nwstep.infrastructure.baseline_store import BaselineStore
from nwstep.infrastructure.checkout_commit import CheckoutCommit
from nwstep.infrastructure.command_runner import CommandRunner
from nwstep.infrastructure.examine_level_binding import ExamineLevelBinding
from nwstep.infrastructure.git_refs import GitRefs
from nwstep.infrastructure.invocation_line import InvocationLine
from nwstep.infrastructure.jsonl_journal import JsonlJournal
from nwstep.infrastructure.kit_store import KitStore
from nwstep.infrastructure.package_paths import PackagePaths
from nwstep.infrastructure.person_answer_store import PersonAnswerStore
from nwstep.infrastructure.record_arguments import RecordArguments
from nwstep.infrastructure.refusing_parser import RefusingParser
from nwstep.infrastructure.size_store import SizeStore
from nwstep.infrastructure.skill_tree_reader import SkillTreeReader
from nwstep.infrastructure.skills_root import SkillsRoot
from nwstep.infrastructure.template_manifest_reader import read_template_manifest
from nwstep.infrastructure.toml_schema_reader import TomlSchemaReader
from nwstep.infrastructure.workspace import Workspace
from nwstep.infrastructure.workspace_mode import WorkspaceMode


BRIEF_KINDS = ("summary", "decisions", "trace")

HOOK_STATUS: dict[HookOutcome, str] = {
    HookOutcome.ALREADY_INSTALLED: "hooks: {root} already has the commit-msg and pre-commit hooks",
    HookOutcome.INSTALLED: "hooks: installed the commit-msg and pre-commit hooks in {root}",
    HookOutcome.INSTALLED_KEEPING_FOREIGN: "hooks: installed the commit-msg and pre-commit hooks in {root}; a hook already there was moved to its .legacy name by pre-commit",
    HookOutcome.NOT_DECLARED: "WARNING: no commit hooks installed in {root}: it has no .pre-commit-config.yaml, so it declares no commit hooks and its commits are not checked by them",
    HookOutcome.GIT_UNAVAILABLE: "WARNING: no commit hooks checked in {root}: git cannot be run here, so no commit can be made from it in this environment",
}
WORKSPACE_ENVIRONMENT = "NWSTEP_HOME"
RECORD_USAGE = (
    "usage: nwstep record STEP --workspace DIR --root DIR "
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
            return self._clone(arguments.source, arguments.dest)
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
        workspace = self._initialized(directory)
        schema = TomlSchemaReader().read(workspace.schema_path)
        journal = JsonlJournal(workspace).snapshot()
        if arguments.command == "replay":
            return self._replay(workspace, arguments.root, schema, journal)
        if arguments.command == "prompt":
            return self._prompt(arguments, workspace, schema)
        if arguments.command in ("finding", "packet", "verdict"):
            return self._review(arguments, workspace)
        if arguments.command == "size":
            return self._size(arguments, workspace, schema)
        if arguments.command == "answer":
            return self._answer(arguments, workspace)
        if arguments.command == "next":
            return self._next(schema, journal, arguments.request, workspace)
        if arguments.command == "status":
            return self._status(workspace, schema, journal)
        if arguments.command == "brief":
            briefer = Briefer(
                schema,
                BaselineStore(workspace).read(),
                KitStore(workspace).state(),
                review_store.read(workspace),
            )
            if arguments.out:
                return self._write_briefs(briefer, journal, Path(arguments.out))
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

    def _parser(self) -> RefusingParser:
        parser = RefusingParser(
            prog="nwstep", description="Record one step of a delivery at a time."
        )
        commands = parser.add_subparsers(
            dest="command", required=True, metavar="COMMAND"
        )
        init = commands.add_parser(
            "init", help="create a workspace from a schema and its pre-feature baseline"
        )
        init.add_argument(
            "--schema",
            required=True,
            help="a shipped schema name such as dynamic-v11, or the path of a schema file",
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
            "record", help="record one step: nwstep record STEP --FIELD VALUE"
        )
        sentences = commands.add_parser(
            "sentences", help="print the numbered sentences of a request file"
        )
        sentences.add_argument("--file", required=True)
        clone = commands.add_parser(
            "clone",
            help="make a git clone with the commit-msg and pre-commit hooks already installed",
        )
        clone.add_argument(
            "--source",
            required=True,
            help="the repository to clone: a path or a URL that git clone accepts",
        )
        clone.add_argument(
            "--dest", required=True, help="the new directory the clone is made in"
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
            help="print the dynamic-mode prompt for a workspace, a clone and a request",
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
        next_step.add_argument(
            "--request",
            help="the request file; its numbered sentences are shown with a step that maps them",
        )
        for name, summary in (
            ("status", "print every step with its revisions"),
            ("export", "print the journal as a JSON array"),
        ):
            commands.add_parser(name, help=summary).add_argument("--workspace")
        brief = commands.add_parser("brief", help="render Markdown from the journal")
        brief.add_argument("--workspace")
        brief.add_argument("--kind", choices=BRIEF_KINDS, default="summary")
        brief.add_argument(
            "--out",
            help="write SUMMARY.md, DECISIONS.md and TRACE.md into this directory (inside the clone) instead of printing one",
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
    def _schema_source(value: str) -> Path:
        """A shipped schema named without a folder (dynamic-v11 or dynamic-v11.toml); any other value is a path."""
        if "/" not in value and "\\" not in value:
            name = value if value.endswith(".toml") else f"{value}.toml"
            if (PackagePaths.SCHEMAS / name).is_file():
                return PackagePaths.SCHEMAS / name
        return Path(value).resolve()

    # fmt: off
    def _init(
        self,
        schema_path: str,
        directory: Path,
        base: str,
        mode: str | None,
        skills: str | None,
    ) -> int:
        initializer = Initializer(self._how)
        schema_source = self._schema_source(schema_path)
        workspace = Workspace(directory)
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
                f"baseline: pre-feature tree {baseline.sha} exported to {baseline.directory}"
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
                "give --workspace DIR (or set NWSTEP_HOME) to list the steps and their fields"
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

    def _clone(self, source: str, dest: str) -> int:
        destination = Path(dest).resolve()
        outcome = clone_with_hooks(source, destination)
        print(f"cloned {source} to {destination}")
        self._report_hooks(destination, outcome)
        return 0

    def _guard_hooks(self, root: Path) -> None:
        self._report_hooks(root, ensure_hooks(root))

    @staticmethod
    def _report_hooks(root: Path, outcome: HookOutcome) -> None:
        text = HOOK_STATUS.get(outcome)
        if text is not None:
            print(text.format(root=root), file=sys.stderr)

    def _replay(
        self,
        workspace: Workspace,
        root_option: str | None,
        schema: Schema,
        journal: Journal,
    ) -> int:
        root = Path(root_option).resolve() if root_option else Path.cwd()
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
        desk = rework.Desk(workspace, root, self._how)
        if arguments.command == "finding":
            return self._finding(desk, arguments)
        if arguments.command == "packet":
            return self._packet(desk)
        return self._verdict(desk, arguments)

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
