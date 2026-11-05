"""Role-source projections, staged prompt preparation and single-pass template binding."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from functools import partial
from types import MappingProxyType

from nwdes import documents, grammar, packets
from nwdes import handoff as model
from nwdes.contracts import Built, Defect, Refused, checked


@dataclass(frozen=True)
class Printed:
    whole: str
    items: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Source:
    placeholder: str
    kind: str
    name: str


@dataclass(frozen=True)
class Recipe:
    """Exact bound fields, with separately admitted unbound invocation inputs."""

    id: str
    roles: tuple[str, ...]
    task: str | None
    template: str
    sources: tuple[Source, ...]
    admitted: frozenset[str]
    optional: frozenset[str] = frozenset()
    review_subject: str | None = None
    slice_review_subject: str | None = None
    checks_all_slice_designs: bool = False


class JevAuthorization(Enum):
    AUTHORIZED = "authorized"
    UNAUTHORIZED = "unauthorized"


# Consent nobody declared: Jev is authorized by default; an explicit refusal still wins.
JEV_DEFAULT = JevAuthorization.AUTHORIZED


@dataclass(frozen=True)
class BaselineFailure:
    id: str
    owner: str


@dataclass(frozen=True)
class Inputs:
    role: str | None
    repo_root: str | None
    handoff: str | None
    slice: str | None = None
    task: str | None = None
    phase: str | None = None
    diff: str | None = None
    root_input: str | None = None
    jev: JevAuthorization | None = JEV_DEFAULT
    baseline_failures: tuple[BaselineFailure, ...] = ()
    workspace: packets.ExaminationWorkspace | None = None
    commit: str | None = None
    touched: str | None = None


def _path(placeholder, name=None):
    return Source(placeholder, "path", name or placeholder)


def _input(placeholder, name=None):
    return Source(placeholder, "input", name or placeholder)


def _derived(placeholder, name=None):
    return Source(placeholder, "derivation", name or placeholder)


_HEAD = (_input("role"), _path("feature", "scope.id"), _path("request"))
_TAIL = (_input("repo_root"), _input("root_input"))
_SLICE_HEAD = (
    *_HEAD,
    _input("value", "slice"),
    _path("observation", "product.slices[].observation"),
    _path("slice_work", "product.slices[].work"),
)
_ATD = (
    *_SLICE_HEAD,
    _derived("authority", "authority/atd"),
    _path("oracle_path", "design.slices.S.oracle"),
    _path("supports", "design.slices.S.supports"),
    _path("targets", "design.slices.S.targets"),
    _path("paradigm", "design.paradigm"),
    _derived("verification"),
    _path("public_oracle", "design.slices.S.public_oracle"),
    _derived("obligations", "atd_obligations"),
    _derived("properties", "atd_properties"),
    _path("promises", "product.promises"),
    _path("journey", "product.journey"),
    _path("slice_deps", "product.slices[].depends_on"),
    _derived("arch_tests", "reach.architectural_tests"),
    _derived("contract_tests", "reach.contract_tests"),
    _path("adrs", "design.adrs"),
)
_CRAFTER_ROLES = ("nw-software-crafter", "nw-functional-software-crafter")


def _recipe(identity, roles, sources, task=None, *, admits=()):
    context = (
        (_derived("baseline_failures"),)
        if any(source.name == "repo_root" for source in sources)
        else ()
    )
    sources = (
        *sources,
        _input("jev"),
        *context,
    )
    return Recipe(
        identity,
        roles,
        task,
        identity + ".tmpl",
        sources,
        frozenset(admits)
        | frozenset(source.name for source in sources if source.kind == "input")
        | (frozenset(("baseline-failure",)) if context else frozenset()),
    )


RECIPES = (
    _recipe(
        "po.discuss-v1",
        ("nw-product-owner",),
        (
            *_HEAD,
            _path("work"),
            _derived("product", "current_product"),
            _derived("authority", "authority/po"),
            _derived("asks"),
            *_TAIL,
        ),
        "discuss",
    ),
    _recipe(
        "design.architect-v10",
        ("nw-solution-architect",),
        (
            *_HEAD,
            _path("work"),
            _derived("authority", "authority/architect"),
            _path("product"),
            _path("adrs", "design.adrs"),
            _derived("design", "current_design"),
            _derived("asks"),
            *_TAIL,
        ),
    ),
    _recipe(
        "oracle.atd-v4",
        ("nw-acceptance-designer",),
        (
            *_ATD,
            _derived("owed", "atd_owed"),
            _derived("examine_rework"),
            _derived("asks"),
            *_TAIL,
        ),
    ),
    replace(
        _recipe(
            "review.atd-v1",
            ("nw-acceptance-designer-reviewer",),
            (
                *(
                    _derived("authority", "authority/review")
                    if source.placeholder == "authority"
                    else _derived("properties", "review_properties")
                    if source.placeholder == "properties"
                    else source
                    for source in _ATD
                ),
                _derived("acceptance_index"),
                _path("expectations"),
                _input("diff"),
                _input("commit"),
                _input("touched"),
                *_TAIL,
            ),
        ),
        review_subject="oracle",
    ),
    _recipe(
        "craft.impl-v4",
        _CRAFTER_ROLES,
        (
            *_SLICE_HEAD,
            _derived("implementation_mode"),
            _derived("authority", "authority/craft"),
            _derived("operations", "reach.constraints"),
            _path("adrs", "design.adrs"),
            _path("targets", "design.slices.S.targets"),
            _path("paradigm", "design.paradigm"),
            _path("oracle_line", "design.slices.S.oracle"),
            _path("supports", "design.slices.S.supports"),
            _derived("verification"),
            _derived("obligations", "craft_view"),
            _derived("examine_rework"),
            *_TAIL,
        ),
    ),
    _recipe(
        "craft.prefactor-v4",
        _CRAFTER_ROLES,
        (
            *(source for source in _SLICE_HEAD if source.placeholder != "slice_work"),
            _input("phase"),
            _derived("authority", "authority/prefactor"),
            _derived("operations", "reach.constraints"),
            _path("targets", "design.slices.S.targets"),
            _path("paradigm", "design.paradigm"),
            _path("move", "design.slices.S.prefactoring.move"),
            _path("preserved", "design.slices.S.prefactoring.preserved"),
            _path("existing_oracle", "design.slices.S.prefactoring.existing_oracle"),
            _derived("verification", "prefactoring_verification"),
            _derived("acceptance_index"),
            *_TAIL,
        ),
    ),
    _recipe(
        "examine.expectations-v1",
        ("nw-user-examiner",),
        (
            _path("promises", "product.promises"),
            _path("expectations"),
            _input("root_input"),
            _derived("asks"),
        ),
        "expectations",
    ),
    replace(
        _recipe(
            "po.charter-v1",
            ("nw-product-owner",),
            (
                _path("request"),
                _path("value", "work.value"),
                _derived("slices", "charter_slices"),
                _path("promises", "product.promises"),
                _path("journey", "product.journey"),
                _input("root_input"),
            ),
            "charter",
        ),
        checks_all_slice_designs=True,
    ),
    _recipe(
        "examine.user-v1",
        ("nw-user-examiner",),
        (
            _derived("packet", "packet/examine"),
            _derived("budget", "examine_budget"),
        ),
        "examine",
    ),
    replace(
        _recipe(
            "review.craft-v1",
            ("nw-software-crafter-reviewer",),
            (
                _path("feature", "scope.id"),
                _path("request"),
                _path("paradigm", "design.paradigm"),
                _derived("authority", "authority/review"),
                _path("adrs", "design.adrs"),
                _derived("packet", "packet/review"),
                _input("commit"),
                _input("touched"),
                *_TAIL,
            ),
            admits=("diff", "slice"),
        ),
        optional=frozenset(("slice",)),
        review_subject="candidate",
        slice_review_subject="slice",
    ),
)
_RECIPE_INDEX = MappingProxyType({recipe.id: recipe for recipe in RECIPES})
_ROLE_INDEX = MappingProxyType(
    {
        role: tuple(recipe for recipe in RECIPES if role in recipe.roles)
        for recipe in RECIPES
        for role in recipe.roles
    }
)
_TEMPLATE_DIRECTORY = "nWave/templates/architect-handoff/"
_INPUT_NAMES = frozenset(Inputs.__dataclass_fields__)
_PATHS = frozenset(model.SCHEMA_PATHS)
CONSUMERS = MappingProxyType(
    {
        path: (
            "handoff.parse",
            "handoff.serialize",
            *(
                recipe.id + "." + source.placeholder
                for recipe in RECIPES
                for source in recipe.sources
                if source.kind == "path"
                and (path == source.name or path.startswith(source.name + "."))
            ),
        )
        for path in model.SCHEMA_PATHS
    }
)
_PLACEHOLDER = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)(?:\|(bullets|csv))?\}\}")
_NONE = Printed("None.")

# The wall budget the examiner is told to keep: a recipe instruction, never an enforced limit.
EXAMINE_WALL_BUDGET_MINUTES = 5
_EXAMINE_REWORK_RULE = (
    "Each examine finding repaired here becomes an oracle test: RED before the repair, "
    "GREEN after, added before or with it. The acceptance designer authors it."
)


def _problem(kind, name, why, how="Use the recipe's declared inputs and source table."):
    return Defect(kind + ": " + name, why, how)


def _binding_problems(template, fields, recipe=""):
    holes = frozenset(match[1] for match in _PLACEHOLDER.finditer(template))
    names = frozenset(fields)
    prefix = recipe + "." if recipe else ""
    return (
        *(
            _problem(
                "PlaceholderUnbound", prefix + name, "The placeholder has no field."
            )
            for name in sorted(holes - names)
        ),
        *(
            _problem("FieldUnused", prefix + name, "The field has no placeholder.")
            for name in sorted(names - holes)
        ),
    )


def bind(template: str, fields: Mapping[str, Printed]):
    problems = _binding_problems(template, fields)
    if problems:
        return checked(None, problems)

    def substitute(match):
        field = fields[match[1]]
        if match[2] is None:
            return field.whole or "None."
        if not field.items:
            return "None."
        return (", " if match[2] == "csv" else "\n").join(field.items)

    return Built(_PLACEHOLDER.sub(substitute, template))


def _source_problems(recipe):
    expected = _RECIPE_INDEX.get(recipe.id)
    canonical = (
        {source.placeholder: (source.kind, source.name) for source in expected.sources}
        if expected is not None
        else {}
    )
    for source in recipe.sources:
        pair = (source.kind, source.name)
        known = (
            source.name in _PATHS
            if source.kind == "path"
            else source.name in _INPUT_NAMES
            if source.kind in ("input", "role")
            else source.name in _DERIVATIONS
            if source.kind == "derivation"
            else False
        )
        if not known or canonical.get(source.placeholder) != pair:
            yield _problem(
                "InconsistentFacts",
                recipe.id + "." + source.placeholder,
                f"The source {source.kind}:{source.name} is not its declared source.",
            )
    names = tuple(source.placeholder for source in recipe.sources)
    for name in dict.fromkeys(names):
        if names.count(name) > 1:
            yield _problem(
                "InconsistentFacts",
                recipe.id + "." + name,
                "A field has multiple sources.",
            )


def check_coverage(recipes, templates):
    return checked(
        None,
        (
            problem
            for recipe in recipes
            for problem in (
                *_binding_problems(
                    templates.get(recipe.id, ""),
                    (source.placeholder for source in recipe.sources),
                    recipe.id,
                ),
                *_source_problems(recipe),
            )
        ),
    )


def check_consumers(paths, consumers):
    return checked(
        None,
        (
            _problem(
                "InconsistentFacts",
                path,
                "No recipe, renderer or operation consumes this schema path.",
                "Declare the actual consumer of this schema path in CONSUMERS.",
            )
            for path in paths
            if not consumers.get(path)
        ),
    )


def recipe_for(role, task=None, phase=None):
    if role is None:
        return checked(None, (model.missing_flag("role"),))
    if not isinstance(role, str) or role not in _ROLE_INDEX:
        return checked(
            None, (_problem("InconsistentFacts", "--role", "Unknown role."),)
        )
    candidates = _ROLE_INDEX[role]
    effective = "discuss" if role == "nw-product-owner" and task is None else task
    candidates = tuple(recipe for recipe in candidates if recipe.task == effective)
    if not candidates:
        return checked(
            None,
            (_problem("InconsistentFacts", "--task", "This role has no such task."),),
        )
    if len(candidates) > 1:
        candidates = tuple(
            recipe
            for recipe in candidates
            if any(source.name == "phase" for source in recipe.sources)
            == (phase is not None)
        )
    return Built(candidates[0])


def template_path(recipe):
    return _TEMPLATE_DIRECTORY + recipe.template


def _slot(value, name):
    if isinstance(value, model.UnavailableInput):
        return value
    if value is None:
        return None
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _part(previous, name):
    return previous.part(name) if previous is not None else None


def _target(previous, identity):
    references = previous.references if previous is not None else None
    if (
        references is None
        or references.slices is None
        or not model._reference_available(identity, references)
    ):
        return None
    slices = _slot(_part(previous, "product"), "slices")
    if isinstance(slices, model.UnavailableInput):
        return None
    selected = next(
        (row for row in (slices or ()) if _slot(row, "id") == identity), None
    )
    lookup_unit = selected if selected is not None else slices
    if model._unavailable(lookup_unit) is not None:
        return None
    return checked(identity, model._slice_problems(identity, references))


_RECIPE_FLAGS = frozenset(
    (
        "slice",
        "phase",
        "diff",
        "commit",
        "observation",
        "observation-file",
        "baseline-failure",
    )
)


def _admission(recipe, provided):
    admitted = recipe.admitted & _RECIPE_FLAGS
    problems = tuple(
        packets.self_gathered("--" + name)
        if name in ("observation", "observation-file")
        or (recipe.id == "examine.user-v1" and name == "root-context")
        else _problem(
            "InconsistentFacts",
            "--" + name,
            "This recipe has no source for this flag.",
            f"Use only the recipe flags admitted by {recipe.id}: "
            + (", ".join("--" + flag for flag in sorted(admitted)) or "none")
            + ".",
        )
        for name in (
            "slice",
            "phase",
            "diff",
            "commit",
            "observation",
            "observation-file",
            "baseline-failure",
            "root-context",
        )
        if name in provided
        and name not in admitted
        and (name != "root-context" or recipe.id == "examine.user-v1")
    )
    return (
        admitted,
        (
            *problems,
            *(
                (model.missing_flag("slice"),)
                if "slice" in admitted
                and "slice" not in provided
                and "slice" not in recipe.optional
                else ()
            ),
        ),
    )


@dataclass(frozen=True)
class _Inspection:
    inputs: Inputs
    previous: model.HandoffInput | None
    template: str | model.UnavailableInput | None
    provided: frozenset[str]
    policy: object
    problems: tuple[Defect, ...] = ()
    recipe_id: str | None = None


@dataclass(frozen=True)
class PreparedPrompt:
    recipe: Recipe
    handoff: model.Handoff
    inputs: Inputs
    template: str
    policy: object

    def build(self):
        return _render_ready(self)


def _problems_of(result):
    return result.defects if isinstance(result, Refused) else ()


def _root_problems(value):
    return (
        (
            _problem(
                "InconsistentFacts",
                "--repo-root",
                "The printed root contains a line boundary.",
            ),
        )
        if value is not None
        and (not isinstance(value, str) or model._LINE_BOUNDARY.search(value))
        else ()
    )


def resolved_jev(flag, repository, global_):
    """Pure: the flag wins, then the repository tier, then the global tier, then the default."""
    for value in (flag, repository, global_):
        if value is not None:
            return value
    return JEV_DEFAULT.value


def _jev_problems(value):
    return (
        ()
        if isinstance(value, JevAuthorization)
        else (
            _problem(
                "PartInvalid",
                "--jev",
                "The authorization is not a declared Jev choice.",
                "Supply --jev authorized or --jev unauthorized on nwdes prompt.",
            ),
        )
    )


def _baseline_problems(failures):
    return tuple(
        _problem(
            "PartInvalid",
            f"--baseline-failure {position} {name}",
            "A baseline failure id and owner must each be non-empty single-line text.",
            "Supply --baseline-failure ID OWNER with two non-empty single-line values.",
        )
        for position, failure in enumerate(failures, 1)
        for name, value in (("id", failure.id), ("owner", failure.owner))
        if not isinstance(value, str)
        or not value.strip()
        or model._LINE_BOUNDARY.search(value)
    )


def _handoff_problems(inputs, previous):
    if inputs.handoff is None:
        return (model.missing_flag("handoff"),)
    if previous is None:
        return (
            _problem(
                "MissingFact",
                "--handoff " + inputs.handoff,
                "The named handoff does not exist.",
            ),
        )
    return _problems_of(previous.result)


def _template_problems(template, recipe):
    if isinstance(template, model.UnavailableInput):
        return (template.defect,)
    if template is None:
        return (
            _problem(
                "AssetMissing",
                template_path(recipe),
                "The installed template does not exist.",
            ),
        )
    return (
        *_binding_problems(template, _RECIPE_FIELDS[recipe.id], recipe.id),
        *_RECIPE_SOURCE_PROBLEMS[recipe.id],
    )


def _design_problems(target, previous, prefactoring):
    if not isinstance(target, Built):
        return _problems_of(target)
    design = _slot(_slot(_part(previous, "design"), "slices"), target.value)
    if design is None:
        return (
            _problem(
                "MissingFact",
                "design.slices." + target.value,
                "The slice has no design.",
            ),
        )
    return (
        (
            _problem(
                "InconsistentFacts",
                "--phase",
                "This slice has no prefactoring move.",
            ),
        )
        if prefactoring
        and not isinstance(design, model.UnavailableInput)
        and _slot(design, "prefactoring") is None
        else ()
    )


def _charter_design_problems(previous):
    references = previous.references if previous is not None else None
    if references is None or references.slices is None:
        return ()
    return tuple(
        defect
        for identity in references.slices
        for defect in _design_problems(Built(identity), previous, False)
    )


_PACKET_KINDS = MappingProxyType(
    {
        "packet/examine": packets.PacketKind.Examine,
        "packet/review": packets.PacketKind.Review,
    }
)


def _packet_problems(inspection, recipe):
    if not any(source.name == "packet/examine" for source in recipe.sources):
        return ()
    previous = inspection.previous if inspection.inputs.handoff is not None else None
    return packets.examination_problems(previous)


def _promise_problems(recipe, previous, target):
    if previous is None:
        return ()
    if recipe.id == "examine.expectations-v1":
        promises = _slot(_part(previous, "product"), "promises")
        path = "product.promises"
        how = "Record public promises with nwdes product promise add and product close, then rebuild the bundle."
    elif recipe.id in ("oracle.atd-v4", "review.atd-v1") and isinstance(target, Built):
        design = _slot(_slot(_part(previous, "design"), "slices"), target.value)
        if design is None or isinstance(design, model.UnavailableInput):
            return ()
        promises = _slot(_slot(design, "public_oracle"), "promises")
        path = f"design.slices.{target.value}.public_oracle.promises"
        how = "Supply nwdes slice set --promise TEXT for this slice, then rebuild the bundle."
    else:
        return ()
    return (
        (
            _problem(
                "MissingFact",
                path,
                "This bundle needs at least one public promise to observe.",
                how,
            ),
        )
        if promises is None or promises == ()
        else ()
    )


def _prose_problems(recipe, previous, target):
    """The acceptance designer writes an oracle, which a prose-only slice does not carry."""
    if (
        recipe.id != "oracle.atd-v4"
        or previous is None
        or not isinstance(target, Built)
    ):
        return ()
    design = _slot(_slot(_part(previous, "design"), "slices"), target.value)
    if not isinstance(design, Mapping) or not model.is_prose_only(design):
        return ()
    return (
        _problem(
            "InconsistentFacts",
            f"design.slices.{target.value}",
            "Every target of this slice is a prose asset, so it has no oracle for the "
            "acceptance designer to write; EXAMINE and the whole-candidate review verify its prose.",
            "Do not run nw-acceptance-designer for this slice; craft the prose and let EXAMINE "
            "verify it, or name a machine-contract source file as a target to write an oracle.",
        ),
    )


def _recipe_problems(inspection, recipe, scalar):
    inputs, previous = inspection.inputs, inspection.previous
    admitted, admission_problems = _admission(recipe, inspection.provided)
    target = (
        _target(previous, scalar.value)
        if "slice" in admitted
        and "slice" in inspection.provided
        and isinstance(scalar, Built)
        else None
    )
    return (
        *(
            (
                _problem(
                    "InconsistentFacts",
                    "recipe",
                    "The requested recipe differs from the role, task and phase.",
                ),
            )
            if inspection.recipe_id is not None and recipe.id != inspection.recipe_id
            else ()
        ),
        *_template_problems(inspection.template, recipe),
        *admission_problems,
        *(
            (model._invalid("--phase", "Unknown prefactoring phase."),)
            if "phase" in admitted
            and inputs.phase not in ("before-move", "after-move-before-behavior")
            else ()
        ),
        *_design_problems(target, previous, "phase" in admitted),
        *(
            _charter_design_problems(previous)
            if recipe.checks_all_slice_designs
            else ()
        ),
        *_promise_problems(recipe, previous, target),
        *_prose_problems(recipe, previous, target),
        *(
            (model.missing_flag("commit"),)
            if recipe.review_subject is not None and inputs.commit is None
            else ()
        ),
        *_packet_problems(inspection, recipe),
        *(
            (
                _problem(
                    "MissingFact",
                    "expectations",
                    "The handoff has no fixed expectation set.",
                ),
            )
            if recipe.id == "review.atd-v1"
            and previous is not None
            and _part(previous, "expectations") is None
            else ()
        ),
    )


def _prepare(inspection):
    inputs, previous = inspection.inputs, inspection.previous
    selected = recipe_for(inputs.role, inputs.task, inputs.phase)
    scalar = model.parse_slice_id(inputs.slice)
    problems = (
        *inspection.problems,
        *_problems_of(selected),
        *_root_problems(inputs.repo_root),
        *_jev_problems(inputs.jev),
        *_baseline_problems(inputs.baseline_failures),
        *_handoff_problems(inputs, previous),
        *_problems_of(scalar),
        *_CONSUMER_PROBLEMS,
        *(
            _recipe_problems(inspection, selected.value, scalar)
            if isinstance(selected, Built)
            else ()
        ),
    )
    refusal = checked(None, problems)
    if isinstance(refusal, Refused):
        return refusal
    return Built(
        PreparedPrompt(
            selected.value,
            previous.result.value,
            inputs,
            inspection.template,
            inspection.policy,
        )
    )


def _provided(flags):
    return frozenset(
        (
            *(
                name
                for name in ("slice", "phase", "diff", "commit")
                if flags.get(name) is not None
            ),
            *(("observation",) if flags.get("observation") else ()),
            *(("baseline-failure",) if flags.get("baseline_failure") else ()),
            *(("root-context",) if flags.get("root_context") is not None else ()),
        )
    )


def _diff(flags, raw):
    if flags.get("diff") is None:
        return None, ()
    if isinstance(raw, model.UnavailableInput):
        return None, (raw.defect,)
    if raw is None:
        return None, (
            _problem(
                "MissingFact",
                "--diff " + flags["diff"],
                "The named diff does not exist.",
            ),
        )
    try:
        return raw.decode("utf-8"), ()
    except UnicodeError as error:
        return None, (
            _problem(
                "InputUnreadable",
                "--diff " + flags["diff"],
                str(error),
                "Supply a readable UTF-8 diff.",
            ),
        )


def prepare_prompt(flags, previous, diff, template, policy):
    refusal = examination_admission(flags)
    if refusal:
        return checked(None, refusal)
    diff_text, problems = _diff(flags, diff)
    raw_jev = flags.get("jev")
    jev = (
        JEV_DEFAULT
        if raw_jev is None
        else next(
            (value for value in JevAuthorization if value.value == raw_jev),
            None,
        )
    )
    inputs = Inputs(
        role=flags.get("role"),
        repo_root=flags.get("repo_root"),
        handoff=flags.get("handoff"),
        slice=flags.get("slice"),
        task=flags.get("task"),
        phase=flags.get("phase"),
        diff=diff_text,
        root_input=flags.get("root_context"),
        jev=jev,
        baseline_failures=tuple(
            BaselineFailure(identity, owner)
            for identity, owner in flags.get("baseline_failure", ())
        ),
        workspace=flags.get("workspace"),
        commit=flags.get("commit"),
        touched=flags.get("touched", touched_files(diff_text)),
    )
    return _prepare(
        _Inspection(
            inputs,
            previous if inputs.handoff is not None else None,
            template,
            _provided(flags),
            policy,
            problems,
        )
    )


def render_prompt(recipe_id, handoff, inputs, template, policy):
    provided = _provided(
        {
            "slice": inputs.slice,
            "phase": inputs.phase,
            "diff": inputs.diff,
            "commit": inputs.commit,
            "baseline_failure": inputs.baseline_failures,
            "root_context": inputs.root_input,
        }
    )
    prepared = _prepare(
        _Inspection(
            inputs,
            model.HandoffInput(Built(handoff), handoff._references),
            template,
            provided,
            policy,
            recipe_id=recipe_id,
        )
    )
    return prepared if isinstance(prepared, Refused) else prepared.value.build()


def examination_admission(flags):
    selected = recipe_for(flags.get("role"), flags.get("task"), flags.get("phase"))
    return packets.examination_admission(
        {**flags, "kind": "examine"}
        if isinstance(selected, Built) and selected.value.id == "examine.user-v1"
        else flags
    )


def touched_files(diff):
    return "\n".join(
        dict.fromkeys(
            path
            for old, new in re.findall(r"(?m)^diff --git a/(.*?) b/(.+)$", diff or "")
            for path in (old, new)
        )
    )


def oracle_approval(slice_id, recorded_content, current_content, then):
    """Refuse once the oracle or support bytes differ from those the oracle review approved.

    ``then`` completes the remedy: the step the caller takes after rerunning the review.
    """
    if recorded_content is None or recorded_content == current_content:
        return Built(None)
    return checked(
        None,
        (
            Defect(
                "OracleChanged: " + slice_id,
                "The oracle or support bytes differ from the approved ones; the approval covered other bytes.",
                "Rerun the oracle review for "
                + slice_id
                + " with nwdes review observation add and close --subject oracle --slice "
                + slice_id
                + ", then "
                + then
                + ".",
            ),
        ),
    )


def _only(spec, names, **overrides):
    wanted = frozenset(names)
    return replace(
        spec,
        members=tuple(
            (name, overrides.get(name, child))
            for name, child in spec.members
            if name in wanted
        ),
        required=tuple(name for name in spec.required if name in wanted),
    )


_OBLIGATION_KEYS = (
    "decisions",
    "constraints",
    "reuse",
    "impact",
    "agreement",
    "boundaries",
    "claims",
    "states",
    "closure",
    "risks",
)
_PROPERTY_KEYS = (
    "laws",
    "observations",
    "equality",
    "constructors",
    "refuted",
    "models",
)
_CRAFT_KEYS = (
    "decisions",
    "reuse",
    "impact",
    "agreement",
    "boundaries",
    "observations",
    "equality",
    "constructors",
    "laws",
    "claims",
    "states",
    "models",
    "architectural_tests",
    "contract_tests",
)
_OBLIGATIONS = _only(model.RECORDS, _OBLIGATION_KEYS)
_PROPERTIES = _only(model.RECORDS, _PROPERTY_KEYS)
_REVIEW_PROPERTIES = _only(packets.REVIEW_RECORDS, _PROPERTY_KEYS)
_CRAFT_LAW = _only(model.LAW, ("statement", "owner"))
_CRAFT_MODEL = _only(
    model.MODEL,
    ("atoms", "properties"),
    **{
        name: replace(
            model.MODEL.index[name],
            members=(
                _only(model.MODEL.index[name].members[0], ("name", "symbol", "site")),
            ),
        )
        for name in ("atoms", "properties")
    },
)
_STATE = model.RECORDS.index["states"].members[0]
_CRAFT_STATE = _only(_STATE, ("kind", "state"), kind=model.enum("Admitted", "Excluded"))
_CRAFT_RECORDS = _only(
    model.RECORDS,
    _CRAFT_KEYS,
    laws=replace(model.RECORDS.index["laws"], members=(_CRAFT_LAW,)),
    states=replace(model.RECORDS.index["states"], members=(_CRAFT_STATE,)),
    models=replace(model.RECORDS.index["models"], members=(_CRAFT_MODEL,)),
)


def _summary_spec(spec):
    if spec is model.MODEL:
        return packets.MODEL_SUMMARY
    if spec.kind in ("array", "table"):
        return replace(spec, members=(_summary_spec(spec.members[0]),))
    if spec.kind in ("record", "choice"):
        members = spec.members
        if spec.identity:
            text = next((name for name, child in members if child.kind == "text"), None)
            if text is not None:
                spec = _only(spec, (text,))
                members = spec.members
        return replace(
            spec, members=tuple((name, _summary_spec(child)) for name, child in members)
        )
    return spec


_CURRENT_DESIGN = _summary_spec(
    _only(model.CANONICAL_SCHEMAS["design"], ("paradigm", "shared", "slices"))
)
_ADRS = model.CANONICAL_SCHEMAS["design"].index["adrs"]
_COMMANDS = model.SLICE_DESIGN.index["verification"]


def _project(spec, value):
    if value is None:
        return None
    if spec.kind == "array":
        child = spec.members[0]
        kind = child.index.get("kind")
        return tuple(
            _project(child, row)
            for row in value
            if kind is None or kind.kind != "enum" or row.get("kind") in kind.members
        )
    if spec.kind == "record":
        return model.Record(
            (
                *((("id", value["id"]),) if spec.identity and "id" in value else ()),
                *(
                    (name, _project(child, value[name]))
                    for name, child in spec.members
                    if name in value
                ),
            )
        )
    return value


def reach(handoff, slice):
    product = handoff.product or model.EMPTY
    own = ((handoff.design or model.EMPTY).get("slices") or model.EMPTY).get(
        slice
    ) or model.EMPTY
    promises = frozenset((own.get("public_oracle") or model.EMPTY).get("promises", ()))
    return model._prune(
        handoff,
        work=model.EMPTY,
        counters=model.EMPTY,
        product=model.Record(
            (
                *(
                    (name, value)
                    for name, value in product.items()
                    if name not in ("slices", "promises")
                ),
                (
                    "promises",
                    tuple(
                        row
                        for row in product.get("promises", ())
                        if row["id"] in promises
                    ),
                ),
                (
                    "slices",
                    tuple(
                        row for row in product.get("slices", ()) if row["id"] == slice
                    ),
                ),
            )
        ),
        design=model.project_design(handoff.design, slice),
        acceptance=model.Record(((slice, handoff.acceptance[slice]),))
        if slice in handoff.acceptance
        else model.EMPTY,
        expectations=None,
        charter=None,
        examination=model.EMPTY,
    )


def craft_view(handoff, slice):
    return _craft_view(reach(handoff, slice), slice)


def _craft_view(reached, slice):
    design = reached.design or model.EMPTY
    scoped = (design.get("slices") or model.EMPTY).get(slice) or model.EMPTY
    own = model.Record(
        (("records", _project(_CRAFT_RECORDS, scoped.get("records") or model.EMPTY)),)
    )
    return model._prune(
        reached,
        product=None,
        design=model.Record(
            (
                (
                    "shared",
                    _project(
                        _shared_spec(_CRAFT_RECORDS),
                        design.get("shared") or model.EMPTY,
                    ),
                ),
                ("slices", model.Record(((slice, own),))),
            )
        ),
    )


def _at_path(handoff, path, inputs):
    value, spec = handoff, model.HANDOFF_INPUT
    for part in path.replace("[]", ".[]").split("."):
        if spec.kind == "array":
            value = next(
                (row for row in value or () if row.get("id") == inputs.slice), None
            )
            spec = spec.members[0]
        elif spec.kind == "table":
            value = _slot(value, inputs.slice)
            spec = spec.members[0]
        else:
            if spec.kind == "choice":
                spec = next(
                    alternative
                    for _, alternative in spec.members
                    if part in alternative.index
                )
            spec = spec.index[part]
            value = _slot(value, part)
    return spec, value


def _printed(spec, value, facts):
    if value in (None, (), model.EMPTY):
        return _NONE
    if spec is model.WORK:
        rework = value.get("rework")
        tail = (
            "Rework:\nDelta:\n"
            + documents.fenced(facts[rework["delta"]])
            + "Reason:\n"
            + documents.fenced(facts[rework["reason"]])
            if rework is not None
            else "Rework: None."
        )
        return Printed(
            "Size: "
            + value["size"]
            + "\nValue:\n"
            + documents.fenced(facts[value["value"]])
            + tail
        )
    if spec is model.PUBLIC_ORACLE:
        return Printed(
            "".join(
                label + ":\n" + documents.fenced(facts[value[name]])
                for label, name in (
                    ("Stimulus", "stimulus"),
                    ("Expected", "expected"),
                    ("Falsifier", "falsifier"),
                )
            )
            + "Promises: "
            + (
                ", ".join(documents.escaped(identity) for identity in value["promises"])
                if value.get("promises")
                else "None."
            )
        )
    if spec.kind == "array" and spec.members[0] is model.TARGET:
        items = tuple(
            documents.inline(row["path"])
            + " "
            + row["change"]
            + (
                "\n" + documents.fenced(facts[row["reason"]])
                if row.get("reason") is not None
                else ""
            )
            for row in value
        )
        return Printed("\n".join(items), items)
    if spec is _ADRS:
        items = tuple(documents.render_adrs((row,)).rstrip("\n") for row in value)
        return Printed("\n".join(items), items)
    if spec.kind == "array":
        if spec.members[0].kind == "command":
            whole = documents.render_field(spec, value, facts).rstrip("\n")
            return Printed(whole, (whole,))
        items = tuple(
            documents.render_field(spec, (child,), facts, compact=True).rstrip("\n")
            for child in value
        )
        return Printed("\n".join(items), items)
    return Printed(
        documents.render_field(spec, value, facts, compact=True).rstrip("\n")
    )


def _shared_spec(spec):
    return replace(
        spec,
        members=tuple(
            (
                name,
                model.SHARED_RECORDS.index[name]
                if name in ("decisions", "constraints")
                else child,
            )
            for name, child in spec.members
        ),
    )


def _print_parts(spec, handoff, slice, facts):
    design = handoff.design or model.EMPTY
    parts = (
        (_shared_spec(spec), design.get("shared") or model.EMPTY),
        (
            spec,
            ((design.get("slices") or model.EMPTY).get(slice) or model.EMPTY).get(
                "records"
            )
            or model.EMPTY,
        ),
    )
    items = tuple(
        documents.render_field(part_spec, part, facts, compact=True).rstrip("\n")
        for part_spec, part in parts
        if any(part.get(name) for name, _ in part_spec.members)
    )
    return Printed("\n".join(items) or "None.", items)


_SIBLINGS = MappingProxyType(
    {
        "po": (),
        "architect": ("brief.md",),
        "atd": ("brief.md", "architecture.md"),
        "prefactor": ("brief.md", "architecture.md"),
        "craft": ("brief.md", "architecture.md", "acceptance.md"),
        "review": ("brief.md", "architecture.md", "acceptance.md"),
    }
)


@dataclass(frozen=True)
class _View:
    plan: PreparedPrompt
    reached: model.Handoff | None
    craft: model.Handoff | None
    owed: tuple = ()


def _relative_path(path, root):
    return (
        posixpath.relpath(path, root)
        if root is not None and posixpath.isabs(root) and posixpath.isabs(path)
        else path
    )


def _authority(family, view):
    directory = posixpath.dirname(view.plan.inputs.handoff)
    paths = tuple(
        _relative_path(posixpath.join(directory, sibling), view.plan.inputs.repo_root)
        for sibling in _SIBLINGS[family]
    )
    items = tuple("- " + documents.inline(path) for path in paths)
    return Printed(
        documents.path_index(tuple(("-", path) for path in paths)).rstrip("\n"), items
    )


def _baseline_failures(view):
    failures = view.plan.inputs.baseline_failures
    return Printed(
        "\n".join(f"- {failure.id} owned by {failure.owner}" for failure in failures)
        if failures
        else "None."
    )


def _current(kind, view):
    handoff = view.plan.handoff
    if not handoff.work.get("rework"):
        return _NONE
    return _printed(
        model.PRODUCT if kind == "product" else _CURRENT_DESIGN,
        getattr(handoff, kind),
        handoff.facts,
    )


def _design(view):
    return ((view.plan.handoff.design or model.EMPTY).get("slices") or model.EMPTY).get(
        view.plan.inputs.slice
    ) or model.EMPTY


def _implementation_mode(view):
    if model.is_prose_only(_design(view)):
        return Printed(
            "Prose-only slice: it records no oracle and no verification; implement the prose "
            "and let EXAMINE verify it."
        )
    return Printed(
        "Implement against the declared immutable oracle; the host supplies baseline evidence under FROM THE ROOT."
        if _design(view).get("targets")
        else "No product changes authorized; preserve the public observation without product edits."
    )


def _verification(prefactoring, view):
    design = _design(view)
    commands = (
        (design.get("prefactoring") or model.EMPTY).get("verification")
        if prefactoring
        else model.slice_verification(view.plan.handoff.design, view.plan.inputs.slice)
    )
    return _printed(_COMMANDS, commands, view.plan.handoff.facts)


def _reachable_field(field, view):
    reached = view.reached if view.reached is not None else view.plan.handoff
    return _print_parts(
        _only(model.RECORDS, (field,)), reached, view.plan.inputs.slice, reached.facts
    )


def _properties(spec, view):
    return _print_parts(
        spec,
        view.reached,
        view.plan.inputs.slice,
        view.reached.facts,
    )


_SCOPE = _only(model.PRODUCT, ("scope_in", "scope_out"))


def _obligations(view):
    handoff, reached, inputs = view.plan.handoff, view.reached, view.plan.inputs
    own = (
        _printed(_SCOPE, handoff.product, handoff.facts)
        if any((handoff.product or model.EMPTY).get(name) for name, _ in _SCOPE.members)
        else _NONE
    )
    records = _print_parts(_OBLIGATIONS, reached, inputs.slice, reached.facts)
    items = tuple(value for value in (own.whole, records.whole) if value != "None.")
    return Printed("\n".join(items) or "None.", items)


def _owed(view):
    items = tuple(key if text is None else f"{key} {text}" for key, text in view.owed)
    return Printed("\n".join(items) or "None.", items)


def _acceptance_index(view):
    plan = view.plan
    return Printed(
        documents.acceptance_index(
            plan.handoff.scope,
            plan.inputs.slice,
            plan.handoff.acceptance.get(plan.inputs.slice, ()),
            handoff_argument=_relative_path(plan.inputs.handoff, plan.inputs.repo_root),
        ).rstrip("\n")
    )


def _craft_obligations(view):
    craft, inputs = view.craft, view.plan.inputs
    records = _print_parts(_CRAFT_RECORDS, craft, inputs.slice, craft.facts)
    acceptance = _acceptance_index(view)
    items = tuple(
        value for value in (records.whole, acceptance.whole) if value != "None."
    )
    return Printed("\n".join(items) or "None.", items)


def _packet(kind, view):
    plan = view.plan
    result = (
        packets.examine(plan.handoff, workspace=plan.inputs.workspace)
        if kind is packets.PacketKind.Examine
        else packets.review(
            plan.handoff,
            (),
            plan.inputs.diff,
            handoff_argument=_relative_path(plan.inputs.handoff, plan.inputs.repo_root),
            slice_id=plan.inputs.slice,
        )
    )
    return Printed(result.value)


def _charter_slices(view):
    handoff = view.plan.handoff
    designs = (handoff.design or model.EMPTY).get("slices") or model.EMPTY
    return Printed(
        "".join(
            "### "
            + documents.escaped(intent["id"])
            + "\n\nObservation:\n"
            + documents.fenced(handoff.facts[intent["observation"]], language="")
            + "\nPublic start recipe:\n"
            + (
                documents.fenced(handoff.facts[oracle["stimulus"]], language="")
                if oracle is not None and "stimulus" in oracle
                else "None.\n"
            )
            for intent in (handoff.product or model.EMPTY).get("slices", ())
            for oracle in (
                (designs.get(intent["id"]) or model.EMPTY).get("public_oracle"),
            )
        )
        or "None."
    )


def recording_kind(recipe):
    return {
        "po.discuss-v1": "product",
        "design.architect-v10": "design",
        "oracle.atd-v4": "acceptance",
        "examine.expectations-v1": "expectations",
        "po.charter-v1": "charter",
        "examine.user-v1": "examine",
        "craft.impl-v4": "craft",
        "craft.prefactor-v4": "craft",
        "review.atd-v1": "review",
        "review.craft-v1": "review",
    }[recipe.id]


def _bundle_scope(handoff):
    scope = handoff.scope
    if scope.kind in ("Feature", "Epic"):
        return scope.kind.lower(), scope.id
    return None


def _verb_reference(recipe, inputs, handoff, policy):
    kind = recording_kind(recipe)
    revision = (
        "Revision: open --from-current only revises authority that is already published, never as the first call of a first recording (the first add/set/remove creates the draft); retain unchanged rows, remove replaced rows before adding. Reference existing ids only.\n"
        if kind not in ("craft", "review")
        else ""
    )
    scope = ""
    if recipe.review_subject is not None:
        subject = (
            recipe.slice_review_subject
            if inputs.slice is not None and recipe.slice_review_subject is not None
            else recipe.review_subject
        )
        scope = (
            " Record scope: --subject "
            + subject
            + (" --slice " + inputs.slice if inputs.slice is not None else "")
        )
    scoped = _bundle_scope(handoff)
    binding = (
        ()
        if scoped is None or kind not in ("examine", "review")
        else (
            "Scope identity for every recording command: --"
            + scoped[0]
            + " "
            + scoped[1]
            + ".",
            *(
                (
                    "Commit owned files with: "
                    + grammar.commit_example(scoped, inputs.role),
                )
                if inputs.role is not None
                else ()
            ),
        )
    )
    recording = (
        "Bash; stated directory/scope/slice. First edit creates draft; close publishes/removes; abort removes. nwdes owns ids/JSON; no manual drafts/handoff or prose."
        + scope,
        "Refusal keeps draft: retry, no replay. Missing facts/authorization/checks: nonaccepted; name prerequisite/owner/remedy.",
        *binding,
    )
    return (
        revision
        + "\n".join(recording)
        + "\n\n"
        + grammar.describe(kind, role=inputs.role, policy=policy)
    )


def _examine_budget(view):
    return Printed(str(EXAMINE_WALL_BUDGET_MINUTES))


def _examine_rework(view):
    handoff = view.plan.handoff
    _, work = _at_path(handoff, "product.slices[].work", view.plan.inputs)
    if handoff.work.get("rework") or _slot(work, "rework"):
        return Printed(_EXAMINE_REWORK_RULE)
    return _NONE


def _verb(member):
    return model.recording_verb(member)


def _accepted(member):
    item = model.member_spec(member)
    if item.kind == "record":
        values = [
            field + " = " + " | ".join(child.members)
            for field, child in item.members
            if child.kind == "enum"
        ]
        return "; ".join(values) or "none, every field is free text"
    if item.kind == "enum":
        return " | ".join(item.members)
    if item.kind == "reference":
        prefixes = "".join(prefix + "<n> " for prefix in item.members)
        return prefixes + "identities already recorded in this handoff"
    return "free text"


def _asks(view):
    """The role's asks from the policy: each asked member's sentence, verb, accepted values,
    shape and example, plus the code targets it owes once the handoff holds slices."""
    policy = view.plan.policy
    targets = model.design_targets(view.plan.handoff.design or model.EMPTY)
    blocks = []
    for name in policy.asks.get(view.plan.inputs.role, ()):
        member = policy.members[name]
        lines = [
            member.ask.replace("{verb}", _verb(name)).replace(
                "{not_applicable}",
                "design not-applicable add --analysis " + name + " --reason TEXT",
            ),
            "Accepted values: " + _accepted(name) + ".",
            "Shape: " + _verb(name) + " " + member.shape + ".",
            "Example locator: " + member.example + ".",
        ]
        if member.minimum:
            lines.append(
                f"Required: at least {member.minimum} recorded; without it nwdes refuses with MissingFact naming {name}."
            )
        if member.cover == "target":
            lines.extend(
                f"Owes {name}: slice {identity}: {path}." for identity, path in targets
            )
        elif member.cover == "design" and targets:
            lines.append(f"Owes {name}: the design, once.")
        elif member.cover == "slice":
            owed = dict.fromkeys(identity for identity, _ in targets)
            lines.extend(f"Owes {name}: slice {identity}." for identity in owed)
        blocks.append("\n".join(lines))
    return Printed("\n\n".join(blocks)) if blocks else _NONE


_DERIVATIONS = MappingProxyType(
    {
        **{"authority/" + family: partial(_authority, family) for family in _SIBLINGS},
        "baseline_failures": _baseline_failures,
        **{name: partial(_packet, kind) for name, kind in _PACKET_KINDS.items()},
        "current_product": partial(_current, "product"),
        "current_design": partial(_current, "design"),
        "implementation_mode": _implementation_mode,
        "verification": partial(_verification, False),
        "prefactoring_verification": partial(_verification, True),
        "reach.constraints": partial(_reachable_field, "constraints"),
        "reach.architectural_tests": partial(_reachable_field, "architectural_tests"),
        "reach.contract_tests": partial(_reachable_field, "contract_tests"),
        "atd_owed": _owed,
        "atd_properties": partial(_properties, _PROPERTIES),
        "review_properties": partial(_properties, _REVIEW_PROPERTIES),
        "atd_obligations": _obligations,
        "craft_view": _craft_obligations,
        "acceptance_index": _acceptance_index,
        "charter_slices": _charter_slices,
        "examine_budget": _examine_budget,
        "asks": _asks,
        "examine_rework": _examine_rework,
    }
)

# Catalog data is immutable; only the template text varies per invocation.
_RECIPE_FIELDS = MappingProxyType(
    {
        recipe.id: frozenset(source.placeholder for source in recipe.sources)
        for recipe in RECIPES
    }
)
_RECIPE_SOURCE_PROBLEMS = MappingProxyType(
    {recipe.id: tuple(_source_problems(recipe)) for recipe in RECIPES}
)
_CONSUMER_PROBLEMS = _problems_of(check_consumers(model.SCHEMA_PATHS, CONSUMERS))


def _render_ready(plan):
    owed = (
        model.owed_obligation_texts(
            plan.handoff.design, plan.handoff.facts, plan.inputs.slice
        )
        if plan.inputs.slice is not None
        else ()
    )
    references = (
        documents.fact_references(plan.handoff, (plan.inputs, plan.template))
        if any(
            source.placeholder == "baseline_failures" for source in plan.recipe.sources
        )
        else None
    )
    if references is not None:
        plan = replace(plan, handoff=references.project(plan.handoff))
    reached = (
        reach(plan.handoff, plan.inputs.slice)
        if plan.inputs.slice is not None
        else None
    )
    craft = (
        _craft_view(reached, plan.inputs.slice)
        if any(source.name == "craft_view" for source in plan.recipe.sources)
        else None
    )
    view = _View(plan, reached, craft, owed)

    def field(source):
        if source.kind in ("input", "role"):
            value = getattr(plan.inputs, source.name)
            if source.name == "slice":
                return Printed(documents.escaped(value))
            if source.name == "jev":
                return Printed(value.value)
            if source.name == "diff":
                return (
                    Printed(documents.fenced(value).rstrip("\n"))
                    if value is not None
                    else _NONE
                )
            return Printed(value if value is not None else "None.")
        if source.kind == "path":
            projected = (
                reached
                if reached is not None and source.name == "product.promises"
                else plan.handoff
            )
            spec, value = _at_path(projected, source.name, plan.inputs)
            if (
                reached is not None
                and source.name == "expectations"
                and value is not None
            ):
                promises = frozenset(
                    row["id"]
                    for row in (reached.product or model.EMPTY).get("promises", ())
                )
                value = model.Record(
                    (
                        (
                            "rows",
                            tuple(
                                row
                                for row in value.get("rows", ())
                                if not row.get("promises")
                                or promises.intersection(row["promises"])
                            ),
                        ),
                    )
                )
            return _printed(spec, value, plan.handoff.facts)
        return _DERIVATIONS[source.name](view)

    bound = bind(
        plan.template,
        {source.placeholder: field(source) for source in plan.recipe.sources},
    )
    if not isinstance(bound, Built):
        return bound
    text = references.expand(bound.value) if references is not None else bound.value
    return Built(
        text.rstrip()
        + "\n\n"
        + _verb_reference(plan.recipe, plan.inputs, plan.handoff, plan.policy)
    )
