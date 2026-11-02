"""Pure role ownership, leaf-path selection and conventional commit messages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from nwdes import documents, drafts, prompts
from nwdes import handoff as model
from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.destinations import Destinations, DocumentKind, local_path


class Role(str, Enum):
    ProductOwner = "nw-product-owner"
    Architect = "nw-solution-architect"
    AcceptanceDesigner = "nw-acceptance-designer"
    Examiner = "nw-user-examiner"
    SoftwareCrafter = "nw-software-crafter"
    FunctionalCrafter = "nw-functional-software-crafter"
    CandidateReviewer = "nw-software-crafter-reviewer"
    OracleReviewer = "nw-acceptance-designer-reviewer"


class CommitType(str, Enum):
    Feature = "feat"
    Fix = "fix"
    Docs = "docs"
    Style = "style"
    Refactor = "refactor"
    Performance = "perf"
    Test = "test"
    Build = "build"
    CI = "ci"
    Chore = "chore"
    Revert = "revert"


_AUTHORITY_DOCUMENTS = MappingProxyType(
    {
        Role.ProductOwner: DocumentKind.Product,
        Role.Architect: DocumentKind.Architecture,
        Role.AcceptanceDesigner: DocumentKind.Acceptance,
        Role.Examiner: DocumentKind.Acceptance,
    }
)


def _selected_slices(handoff, slice_id):
    slices = (handoff.design or model.EMPTY).get("slices", model.EMPTY)
    return tuple(
        (identity, value)
        for identity, value in slices.items()
        if slice_id is None or identity == slice_id
    )


def _review_records(role, selected, directory):
    scopes = (
        drafts.review_scope(subject, identity)
        for recipe in prompts.RECIPES
        if role.value in recipe.roles
        for subject in (recipe.review_subject, recipe.slice_review_subject)
        if subject is not None
        for identity in (
            (None,) if subject == drafts.ReviewSubject.CANDIDATE.value else selected
        )
    )
    return frozenset(
        directory + "/runs/" + drafts.DraftKey("review", scope.value).filename
        for scope in scopes
    )


def owned_paths(
    role: Role,
    handoff: model.Handoff,
    destinations: Destinations,
    slice: str | None,
) -> frozenset[str]:
    """Project one role's ownership; a trailing slash denotes an owned subtree."""
    directory = destinations.handoff.rpartition("/")[0]
    selected = _selected_slices(handoff, slice)
    authority = _AUTHORITY_DOCUMENTS.get(role)
    briefs = dict(destinations.briefs)
    authority_paths = (
        frozenset(
            (
                destinations.handoff,
                briefs[authority],
                briefs[authority].removesuffix(".md") + ".html",
            )
        )
        if authority is not None
        else frozenset()
    )
    match role:
        case Role.ProductOwner | Role.Examiner:
            return authority_paths
        case Role.Architect:
            return authority_paths | {
                directory + "/design/",
                destinations.adr_directory.rstrip("/") + "/",
            }
        case Role.AcceptanceDesigner:
            return authority_paths | frozenset(
                path
                for _, designed in selected
                for path in (designed.get("oracle"), *designed.get("supports", ()))
                if path is not None
            )
        case Role.SoftwareCrafter | Role.FunctionalCrafter:
            return frozenset(
                (
                    *(
                        target["path"]
                        for _, value in selected
                        for target in value.get("targets", ())
                    ),
                    *(
                        directory
                        + "/runs/"
                        + drafts.DraftKey("craft", identity).filename
                        for identity, _ in selected
                    ),
                )
            )
        case Role.CandidateReviewer | Role.OracleReviewer:
            return _review_records(
                role, tuple(identity for identity, _ in selected), directory
            )


def owns(owned: frozenset[str], path: str) -> bool:
    return local_path(path) and (
        path in owned
        or any(root.endswith("/") and path.startswith(root) for root in owned)
    )


def path_owners(handoff, destinations, paths) -> Mapping[str, frozenset[Role]]:
    """Project the complete ownership relation, never an inferred writer."""
    permissions = tuple(
        (role, owned_paths(role, handoff, destinations, None)) for role in Role
    )
    return MappingProxyType(
        {
            path: frozenset(role for role, owned in permissions if owns(owned, path))
            for path in paths
        }
    )


@dataclass(frozen=True)
class _SelectionRefused(Refused):
    """Retain unadmitted names for independent receipt diagnostics, never effects."""

    candidate_paths: tuple[str, ...]


def select_paths(
    role: Role,
    owned: frozenset[str],
    owners: Mapping[str, frozenset[Role]],
    changed: frozenset[str],
    explicit: tuple[str, ...],
):
    paths = (
        tuple(dict.fromkeys(explicit))
        if explicit
        else tuple(sorted(path for path in changed if owns(owned, path)))
    )
    problems = tuple(
        Defect(
            f"UnownedFile: {path}",
            f"No delivery role owns {path}.",
            "Name only paths a delivery role owns; nwdes never stages an unowned file.",
        )
        for path in paths
        if not owns(owned, path) and not owners.get(path)
    )
    empty = (
        (
            Defect(
                f"NothingToCommit: {role.value}",
                "No changed owned file was selected.",
                "Close this role's work and select its changed owned files with nwdes commit.",
            ),
        )
        if not paths
        else ()
    )
    result = checked(paths, (*problems, *empty))
    return (
        _SelectionRefused(result.refusal, paths)
        if isinstance(result, Refused)
        else result
    )


def message(
    kind: CommitType, description: str, scope: str | None, body: str | None
) -> str:
    subject = (
        kind.value + (f"({scope})" if scope is not None else "") + ": " + description
    )
    return subject + ("\n\n" + body if body is not None else "")


@dataclass(frozen=True)
class CloseReceipt:
    role: Role
    scope: model.Record
    head: str
    paths: model.Record

    def __post_init__(self):
        if not isinstance(self.role, Role):
            raise TypeError("A close receipt requires its declared Role.")


@dataclass(frozen=True)
class ReceiptUnavailable:
    role: Role
    defect: Defect


def digest(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def close_receipt(role: Role, scope, head, published: documents.OutputSet):
    return CloseReceipt(
        role,
        model.freeze(scope),
        head,
        model.Record(
            (output.path, digest(output.data)) for output in published.outputs
        ),
    )


def refreshed_receipt(receipt, published: documents.OutputSet):
    """Re-point a receipt at the bytes its typed write generated, never at disk.

    A receipt that does not already cover every published path is not refreshed,
    so it keeps refusing the commit.
    """
    generated = {output.path: digest(output.data) for output in published.outputs}
    if not set(generated) <= set(receipt.paths):
        return None
    return CloseReceipt(
        receipt.role,
        receipt.scope,
        receipt.head,
        model.Record(
            (path, generated.get(path, sha)) for path, sha in receipt.paths.items()
        ),
    )


def receipt_bytes(receipt: CloseReceipt) -> bytes:
    return (
        json.dumps(
            {
                "role": receipt.role.value,
                "scope": model.to_data(receipt.scope),
                "head": receipt.head,
                "paths": model.to_data(receipt.paths),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def read_receipt(raw: bytes, path: str):
    try:
        value = json.loads(raw)
        role = Role(value["role"])
        scope, head, paths = value["scope"], value["head"], value["paths"]
        if (
            not isinstance(scope, Mapping)
            or not isinstance(head, str)
            or not isinstance(paths, Mapping)
            or any(
                not isinstance(name, str)
                or not local_path(name)
                or not isinstance(sha, str)
                for name, sha in paths.items()
            )
        ):
            raise ValueError("A close receipt needs scope, HEAD and path digests.")
    except (UnicodeError, ValueError, TypeError, KeyError) as error:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: " + path,
                    "The close receipt cannot be read: " + str(error),
                    "Restore the role's published close receipt before nwdes commit.",
                ),
            ),
        )
    return Built(CloseReceipt(role, model.freeze(scope), head, model.freeze(paths)))


def recording_role(kind, subject=None, actor=None):
    if kind == "craft":
        if actor is None:
            return checked(
                None,
                (
                    Defect(
                        "MissingFact: --role",
                        "The close receipt names the crafter that actually closed.",
                        "Rerun craft close with --role "
                        + " or --role ".join(drafts.CRAFT_ACTOR.members)
                        + ".",
                    ),
                ),
            )
        if actor not in drafts.CRAFT_ACTOR.members:
            return checked(
                None,
                (
                    Defect(
                        "PartInvalid: --role",
                        "A craft close must name one of its two crafter roles.",
                        "Use --role "
                        + " or --role ".join(drafts.CRAFT_ACTOR.members)
                        + ".",
                    ),
                ),
            )
        return Built(Role(actor))
    return Built(
        Role(
            next(
                role
                for recipe in prompts.RECIPES
                if prompts.recording_kind(recipe) == kind
                and (
                    kind != "review"
                    or subject in (recipe.review_subject, recipe.slice_review_subject)
                )
                for role in recipe.roles
            )
        )
    )


def _scope_flags(scope):
    kind = scope.get("kind", "").lower()
    return f" --{kind} {scope['id']}" if kind in ("feature", "epic") else ""


def _close_command(role, scope, slice_id):
    recipe = next(recipe for recipe in prompts.RECIPES if role.value in recipe.roles)
    kind = prompts.recording_kind(recipe)
    subject = (
        recipe.slice_review_subject
        if slice_id is not None and recipe.slice_review_subject is not None
        else recipe.review_subject
    )
    return (
        "nwdes "
        + kind
        + " close"
        + (f" --subject {subject}" if subject else "")
        + _scope_flags(scope)
        + (f" --slice {slice_id}" if slice_id else "")
        + (f" --role {role.value}" if kind == "craft" else "")
    )


def authority_kind(kind):
    return any(
        prompts.recording_kind(recipe) == kind
        and any(Role(role) in _AUTHORITY_DOCUMENTS for role in recipe.roles)
        for recipe in prompts.RECIPES
    )


def is_own_matching_receipt(receipt, role, scope, current) -> bool:
    """This role's close for this recorded scope, still matching the disk."""
    return (
        isinstance(receipt, CloseReceipt)
        and receipt.role == role
        and receipt.scope == scope
        and matches_disk(receipt, current)
    )


@dataclass(frozen=True)
class CommitRequest:
    role: Role
    slice: str | None
    explicit: tuple[str, ...]


@dataclass(frozen=True)
class CommitObservation:
    head: str
    identity: str | None
    identity_reason: str
    staged: tuple[str, ...]
    changed: frozenset[str]
    receipts: tuple[CloseReceipt | ReceiptUnavailable, ...]
    current: model.Record
    directories: frozenset[str]


def _receipt_problems(request, scope, receipt, observed):
    role, slice_id = request.role, request.slice
    if isinstance(receipt, ReceiptUnavailable):
        return ()
    if receipt is None:
        return (
            Defect(
                "MissingCloseReceipt: "
                + role.value
                + _scope_flags(scope)
                + (f" --slice {slice_id}" if slice_id else ""),
                "No close receipt exists for this role and scope.\n"
                "StaleBase not run: no close receipt exists.",
                "Close your draft first with "
                + _close_command(role, scope, slice_id)
                + ".",
            ),
        )
    stale = (
        (
            Defect(
                "StaleBase: " + role.value,
                f"The role closed at {receipt.head}; lane HEAD is {observed.head}.",
                "Reconcile the intervening commit and close this role's draft again before nwdes commit.",
            ),
        )
        if receipt.head != observed.head
        else ()
    )
    return stale


def prepare_commit(request: CommitRequest, document, destinations, observed):
    role, slice_id, explicit = request.role, request.slice, request.explicit
    owned = owned_paths(role, document, destinations, slice_id)
    selected = select_paths(
        role,
        owned,
        path_owners(document, destinations, (*observed.changed, *explicit)),
        observed.changed,
        explicit,
    )
    paths = (
        selected.candidate_paths
        if isinstance(selected, _SelectionRefused)
        else selected.value
    )
    scope = model.freeze(model.to_data(document.scope))
    receipt = next(
        (
            receipt
            for receipt in observed.receipts
            if receipt.role == role
            and (
                isinstance(receipt, ReceiptUnavailable)
                or (
                    model.Record(
                        (name, value)
                        for name, value in receipt.scope.items()
                        if name != "slice"
                    )
                    == scope
                    and (slice_id is None or receipt.scope.get("slice") == slice_id)
                )
            )
        ),
        None,
    )
    identity = (
        (
            Defect(
                "IdentityMissing: git var GIT_AUTHOR_IDENT",
                observed.identity_reason,
                "Configure the repository's Git author name and email, then rerun nwdes commit.",
            ),
        )
        if observed.identity is None
        else ()
    )
    index = (
        (
            Defect(
                "IndexNotClean: " + ", ".join(observed.staged),
                "The index already holds staged paths.",
                "Run git restore --staged -- "
                + " ".join(observed.staged)
                + " without discarding their working-tree changes, then rerun nwdes commit.",
            ),
        )
        if observed.staged
        else ()
    )
    directories = tuple(
        Defect(
            "UnownedFile: " + path,
            "A directory is not an owned leaf path that nwdes can stage exactly.",
            "Name each owned file separately with --path; nwdes never stages a directory.",
        )
        for path in paths
        if path in observed.directories
    )
    problems = (
        *identity,
        *index,
        *(
            receipt.defect
            for receipt in observed.receipts
            if isinstance(receipt, ReceiptUnavailable)
        ),
        *(
            value.defect
            for value in observed.current.values()
            if isinstance(value, model.UnavailableInput)
        ),
        *_receipt_problems(request, scope, receipt, observed),
        *(
            defect
            for defect in (selected.defects if isinstance(selected, Refused) else ())
            if not (
                defect.what == f"NothingToCommit: {role.value}"
                and not any(owns(owned, path) for path in observed.changed)
                and isinstance(receipt, CloseReceipt)
                and all(
                    observed.current.get(path) == value
                    for path, value in receipt.paths.items()
                )
            )
        ),
        *directories,
    )
    return checked(
        paths
        if any(path in observed.changed for path in paths)
        or any(owns(owned, path) for path in observed.changed)
        else (),
        problems,
    )


def receipt_is_pending(receipt, current, at_head):
    return any(current.get(path) != at_head.get(path) for path in receipt.paths)


def matches_disk(receipt, current):
    """Whether every path this receipt published still holds those exact bytes."""
    return all(current.get(path) == digest for path, digest in receipt.paths.items())
