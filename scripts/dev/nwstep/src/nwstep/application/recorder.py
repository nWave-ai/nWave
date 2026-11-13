from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nwstep.application import rework
from nwstep.application.baseline_compare import BaselineCompare
from nwstep.application.case_differential import CaseDifferential
from nwstep.application.diff_contracts import DiffContracts
from nwstep.application.formal_model_check import FormalModelCheck
from nwstep.application.how_line import HowLine
from nwstep.application.prereview_run import PrereviewRun
from nwstep.application.progress import Progress
from nwstep.application.record_how import RecordHow
from nwstep.application.recorded import Recorded
from nwstep.application.red_run import RedRun
from nwstep.application.refactoring_check import Refactoring
from nwstep.application.test_names import TestNames, test_name_of
from nwstep.domain import prereview, review, run_mode
from nwstep.domain.case_result import CaseResult
from nwstep.domain.case_spec import CaseSpec
from nwstep.domain.command_outcome import CommandOutcome
from nwstep.domain.conflict_coverage import ConflictCoverage
from nwstep.domain.conflict_decisions import ConflictDecisions
from nwstep.domain.contract_outcome import ContractOutcome
from nwstep.domain.edge_matrix import EdgeMatrix
from nwstep.domain.fault import Fault
from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.journal import Journal
from nwstep.domain.prediction import Prediction
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.record import Record
from nwstep.domain.refusal import Refusal
from nwstep.domain.request_sentences import RequestSentences
from nwstep.domain.scenario_coverage import ScenarioCoverage
from nwstep.domain.sentence_coverage import SentenceCoverage
from nwstep.domain.step import Step
from nwstep.domain.submission import Submission
from nwstep.infrastructure import review_store
from nwstep.infrastructure.baseline_store import BaselineStore
from nwstep.infrastructure.candidate_git import CandidateGit
from nwstep.infrastructure.command_runner import CommandRunner
from nwstep.infrastructure.journal_session import JournalSession
from nwstep.infrastructure.jsonl_journal import JsonlJournal
from nwstep.infrastructure.person_answer_store import PersonAnswerStore
from nwstep.infrastructure.size_store import SizeStore
from nwstep.infrastructure.toml_schema_reader import TomlSchemaReader
from nwstep.infrastructure.workspace import Workspace
from nwstep.infrastructure.workspace_mode import WorkspaceMode


class Recorder:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._schema = TomlSchemaReader().read(workspace.schema_path)
        self._journal = JsonlJournal(workspace)
        self._runner = CommandRunner()
        baseline = BaselineStore(workspace).read()
        self._differential = CaseDifferential(
            self._runner, baseline, workspace.directory
        )
        self._contracts = DiffContracts(baseline)
        self._formal_model = FormalModelCheck(self._contracts)
        self._red = RedRun(self._runner, workspace, baseline)
        self._refactoring = Refactoring(self._runner, workspace, baseline)
        self._compared = BaselineCompare(self._runner, baseline)
        # A declared command gets a longer bound than a command field: it may first wait its turn on a project lock.
        self._prereview = PrereviewRun(
            CommandRunner(timeout_s=prereview.COMMAND_TIMEOUT_S),
            CandidateGit(workspace.directory),
        )
        self._test_names = TestNames(workspace.directory)
        self._how = HowLine()
        declaration = SizeStore(workspace).current()
        self._size = (
            declaration.size if self._schema.sized and declaration is not None else None
        )
        self._progress = Progress(self._schema, self._size)
        self._answers = PersonAnswerStore(workspace)
        self._mode = WorkspaceMode(workspace).read()

    def record(self, step_id: str, submission: Submission, root: Path) -> Recorded:
        try:
            with self._journal.exclusive() as session:
                result = self._record_locked(session, step_id, submission, root)
                if not self._schema.find(step_id).replay:
                    return result
                kept = f"'{step_id}' revision {result.record.revision} is kept"
                replayed = self._replay_locked(session, root, cause=kept)
                return Recorded(
                    record=result.record,
                    next_step=result.next_step,
                    remaining=result.remaining,
                    warnings=result.warnings,
                    stale=result.stale,
                    replayed=replayed,
                )
        except Refusal as refusal:
            raise self._with_how(refusal, step_id, submission, root) from None

    def _record_locked(
        self, session: JournalSession, step_id: str, submission: Submission, root: Path
    ) -> Recorded:
        step = self._known_step(step_id)
        if submission.problems:
            raise Refusal(
                what=submission.problems[0], why=step.help, fault=Fault.SYNTAX
            )
        journal = session.snapshot()
        log = review_store.read(self._workspace)
        self._refuse_repeat(step, journal)
        self._refuse_outside_size(step, journal)
        self._refuse_while_awaiting(step, journal)
        unmet = self._progress.unmet(step.id, journal)
        if unmet:
            raise Refusal(
                what=f"step '{step.id}' is blocked: needs {', '.join(unmet)} recorded first",
                why=step.help,
                how=self._next_how(),
            )
        self._reject_unknown_names(step, submission)
        values, commands = self._accept(step, submission, root)
        self._refuse_absent_required(step, values)
        sentences = self._request_sentences(step, values, root)
        self._check_coverage(step, journal, values, sentences, root)
        self._check_decided(step, journal, values)
        self._refactoring.check_pairing(step, values, commands)
        superseded: list[str] = []
        implemented = journal.recorded(step.id) and self._implementation_recorded(
            journal
        )
        fallback_notes: list[str] = []
        commanded = {field.name: argv for field, argv in commands}
        covered = {
            field.fallback
            for field, _argv in commands
            if field.fallback is not None and field.fallback in commanded
        }
        for field, argv in commands:
            if field.name in covered:
                continue
            if field.runs_on == Field.RUNS_ON_PRE_FEATURE:
                values[field.name] = self._red.observe(
                    field, argv, root, self._expected_failures(field, values)
                )
            elif field.runs_on == Field.RUNS_ON_REFACTOR:
                values[field.name] = self._refactoring.receipts(
                    field, argv, values, root, journal
                )
            elif field.compare_baseline:
                values[field.name] = self._compared.observe(field, argv, root)
            else:
                outcome = self._runner.run(argv, root)
                checker = field
                primary_problem = outcome.problem
                if primary_problem is not None and field.fallback in commanded:
                    checker = step.field(field.fallback)
                    fallback_notes.append(
                        f"'{field.name}' could not start ({primary_problem}): its declared fallback "
                        f"'{checker.name}' ran instead; the record says so"
                    )
                    outcome = self._runner.run(commanded[checker.name], root)
                kept = self._keep_output(step, checker, outcome)
                if implemented and checker.expect == "fail" and outcome.exit_code == 0:
                    superseded.append(checker.name)
                else:
                    checker.check_outcome(outcome, kept)
                value = outcome.as_value()
                if primary_problem is not None:
                    value["fallback"] = {
                        "primary_problem": primary_problem,
                        "used": checker.name,
                    }
                values[field.name] = value
        warnings = [
            *fallback_notes,
            *(self._superseded_warning(name) for name in superseded),
        ]
        warnings += self._formal_model.check(step, values, root)
        warnings += self._check_contracts(step, values, root, journal)
        warnings += self._run_cases(step, values, root, journal)
        if sentences is not None:
            values[RequestSentences.KEY] = sentences.to_values()
        # Before the record: the case of every open finding must pass, and the receipts go into this same journal
        # line, so a finding is never closed without the record that saw it green, nor the reverse.
        closed = rework.close_findings(
            rework.Desk(self._workspace, root, self._how),
            self._runner,
            schema=self._schema,
            log=log,
            journal=journal,
            step=step,
        )
        if closed:
            values[review.CLOSED_KEY] = list(closed)
        # Last, so that a remote verification is requested only for a record that nothing else refuses.
        if step.prereview:
            values[prereview.KEY] = self._prereview.receipt(
                step, root, journal, self._keep_text
            )
        record = Record(
            seq=len(journal.records) + 1,
            step=step.id,
            revision=journal.revisions(step.id) + 1,
            recorded_at=datetime.now(UTC).isoformat(timespec="seconds"),
            values=values,
            given=submission.given(),
        )
        session.append(record)
        after = journal.appended(record)
        progress = self._progress
        return Recorded(
            record=record,
            next_step=progress.next_ready(after),
            remaining=progress.remaining(after),
            warnings=tuple(warnings),
            stale=rework.stale_steps(self._schema, after, log),
        )

    def _refuse_outside_size(self, step: Step, journal: Journal) -> None:
        """A sized delivery records only the steps its size makes due, after a size is declared, and closes once all of them are recorded."""
        if not self._schema.sized:
            return
        if self._size is None:
            raise Refusal(
                what=f"no size is declared for this delivery, so '{step.id}' cannot be recorded",
                why="the size decides which steps are due; a sized delivery declares its size before its first record",
                how=self._how.command(
                    "size",
                    "--workspace",
                    str(self._workspace.directory),
                    "--size",
                    "<S, M or L>",
                    "--why",
                    "<one sentence>",
                ),
            )
        if not self._schema.is_due(step.id, self._size):
            raise Refusal(
                what=f"step '{step.id}' is not due for size {self._size}: size {self._size} makes due {', '.join(self._schema.due_ids(self._size))}",
                why="a step the declared size skips is never recorded for it, so the record does not claim work the size did not ask for",
                how=self._how.command(
                    "size",
                    "--workspace",
                    str(self._workspace.directory),
                    "--size",
                    "<a size that makes it due>",
                    "--why",
                    "<one sentence>",
                ),
            )
        if self._schema.closing_step(self._size) != step.id:
            return
        missing = self._schema.missing_due(
            self._progress.recorded(journal), self._size, leaving_out=step.id
        )
        if missing:
            raise Refusal(
                what=f"'{step.id}' closes size {self._size}, but these due steps are not recorded: {', '.join(missing)}",
                why="the closing step says the delivery is done; a delivery with due steps still open is not done",
                how=self._next_how(),
            )

    def _refuse_while_awaiting(self, step: Step, journal: Journal) -> None:
        pause = self._progress.pending_pause(
            journal,
            self._answers.read(),
            interactive=self._mode == run_mode.INTERACTIVE,
        )
        if pause is None:
            return
        raise Refusal(
            what=f"step '{step.id}' waits: awaiting the person's answer to the pause after '{pause.after_step}'",
            why="interactive mode asks the person after each pause step of the size, so they decide before the next step is recorded",
            how=self._how.command(
                "answer",
                "--workspace",
                str(self._workspace.directory),
                "--author",
                "<the person's id>",
                "--text",
                "<the answer>",
            ),
        )

    def _refuse_absent_required(self, step: Step, values: dict[str, Any]) -> None:
        for field in step.fields:
            if self._size in field.required_sizes and field.name not in values:
                raise field.refuse_missing()

    def _known_step(self, step_id: str) -> Step:
        step = self._schema.find(step_id)
        if step is None:
            raise Refusal(
                what=f"unknown step '{step_id}'",
                why=f"steps come from the schema: {', '.join(self._schema.ids)}",
                how=self._next_how(),
            )
        return step

    def _refuse_repeat(self, step: Step, journal: Journal) -> None:
        if not step.repeat and journal.recorded(step.id):
            raise Refusal(
                what=f"step '{step.id}' is already recorded (revision {journal.revisions(step.id)}) and does not repeat",
                why=f"'{step.id}' is recorded once so that its values stay the single record later steps rely on",
                how=self._next_how(),
            )

    def _implementation_recorded(self, journal: Journal) -> bool:
        """True once some step has recorded a passing command: the implementation exists and a RED command is not expected to fail any more."""
        return any(
            journal.recorded(step.id)
            and any(
                field.kind is FieldKind.COMMAND and field.expect == "pass"
                for field in step.fields
            )
            for step in self._schema.steps
        )

    @staticmethod
    def _superseded_warning(name: str) -> str:
        return (
            f"'{name}' exited 0 although its expect is fail: the implementation exists now, so this revision "
            "records the run it observed; the RED result of the first revision of this step stands"
        )

    @staticmethod
    def _reject_unknown_names(step: Step, submission: Submission) -> None:
        for name in submission.names():
            if step.field(name) is None:
                declared = ", ".join(field.name for field in step.fields) or "none"
                raise Refusal(
                    what=f"step '{step.id}' has no field '{name}'",
                    why=f"the fields of '{step.id}' are: {declared}",
                    field=name,
                    fault=Fault.UNKNOWN_NAME,
                )
        for name in submission.repeated_scalars():
            repeated = step.field(name)
            if repeated is not None:
                raise repeated.refuse(
                    f"field '{name}' was given more than once", fault=Fault.DUPLICATE
                )

    def _accept(
        self, step: Step, submission: Submission, root: Path
    ) -> tuple[dict[str, Any], list[tuple[Field, list[str]]]]:
        values: dict[str, Any] = {}
        commands: list[tuple[Field, list[str]]] = []
        for field in step.fields:
            if field.kind.is_multi:
                self._accept_multi(field, submission, root, values)
            else:
                self._accept_single(field, submission, values, commands)
        return values, commands

    @staticmethod
    def _accept_multi(
        field: Field, submission: Submission, root: Path, values: dict[str, Any]
    ) -> None:
        if submission.scalar(field.name) is not None:
            raise field.refuse(
                f"field '{field.name}' takes --item {field.name}=VALUE, not --{field.name} VALUE",
                fault=Fault.WRONG_FORM,
            )
        items = submission.items_of(field.name)
        if items or field.required:
            values[field.name] = field.accept_items(items, root)

    @staticmethod
    def _accept_single(
        field: Field,
        submission: Submission,
        values: dict[str, Any],
        commands: list[tuple[Field, list[str]]],
    ) -> None:
        if submission.items_of(field.name):
            raise field.refuse(
                f"field '{field.name}' takes --{field.name} VALUE, not --item",
                fault=Fault.WRONG_FORM,
            )
        raw = submission.scalar(field.name)
        if raw is None:
            if field.required:
                raise field.refuse_missing()
            return
        if field.kind is FieldKind.COMMAND:
            commands.append((field, field.accept_command(raw)))
        else:
            values[field.name] = field.accept_value(raw)

    def _request_sentences(
        self, step: Step, values: dict[str, Any], root: Path
    ) -> RequestSentences | None:
        """The sentences of the request file that the step's sentence map must cover, if the step maps any."""
        mapper = next(
            (field for field in step.fields if field.covers_sentences is not None),
            None,
        )
        if mapper is None or mapper.covers_sentences is None:
            return None
        source = step.field(mapper.covers_sentences)
        if source is None:
            return None
        items = values.get(source.name)
        if items is None:
            raise source.refuse_missing()
        sentences = RequestSentences.from_text(source.read_single_file(items, root))
        if not sentences.sentences:
            raise source.refuse(f"field '{source.name}' holds no sentence to map")
        return sentences

    def _check_coverage(
        self,
        step: Step,
        journal: Journal,
        values: dict[str, Any],
        sentences: RequestSentences | None,
        root: Path,
    ) -> None:
        for field in step.fields:
            if field.decides is not None:
                self._check_decisions(step, field, field.decides, journal, values)
                continue
            if field.name not in values:
                continue
            value = values[field.name]
            if field.covers is not None:
                available, source = self._reference(step, journal, values, field.covers)
                if not available:
                    raise self._missing_reference(step, field, field.covers)
                required = self._schema.field_of(*field.covers).identifiers_of(source)
                field.check_coverage(
                    value, required, f"{field.covers[0]}.{field.covers[1]}"
                )
                if field.names_tests:
                    self._check_test_names(field, value, root)
            elif field.ids:
                field.check_coverage(
                    value, field.ids, f"the fixed ids {', '.join(field.ids)}"
                )
                field.check_evidence(value)
            elif field.covers_sentences is not None and sentences is not None:
                SentenceCoverage(field, sentences, self._promise_ids(values)).check(
                    value
                )
            elif field.cross_with is not None:
                interfaces = step.field(field.cross_with)
                if interfaces is None:
                    continue
                EdgeMatrix(field, interfaces, field.categories).check(
                    value, values.get(field.cross_with, [])
                )
            elif field.needs_ids is not None:
                available, source = self._reference(
                    step, journal, values, field.needs_ids
                )
                if not available:
                    raise self._missing_reference(step, field, field.needs_ids)
                required = [
                    item.identifier
                    for item in (PrefixedItem(str(text)) for text in source)
                    if item.identifier is not None and not item.not_applicable
                ]
                field.check_identifiers(
                    [spec.identifier for spec in field.parse_cases(value)],
                    required,
                    f"{field.needs_ids[0]}.{field.needs_ids[1]}",
                )
            elif field.kind is FieldKind.SCENARIOS:
                ScenarioCoverage(
                    field, value, self._sentence_items(step, values)
                ).check()
            elif field.kind is FieldKind.CONFLICTS and sentences is not None:
                ConflictCoverage(field, sentences, value).check()

    @staticmethod
    def _check_decided(step: Step, journal: Journal, values: dict[str, Any]) -> None:
        """A field another step decides is required when the decision is yes and refused when it is no; an undecided field is not checked yet."""
        for field in step.fields:
            if field.decided_by is None:
                continue
            decision = journal.latest_value(*field.decided_by)
            if decision is None:
                continue
            source = f"{field.decided_by[0]}.{field.decided_by[1]}"
            given = field.name in values
            if decision == "yes" and not given:
                raise field.refuse(
                    f"'{field.name}' is required because {source} is yes",
                    fault=Fault.MISSING,
                )
            if decision != "yes" and given:
                raise field.refuse(
                    f"'{field.name}' is given but {source} is {decision}: nothing is refactored when the design decides against it",
                    fault=Fault.VALUE,
                )

    @staticmethod
    def _expected_failures(field: Field, values: dict[str, Any]) -> list[str]:
        """The test names the oracle maps to promises: each must fail on the pre-feature tree, or it proves no change."""
        names = [
            test_name_of(str(item))
            for source in field.must_fail
            for item in values.get(source) or []
        ]
        return [name for name in names if name]

    def _check_test_names(self, field: Field, value: list[str], root: Path) -> None:
        """A test a mapping names must be defined by the clone's own test files now: a misspelt name is refused at record time."""
        defined = self._test_names.defined_in(root)
        missing = [
            name
            for name in (test_name_of(str(item)) for item in value)
            if name and name not in defined
        ]
        if missing:
            raise field.refuse(
                f"field '{field.name}' names test(s) that no test file of the clone defines: {', '.join(dict.fromkeys(missing))}",
                fault=Fault.COVERAGE,
            )

    def _keep_output(self, step: Step, field: Field, outcome: CommandOutcome) -> Path:
        """The full output of the last run of each command field, kept in the workspace so that a refusal can name it."""
        return self._keep_text(f"{step.id}.{field.name}", outcome.output)

    def _keep_text(self, name: str, text: str) -> Path:
        directory = self._workspace.directory / "output"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def replay(self, root: Path) -> tuple[Recorded, ...]:
        """Record again, in schema order, each stale step from the submission its latest record kept, under the journal lock."""
        with self._journal.exclusive() as session:
            return self._replay_locked(session, root, cause="")

    def _replay_locked(
        self, session: JournalSession, root: Path, *, cause: str
    ) -> tuple[Recorded, ...]:
        """Record again the stale steps, in schema order, inside the caller's lock. A refused step stops the replay: the records already kept stay, and the refusal names them."""
        replayed: list[Recorded] = []
        for _ in range(len(self._schema.steps) ** 2):
            journal = session.snapshot()
            stale = rework.replayable_steps(
                self._schema, journal, review_store.read(self._workspace)
            )
            if not stale:
                return tuple(replayed)
            step_id = stale[0]
            latest = next(
                record for record in reversed(journal.records) if record.step == step_id
            )
            submission = Submission.from_given(latest.given)
            try:
                replayed.append(self._record_locked(session, step_id, submission, root))
            except Refusal as refusal:
                wrapped = self._with_how(refusal, step_id, submission, root)
                prefix = f"{cause}; " if cause else ""
                raise wrapped.with_what(
                    f"{prefix}stale step '{step_id}' could not be replayed: {refusal.what}"
                ) from None
        raise Refusal(
            what="replay does not settle: a step keeps going stale after it is recorded again",
            why="each replayed record must leave no earlier step newer than itself; the needs of the schema may be cyclic",
            how=self._next_how(),
        )

    @staticmethod
    def _reference(
        step: Step,
        journal: Journal,
        values: dict[str, Any],
        reference: tuple[str, str],
    ) -> tuple[bool, list[Any]]:
        """The items a reference names: a step that refers to one of its own fields reads this record, any other step reads the journal."""
        source_step, source_field = reference
        if source_step == step.id:
            return source_field in values, list(values.get(source_field) or [])
        return (
            journal.recorded(source_step),
            list(journal.latest_value(source_step, source_field) or []),
        )

    def _missing_reference(
        self, step: Step, field: Field, reference: tuple[str, str]
    ) -> Refusal:
        source_step, source_field = reference
        if source_step == step.id:
            return field.refuse(
                f"field '{field.name}' needs field '{source_field}' given in the same record first"
            )
        return field.refuse(
            f"field '{field.name}' needs step '{source_step}' recorded first"
        )

    @staticmethod
    def _promise_ids(values: dict[str, Any]) -> tuple[str, ...]:
        promises = values.get(SentenceCoverage.PROMISES, [])
        return tuple(
            identifier
            for identifier in (PrefixedItem(str(text)).identifier for text in promises)
            if identifier is not None
        )

    @staticmethod
    def _sentence_items(step: Step, values: dict[str, Any]) -> list[str]:
        mapper = next(
            (field for field in step.fields if field.covers_sentences is not None),
            None,
        )
        return [] if mapper is None else list(values.get(mapper.name, []))

    def _check_decisions(
        self,
        step: Step,
        field: Field,
        source: tuple[str, str],
        journal: Journal,
        values: dict[str, Any],
    ) -> None:
        """A promise whose sentence has an open CONFLICT is not recorded until that sentence has a decision."""
        _, lines = self._reference(step, journal, values, source)
        ConflictDecisions(
            field,
            [str(line) for line in lines],
            self._sentence_map_of(step, journal, values, source),
            values.get(field.name, []),
        ).check()

    def _sentence_map_of(
        self,
        step: Step,
        journal: Journal,
        values: dict[str, Any],
        decides: tuple[str, str] | None,
    ) -> list[str]:
        """The sentence map of the step that owns the conflict lines: this record's own map when the step owns them."""
        if decides is None:
            return []
        owner = self._schema.find(decides[0])
        mapper = (
            None
            if owner is None
            else next((f for f in owner.fields if f.covers_sentences is not None), None)
        )
        if mapper is None:
            return []
        _, items = self._reference(step, journal, values, (decides[0], mapper.name))
        return [str(item) for item in items]

    def _check_contracts(
        self, step: Step, values: dict[str, Any], root: Path, journal: Journal
    ) -> list[str]:
        """Check the step's contract fields before craft, its locators and its verified items after craft; a refusal is raised unless every item is supported."""
        warnings: list[str] = []
        for field in step.fields:
            if field.name not in values:
                continue
            if field.contract is not None:
                outcome = self._contracts.check(field, values[field.name], root)
                warnings += self._apply(field, outcome, values)
            if field.locator_ids:
                outcome = self._contracts.check_locators(
                    field, values[field.name], root
                )
                warnings += self._apply(field, outcome, values)
            for reference in field.verifies:
                warnings += self._verify(step, field, reference, journal, root, values)
        return warnings

    @staticmethod
    def _apply(
        field: Field, outcome: ContractOutcome, values: dict[str, Any]
    ) -> list[str]:
        if outcome.problems:
            raise field.refuse(
                f"'{field.name}' has {len(outcome.problems)} item(s) the change does not support: "
                + "; ".join(outcome.problems),
                fault=Fault.COMMAND,
            )
        if outcome.lint is not None:
            values[DiffContracts.DIFF_LINT] = outcome.lint
        return list(outcome.warnings)

    def _verify(
        self,
        step: Step,
        field: Field,
        reference: tuple[str, str],
        journal: Journal,
        root: Path,
        values: dict[str, Any],
    ) -> list[str]:
        source_step, source_field = reference
        declared = self._schema.find(source_step)
        contract_field = None if declared is None else declared.field(source_field)
        if contract_field is None or contract_field.contract is None:
            raise field.refuse(
                f"'{field.name}' verifies '{source_step}.{source_field}', which is no contract field",
                fault=Fault.SYNTAX,
            )
        items = journal.latest_value(source_step, source_field) or []
        outcome = self._contracts.verify(
            contract_field.contract, items, root, generated=contract_field.generated
        )
        if outcome.problems:
            raise Refusal(
                what=f"the committed change does not support '{source_step}.{source_field}': "
                + "; ".join(outcome.problems),
                why="items recorded before craft are verified against the committed change after craft; a witness, generator or test that the change does not contain is refused",
                how=(
                    f"correct the item in '{source_step}' and record it again (the latest revision wins), "
                    f"then record '{step.id}' again; the state is shown by "
                    + self._how.command(
                        "status", "--workspace", str(self._workspace.directory)
                    )
                ),
                field=field.name,
                fault=Fault.COMMAND,
            )
        if outcome.lint is not None:
            values[DiffContracts.DIFF_LINT] = outcome.lint
        return list(outcome.warnings)

    def _run_cases(
        self, step: Step, values: dict[str, Any], root: Path, journal: Journal
    ) -> list[str]:
        """Run every case on the candidate and on the pre-feature tree; the record is refused unless each case holds, proves the change its kind names, and any artifact it names is defined by the committed change."""
        warnings: list[str] = []
        for field in step.fields:
            if field.kind is not FieldKind.CASES or field.name not in values:
                continue
            specs = field.parse_cases(values[field.name])
            predictions = self._predictions(step, field, specs, journal, values)
            for spec in specs:
                if spec.expectation.artifact is None:
                    continue
                outcome = self._contracts.artifact(spec.expectation.artifact, root)
                if outcome.problems:
                    raise field.refuse(
                        f"case '{spec.identifier}': " + "; ".join(outcome.problems),
                        fault=Fault.COMMAND,
                    )
                warnings += list(outcome.warnings)
            results = self._differential.judge(specs, root)
            failing = [result for result in results if not result.held]
            if failing:
                raise field.refuse_cases(failing)
            unproven = [
                (result, reason)
                for result in results
                if (reason := result.refusal()) is not None
            ]
            if unproven:
                raise field.refuse_unproven(unproven)
            values[field.name] = [
                self._stored(spec, result, predictions)
                for spec, result in zip(specs, results, strict=True)
            ]
            warnings += self._unverified_warnings(field, results)
        return warnings

    def _predictions(
        self,
        step: Step,
        field: Field,
        specs: list[CaseSpec],
        journal: Journal,
        values: dict[str, Any],
    ) -> dict[str, str]:
        """The outcomes the oracle predicted before any code existed; each must name a case of this record."""
        if field.predicted_by is None:
            return {}
        available, items = self._reference(step, journal, values, field.predicted_by)
        if not available:
            raise self._missing_reference(step, field, field.predicted_by)
        predictions: dict[str, str] = {}
        for text in items:
            try:
                prediction = Prediction.parse(str(text))
            except ValueError as error:
                raise field.refuse(
                    f"prediction '{text}' is not valid: {error}", fault=Fault.SYNTAX
                ) from None
            predictions[prediction.identifier] = prediction.status
        known = {spec.identifier for spec in specs}
        unknown = sorted(set(predictions) - known)
        if unknown:
            raise field.refuse(
                f"prediction(s) {', '.join(unknown)} name no case of this record",
                fault=Fault.COVERAGE,
            )
        return predictions

    @staticmethod
    def _stored(
        spec: CaseSpec, result: CaseResult, predictions: dict[str, str]
    ) -> dict[str, object]:
        value = result.as_value()
        if spec.expectation.artifact is not None:
            value["artifact"] = spec.expectation.artifact
        if spec.identifier in predictions:
            value["predicted"] = predictions[spec.identifier]
        return value

    @staticmethod
    def _unverified_warnings(field: Field, results: list[CaseResult]) -> list[str]:
        unverified = [result for result in results if result.unverified_reason()]
        if not unverified:
            return []
        ids = ", ".join(result.identifier for result in unverified)
        reason = unverified[0].unverified_reason()
        return [
            f"'{field.name}': cannot verify {ids} against the pre-feature tree or its trace: "
            f"{reason}; these cases are recorded as could-not-verify, not as holding or differing"
        ]

    def _with_how(
        self, refusal: Refusal, step_id: str, submission: Submission, root: Path
    ) -> Refusal:
        if refusal.how is not None:
            return refusal
        step = self._schema.find(step_id)
        if step is None:
            return refusal.with_how(self._next_how())
        writer = RecordHow(self._how, self._workspace.directory, root)
        return refusal.with_how(writer.for_refusal(step, submission, refusal))

    def _next_how(self) -> str:
        return self._how.command("next", "--workspace", str(self._workspace.directory))
