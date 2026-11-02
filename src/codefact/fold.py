"""Total, read-only interpretation of an ordered provider composition."""

from __future__ import annotations

from codefact.model import (
    D3_CAUSES,
    REFERENCE_SHAPES,
    STABLE_CORE_CAPABILITY_IDS,
    TRACE_DETAIL_MAX_CHARS,
    TRACE_EXEMPLARS_MAX,
    Answered,
    Answers,
    Capability,
    Failed,
    Fault,
    Indeterminate,
    Passes,
    Provider,
    Reply,
    Request,
    Resolution,
    Snapshot,
    Source,
    Stale,
    TraceEntry,
    Unsupported,
)


def _entry(provider_id, event, observation=None, *, detail=""):
    return TraceEntry(
        provider_id,
        event,
        observation.scope if observation is not None else "complete",
        observation.fault_count if observation is not None else 0,
        tuple(observation.exemplars[:TRACE_EXEMPLARS_MAX])
        if observation is not None
        else (),
        detail[:TRACE_DETAIL_MAX_CHARS],
    )


def _attempt(
    provider: Provider, capability: Capability, request: Request, snapshot: Snapshot
):
    try:
        cover = provider.cover(capability, request, snapshot)
        match cover:
            case Passes() | Stale():
                return cover, None
            case Answers():
                reply = provider.answer(capability, request, snapshot)
                if isinstance(reply, Reply):
                    return cover, reply
                if isinstance(reply, Fault):
                    return cover, (
                        reply
                        if reply.cause in D3_CAUSES
                        else Fault(
                            "provider-error",
                            reply.fault_count,
                            reply.exemplars,
                            reply.scope,
                        )
                    )
        return Passes(), Fault("provider-error")
    except Exception:
        return Passes(), Fault("provider-error")


def resolve(
    capability: Capability,
    request: Request,
    providers: tuple[Provider, ...],
    snapshot: Snapshot,
) -> Resolution:
    return _resolve(capability, request, providers, snapshot, ())


def _resolve(capability, request, providers, snapshot, trace) -> Resolution:
    if not providers:
        return (
            Failed(trace[-1].event.removeprefix("failed:"), trace)
            if trace
            else Unsupported(capability.id, (), trace)
        )
    provider, *remaining = providers
    cover, reply = _attempt(provider, capability, request, snapshot)
    match cover:
        case Stale(index, coverage):
            entry = _entry(
                provider.id,
                "attempted",
                Fault("provider-error", exemplars=coverage.uncovered()),
                detail=f"index does not cover {len(coverage.uncovered())} file(s) in scope ({len(coverage.missing)} missing, {len(coverage.stale)} stale)",
            )
            return Indeterminate(provider.id, index, coverage, (*trace, entry))
        case Passes(cause) if cause is not None:
            trace = (*trace, _entry(provider.id, "failed:provider-error", detail=cause))
        case _:
            pass
    if reply is None:
        return _resolve(capability, request, tuple(remaining), snapshot, trace)
    missing = (
        set(REFERENCE_SHAPES) - set(cover.represents)
        if isinstance(cover, Answers)
        and capability.id in {"query.callers-of", "query.reads-of", "query.never-wired"}
        else set()
    )
    if isinstance(reply, Reply) and reply.evidence_count == 0 and missing:
        entry = _entry(
            provider.id,
            "failed:unrepresented-reference-shape",
            Fault("unrepresented-reference-shape", scope=reply.scope),
            detail=", ".join(sorted(missing)),
        )
    elif isinstance(reply, Reply):
        entry = _entry(provider.id, "answered", reply)
        return Answered(
            provider.id,
            cover.confidence,
            reply.payload,
            (*trace, entry),
            reply.index,
            reply.coverage,
            reply.evidence_count,
        )
    else:
        entry = _entry(provider.id, "failed:" + reply.cause, reply)
    return _resolve(capability, request, tuple(remaining), snapshot, (*trace, entry))


def verify_composition_coverage(
    providers: tuple[Provider, ...],
) -> tuple[Provider, ...]:
    ids = tuple(p.id for p in providers)
    if any(not p.strip() for p in ids) or len(set(ids)) != len(ids):
        raise ValueError(
            "WHAT: blank or duplicate provider id. WHY: provider identity must be unique and nonempty. HOW: compose providers with distinct nonempty ids."
        )
    sample = Snapshot(
        "/scope",
        {"example.py": Source(b"def target(): pass\n", 0)},
    )
    missing = tuple(
        c
        for c in sorted(STABLE_CORE_CAPABILITY_IDS)
        if not any(_covers(p, Capability(c), sample) for p in providers)
    )
    if missing:
        raise ValueError(
            "WHAT: uncovered stable core capabilities: "
            + ", ".join(missing)
            + ". WHY: no provider covers them. HOW: compose a provider covering every stable core capability."
        )
    return providers


def _covers(provider, capability, snapshot) -> bool:
    try:
        return isinstance(
            provider.cover(
                capability, {"symbol": "target", "anchor": "target"}, snapshot
            ),
            Answers,
        )
    except Exception:
        return False
