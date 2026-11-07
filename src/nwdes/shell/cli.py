"""Driving CLI: decode inputs, call the pure core, enact declared output plans."""

import argparse
import errno
import os
import re
import shlex
import shutil
import sys
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

from nwdes import (
    commits,
    documents,
    drafts,
    grammar,
    handoff,
    lanes,
    measurement,
    packets,
    prompts,
)
from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.destinations import (
    CommitLocations,
    Destinations,
    readable_directory,
    readable_paths,
    readable_setting,
    resolve,
)
from nwdes.shell import host_sessions, probe
from nwdes.shell.asset_tree import decode_utf8, read_asset
from nwdes.shell.filesystem import (
    check_paths,
    ensure_exclude,
    read_file,
    read_register,
    read_register_files,
    remove_paths,
    write_outputs,
)
from nwdes.shell.git import (
    _status_entries,
    failure_reason,
    observe_lane,
    run_git,
    scrubbed_env,
)
from nwdes.shell.json_configuration import (
    configuration_failed,
    read_configuration_tier,
    read_lane_configuration,
)
from nwdes.shell.ports import (
    AssetMissing,
    AssetUnreadable,
    BrandUnavailable,
    ConfigurationRead,
    DocumentPorts,
    IOFailure,
    Missing,
    Unreadable,
)


class _Usage(ValueError):
    def __init__(self, message="", *, defects=()):
        super().__init__(message)
        self.defects = defects


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def parse_args(self, args=None, namespace=None):
        result = super().parse_args(args, namespace)
        if getattr(result, "verb", None) == "review" and hasattr(result, "role_verb"):
            result.review_scope = drafts.review_scope(
                result.subject, result.slice, replay=result.review_replay
            )
        if getattr(result, "verb", None) in drafts.KINDS and hasattr(
            result, "role_verb"
        ):
            problems = drafts.argument_problems(
                result.verb, result.role_verb, vars(result)
            )
            if problems:
                if result.verb == "review" or any(
                    field.role_refused
                    for verb in drafts.role_verbs(result.verb)
                    if verb.name == result.role_verb
                    for field in verb.fields
                ):
                    raise _Usage(defects=tuple(problems))
                self.error(
                    "; ".join(
                        problem.what + ": " + problem.why + " HOW: " + problem.how
                        for problem in problems
                    )
                )
        return result

    def error(self, message):
        raise _Usage(message)


class _RoleText(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        item = (option_string.endswith("-file"), value)
        if self.const:
            setattr(
                namespace, self.dest, [*(getattr(namespace, self.dest) or []), item]
            )
        else:
            setattr(namespace, self.dest, item)


_INSPECTION_TRAILING = {"PATH": "*", "-- ARGV": argparse.REMAINDER}


def _role_parser(entry, kind, *, replay=False):
    commands = entry.add_subparsers(dest="role_record", required=True)
    if kind == "examine":
        for command in grammar.EXAMINATION_COMMANDS:
            leaf = commands.add_parser(command.action, add_help=False)
            leaf.set_defaults(examination_action=command.action)
            for argument in command.arguments:
                if argument.flag == "--workspace":
                    leaf.add_argument("--workspace", required=True)
                else:
                    leaf.add_argument(
                        "arguments", nargs=_INSPECTION_TRAILING[argument.flag]
                    )
    records = {}
    for verb in drafts.role_verbs(kind):
        if verb.record:
            if verb.record not in records:
                parent = commands.add_parser(verb.record, add_help=False)
                records[verb.record] = parent.add_subparsers(
                    dest="role_action", required=True
                )
            leaf = records[verb.record].add_parser(verb.action, add_help=False)
        else:
            leaf = commands.add_parser(verb.action, add_help=False)
        leaf.set_defaults(role_verb=verb.name)
        if kind == "review":
            leaf.set_defaults(review_replay=replay)
        grouped = {}
        for names in verb.exclusive:
            group = leaf.add_mutually_exclusive_group(
                required=names in (("shared", "in"), ("at", "id"), ("id", "at"))
            )
            grouped.update((name, group) for name in names)
        for field in verb.fields:
            owner = grouped.get(field.name, leaf)
            options = {"dest": field.name.replace("-", "_"), "default": None}
            if field.spec.kind == "boolean":
                owner.add_argument(
                    "--" + field.name,
                    action="store_true",
                    required=field.required,
                    **options,
                )
                continue
            if field.text:
                group = (
                    owner
                    if field.repeated
                    else owner.add_mutually_exclusive_group(required=field.required)
                )
                for suffix in ("", "-file"):
                    group.add_argument(
                        "--" + field.name + suffix,
                        action=_RoleText,
                        const=field.repeated,
                        **options,
                    )
                continue
            if field.repeated:
                options["action"] = "append"
            if field.spec.kind == "integer":
                options["type"] = int
            if field.choices:
                options["choices"] = field.choices
            if field.name not in grouped:
                # Product coverage owns the actionable WHAT/WHY/HOW refusal.
                options["required"] = field.required and not (
                    field.role_refused
                    or (replay and kind == "review" and field.name == "subject")
                )
            owner.add_argument("--" + field.name, **options)


def _parser(*, replay=False):
    common = _Parser(add_help=False)
    for option in grammar.SINGLE_OPTIONS:
        common.add_argument("--" + option)
    for option in grammar.REPEATED_OPTIONS:
        if option == "handoff":
            common.add_argument("--handoff", action="extend", nargs="+", default=[])
        else:
            common.add_argument(
                "--" + option,
                action="append",
                default=None if option in ("decision", "constraint") else [],
            )
    common.add_argument("--product", action="store_true")
    parser = _Parser(
        prog="nwdes",
        description="Build canonical handoffs and render their briefs from supplied values.",
        add_help=False,
    )
    verbs = parser.add_subparsers(dest="verb")
    for verb in grammar.VERBS:
        if verb.name == "commit":
            entry = verbs.add_parser("commit", add_help=False)
            for option in (
                "repo-root",
                "project-root",
                "global-config",
                "feature",
                "epic",
                "slice",
            ):
                entry.add_argument("--" + option)
            entry.add_argument(
                "--role",
                required=True,
                choices=tuple(role.value for role in commits.Role),
            )
            entry.add_argument(
                "--type",
                required=True,
                choices=tuple(kind.value for kind in commits.CommitType),
            )
            entry.add_argument("--description", required=True)
            entry.add_argument("--scope", dest="message_scope")
            entry.add_argument("--body")
            entry.add_argument("--path", action="append", default=[])
            continue
        if verb.name == "measure":
            entry = verbs.add_parser("measure", add_help=False)
            for option in grammar.MEASURE_OPTIONS:
                entry.add_argument("--" + option, action="append")
            continue
        if verb.name in drafts.KINDS:
            _role_parser(
                verbs.add_parser(verb.name, add_help=False), verb.name, replay=replay
            )
            continue
        if verb.name == "lane":
            entry = verbs.add_parser("lane", add_help=False)
            entry.add_argument("action", choices=verb.actions)
            for option in ("repo-root", "feature", "key", "expected", "candidate"):
                entry.add_argument("--" + option)
            continue
        if verb.name in ("prompt", "packet"):
            entry = verbs.add_parser(verb.name, add_help=False)
            options = (
                grammar.PROMPT_OPTIONS
                if verb.name == "prompt"
                else grammar.PACKET_OPTIONS
            )
            for option in options:
                entry.add_argument(
                    "--" + option,
                    help=grammar.ROOT_CONTEXT_HELP
                    if option == "root-context"
                    else None,
                    choices=tuple(value.value for value in prompts.JevAuthorization)
                    if option == "jev"
                    else None,
                )
            if verb.name == "prompt":
                entry.add_argument(
                    "--baseline-failure", action="append", nargs=2, default=[]
                )
                entry.add_argument("--project-root")
                entry.add_argument("--global-config")
            continue
        entry = verbs.add_parser(verb.name, parents=[common], add_help=False)
        if verb.actions:
            entry.add_argument("action", choices=verb.actions)
    return parser


PARSER = _parser()
REPLAY_PARSER = _parser(replay=True)


def _refusal(defects):
    result = checked(None, defects)
    if isinstance(result, Refused):
        for number, defect in enumerate(result.defects, 1):
            print(
                f"{number}. WHAT: {defect.what}\nWHY: {defect.why}\nHOW: {defect.how}",
                file=sys.stderr,
            )
        return 2
    return 0


def _read_named(path):
    raw = read_file(path)
    if isinstance(raw, bytes):
        try:
            raw.decode("utf-8")
        except UnicodeError as error:
            return Unreadable(path, str(error))
    return raw


def _inspection_failure(defects, unreadable=(), brand=None):
    input_defects = tuple(
        Defect(
            "InputUnreadable: " + raw.path,
            raw.reason
            if raw.path.startswith("git ")
            else f"The named file could not be read as UTF-8: {raw.reason}.",
            "Correct the cause in WHY, then rerun the same nwdes lane command."
            if raw.path.startswith("git ")
            else "Make the named file readable as UTF-8, then rerun the same nwdes command.",
        )
        for raw in unreadable
    )
    asset_defects = tuple(
        defect
        for failure in (brand.failures if isinstance(brand, BrandUnavailable) else ())
        for defect in (
            (
                Defect(
                    "AssetMissing: " + failure.path,
                    "The installed asset is absent: " + failure.reason + ".",
                    "Reinstall the nwave-ai package that supplies nwdes, "
                    "so the named asset is present.",
                ),
            )
            if isinstance(failure, AssetMissing)
            else failure.defects
        )
    )
    reported = frozenset(defect.what for defect in (*input_defects, *asset_defects))
    refusal = _refusal(
        (
            *input_defects,
            *asset_defects,
            *(defect for defect in defects if defect.what not in reported),
        )
    )
    return 1 if unreadable or isinstance(brand, BrandUnavailable) else refusal


def _named_failures(inputs, defects=()):
    missing = tuple(
        Defect(
            f"MissingFact: {flag} {path}",
            "The named input file does not exist.",
            f"Supply {flag} with the path of an existing handoff.",
        )
        for flag, path, raw in inputs
        if isinstance(raw, Missing)
    )
    unreadable = tuple(raw for _, _, raw in inputs if isinstance(raw, Unreadable))
    return _inspection_failure((*missing, *defects), unreadable)


def _delta(args, initial=()):
    inputs = tuple(
        (flag, path, _read_named(path))
        for flag, path in (("--previous", args.previous), ("--new", args.new))
        if path is not None
    )
    parsed = tuple(
        (flag, path, handoff.parse(raw))
        for flag, path, raw in inputs
        if isinstance(raw, bytes)
    )
    defects = tuple(
        Defect(f"{defect.what} ({flag} {path})", defect.why, defect.how)
        for flag, path, result in parsed
        if isinstance(result, Refused)
        for defect in result.defects
    )
    failure = _named_failures(inputs, (*initial, *defects))
    if failure:
        return failure
    for change, path in handoff.compare(parsed[0][2].value, parsed[1][2].value):
        print(change, path)
    for identity in handoff.affected_slices(parsed[0][2].value, parsed[1][2].value):
        print("AFFECTED", identity)
    return 0


def _installed_root():
    package_parent = Path(__file__).resolve().parents[2]
    return package_parent.parent if package_parent.name == "src" else package_parent


def _document_ports(args):
    root = _installed_root()
    global_config = args.global_config or str(Path.home() / ".nwave/config.json")
    return DocumentPorts(
        configuration=lambda tier, scope: read_configuration_tier(
            args.project_root,
            global_config,
            tier,
            scope,
        ),
        file=read_file,
        outputs=lambda outputs: write_outputs(args.repo_root, outputs),
        asset=lambda relative: read_asset(str(root), relative),
        register=lambda directory: read_register(args.repo_root, directory),
        confinement=lambda paths: check_paths(args.repo_root, paths),
        input=lambda: b"",
        asset_root=str(root),
    )


def _brand(ports: DocumentPorts) -> Built[documents.Brand] | BrandUnavailable:
    root = Path(ports.asset_root)
    assets = []
    failures = []
    for name in ("nwave.css", "logo.svg"):
        relative = "nWave/data/brand/" + name
        value = ports.asset(relative)
        if isinstance(value, (AssetMissing, AssetUnreadable)):
            failures.append(value)
            continue
        decoded = decode_utf8(value, str(root / relative))
        if isinstance(decoded, AssetUnreadable):
            failures.append(decoded)
            continue
        assets.append((decoded.value, value))
    if failures:
        return BrandUnavailable(tuple(failures))
    return Built(documents.Brand(assets[0][0], assets[1][1]))


def _emit(ports: DocumentPorts, outputs):
    confined = ports.confinement(tuple(output.path for output in outputs.outputs))
    if isinstance(confined, Refused):
        return _refusal(confined.defects)
    result = ports.outputs(outputs)
    if isinstance(result, IOFailure):
        _refusal(
            (
                Defect(
                    "OutputUnreadable: " + ", ".join(result.unwritten),
                    f"Writing these paths failed: {result.reason}.",
                    "Correct the filesystem condition reported in WHY (including "
                    "required read/write access, available space, or the named I/O "
                    "failure), then rerun the same nwdes command; outputs already "
                    "written print UNCHANGED.",
                ),
            )
        )
        return 1
    for status, path in result.paths:
        print(status, path)
    return 0


def _project(
    args,
    destinations,
    ports: DocumentPorts,
    initial=(),
    previous_path=None,
):
    brand = args.prepared_brand
    previous_raw = (
        ports.file(str(Path(args.repo_root) / previous_path))
        if previous_path is not None
        else None
    )
    previous = (
        Built(documents.ProductHandoff())
        if isinstance(previous_raw, Missing)
        else documents.parse_product(previous_raw)
        if isinstance(previous_raw, bytes)
        else None
    )
    handoffs = []
    defects = [*initial, *(previous.defects if isinstance(previous, Refused) else ())]
    unreadable = []
    if isinstance(previous_raw, Unreadable):
        unreadable.append(previous_raw)
    for path in args.handoff:
        file = Path(path)
        if not file.is_absolute():
            if isinstance(args.invocation.roots, Refused):
                continue
            file = Path(args.repo_root) / file
        raw = ports.file(str(file))
        if isinstance(raw, Missing):
            defects.append(
                Defect(
                    f"MissingFact: --handoff {path}",
                    "The named feature handoff does not exist.",
                    "Supply an existing feature handoff.",
                )
            )
        elif isinstance(raw, Unreadable):
            unreadable.append(raw)
        else:
            parsed = handoff.parse(raw)
            if isinstance(parsed, Refused):
                defects.extend(parsed.defects)
            else:
                handoffs.append(parsed.value)
    failure = _inspection_failure(defects, unreadable, brand)
    if failure:
        return 1 if args.configuration_operational else failure
    return _emit(
        ports,
        documents.project_outputs(
            previous.value, tuple(handoffs), destinations, brand.value
        ),
    )


def _command_program(command):
    words = shlex.shlex(command, posix=True)
    words.whitespace_split = True
    words.commenters = ""
    try:
        return next(words, None)
    except ValueError:
        return None


def _program_file(root, program):
    location = Path(program)
    try:
        if not location.is_absolute():
            root = Path(os.path.normpath(Path(root).absolute()))
            location = root / location
            if not Path(os.path.normpath(location)).is_relative_to(root):
                return False
        return location.is_file()
    except (OSError, RuntimeError):
        return False


def _program_resolves(root, program, path):
    if program is None:
        return False
    return (
        _program_file(root, program)
        if any(separator in program for separator in (os.sep, os.altsep) if separator)
        else shutil.which(program, path=path) is not None
    )


def resolve_programs(root, commands, *, path=None) -> handoff.ProgramResolution:
    programs = {
        command: _command_program(command)
        for command in dict.fromkeys(command for _, command in commands)
    }
    resolved = {
        program: _program_resolves(root, program, path)
        for program in dict.fromkeys(programs.values())
    }
    return handoff.Record(
        (command, resolved[program]) for command, program in programs.items()
    )


def _reference_resolves(root, locator, symbol):
    """The shell's answer for one reuse row: its file lies under the root, its line exists, and its symbol occurs."""
    path, line = handoff.split_locator(locator)
    base = Path(os.path.normpath(Path(root).absolute()))
    location = Path(os.path.normpath(base / path))
    if not location.is_relative_to(base) or not symbol.strip():
        return False
    try:
        text = location.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return (
        line.isdigit()
        and 1 <= int(line) <= len(text.splitlines())
        and re.search(r"\b" + re.escape(symbol) + r"\b", text) is not None
    )


def _resolve_references(root, sites):
    return {site: _reference_resolves(root, *site) for site in sites}


def _test_resolves(root, locator):
    """The shell's answer for one test locator a row binds: its file lies under the root and its name occurs in it as a whole word."""
    path, separator, name = locator.partition("::")
    base = Path(os.path.normpath(Path(root).absolute()))
    location = Path(os.path.normpath(base / path))
    if not separator or not name.strip() or not location.is_relative_to(base):
        return False
    try:
        text = location.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return re.search(r"\b" + re.escape(name) + r"\b", text) is not None


def _resolve_coverage(root, locators):
    return {locator: _test_resolves(root, locator) for locator in locators}


def _load_policy():
    """The composition root's one read of policy.toml, checked against the record shape."""
    try:
        text = (Path(__file__).resolve().parents[1] / "policy.toml").read_text("utf-8")
    except (OSError, UnicodeError) as error:
        return Refused(
            (
                Defect(
                    "InputUnreadable: policy.toml",
                    str(error),
                    "Restore src/nwdes/policy.toml from the installed package.",
                ),
            )
        )
    return handoff.parse_policy(text)


def _inspected_output(args, raw):
    if raw is None:
        return raw
    if args.verb == "design":
        return handoff.inspect_output(
            args.verb,
            raw,
            policy=args.policy,
            resolution=_resolve_references(
                args.repo_root, handoff.reference_sites(raw, args.policy)
            ),
        )
    if args.verb in handoff.ASKED_KINDS:
        return handoff.inspect_output(args.verb, raw, policy=args.policy)
    return raw


def _prepare_transition(args, previous, raw):
    output = _inspected_output(args, raw)
    commands = handoff.invocation_commands(args.invocation, previous, output)
    programs = resolve_programs(args.repo_root, commands)
    coverage = _resolve_coverage(
        args.repo_root,
        handoff.coverage_locators(args.verb, output, previous),
    )
    return handoff.prepare_invocation(
        args.invocation, previous, output, programs=programs, resolution=coverage
    )


def _document(args, ports: DocumentPorts, initial=(), raw=None, existing=None):
    defects = [*initial]
    brand = _brand(ports)
    args.prepared_brand = brand
    configuration_ready = (
        isinstance(args.invocation.roots, Built) and args.scope is not None
    )
    tier_kinds = (
        "global",
        "repository",
        *(
            (args.scope.kind.lower(),)
            if not args.product and args.scope is not None
            else ()
        ),
    )
    tiers = (
        tuple(ports.configuration(kind, args.scope) for kind in tier_kinds)
        if configuration_ready
        else ()
    )
    resolved = resolve(tiers, args.scope) if configuration_ready else None
    defects.extend(
        resolved.defects
        if isinstance(resolved, Refused)
        else (
            defect
            for tier in tiers
            if isinstance(tier, Refused)
            for defect in tier.defects
        )
    )
    destinations = resolved.value if isinstance(resolved, Built) else None
    adr_directory = (
        readable_setting(tiers, "adr.directory", "docs/product/architecture")
        if configuration_ready
        else None
    )
    known_paths = readable_paths(tiers, args.scope) if configuration_ready else ()
    directory = readable_directory(tiers, args.scope) if configuration_ready else None
    confined = (
        ports.confinement(
            (*known_paths, *((adr_directory,) if adr_directory is not None else ()))
        )
        if configuration_ready
        else None
    )
    if isinstance(confined, Refused):
        defects.extend(confined.defects)
    args.configuration_operational = configuration_failed(tiers)
    if args.product:
        return _project(
            args,
            destinations,
            ports,
            defects,
            directory + "/handoff.json" if directory is not None else None,
        )
    register = ports.register(adr_directory) if adr_directory is not None else None
    unreadable = [register] if isinstance(register, Unreadable) else []
    if isinstance(register, Refused):
        defects.extend(register.defects)
    if existing is None:
        existing = (
            ports.file(str(Path(args.repo_root) / directory / "handoff.json"))
            if directory is not None
            else None
        )
    previous = None
    inspected = None
    if isinstance(existing, Unreadable):
        unreadable.append(existing)
    if isinstance(existing, bytes):
        inspected = handoff.inspect_handoff(existing)
        if isinstance(inspected.result, Built):
            previous = inspected.result.value
    result = None
    if isinstance(existing, (bytes, Missing)):
        result = _prepare_transition(args, inspected, raw)
        if isinstance(result, Refused):
            defects.extend(result.defects)
    elif raw is not None:
        shape = handoff.check_output(
            args.verb,
            raw,
            None,
            args.invocation.values["slice"],
        )
        if isinstance(shape, Refused):
            defects.extend(shape.defects)
    adr_result = None
    decoded = (
        result.output
        if isinstance(result, handoff.InvocationRefused)
        else result.value.output
        if isinstance(result, Built)
        else handoff.inspect_output(args.verb, raw)
        if raw is not None
        else None
    )
    if (
        args.verb == "design"
        and isinstance(register, Built)
        and decoded is not None
        and decoded.outcome == "accepted"
        and isinstance(decoded.payload, Mapping)
    ):
        adr_result = documents.prepare_adr(
            register.value,
            decoded.payload.get("adrs", ()),
            (previous.design or {}).get("adrs", ()) if previous is not None else (),
        )
        if isinstance(adr_result, Refused):
            defects.extend(adr_result.defects)
    refreshed = None
    if inspected is not None and args.verb != "design" and isinstance(register, Built):
        refreshed = documents.declaration_snapshot(
            inspected.part("design"), register.value
        )
        if isinstance(refreshed, Refused):
            defects.extend(refreshed.defects)
    failure = _inspection_failure(defects, unreadable, brand)
    if failure:
        return 1 if args.configuration_operational else failure
    completed = handoff.finish(result)
    if isinstance(completed, Refused):
        return _refusal(completed.defects)
    current = completed.value
    if adr_result is not None:
        adr_result = adr_result.value.build()
        if isinstance(adr_result, Refused):
            return _refusal(adr_result.defects)
    if args.verb == "feature" and current is previous:
        adr_outputs = documents.adr_outputs(
            register.value,
            destinations.adr_directory,
            (current.design or {}).get("adrs", ()),
        )
        paths = (
            *(output.path for output in adr_outputs),
            *(path for _, path in destinations.briefs),
            *(path[:-3] + ".html" for _, path in destinations.briefs),
            destinations.handoff,
        )
        for path in paths:
            print("UNCHANGED", path)
        return 0
    adr_outputs = ()
    if adr_result is not None:
        current = handoff.snapshot_adrs(current, adr_result.value.snapshot)
        predecessors = tuple(
            row["supersedes"]
            for row in decoded.payload.get("adrs", ())
            if "supersedes" in row
        )
        adr_outputs = documents.adr_outputs(
            adr_result.value.register,
            destinations.adr_directory,
            adr_result.value.snapshot,
            predecessors,
        )
    elif current.design:
        if refreshed is not None:
            current = handoff.snapshot_adrs(current, refreshed.value)
        adr_outputs = documents.adr_outputs(
            register.value,
            destinations.adr_directory,
            current.design.get("adrs", ()),
        )
    result = _emit(
        ports,
        documents.feature_outputs(current, destinations, brand.value, adr_outputs),
    )
    if result == 0:
        for notice in current.withdrawals:
            print(notice)
    if result == 0 and args.verb == "examine":
        print(handoff.examination_outcome(current.examination))
    return result


def _work_set(args, defects):
    ports = _document_ports(args)
    if defects or args.scope is None or not _git_worktree(args.repo_root):
        return _document(args, ports, defects)
    resolved = _resolve_destinations(args, ports)
    if isinstance(resolved, Refused):
        return _document(args, ports, defects)
    located = _commit_locations(args.repo_root)
    if isinstance(located, Refused):
        return _commit_failure(located)
    locations = located.value
    with _commit_lock(locations) as locked:
        if isinstance(locked, Refused):
            return _commit_failure(locked)
        handoff_path = resolved.value.handoff
        inputs = _read_inputs(ports, args.repo_root, resolved.value)
        receipts = _read_close_receipts(locations)
        current = _receipt_digests(
            args.repo_root, receipts, handoff_path, inputs.handoff
        )
        scope = _recorded_scope(args.scope, args.invocation.values["slice"])
        receipt = next(
            (
                receipt
                for receipt in receipts
                if commits.is_own_matching_receipt(
                    receipt, commits.Role.ProductOwner, scope, current
                )
                and handoff_path in receipt.paths
            ),
            None,
        )
        rendering = _pinned_ports(ports, inputs)
        publishing = (
            replace(
                rendering,
                outputs=lambda outputs: _publish_work(
                    ports, outputs, locations, receipt
                ),
            )
            if receipt is not None
            else rendering
        )
        return _document(args, publishing, defects, existing=inputs.handoff)


def _unavailable_input(flag, path, reason):
    return handoff.UnavailableInput(
        Defect(
            f"InputUnreadable: --{flag} {path}",
            reason,
            "Supply the named input as a readable UTF-8 file.",
        )
    )


def _read_handoff_diff(args):
    previous = None
    if args.handoff is not None:
        raw = _read_named(args.handoff)
        if isinstance(raw, bytes):
            previous = handoff.inspect_handoff(raw)
        elif isinstance(raw, Unreadable):
            failed = _unavailable_input("handoff", args.handoff, raw.reason)
            previous = handoff.HandoffInput(checked(None, (failed.defect,)), None)
    diff = None
    if args.diff is not None:
        raw = _read_named(args.diff)
        diff = (
            _unavailable_input("diff", args.diff, raw.reason)
            if isinstance(raw, Unreadable)
            else raw
            if isinstance(raw, bytes)
            else None
        )
    return previous, diff


def _declared_jev(tiers, kind):
    """The jev one tier declares; an absent, unknown or refused tier declares nothing."""
    result = dict(tiers).get(kind)
    if result is None:
        return None
    tier = result.value if isinstance(result, Built) else result.tier
    return None if tier.unknown else tier.get("jev")


def _handoff_scope(previous):
    """The scope the handoff names; a handoff that did not read names none."""
    result = previous.result if previous is not None else None
    return result.value.scope if isinstance(result, Built) else None


def _consent_tiers(args, previous):
    """Read every tier that may hold Jev consent, as (tier name, result) pairs.

    The repository tier lives at the project root, or at the repository root when no
    project root is named. The handoff's own feature or epic tier is read as well, so a
    scoped jev is refused there instead of being ignored.
    """
    global_config = args.global_config or str(Path.home() / ".nwave/config.json")
    root = args.project_root or args.repo_root
    scope = _handoff_scope(previous)
    named = [("global", None), ("repository", None)]
    if isinstance(scope, (handoff.Feature, handoff.Epic)):
        named.append((scope.kind.lower(), scope))
    tiers = tuple(
        (kind, read_configuration_tier(root, global_config, kind, scope))
        for kind, scope in named
    )
    defects = tuple(
        defect
        for _, result in tiers
        if isinstance(result, Refused)
        for defect in result.defects
    )
    return tiers, defects


def _approval_record(root, directory, slice_id):
    """The slice's oracle review record: Built(None) when none is recorded, else Built(mapping)."""
    scope = drafts.review_scope("oracle", slice_id)
    if isinstance(scope, Refused):
        return scope
    record_path = str(
        Path(directory) / "runs" / drafts.DraftKey("review", scope.value).filename
    )
    raw = read_file(str(Path(root) / record_path))
    if isinstance(raw, Missing):
        return Built(None)
    if isinstance(raw, Unreadable):
        return raw
    record = handoff.parse_json(raw, "review record")
    if isinstance(record, Refused):
        return record
    if not isinstance(record.value, Mapping):
        return checked(
            None,
            (
                Defect(
                    "HandoffInvalid: " + record_path,
                    "The review record is not a JSON object.",
                    "Rerun the oracle review so its record is published again.",
                ),
            ),
        )
    return Built(record.value)


def _approval_refusal(root, directory, slice_id, read_current, then):
    """Refuse once a slice's current oracle or support bytes differ from the approved ones.

    ``read_current`` returns the (path, bytes or None) pairs to compare; None when no review
    approved the slice, so nothing is checked.
    """
    record = _approval_record(root, directory, slice_id)
    if isinstance(record, Unreadable):
        return _inspection_failure((), (record,))
    if isinstance(record, Refused):
        return _refusal(record.defects)
    if record.value is None:
        return None
    current = read_current()
    if isinstance(current, Refused):
        return _refusal(current.defects)
    verdict = prompts.oracle_approval(
        slice_id,
        record.value.get("content"),
        drafts.content_digest(current.value),
        then,
    )
    return _refusal(verdict.defects) if isinstance(verdict, Refused) else None


def _approved_slice_paths(root, directory, slice_id, read_current):
    """The slice's oracle and support paths whose current bytes its oracle review approved.

    Nothing counts as approved without a recorded review, readable bytes, and bytes equal to
    the approved ones: the comparison _approval_refusal makes.
    """
    record = _approval_record(root, directory, slice_id)
    if not isinstance(record, Built) or record.value is None:
        return frozenset()
    recorded = record.value.get("content")
    current = read_current()
    if recorded is None or isinstance(current, Refused):
        return frozenset()
    verdict = prompts.oracle_approval(
        slice_id, recorded, drafts.content_digest(current.value), "commit them"
    )
    if isinstance(verdict, Refused):
        return frozenset()
    return frozenset(path for path, _ in current.value)


def _approved_oracle_paths(root, directory, ports, inspected):
    """The oracle and support paths the oracle review approved, across every designed slice."""
    slices = (inspected.result.value.design or {}).get("slices") or {}
    return frozenset().union(
        *(
            _approved_slice_paths(
                root,
                directory,
                slice_id,
                partial(_oracle_files, ports, root, inspected, slice_id),
            )
            for slice_id in slices
        )
    )


def _refuse_changed_oracle(args, previous):
    """Refuse a crafter prompt whose oracle bytes differ from the approved oracle review."""
    directory = os.path.relpath(Path(args.handoff).absolute().parent, args.repo_root)
    return _approval_refusal(
        args.repo_root,
        directory,
        args.slice,
        lambda: _oracle_files(
            _document_ports(args), args.repo_root, previous, args.slice
        ),
        "rebuild this prompt",
    )


def _prompt(args):
    admission = prompts.examination_admission(vars(args))
    if admission:
        return _refusal(admission)
    selected = prompts.recipe_for(args.role, args.task, args.phase)
    previous, diff = _read_handoff_diff(args)
    if (
        isinstance(selected, Built)
        and selected.value.review_subject is not None
        and args.commit is not None
        and not prompts._root_problems(args.repo_root)
    ):
        requested = _review_git(
            args.repo_root,
            ("rev-parse", "--verify", "--end-of-options", args.commit + "^{commit}"),
        )
        if isinstance(requested, Refused):
            _refusal(requested.defects)
            return 1
        args.commit = requested.value.strip()
    if (
        isinstance(selected, Built)
        and selected.value.id == "craft.impl-v4"
        and args.slice is not None
        and previous is not None
        and not prompts._root_problems(args.repo_root)
    ):
        changed = _refuse_changed_oracle(args, previous)
        if changed is not None:
            return changed
    template = None
    if isinstance(selected, Built):
        relative = prompts.template_path(selected.value)
        root = _installed_root()
        raw = read_asset(str(root), relative)
        if isinstance(raw, AssetMissing):
            template = handoff.UnavailableInput(
                Defect(
                    f"AssetMissing: {raw.path}",
                    raw.reason,
                    "Install the recipe's template beneath the installed nWave root.",
                )
            )
        elif isinstance(raw, AssetUnreadable):
            template = handoff.UnavailableInput(raw.defects[0])
        else:
            decoded = decode_utf8(raw, str(root / relative))
            template = (
                handoff.UnavailableInput(decoded.defects[0])
                if isinstance(decoded, AssetUnreadable)
                else decoded.value
            )
    flags = vars(args)
    if args.repo_root is not None:
        # This boundary knows invocation coordinates; renderers use the declared root.
        flags = {
            **flags,
            "repo_root": str(Path(args.repo_root).absolute()),
            "handoff": str(Path(args.handoff).absolute())
            if args.handoff is not None
            else None,
        }
    if flags.get("jev") is None:
        # Consent comes from a persistent, user-owned tier; with none declared, Jev is authorized.
        tiers, defects = _consent_tiers(args, previous)
        if defects:
            return _refusal(defects)
        flags = {
            **flags,
            "jev": prompts.resolved_jev(
                None,
                _declared_jev(tiers, "repository"),
                _declared_jev(tiers, "global"),
            ),
        }
    prepared = prompts.prepare_prompt(flags, previous, diff, template, args.policy)
    if isinstance(prepared, Refused):
        failure = _refusal(prepared.defects)
        return (
            1
            if any(
                defect.what.startswith(
                    ("InputUnreadable:", "AssetMissing:", "AssetUnreadable:")
                )
                for defect in prepared.defects
            )
            else failure
        )
    if prepared.value.recipe.id == "examine.user-v1":
        workspace = _examination_workspace(args.repo_root, args.handoff)
        if isinstance(workspace, Refused):
            return _examination_failure(workspace)
        prepared = Built(
            replace(
                prepared.value,
                inputs=replace(prepared.value.inputs, workspace=workspace.value),
            )
        )
    rendered = prepared.value.build()
    if isinstance(rendered, Refused):
        return _refusal(rendered.defects)
    sys.stdout.write(rendered.value)
    return 0


def _packet(args):
    admission = packets.examination_admission(vars(args))
    if admission:
        return _refusal(admission)
    previous, diff = _read_handoff_diff(args)
    flags = vars(args)
    prepared = packets.prepare_packet(flags, previous, diff)
    if isinstance(prepared, Refused):
        failure = _refusal(prepared.defects)
        return (
            1
            if any(
                defect.what.startswith("InputUnreadable:")
                for defect in prepared.defects
            )
            else failure
        )
    if prepared.value.kind is packets.PacketKind.Examine:
        workspace = _examination_workspace(args.repo_root, args.handoff)
        if isinstance(workspace, Refused):
            return _examination_failure(workspace)
        prepared = Built(replace(prepared.value, workspace=workspace.value))
    sys.stdout.write(prepared.value.build().value)
    return 0


def _examination_failure(result):
    _refusal(result.defects)
    return (
        1 if any(d.what.startswith("InputUnreadable:") for d in result.defects) else 2
    )


def _examination_workspace(root, handoff):
    """The examine prompt's workspace; its record lives in this checkout's private nwdes directory."""
    locations = _commit_locations(root)
    if isinstance(locations, Refused):
        return locations
    return probe.materialize(root, locations.value.workspaces, handoff)


def _lane(args):
    configuration = (
        read_lane_configuration(args.repo_root, str(Path.home() / ".nwave/config.json"))
        if args.repo_root
        else ConfigurationRead({}, (), False)
    )
    config, defects = configuration.values, configuration.defects
    observed, failures = observe_lane(
        args.repo_root, args.feature, args.action, config, vars(args)
    )
    observed["configuration_errors"] = defects
    resources = _lane_rekey_inputs(args, observed) if args.action == "rekey" else None
    prepared = lanes.prepare_lane(
        args.action,
        vars(args),
        observed,
        resources["inspection"] if resources else None,
    )
    if resources:
        defects = (*defects, *resources["defects"])
        failures = (*failures, *resources["failures"])
    defects = (*defects, *(prepared.defects if isinstance(prepared, Refused) else ()))
    failure = _inspection_failure(
        defects, failures, resources["brand"] if resources else None
    )
    if failure:
        return (
            1
            if configuration.operational or (resources and resources["operational"])
            else failure
        )
    plan = prepared.value
    if isinstance(plan, lanes.IntegrationPlan):
        if not plan.already_integrated:
            command = ("merge", "--ff-only", plan.candidate.tip)
            result = run_git(plan.checkout.root, command)
            if _git_failure(result, command, args):
                return 1
        command = ("rev-parse", "refs/heads/" + plan.checkout.branch)
        actual = run_git(plan.checkout.root, command)
        if _git_failure(actual, command, args):
            return 1
        integrated = lanes.integrated(
            plan.candidate, actual.stdout.decode().strip(), args.repo_root, args.feature
        )
        if isinstance(integrated, Refused):
            _refusal(integrated.defects)
            return 1
        print("INTEGRATED", integrated.value.commit)
        removed = remove_paths(
            str(Path(plan.location.root) / plan.location.path),
            tuple(item.path for item in plan.disposable),
        )
        if isinstance(removed, IOFailure):
            _effect_failure(
                args,
                "RemovePaths " + ", ".join(item.path for item in plan.disposable),
                f"The filesystem refused the change: {removed.reason}.",
            )
            return 1
        for status, path in removed.paths:
            print(status, path)
        if plan.worktree:
            result = run_git(
                plan.location.root, ("worktree", "remove", plan.location.path)
            )
            if _git_failure(result, ("worktree", "remove", plan.location.path), args):
                return 1
            print("REMOVED", plan.location.path)
        if plan.branch:
            # Compare and delete only the lane tip admitted as contained in CANDIDATE.
            command = (
                "update-ref",
                "-d",
                "refs/heads/" + plan.location.branch,
                plan.branch,
            )
            result = run_git(plan.location.root, command)
            if _git_failure(result, command, args):
                return 1
        if plan.branch or not plan.worktree:
            section = "branch." + plan.location.branch
            command = (
                "config",
                "--local",
                "--get-regexp",
                "^" + re.escape(section) + r"\.",
            )
            result = run_git(plan.location.root, command)
            if isinstance(result, Unreadable) or result.code != 1:
                if _git_failure(result, command, args):
                    return 1
                command = ("config", "--local", "--remove-section", section)
                result = run_git(plan.location.root, command)
                if _git_failure(result, command, args):
                    return 1
            if plan.branch:
                print("REMOVED", plan.location.branch)
        return 0
    if isinstance(plan, lanes.RekeyPlan):
        outputs = documents.rekey_adr(
            resources["inspection"].result.value,
            documents.RekeyRegisters(
                resources["register"], observed.get("trunk_register", ())
            ),
            plan.key,
            resources["destinations"],
            resources["brand"].value,
        )
        written = _emit(resources["ports"], outputs)
        if written:
            return written
        original = next(
            entry.path for entry in resources["register"] if entry.key.text == plan.key
        )
        removed = remove_paths(
            str(Path(plan.location.root) / plan.location.path),
            (resources["destinations"].adr_directory + "/" + original,),
        )
        if isinstance(removed, IOFailure):
            _effect_failure(
                args,
                "RemovePaths "
                + resources["destinations"].adr_directory
                + "/"
                + original,
                f"The filesystem refused the change: {removed.reason}.",
            )
            return 1
        for status, path in removed.paths:
            print(status, path)
        return 0
    if isinstance(plan, lanes.ComposePlan):
        result = run_git(
            str(Path(plan.location.root) / plan.location.path),
            ("merge", "--no-edit", "refs/heads/" + plan.trunk),
        )
        if _git_failure(
            result, ("merge", "--no-edit", "refs/heads/" + plan.trunk), args
        ):
            return 1
        tip = run_git(
            plan.location.root, ("rev-parse", "refs/heads/" + plan.location.branch)
        )
        if _git_failure(tip, ("rev-parse", "refs/heads/" + plan.location.branch), args):
            return 1
        print("EXPECTED", plan.expected)
        print("CANDIDATE", tip.stdout.decode().strip())
        return 0
    if plan.present:
        print("PRESENT")
        return 0
    exclusion = ensure_exclude(plan.location.root)
    if isinstance(exclusion, IOFailure):
        _effect_failure(
            args,
            "EnsureExclude .git/info/exclude",
            f"The filesystem refused the change: {exclusion.reason}.",
        )
        return 1
    result = run_git(
        plan.location.root,
        (
            "worktree",
            "add",
            "-b",
            plan.location.branch,
            plan.location.path,
            "refs/heads/" + plan.trunk,
        ),
    )
    if _git_failure(
        result,
        (
            "worktree",
            "add",
            "-b",
            plan.location.branch,
            plan.location.path,
            "refs/heads/" + plan.trunk,
        ),
        args,
    ):
        return 1
    print("OPENED")
    return 0


def _effect_failure(args, step, why):
    command = f"nwdes lane {args.action} --repo-root {args.repo_root} --feature {args.feature}"
    match args.action:
        case "compose":
            how = (
                "Correct the cause in WHY; if git left a merge in progress, run git -C "
                f"{Path(args.repo_root) / 'lanes' / args.feature} merge --abort; then rerun {command}."
            )
        case "integrate":
            how = (
                f"Correct the cause in WHY, then rerun {command} "
                f"--expected {args.expected} --candidate {args.candidate} with the same "
                "values; it continues from the observed state. If the rerun reports "
                f"TrunkMoved, run nwdes lane compose --repo-root {args.repo_root} "
                f"--feature {args.feature} and integrate with the two values it prints."
            )
        case "rekey":
            how = (
                f"Correct the cause in WHY, then rerun {command} --key {args.key}; "
                "it converges on the uninterrupted result."
            )
        case _:
            how = f"Correct the cause in WHY, then rerun {command}."
    _refusal((Defect("EffectFailed: " + step, why, how),))


def _git_failure(result, arguments, args):
    if isinstance(result, Unreadable) or result.code:
        _effect_failure(args, "git " + " ".join(arguments), failure_reason(result))
        return True
    return False


def _lane_rekey_inputs(args, observed):
    lane = observed.get("lane", {})
    if not isinstance(lane, Mapping) or lane.get("path") != "worktree":
        return None
    root = str(Path(args.repo_root) / "lanes" / args.feature)
    local = argparse.Namespace(repo_root=root, project_root=root, global_config=None)
    ports = _document_ports(local)
    scope = handoff.build_scope("Feature", args.feature).value
    tiers = tuple(
        ports.configuration(kind, scope) for kind in ("global", "repository", "feature")
    )
    destinations = resolve(tiers, scope)
    brand = _brand(ports)
    defects = tuple(destinations.defects if isinstance(destinations, Refused) else ())
    failures = []
    directory = readable_directory(tiers, scope)
    adr = readable_setting(tiers, "adr.directory", "docs/product/architecture")
    register = []
    if adr is not None:
        files = read_register_files(root, adr)
        if isinstance(files, Unreadable):
            failures.append(files)
            observed["register"] = handoff.UnavailableInput(
                Defect(
                    "InputUnreadable: " + files.path,
                    files.reason,
                    "Make the ADR register readable before retrying.",
                )
            )
        else:
            records = []
            for name, raw in files.value.items():
                if isinstance(raw, handoff.UnavailableInput):
                    records.append((documents.parse_adr_filename(name).text, name, raw))
                    failures.append(
                        Unreadable(str(Path(root) / adr / name), raw.defect.why)
                    )
                    continue
                entry = documents.read_adr({name: raw}).value[0]
                register.append(entry)
                records.append((entry.key.text, entry.path, entry.body is not None))
            observed["register"] = tuple(records)
    observed["supersedes"] = {
        entry.key.text: [
            previous.key.text
            for previous in register
            if previous.status == "Superseded by " + entry.key.text
        ]
        for entry in register
    }
    previous = (
        ports.file(str(Path(root) / directory / "handoff.json"))
        if directory is not None
        else None
    )
    inspection = (
        handoff.inspect_handoff(previous) if isinstance(previous, bytes) else None
    )
    if isinstance(previous, Unreadable):
        failures.append(previous)
    observed["previous_ready"] = directory is not None and not isinstance(
        previous, Unreadable
    )
    confined = ports.confinement(
        (*readable_paths(tiers, scope), *((adr,) if adr is not None else ()))
    )
    if isinstance(confined, Refused):
        defects = (*defects, *confined.defects)
    return {
        "ports": ports,
        "destinations": destinations.value if isinstance(destinations, Built) else None,
        "inspection": inspection,
        "register": tuple(register),
        "brand": brand,
        "defects": defects,
        "failures": tuple(failures),
        "operational": configuration_failed(tiers),
    }


def _review_subject(tokens):
    """The --subject the review parser binds: its last occurrence, in either spelling."""
    subject = None
    for index, token in enumerate(tokens):
        if token == "--subject" and index + 1 < len(tokens):
            subject = tokens[index + 1]
        elif token.startswith("--subject="):
            subject = token.partition("=")[2]
    return subject


def _slice_required(arguments):
    """True when the probed nwdes command names a slice it requires or owns."""
    argv = list(arguments[1:] if arguments[:1] == ["--"] else arguments)
    tokens = argv[1:]
    if tokens[:1] == ["review"] and _review_subject(tokens) in ("oracle", "slice"):
        return True
    for command in grammar.COMMANDS:
        words = command.name.split()
        if tokens[: len(words)] == words:
            return any(
                argument.flag == "--slice" and argument.meaning.startswith("required;")
                for argument in command.arguments
            )
    return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv and not argv[0].startswith("-") else None
    if verb in ("prompt", "packet"):
        retired = grammar.retired(argv)
        if retired:
            return _refusal(tuple(packets.self_gathered(name) for name in retired))
    action = (
        argv[1]
        if len(argv) > 1
        and not argv[1].startswith("-")
        and any(c.verb == verb and c.action is not None for c in grammar.COMMANDS)
        else None
    )
    if verb in drafts.KINDS:
        action = next(
            (
                row.name
                for row in drafts.role_verbs(verb)
                if argv[1 : 1 + len(row.name.split())] == row.name.split()
            ),
            action,
        )
    help_result = grammar.help_text(verb, action)
    if isinstance(help_result, Refused):
        return _refusal(help_result.defects)
    if (
        "--help" in argv
        and not (verb == "examine" and action == "probe" and "--" in argv)
    ) or not argv:
        sys.stdout.write(help_result.value)
        return 0
    try:
        args = PARSER.parse_args(argv)
    except _Usage as error:
        if error.defects:
            return _refusal(error.defects)
        return _refusal(
            (
                Defect(
                    "PartInvalid: command line",
                    str(error),
                    "Use nwdes --help for the declared invocation grammar.",
                ),
            )
        )
    if args.verb == "measure":
        return _measure(args)
    if not getattr(args, "repo_root", None):
        args.repo_root = str(Path.cwd())
        if args.verb == "lane":
            common = run_git(
                args.repo_root,
                ("rev-parse", "--path-format=absolute", "--git-common-dir"),
            )
            if not isinstance(common, Unreadable) and common.code == 0:
                args.repo_root = str(Path(common.stdout.decode("utf-8").strip()).parent)
    if not getattr(args, "project_root", None):
        args.project_root = args.repo_root
    if args.verb is None:
        sys.stdout.write(grammar.help_text().value)
        return 0
    loaded = _load_policy()
    if isinstance(loaded, Refused):
        return _refusal(loaded.defects)
    args.policy = loaded.value
    if getattr(args, "examination_action", None):
        if any(
            token == "--slice" or token.startswith("--slice=")
            for token in args.arguments
        ) and not (
            args.examination_action == "probe" and _slice_required(args.arguments)
        ):
            return _examination_failure(
                checked(
                    None,
                    (
                        Defect(
                            "PartInvalid: --slice",
                            "An EXAMINE judges the complete Feature, never an individual slice.",
                            "Repeat nwdes examine probe or read without --slice.",
                        ),
                    ),
                )
            )
        result = probe.run(
            args.repo_root, args.workspace, args.examination_action, args.arguments
        )
        return _examination_failure(result) if isinstance(result, Refused) else result
    if args.verb in drafts.KINDS:
        from types import SimpleNamespace

        result = drafts.run(
            SimpleNamespace(run_role=_run_role), args.verb, args.role_verb, vars(args)
        )
        return _refusal(result.defects) if isinstance(result, Refused) else result
    if args.verb == "lane":
        return _lane(args)
    if args.verb == "prompt":
        return _prompt(args)
    if args.verb == "packet":
        return _packet(args)
    if args.verb == "commit":
        return _commit(args)
    args.invocation = handoff.invocation(
        args.verb,
        getattr(args, "action", None),
        vars(args),
        project_root_is_directory=bool(
            args.project_root and Path(args.project_root).is_dir()
        ),
    )
    args.scope = (
        args.invocation.scope.value
        if isinstance(args.invocation.scope, Built)
        else None
    )
    defects = args.invocation.defects
    if args.verb == "delta":
        return _delta(args, defects)
    if args.verb == "work":
        return _work_set(args, defects)
    return _document(args, _document_ports(args), defects)


def _write_role_bytes(root, path, raw):
    confined = check_paths(root, (path,))
    if isinstance(confined, Refused):
        return _refusal(confined.defects)
    result = write_outputs(
        root,
        documents.OutputSet(
            (
                documents.Output(
                    documents.OutputKind.Handoff,
                    path,
                    raw,
                ),
            )
        ),
    )
    if isinstance(result, IOFailure):
        return _role_effect_failure(result)
    return 0


def _role_values(kind, verb, supplied):
    values = {name.replace("_", "-"): value for name, value in supplied.items()}
    defects = []
    for field in verb.fields:
        value = values.get(field.name)
        if value is None:
            continue
        if field.text:
            occurrences = value if field.repeated else (value,)
            decoded = []
            for item in occurrences:
                if (
                    isinstance(item, tuple)
                    and len(item) == 2
                    and isinstance(item[0], bool)
                ):
                    is_file, text = item
                    raw = _read_named(text) if is_file else None
                    if isinstance(raw, bytes):
                        text = raw.decode("utf-8")
                    elif raw is not None:
                        defects.append(
                            Defect(
                                "InputUnreadable: --" + field.name + "-file " + text,
                                raw.reason,
                                "Supply a readable strict UTF-8 file for this field.",
                            )
                        )
                    decoded.append(text)
                else:
                    decoded.append(item)
            values[field.name] = tuple(decoded) if field.repeated else decoded[0]
    return checked(handoff.freeze(values), defects)


def _run_role(kind, name, supplied):
    verb = next(row for row in drafts.role_verbs(kind) if row.name == name)
    normalized = _role_values(kind, verb, supplied)
    if isinstance(normalized, Refused):
        return _refusal(normalized.defects)
    return _record_role(kind, name, normalized.value)


@dataclass(frozen=True)
class _DraftScope:
    destinations: Destinations
    directory: str
    key: drafts.DraftKey
    path: str
    handoff_bytes: bytes


@dataclass(frozen=True)
class _RoleContext:
    args: object
    ports: DocumentPorts
    destinations: Destinations
    review: Built | None


def _resolve_destinations(args, ports):
    tiers = tuple(
        ports.configuration(tier, args.scope)
        for tier in ("global", "repository", args.scope.kind.lower())
    )
    return resolve(tiers, args.scope)


def _record_role(kind, name, values):
    review = None
    if kind == "review":
        review = values.get("review-scope")
        if review is None:
            review = drafts.review_scope(values.get("subject"), values.get("slice"))
        if isinstance(review, Refused):
            return _refusal(review.defects)
    from types import SimpleNamespace

    args = SimpleNamespace(
        **{
            **{option.replace("-", "_"): None for option in grammar.SINGLE_OPTIONS},
            **{key.replace("-", "_"): value for key, value in values.items()},
            "verb": kind if kind in handoff.ROLE_SCHEMAS else "document",
            "action": "revise" if values.get("revise") else "apply",
            "product": False,
        }
    )
    args.invocation = handoff.invocation(
        args.verb,
        args.action,
        vars(args),
        project_root_is_directory=bool(
            args.project_root and Path(args.project_root).is_dir()
        ),
    )
    args.scope = (
        args.invocation.scope.value
        if isinstance(args.invocation.scope, Built)
        else None
    )
    if args.invocation.defects:
        return _refusal(args.invocation.defects)
    ports = _document_ports(args)
    resolved = _resolve_destinations(args, ports)
    if isinstance(resolved, Refused):
        return _refusal(resolved.defects)
    context = _RoleContext(args, ports, resolved.value, review)
    if name == "close":
        return _record_close(kind, name, values, context)
    return _record_role_scoped(kind, name, values, context, None)


def _recorded_scope(scope, slice_id):
    """Scope a close records on its receipt: feature or epic, plus any slice."""
    return handoff.freeze(
        {
            **handoff.to_data(scope),
            **({"slice": slice_id} if slice_id is not None else {}),
        }
    )


def _record_role_scoped(kind, name, values, context, close_session):
    args, ports, destinations, review = (
        context.args,
        context.ports,
        context.destinations,
        context.review,
    )
    handoff_path = str(Path(args.repo_root) / destinations.handoff)
    current = (
        close_session.inputs.handoff
        if close_session is not None
        else ports.file(handoff_path)
    )
    if isinstance(current, Missing):
        return _refusal(
            (
                Defect(
                    "MissingFact: " + handoff_path,
                    "This checkout has no handoff for the requested scope.",
                    "Run from the bundle's working directory or pass --repo-root naming the checkout that holds this handoff.",
                ),
            )
        )
    if isinstance(current, Unreadable):
        return _inspection_failure((), (current,))
    directory = str(Path(destinations.handoff).parent)
    key = drafts.DraftKey(
        kind,
        review.value
        if review is not None
        else args.slice
        if kind in ("acceptance", "charter", "craft")
        else None,
    )
    path = str(Path(directory) / ".nwdes-drafts" / key.filename)
    scope = _DraftScope(destinations, directory, key, path, current)
    if kind == "review" and name == "findings":
        return _read_review_findings(args, ports, scope, values["owner"])
    if close_session is not None:
        recorded_scope = _recorded_scope(args.scope, args.slice)
        original_ports = ports
        ports = replace(
            _pinned_ports(ports, close_session.inputs),
            outputs=lambda outputs: _publish_role_close(
                original_ports, outputs, close_session, recorded_scope
            ),
        )
    lock = Path(args.repo_root) / (path + ".lock")
    confined = ports.confinement((path, path + ".lock", path + ".closing"))
    if isinstance(confined, Refused):
        return _refusal(confined.defects)
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return _refusal(
            (
                Defect(
                    "PartInvalid: draft locked " + str(lock),
                    "Another recording verb holds this draft's lock.",
                    "If no other session is running, delete "
                    + str(lock)
                    + "; otherwise let it finish before retrying.",
                ),
            )
        )
    except OSError as error:
        return _role_effect_failure(IOFailure((str(lock),), str(error)))
    try:
        os.close(descriptor)
        if name == "abort" and kind == "examine":
            failure = _discard_workspace(args, destinations)
            if failure is not None:
                return failure
        return _record_draft(name, values, args, ports, scope)
    finally:
        try:
            lock.unlink()
        except OSError as error:
            print(
                "WARNING WHAT: Draft lock cleanup failed: "
                + str(lock)
                + "\nWHY: "
                + str(error)
                + "\nHOW: Restore filesystem access and remove the named leftover lock; the command outcome is unchanged.",
                file=sys.stderr,
            )


def _record_draft(name, values, args, ports, scope: _DraftScope):
    kind = scope.key.kind
    path = scope.path
    source = ports.file(str(Path(args.repo_root) / path))
    closing = path + ".closing"
    closing_source = ports.file(str(Path(args.repo_root) / closing))
    if not isinstance(closing_source, Missing) and name != "abort":
        return _refusal(
            (
                Defect(
                    "PartInvalid: draft closing " + path,
                    "A prior close consumed this draft; its publication or cleanup left "
                    + closing
                    + ".",
                    "Do not close it again. Run nwdes "
                    + kind
                    + " abort with the same scope to discard the leftover draft.",
                ),
            )
        )
    if isinstance(source, Unreadable):
        return _inspection_failure((), (source,))
    if (
        isinstance(source, Missing)
        and isinstance(closing_source, Missing)
        and name == "abort"
    ):
        return _refusal(
            (
                Defect(
                    "PartInvalid: no open draft " + path,
                    "This kind and scope have no open draft.",
                    "The first add, set or remove verb of nwdes "
                    + kind
                    + " creates its draft; record a value first.",
                ),
            )
        )
    if name == "abort":
        paths = tuple(
            candidate
            for candidate, content in ((path, source), (closing, closing_source))
            if not isinstance(content, Missing)
        )
        removed = remove_paths(args.repo_root, paths)
        if isinstance(removed, IOFailure):
            return _role_effect_failure(removed)
        print("ABORTED", kind)
        return 0
    if isinstance(source, bytes) and name != "open":
        loaded = handoff.parse_json(source, "draft")
        if isinstance(loaded, Refused):
            return _refusal(loaded.defects)
        draft = loaded.value
    else:
        draft = drafts.empty(kind)
    before = draft
    evidence = None
    if drafts.needs_review_evidence(kind, name):
        files, others = None, ()
        slice_id = drafts.oracle_slice(scope.key.scope)
        if slice_id is not None:
            approved = _oracle_files(
                ports,
                args.repo_root,
                handoff.inspect_handoff(scope.handoff_bytes),
                slice_id,
            )
            if isinstance(approved, Refused):
                _refusal(approved.defects)
                return 1
            files = approved.value
            others = _other_oracle_paths(
                handoff.inspect_handoff(scope.handoff_bytes), slice_id
            )
        observed = _review_evidence(args.repo_root, scope.directory, files, others)
        if isinstance(observed, Refused):
            _refusal(observed.defects)
            return 1
        evidence = observed.value
    if name == "open" and kind in ("craft", "review"):
        record_path = str(Path(scope.directory) / "runs" / scope.key.filename)
        confined = ports.confinement((record_path,))
        if isinstance(confined, Refused):
            return _refusal(confined.defects)
        current = ports.file(str(Path(args.repo_root) / record_path))
        if isinstance(current, Unreadable):
            return _inspection_failure((), (current,))
        if isinstance(current, bytes):
            parsed = handoff.parse_json(current, "run record")
            if isinstance(parsed, Refused):
                return _refusal(parsed.defects)
            draft = drafts.seed(parsed.value, kind)
            if isinstance(draft, Refused):
                return _refusal(draft.defects)
    elif name == "open":
        inspected = handoff.inspect_handoff(scope.handoff_bytes)
        if isinstance(inspected.result, Refused):
            return _refusal(inspected.result.defects)
        adr_bodies = handoff.EMPTY
        if kind == "design" and (inspected.result.value.design or {}).get("adrs"):
            register = ports.register(scope.destinations.adr_directory)
            if isinstance(register, Unreadable):
                return _inspection_failure((), (register,))
            if isinstance(register, Refused):
                return _refusal(register.defects)
            adr_bodies = handoff.Record(
                (entry.key.text, entry.body) for entry in register.value
            )
        draft = drafts.seed(
            inspected.result.value, kind, args.slice, adr_bodies=adr_bodies
        )
    elif name == "close":
        if kind == "review" and drafts.candidate_scope(scope.key.scope):
            refused = _refuse_committed_oracles(args, ports, scope)
            if refused is not None:
                return refused
        reviewed = (
            drafts.review_record(
                draft, evidence, values["outcome"], values["diagnostic"]
            )
            if kind == "review"
            else None
        )
        if isinstance(reviewed, Refused):
            return _refusal(reviewed.defects)
        owner_notice = ""
        paradigm = None
        if kind == "review" and values["outcome"] == "rejected":
            inspected = handoff.inspect_handoff(scope.handoff_bytes)
            if isinstance(inspected.result, Refused):
                return _refusal(inspected.result.defects)
            paradigm = (inspected.result.value.design or handoff.EMPTY).get("paradigm")
        raw = drafts.envelope_bytes(draft, values["outcome"], values["diagnostic"])
        publishing = (
            replace(
                ports,
                outputs=lambda outputs: _publish_draft(
                    kind, args.repo_root, path, ports, outputs
                ),
            )
            if isinstance(source, bytes)
            else ports
        )
        if kind in ("craft", "review"):
            record = (
                reviewed.value
                if reviewed is not None
                else handoff.freeze(
                    {
                        **draft,
                        "outcome": values["outcome"],
                        "diagnostic": values["diagnostic"],
                        **(
                            {
                                "blocked_by": values.get("blocked-by"),
                                "slice": args.slice,
                            }
                            if kind == "craft"
                            else {}
                        ),
                    }
                )
            )
            if kind == "review" and values["outcome"] == "rejected":
                flags = shlex.join(
                    (
                        "--subject",
                        values["subject"],
                        *(("--slice", args.slice) if args.slice else ()),
                        *(("--feature", args.feature) if args.feature else ()),
                        *(("--epic", args.epic) if args.epic else ()),
                    )
                )
                owner_notice = drafts.owner_lines(record, paradigm, flags)
            result = _emit(
                publishing,
                documents.OutputSet(
                    (
                        documents.Output(
                            documents.OutputKind.Handoff,
                            str(Path(scope.directory) / "runs" / scope.key.filename),
                            drafts.record_bytes(record),
                        ),
                    )
                ),
            )
        else:
            result = _document(args, publishing, raw=raw, existing=scope.handoff_bytes)
        if result:
            return result
        print("RECORDED", kind)
        if owner_notice:
            print(owner_notice)
        return 0
    else:
        previous = None
        if kind == "product":
            inspected = handoff.inspect_handoff(scope.handoff_bytes)
            previous = handoff._invocation_source(inspected, args.scope)
        edit = drafts.prepare_edit(
            kind, name, values, previous=previous, policy=args.policy
        )
        if isinstance(edit, Refused):
            return _refusal(edit.defects)
        if evidence is not None:
            edit = drafts.stamp_review(edit, evidence)
        draft = drafts.apply_edit(draft, edit, previous=previous)
        if isinstance(draft, Refused):
            return _refusal(draft.defects)
    result = _write_role_bytes(args.repo_root, path, drafts.draft_bytes(draft))
    if result == 0:
        identity = drafts.issued(kind, name, before, draft)
        print("RECORDED", kind, name, *((identity,) if identity is not None else ()))
    return result


def _review_git(root, arguments):
    result = run_git(root, arguments, env=scrubbed_env(os.environ))
    if isinstance(result, Unreadable) or result.code:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: git " + " ".join(arguments),
                    failure_reason(result),
                    "Run from the candidate git checkout with git on PATH before recording or reviewing evidence.",
                ),
            ),
        )
    return Built(result.stdout.decode("utf-8", "surrogateescape"))


def _oracle_paths(inspected, slice_id):
    """The slice's declared oracle and support paths, or the handoff refusal."""
    if inspected is None:
        return Built(())
    if isinstance(inspected.result, Refused):
        return inspected.result
    design = inspected.result.value.design or {}
    declared = (design.get("slices") or {}).get(slice_id) or {}
    return Built(
        tuple(
            path
            for path in (declared.get("oracle"), *(declared.get("supports") or ()))
            if path
        )
    )


def _other_oracle_paths(inspected, slice_id):
    """Oracle and support paths of every other designed slice: work that is not under review."""
    if inspected is None or isinstance(inspected.result, Refused):
        return ()
    slices = (inspected.result.value.design or {}).get("slices") or {}
    return tuple(
        path
        for other in slices
        if other != slice_id
        for path in _oracle_paths(inspected, other).value
    )


def _oracle_files(ports, root, inspected, slice_id):
    """The slice's oracle and supports as (path, bytes or None) pairs read from the checkout."""
    paths = _oracle_paths(inspected, slice_id)
    if isinstance(paths, Refused):
        return paths
    confined = ports.confinement(paths.value)
    if isinstance(confined, Refused):
        return confined
    pairs = []
    for path in paths.value:
        raw = read_file(str(Path(root) / path))
        if isinstance(raw, Unreadable):
            return checked(
                None,
                (
                    Defect(
                        "InputUnreadable: " + path,
                        raw.reason,
                        "Make the slice's oracle and supports readable from the checkout before reviewing them.",
                    ),
                ),
            )
        pairs.append((path, None if isinstance(raw, Missing) else raw))
    return Built(tuple(pairs))


def _head_oracle_files(ports, root, inspected, slice_id):
    """The slice's oracle and supports as committed at HEAD: (path, bytes or None) pairs."""
    paths = _oracle_paths(inspected, slice_id)
    if isinstance(paths, Refused):
        return paths
    confined = ports.confinement(paths.value)
    if isinstance(confined, Refused):
        return confined
    return _head_blobs(root, "HEAD", paths.value)


def _refuse_committed_oracles(args, ports, scope):
    """Refuse a candidate close whose committed oracle or support bytes differ from an approval."""
    inspected = handoff.inspect_handoff(scope.handoff_bytes)
    if isinstance(inspected.result, Refused):
        return _refusal(inspected.result.defects)
    design = inspected.result.value.design or {}
    for slice_id in sorted(design.get("slices") or {}):
        refusal = _approval_refusal(
            args.repo_root,
            scope.directory,
            slice_id,
            partial(_head_oracle_files, ports, args.repo_root, inspected, slice_id),
            "commit them",
        )
        if refusal is not None:
            return refusal
    return None


def _review_evidence(root, directory, files=None, others=()):
    head = _review_git(root, ("rev-parse", "--verify", "HEAD^{commit}"))
    status = _review_git(
        root, ("status", "--porcelain", "-z", "--untracked-files=all", "--no-renames")
    )
    problems = tuple(
        defect
        for result in (head, status)
        if isinstance(result, Refused)
        for defect in result.defects
    )
    if problems:
        return checked(None, problems)
    return Built(
        drafts.review_evidence(
            head.value.strip(), _status_entries(status.value), directory, files, others
        )
    )


def _read_review_findings(args, ports, scope, owner):
    path = str(Path(scope.directory) / "runs" / scope.key.filename)
    confined = ports.confinement((path,))
    if isinstance(confined, Refused):
        return _refusal(confined.defects)
    raw = ports.file(str(Path(args.repo_root) / path))
    if isinstance(raw, Missing):
        return _refusal(
            (
                Defect(
                    "MissingFact: " + path,
                    "No review record has been published for this subject and slice.",
                    "Record the review and publish it with nwdes review close before reading findings.",
                ),
            )
        )
    if isinstance(raw, Unreadable):
        return _inspection_failure((), (raw,))
    record = handoff.parse_json(raw, "review record")
    if isinstance(record, Refused):
        return _refusal(record.defects)
    sys.stdout.write(drafts.owner_findings(record.value, owner))
    return 0


def _publish_draft(kind, root, path, ports, outputs):
    draft = Path(root) / path
    closing = path + ".closing"
    consumed = Path(root) / closing
    try:
        draft.rename(consumed)
    except OSError as error:
        return IOFailure((path,), str(error))
    result = ports.outputs(outputs)
    if isinstance(result, IOFailure):
        try:
            consumed.rename(draft)
        except OSError as error:
            return IOFailure(
                (*result.unwritten, closing),
                result.reason
                + "; restoring the unpublished draft failed: "
                + str(error),
            )
        return result
    removed = remove_paths(root, (closing,))
    if isinstance(removed, IOFailure):
        print(
            "WARNING WHAT: Published draft cleanup failed: "
            + closing
            + "\nWHY: "
            + removed.reason
            + "\nHOW: Publication succeeded and this draft cannot be closed again. Restore filesystem access and use nwdes "
            + kind
            + " abort with the same scope to remove the leftover draft.",
            file=sys.stderr,
        )
    return result


def _role_effect_failure(failure):
    _refusal(
        (
            Defect(
                "OutputUnreadable: " + ", ".join(failure.unwritten),
                failure.reason,
                "Restore filesystem access and retry the same role verb; the draft remains available.",
            ),
        )
    )
    return 1


def _measure_values(argv):
    """Decode native argv with the same parser as the producing CLI, without effects."""
    try:
        args = REPLAY_PARSER.parse_args(list(argv))
    except (_Usage, ValueError, TypeError):
        return None
    if args.verb in drafts.KINDS:
        verb = next(
            row for row in drafts.role_verbs(args.verb) if row.name == args.role_verb
        )
        result = _role_values(args.verb, verb, vars(args))
        if isinstance(result, Refused):
            return None
        if args.verb == "review" and isinstance(args.review_scope.value, drafts.Legacy):
            return handoff.freeze({**result.value, "subject": "legacy"})
        return result.value
    return handoff.freeze(
        {name.replace("_", "-"): value for name, value in vars(args).items()}
    )


def _measure(args):
    repeated = tuple(
        name
        for name in grammar.MEASURE_OPTIONS
        if len(getattr(args, name.replace("-", "_")) or ()) > 1
    )
    supplied = {
        name
        for name in grammar.MEASURE_OPTIONS
        if getattr(args, name.replace("-", "_"))
    }
    for name in grammar.MEASURE_OPTIONS:
        values = getattr(args, name.replace("-", "_"))
        setattr(args, name.replace("-", "_"), values[0] if values else None)
    sources = supplied & {"requests", "host-sessions"}
    host_only = set(grammar.MEASURE_OPTIONS) - {
        "requests",
        "host-sessions",
        "objective-minutes",
    }
    if (
        repeated
        or len(sources) != 1
        or ("requests" in supplied and supplied & host_only)
        or (args.feature and args.epic)
    ):
        return _refusal(
            (
                measurement.invalid(
                    "command line",
                    "Choose exactly one source, no repeated flags, and use candidate, rework and roots only with host sessions.",
                ),
            )
        )
    if args.objective_minutes is not None:
        if (
            not re.fullmatch(r"[0-9]+", args.objective_minutes)
            or int(args.objective_minutes) <= 0
        ):
            return _refusal(
                (
                    measurement.invalid(
                        "--objective-minutes",
                        "The objective must be a positive integer.",
                    ),
                )
            )
        args.objective_minutes = int(args.objective_minutes)
    if args.requests:
        read = host_sessions.read_named(args.requests, "--requests")
        if isinstance(read, Refused):
            code = _refusal(read.defects)
            return (
                1
                if any(d.what.startswith("InputUnreadable:") for d in read.defects)
                else code
            )
        result = measurement.report_from_requests(
            read.value, args.requests, args.objective_minutes
        )
        if isinstance(result, Refused):
            code = _refusal(result.defects)
            return (
                1
                if any(d.what.startswith("InputUnreadable:") for d in result.defects)
                else code
            )
        sys.stdout.write(measurement.render(result.value))
        return 0
    tree = host_sessions.read_tree(args.host_sessions)
    if isinstance(tree, Refused):
        causes = (
            "root session "
            + args.host_sessions
            + " "
            + "; ".join(d.what + " " + d.why for d in tree.defects),
        )
        sys.stdout.write(
            measurement.render(
                measurement.unavailable_report(
                    causes, args.objective_minutes, root=True
                )
            )
        )
        return 0
    context = measurement.session_occurrences(tree.value, _measure_values)
    args.repo_root = args.repo_root or str(Path.cwd())
    args.project_root = args.project_root or args.repo_root
    evidence = []
    if not args.feature and not args.epic:
        scopes = {
            (key, o.values[key])
            for o in context
            if o.values
            for key in ("feature", "epic")
            if o.values.get(key)
        }
        if len(scopes) == 1:
            key, value = next(iter(scopes))
            setattr(args, key, value)
    call = handoff.invocation(
        "document",
        None,
        vars(args),
        project_root_is_directory=Path(args.project_root).is_dir(),
    )
    path = ""
    if call.defects:
        evidence.extend(d.what + " " + d.why for d in call.defects)
    else:
        ports = _document_ports(args)
        scope = call.scope.value
        resolved = resolve(
            tuple(
                ports.configuration(tier, scope)
                for tier in ("global", "repository", scope.kind.lower())
            ),
            scope,
        )
        if isinstance(resolved, Refused):
            evidence.extend(d.what + " " + d.why for d in resolved.defects)
        else:
            path = resolved.value.handoff
    history, failures = (
        host_sessions.read_history(args.repo_root, args.candidate, path, context)
        if path
        else (None, ("unresolved handoff destination",))
    )
    evidence.extend(failures)
    rework = host_sessions.read_named(args.rework, "--rework") if args.rework else None
    rework_cause = (
        "; ".join(d.what + " " + d.why for d in rework.defects)
        if isinstance(rework, Refused)
        else None
    )
    result = measurement.report_from_sessions(
        tree.value,
        rework.value if isinstance(rework, Built) else None,
        args.rework,
        args.objective_minutes,
        evidence=measurement.SessionEvidence(
            history=history,
            handoff_path=path,
            parse_values=_measure_values,
            causes=tuple(evidence),
            rework_cause=rework_cause,
        ),
    )
    sys.stdout.write(measurement.render(result.value))
    return 0


def _commit_git(root, arguments):
    result = run_git(root, arguments)
    if isinstance(result, Unreadable) or result.code:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: git " + " ".join(arguments),
                    failure_reason(result),
                    "Run from the candidate Git checkout with git on PATH and correct the reported Git condition.",
                ),
            ),
        )
    return Built(result.stdout)


def _commit_failure(result):
    _refusal(result.defects)
    return (
        1
        if any(defect.what.startswith("InputUnreadable:") for defect in result.defects)
        else 2
    )


def _commit_locations(root):
    answer = _commit_git(root, ("rev-parse", "--git-path", "nwdes"))
    if isinstance(answer, Refused):
        return answer
    directory = answer.value.decode("utf-8", "surrogateescape").strip()
    return Built(CommitLocations(str((Path(root) / directory).resolve())))


@contextmanager
def _commit_lock(locations):
    descriptor = None
    acquiring = False
    try:
        Path(locations.lock).parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(locations.lock, os.O_CREAT | os.O_RDWR, 0o600)
        if os.name == "nt":
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            acquiring = True
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            acquiring = True
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        busy = isinstance(error, BlockingIOError) or (
            os.name == "nt"
            and acquiring
            and error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK)
        )
        yield checked(
            None,
            (
                Defect(
                    "CommitInProgress: " + locations.lock,
                    "Another nwdes commit or authority close holds the lane's exclusive lock.",
                    "Let that invocation finish, then rerun this command; never remove a live OS lock.",
                )
                if busy
                else Defect(
                    "InputUnreadable: " + locations.lock,
                    str(error),
                    "Restore access to the Git metadata directory, then rerun this command.",
                ),
            ),
        )
        return
    try:
        yield Built(locations)
    finally:
        os.close(descriptor)


def _read_close_receipts(locations):
    receipts = []
    for role in commits.Role:
        path = locations.receipt(role.value)
        raw = read_file(path)
        if isinstance(raw, Missing):
            continue
        if isinstance(raw, Unreadable):
            receipts.append(
                commits.ReceiptUnavailable(
                    role,
                    Defect(
                        "InputUnreadable: " + path,
                        raw.reason,
                        "Restore read access to the role's close receipt.",
                    ),
                )
            )
            continue
        parsed = commits.read_receipt(raw, path)
        receipts.append(
            commits.ReceiptUnavailable(role, parsed.defects[0])
            if isinstance(parsed, Refused)
            else parsed.value
        )
    return tuple(receipts)


def _current_digests(root, paths):
    values = []
    for relative in paths:
        path = Path(root) / relative
        try:
            raw = (
                os.readlink(os.fsencode(path))  # noqa: PTH115 - Path.readlink normalizes raw target bytes.
                if path.is_symlink()
                else path.read_bytes()
            )
            value = commits.digest(raw)
        except FileNotFoundError:
            value = None
        except OSError as error:
            value = handoff.UnavailableInput(
                Defect(
                    "InputUnreadable: " + relative,
                    str(error),
                    "Restore access to the named file before closing or committing.",
                )
            )
        values.append((relative, value))
    return handoff.Record(values)


def _receipt_digests(root, receipts, handoff_path, handoff_read):
    """Digest each covered path once; the handoff uses the bytes already read."""
    covered = dict.fromkeys(
        path
        for receipt in receipts
        if isinstance(receipt, commits.CloseReceipt)
        for path in receipt.paths
    )
    digests = _current_digests(
        root, tuple(path for path in covered if path != handoff_path)
    )
    if handoff_path not in covered:
        return digests
    return handoff.Record(
        (*digests.items(), (handoff_path, _read_digest(handoff_path, handoff_read)))
    )


def _read_digest(relative, read):
    if isinstance(read, Missing):
        return None
    if isinstance(read, Unreadable):
        return handoff.UnavailableInput(
            Defect(
                "InputUnreadable: " + relative,
                read.reason,
                "Restore access to the named file before closing or committing.",
            )
        )
    return commits.digest(read)


def _head_blobs(root, head, paths):
    """The committed bytes of each path at head as (path, bytes or None) pairs; None is absent."""
    if not paths:
        return Built(())
    listed = _commit_git(
        root,
        ("--literal-pathspecs", "ls-tree", "-rz", "--full-tree", head, "--", *paths),
    )
    if isinstance(listed, Refused):
        return listed
    oids = {}
    for row in listed.value.split(b"\0"):
        if not row:
            continue
        metadata, path = row.split(b"\t", 1)
        oids[path.decode("utf-8", "surrogateescape")] = metadata.split()[2].decode(
            "ascii"
        )
    blobs = {}
    for oid in set(oids.values()):
        content = _commit_git(root, ("cat-file", "blob", oid))
        if isinstance(content, Refused):
            return content
        blobs[oid] = content.value
    return Built(tuple((path, blobs.get(oids.get(path))) for path in paths))


def _head_digests(root, head, paths):
    if not paths:
        return Built(handoff.EMPTY)
    blobs = _head_blobs(root, head, paths)
    if isinstance(blobs, Refused):
        return blobs
    return Built(
        handoff.Record(
            (path, None if data is None else commits.digest(data))
            for path, data in blobs.value
        )
    )


@dataclass(frozen=True)
class _ReceiptSnapshot:
    head: str
    receipts: tuple[commits.CloseReceipt | commits.ReceiptUnavailable, ...]
    current: handoff.Record


def _active_close_receipts(root, locations, snapshot, retain_role=None):
    paths = tuple(
        dict.fromkeys(
            path
            for receipt in snapshot.receipts
            if isinstance(receipt, commits.CloseReceipt)
            for path in receipt.paths
        )
    )
    at_head = _head_digests(root, snapshot.head, paths)
    if isinstance(at_head, Refused):
        return at_head
    active = []
    for receipt in snapshot.receipts:
        if (
            isinstance(receipt, commits.ReceiptUnavailable)
            or receipt.role == retain_role
            or any(
                isinstance(snapshot.current.get(path), handoff.UnavailableInput)
                for path in receipt.paths
            )
            or commits.receipt_is_pending(receipt, snapshot.current, at_head.value)
        ):
            active.append(receipt)
            continue
        try:
            Path(locations.receipt(receipt.role.value)).unlink()
        except OSError as error:
            return checked(
                None,
                (
                    Defect(
                        "InputUnreadable: " + locations.receipt(receipt.role.value),
                        str(error),
                        "Restore access to the obsolete close receipt, then rerun.",
                    ),
                ),
            )
    return Built(tuple(active))


def _commit_context(args):
    args.product = False
    args.invocation = handoff.invocation(
        "document",
        None,
        vars(args),
        project_root_is_directory=Path(args.project_root).is_dir(),
    )
    if args.invocation.defects:
        return checked(None, args.invocation.defects)
    args.scope = args.invocation.scope.value
    ports = _document_ports(args)
    tiers = tuple(
        ports.configuration(tier, args.scope)
        for tier in ("global", "repository", args.scope.kind.lower())
    )
    resolved = resolve(tiers, args.scope)
    if isinstance(resolved, Refused):
        return resolved
    path = str(Path(args.repo_root) / resolved.value.handoff)
    raw = ports.file(path)
    if isinstance(raw, Missing):
        return checked(
            None,
            (
                Defect(
                    "MissingFact: " + path,
                    "The requested delivery has no published handoff.",
                    "Close the role's draft in this checkout before nwdes commit.",
                ),
            ),
        )
    if isinstance(raw, Unreadable):
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: " + path,
                    raw.reason,
                    "Restore read access to the published handoff before nwdes commit.",
                ),
            ),
        )
    inspected = handoff.inspect_handoff(raw)
    parsed = inspected.result
    return (
        parsed
        if isinstance(parsed, Refused)
        else Built((parsed.value, resolved.value, inspected))
    )


def _commit_observation(args, document, destinations, locations, inspected):
    head = _commit_git(args.repo_root, ("rev-parse", "--verify", "HEAD^{commit}"))
    status = _commit_git(
        args.repo_root,
        ("status", "--porcelain", "-z", "--untracked-files=all", "--no-renames"),
    )
    failures = tuple(
        defect
        for result in (head, status)
        if isinstance(result, Refused)
        for defect in result.defects
    )
    if failures:
        return checked(None, failures)
    entries = _status_entries(status.value.decode("utf-8", "surrogateescape"))
    changed = frozenset(path for code, path in entries if code != "!!")
    approved = _approved_oracle_paths(
        args.repo_root,
        destinations.handoff.rpartition("/")[0],
        _document_ports(args),
        inspected,
    )
    protected = commits.protected_paths(document, destinations, approved)
    owned = commits.owned_paths(
        commits.Role(args.role), document, destinations, args.slice
    )
    permission = commits.Permission(
        commits.Role(args.role),
        owned,
        commits.path_owners(document, destinations, (*changed, *args.path)),
        protected,
    )
    selection = commits.select_paths(permission, changed, tuple(args.path))
    selected = (
        selection.candidate_paths if isinstance(selection, Refused) else selection.value
    )
    receipts = _read_close_receipts(locations)
    paths = tuple(
        dict.fromkeys(
            path
            for receipt in receipts
            if isinstance(receipt, commits.CloseReceipt)
            for path in receipt.paths
        )
    )
    current = _current_digests(args.repo_root, paths)
    revision = head.value.decode("ascii").strip()
    active = _active_close_receipts(
        args.repo_root,
        locations,
        _ReceiptSnapshot(revision, receipts, current),
        retain_role=commits.Role(args.role),
    )
    if isinstance(active, Refused):
        return active
    return Built(
        commits.CommitObservation(
            revision,
            tuple(path for code, path in entries if code[0] not in (" ", "?", "!")),
            changed,
            active.value,
            current,
            frozenset(
                path
                for path in selected
                if (Path(args.repo_root) / path).is_dir()
                and not (Path(args.repo_root) / path).is_symlink()
            ),
            approved,
        )
    )


def _commit_rejected(root, paths, rejected):
    staged = _commit_git(
        root,
        ("--literal-pathspecs", "diff", "--cached", "--name-only", "-z", "--", *paths),
    )
    rollback = None
    if isinstance(staged, Built):
        names = tuple(
            path.decode("utf-8", "surrogateescape")
            for path in staged.value.split(b"\0")
            if path
        )
        if names:
            rollback = _commit_git(
                root, ("--literal-pathspecs", "restore", "--staged", "--", *names)
            )
    problems = (
        Defect(
            "CommitRejected: role commit",
            failure_reason(rejected),
            "Correct the Git or hook rejection and rerun nwdes commit; hooks stay enabled.",
        ),
        *(staged.defects if isinstance(staged, Refused) else ()),
        *(rollback.defects if isinstance(rollback, Refused) else ()),
    )
    return _commit_failure(checked(None, problems))


def _commit(args):
    located = _commit_locations(args.repo_root)
    if isinstance(located, Refused):
        return _commit_failure(located)
    with _commit_lock(located.value) as locked:
        if isinstance(locked, Refused):
            return _commit_failure(locked)
        context = _commit_context(args)
        if isinstance(context, Refused):
            return _commit_failure(context)
        document, destinations, inspected = context.value
        observed = _commit_observation(
            args, document, destinations, located.value, inspected
        )
        if isinstance(observed, Refused):
            return _commit_failure(observed)
        admitted = commits.prepare_commit(
            commits.CommitRequest(
                commits.Role(args.role), args.slice, tuple(args.path)
            ),
            document,
            destinations,
            observed.value,
        )
        if isinstance(admitted, Refused):
            return _commit_failure(admitted)
        paths = admitted.value
        if not paths:
            try:
                Path(located.value.receipt(args.role)).unlink()
            except OSError as error:
                return _commit_failure(
                    checked(
                        None,
                        (
                            Defect(
                                "InputUnreadable: " + located.value.receipt(args.role),
                                str(error),
                                "Restore access to remove the unchanged close receipt, then rerun nwdes commit.",
                            ),
                        ),
                    )
                )
            print("NOOP", observed.value.head)
            return 0
        present, deleted = [], []
        for path in paths:
            (
                present if os.path.lexists(Path(args.repo_root) / path) else deleted
            ).append(path)
        for arguments in (
            ("--literal-pathspecs", "add", "--", *present) if present else (),
            ("--literal-pathspecs", "rm", "--cached", "--quiet", "--", *deleted)
            if deleted
            else (),
        ):
            if not arguments:
                continue
            staged = run_git(args.repo_root, arguments)
            if isinstance(staged, Unreadable) or staged.code:
                return _commit_rejected(args.repo_root, paths, staged)
        message = commits.message(
            commits.CommitType(args.type),
            args.description,
            args.message_scope,
            args.body,
        )
        committed = run_git(
            args.repo_root,
            (
                "commit",
                "--only",
                "-m",
                message,
                "--",
                *(f":(literal){path}" for path in paths),
            ),
        )
        if isinstance(committed, Unreadable) or committed.code:
            return _commit_rejected(args.repo_root, paths, committed)
        revision = _commit_git(
            args.repo_root, ("rev-parse", "--verify", "HEAD^{commit}")
        )
        if isinstance(revision, Refused):
            return _commit_failure(revision)
        try:
            Path(located.value.receipt(args.role)).unlink()
        except OSError as error:
            return _commit_failure(
                checked(
                    None,
                    (
                        Defect(
                            "InputUnreadable: " + located.value.receipt(args.role),
                            str(error),
                            "The Git commit landed; restore access to remove its consumed close receipt before another role closes.",
                        ),
                    ),
                )
            )
        print("COMMITTED", revision.value.decode("ascii").strip())
        for path in paths:
            print(path)
        return 0


@dataclass(frozen=True)
class _RoleInputs:
    """The handoff and ADR register, read once per invocation."""

    handoff: object
    adr_directory: str
    register: object


def _read_inputs(ports, repo_root, destinations):
    return _RoleInputs(
        handoff=ports.file(str(Path(repo_root) / destinations.handoff)),
        adr_directory=destinations.adr_directory,
        register=ports.register(destinations.adr_directory),
    )


def _pinned_ports(ports, inputs):
    """Serve the ADR register from the invocation's read set."""

    def register(directory):
        if directory == inputs.adr_directory:
            return inputs.register
        return ports.register(directory)

    return replace(ports, register=register)


@dataclass(frozen=True)
class _CloseSession:
    locations: CommitLocations
    head: str
    role: commits.Role
    inputs: _RoleInputs


def _git_marker_above(root):
    """Whether `root` or an ancestor holds a `.git` entry (a directory, or a file in a worktree)."""
    start = Path(root or ".").resolve()
    return any((directory / ".git").exists() for directory in (start, *start.parents))


def _git_worktree(root):
    """Whether root sits in a Git worktree; outside one no receipt or lock applies."""
    if not (os.environ.get("GIT_DIR") or _git_marker_above(root)):
        return False
    repository = run_git(root, ("rev-parse", "--git-dir"))
    return not (isinstance(repository, Unreadable) or repository.code)


def _record_close(kind, name, values, context):
    args = context.args
    if not _git_worktree(args.repo_root):
        return _record_role_scoped(kind, name, values, context, None)
    actor = commits.recording_role(kind, values.get("subject"), values.get("role"))
    if isinstance(actor, Refused):
        return _commit_failure(actor)
    locations = _commit_locations(args.repo_root)
    if isinstance(locations, Refused):
        return _commit_failure(locations)
    guard = (
        _commit_lock(locations.value)
        if commits.authority_kind(kind)
        else nullcontext(Built(locations.value))
    )
    with guard as locked:
        if isinstance(locked, Refused):
            return _commit_failure(locked)
        head = _commit_git(args.repo_root, ("rev-parse", "--verify", "HEAD^{commit}"))
        if isinstance(head, Refused):
            return _commit_failure(head)
        result = _record_role_scoped(
            kind,
            name,
            values,
            context,
            _CloseSession(
                locations.value,
                head.value.decode("ascii").strip(),
                actor.value,
                _read_inputs(context.ports, args.repo_root, context.destinations),
            ),
        )
        if result == 0 and kind == "examine":
            handoff = str(Path(args.repo_root) / context.destinations.handoff)
            _retire_workspaces(args.repo_root, locations.value, handoff)
        return result


def _retire_workspaces(root, locations, handoff):
    """Remove the examination workspace this scope's prompt recorded, after publication."""
    outcomes = probe.retire(root, locations.workspaces, handoff)
    if not outcomes:
        print(
            "WARNING WHAT: no examination workspace is recorded for this scope in "
            + locations.workspaces
            + ".\nWHY: a workspace is removed only by a close run from the worktree whose "
            "prompt recorded it; this close found none here and removes nothing.\n"
            "HOW: run nwdes examine close from the worktree that built the examine prompt.",
            file=sys.stderr,
        )
    _report_workspaces(outcomes)


def _report_workspaces(outcomes):
    for outcome, path, reason in outcomes:
        if outcome == "removed":
            print("REMOVED", path)
        elif outcome == "gone":
            print("ABSENT", path, "- already removed; its record is dropped")
        else:
            print("KEPT", path, "-", reason)


def _discard_workspace(args, destinations):
    """Remove the workspace an aborted examination recorded; nothing is published by an abort."""
    if not _git_worktree(args.repo_root):
        return None
    locations = _commit_locations(args.repo_root)
    if isinstance(locations, Refused):
        return _commit_failure(locations)
    handoff = str(Path(args.repo_root) / destinations.handoff)
    _report_workspaces(probe.discard(locations.value.workspaces, handoff))
    return None


def _write_receipt(locations, receipt, result):
    path = Path(locations.receipt(receipt.role.value))
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            dir=path.parent, prefix=path.name + ".", suffix=".tmp"
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(commits.receipt_bytes(receipt))
        Path(temporary).replace(path)
        temporary = None
    except OSError as error:
        return IOFailure((str(path),), str(error))
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass
    return result


def _publish_role_close(ports, outputs, session, scope):
    result = ports.outputs(outputs)
    if isinstance(result, IOFailure):
        return result
    receipt = commits.close_receipt(session.role, scope, session.head, outputs)
    return _write_receipt(session.locations, receipt, result)


def _publish_work(ports, outputs, locations, receipt):
    result = ports.outputs(outputs)
    if isinstance(result, IOFailure):
        return result
    refreshed = commits.refreshed_receipt(receipt, outputs)
    if refreshed is None:
        return result
    return _write_receipt(locations, refreshed, result)
