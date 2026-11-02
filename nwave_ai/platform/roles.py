"""Typed provider/model selection for one DES role invocation.

The selected pair is deliberately atomic: a configuration tier either owns
both provider and model for a role/default, or it is invalid.  Selecting a
provider from one tier and a model from another would manufacture a runtime no
operator declared.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from nwave_ai.platform.capability import resolve_declared_capability


if TYPE_CHECKING:
    from pathlib import Path


class ModelProvider(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass(frozen=True, slots=True)
class RoleRuntime:
    provider: ModelProvider
    model: str


class ModelRuntimeConfigError(ValueError):
    """A present model-runtime declaration cannot safely select a provider."""


#: Separates a role id from an optional competence label in one resolvable
#: key. Kept out of role ids and competence labels themselves (rejected at
#: construction below) so splitting is never ambiguous.
_COMPETENCE_SEPARATOR = "#"


def qualify_role_id(role_id: str, competence: str | None) -> str:
    """Build the resolvable key for ``role_id`` under one optional competence.

    The orchestrator passes ``competence`` as an explicit construction
    parameter when a turn needs a different competence than the role's
    ordinary one -- never derived here from Request size or any other
    heuristic (ADR-SSOT-002 Section 4b: DES constructs, it does not route).
    ``competence=None`` returns ``role_id`` unchanged, so every existing
    caller that never passes a competence resolves byte-identically to today.
    """
    if competence is None:
        return role_id
    if not competence.strip():
        raise ValueError("competence must be a non-empty string")
    if _COMPETENCE_SEPARATOR in competence or _COMPETENCE_SEPARATOR in role_id:
        raise ValueError(
            f"role id and competence must not contain {_COMPETENCE_SEPARATOR!r}"
        )
    return f"{role_id}{_COMPETENCE_SEPARATOR}{competence}"


def _base_role_id(role_id: str) -> str:
    return role_id.split(_COMPETENCE_SEPARATOR, 1)[0]


def _runtime(value: object, *, source: str) -> RoleRuntime:
    if not isinstance(value, dict):
        raise ModelRuntimeConfigError(
            f"{source} must be an object with provider and model"
        )
    if set(value) != {"provider", "model"}:
        raise ModelRuntimeConfigError(
            f"{source} must declare exactly provider and model as one atomic pair"
        )
    provider = value["provider"]
    model = value["model"]
    if not isinstance(provider, str):
        raise ModelRuntimeConfigError(f"{source}.provider must be claude or codex")
    try:
        selected_provider = ModelProvider(provider)
    except ValueError as exc:
        raise ModelRuntimeConfigError(
            f"{source}.provider must be claude or codex, got {provider!r}"
        ) from exc
    if not isinstance(model, str) or not model.strip():
        raise ModelRuntimeConfigError(f"{source}.model must be a non-empty string")
    return RoleRuntime(selected_provider, model)


def _declared(tier: dict[str, Any], *, role_id: str, source: str) -> RoleRuntime | None:
    if "model_runtime" not in tier:
        return None
    runtime = tier["model_runtime"]
    if not isinstance(runtime, dict):
        raise ModelRuntimeConfigError(f"{source}.model_runtime must be an object")
    unknown = set(runtime) - {"default", "roles"}
    if unknown:
        raise ModelRuntimeConfigError(
            f"{source}.model_runtime has unsupported keys {sorted(unknown)!r}"
        )
    roles = runtime.get("roles")
    if roles is not None and not isinstance(roles, dict):
        raise ModelRuntimeConfigError(f"{source}.model_runtime.roles must be an object")
    if isinstance(roles, dict) and role_id in roles:
        return _runtime(
            roles[role_id], source=f"{source}.model_runtime.roles[{role_id!r}]"
        )
    if "default" in runtime:
        return _runtime(runtime["default"], source=f"{source}.model_runtime.default")
    # A tier that declares only roles for other roles has no opinion here.
    return None


def resolve_role_runtime(
    role_id: str,
    *,
    global_tier: dict[str, Any],
    repo_tier: dict[str, Any],
    repo_root: Path,
    framework_root: Path | None = None,
) -> RoleRuntime:
    """Resolve one role with repo -> global -> declared-Claude precedence.

    ``role_id`` may carry a competence suffix from :func:`qualify_role_id`.
    Each tier is searched for the qualified key first, falling back to the
    bare role within the SAME tier before moving to the next tier -- so a
    project override of the bare role still wins over a global competence
    declaration, and an undeclared competence quietly resolves to whatever
    the bare role already resolves to today.
    """
    base_role_id = _base_role_id(role_id)
    candidates = (role_id,) if base_role_id == role_id else (role_id, base_role_id)
    for tier, source in ((repo_tier, "repo config"), (global_tier, "global config")):
        for candidate in candidates:
            selected = _declared(tier, role_id=candidate, source=source)
            if selected is not None:
                return selected
    declared = resolve_declared_capability(
        base_role_id, repo_root=repo_root, framework_root=framework_root
    ).declared_model
    if declared is None:
        raise ModelRuntimeConfigError(
            f"no model_runtime declaration and {role_id!r} declares no legacy Claude model"
        )
    return RoleRuntime(ModelProvider.CLAUDE, declared)
