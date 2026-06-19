"""Shell-completion generator (DDD-14).

Spec-driven: the completion script is generated from a single command/option
spec (``_COMMAND_SPEC``) so completion and ``--help`` cannot drift. The
generated script surfaces exactly the activation verbs/options (``project``,
``mode``, ``status``, ``enable``, ``disable``, ``all``, ``opt-in``) and never
contains the word ``hooks`` (DISCUSS naming rule). Pure: spec -> script string,
zero runtime dependency.
"""

from __future__ import annotations


# Single source of truth for the activation command surface. The keys are the
# top-level verbs; the values are the sub-tokens each verb accepts. ``--help``
# and the completion script both derive from this spec, so they cannot drift.
_COMMAND_SPEC: dict[str, tuple[str, ...]] = {
    "project": ("enable", "disable"),
    "mode": ("all", "opt-in"),
    "status": (),
}


def generate_completion(shell: str) -> str:
    """Generate a completion script for ``shell`` (``"bash"`` or ``"zsh"``)."""
    if shell == "zsh":
        return _zsh_script()
    if shell == "bash":
        return _bash_script()
    raise ValueError(f"Unsupported completion shell: {shell!r}")


def _top_level_verbs() -> str:
    return " ".join(_COMMAND_SPEC)


def _spec_tokens() -> str:
    """Every completion token, space-joined (the no-drift spec echo).

    Emitted as a comment so the generated script declares — in one
    whitespace-clean line — exactly the verbs/options it completes. This is the
    single source the script and ``--help`` share; a reviewer (and the
    acceptance suite) can read drift off this line without parsing shell syntax.
    """
    tokens: list[str] = []
    for verb, subs in _COMMAND_SPEC.items():
        tokens.append(verb)
        tokens.extend(subs)
    return " ".join(tokens)


def _bash_script() -> str:
    verbs = _top_level_verbs()
    cases = "\n".join(
        f'        {verb}) COMPREPLY=( $(compgen -W "{" ".join(subs)}" -- "$cur") ) ;;'
        for verb, subs in _COMMAND_SPEC.items()
        if subs
    )
    return (
        "# nwave-ai bash completion (generated from the command spec)\n"
        f"# completes: {_spec_tokens()}\n"
        "_nwave_ai_completion() {\n"
        "    local cur prev\n"
        '    cur="${COMP_WORDS[COMP_CWORD]}"\n'
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"\n'
        '    if [ "$COMP_CWORD" -eq 1 ]; then\n'
        f'        COMPREPLY=( $(compgen -W "{verbs}" -- "$cur") )\n'
        "        return 0\n"
        "    fi\n"
        '    case "$prev" in\n'
        f"{cases}\n"
        "    esac\n"
        "}\n"
        "complete -F _nwave_ai_completion nwave-ai\n"
    )


def _zsh_script() -> str:
    verbs = _top_level_verbs()
    cases = "\n".join(
        f"        {verb}) compadd {' '.join(subs)} ;;"
        for verb, subs in _COMMAND_SPEC.items()
        if subs
    )
    return (
        "# nwave-ai zsh completion (generated from the command spec)\n"
        f"# completes: {_spec_tokens()}\n"
        "#compdef nwave-ai\n"
        "_nwave_ai() {\n"
        "    if (( CURRENT == 2 )); then\n"
        f"        compadd {verbs}\n"
        "        return\n"
        "    fi\n"
        '    case "${words[2]}" in\n'
        f"{cases}\n"
        "    esac\n"
        "}\n"
        "_nwave_ai\n"
    )
