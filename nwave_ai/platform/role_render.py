"""Installed role text: the self-contained snapshot each host loads for one role.

Moved verbatim from the removed DES task-invocation renderer (S5-OQ1). Only the closure of
``render_installed_role`` is kept: the preloaded skills, the removed ``skills:`` key and the
deployed skills root. The source-blind and expectation-charter branches have no kept consumer
and are not ported; the installed bytes of every covered role are unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path


_SKILL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_INVOCATION = re.compile(r"Invoke (?:ONE )?Skill\(([A-Za-z0-9][A-Za-z0-9._-]*)\)")
_PREFIXES = ("~/.claude/skills/", "~/.agents/skills/")
# "Read `des <subcommand> --help`" names a command to execute, not a file.
_COMMAND_READ = re.compile(r"\bRead (`des(?: [a-z][a-z-]*)+ --help`)")
# "Read `<skill-id>`" names a skill by id; it resolves to that skill's file.
_SKILL_ID_READ = re.compile(r"\bRead `([A-Za-z0-9][A-Za-z0-9._-]*)`")
_CONDITIONAL_INDEX = re.compile(
    r"<!-- GENERATED:role-skill-loading START.*?"
    r"<!-- GENERATED:role-skill-loading END -->\n?",
    re.DOTALL,
)


def _conditional_index_first(text: str) -> str:
    """Emit the role's conditional skill index directly after its frontmatter.

    The index is the role's only statement of when to load a non-preloaded
    skill; read late, after the workflow, it was skipped. Placement is the
    renderer's job, not an authoring convention.
    """
    index = _CONDITIONAL_INDEX.search(text)
    if index is None:
        return text
    rest = text[: index.start()] + text[index.end() :]
    match = re.match(r"\s*---\n.*?\n---\n", rest, re.DOTALL)
    split = match.end() if match else 0
    block = index.group(0).rstrip("\n") + "\n"
    body = rest[split:].lstrip("\n")
    return rest[:split] + "\n" + block + ("\n" + body if body else "")


def _declared_skills(text: str) -> tuple[str, ...]:
    lines = text.lstrip().splitlines()
    if not lines or lines[0].strip() != "---":
        return ()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError(
            "Agent frontmatter has no closing delimiter; close it before loading skills."
        )
    frontmatter = "\n".join(lines[1:end])
    match = re.search(
        r"(?:^|[,{]\s*)skills\s*:\s*\[([^\]]*)\]", frontmatter, re.MULTILINE
    )
    if match is None:
        # The public role contract permits a block sequence too.  Do not try
        # to be a YAML parser: role skill names deliberately have a much
        # narrower grammar than YAML and this module ships without PyYAML.
        block = re.search(r"^skills\s*:\s*$", frontmatter, re.MULTILINE)
        if block is None:
            if re.search(r"(?:^|[,{]\s*)skills\s*:", frontmatter, re.MULTILINE):
                raise ValueError(
                    "Agent skills must be a bracketed or block list of plain skill directory names; correct the skills declaration."
                )
            return ()
        tail = frontmatter[block.end() :].splitlines()
        names: list[str] = []
        for line in tail:
            if not line.strip():
                continue
            item = re.fullmatch(r"\s+-\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*", line)
            if item is None:
                break
            names.append(item.group(1))
        if not names:
            raise ValueError(
                "Agent skills must be a bracketed or block list of plain skill directory names; correct the skills declaration."
            )
        return tuple(dict.fromkeys(names))

    raw_names = [name.strip() for name in match.group(1).split(",")]
    if not raw_names or any(
        not _SKILL_NAME.fullmatch(name) or name.isdecimal() for name in raw_names
    ):
        raise ValueError(
            "Agent skills must be a list of plain skill directory names; correct the skills declaration."
        )
    return tuple(dict.fromkeys(raw_names))


def _without_skills_key(text: str) -> str:
    """Remove the narrow, validated ``skills`` field without requiring PyYAML."""
    lines = text.splitlines(keepends=True)
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None or lines[first].strip() != "---":
        return text
    end = next(
        (i for i in range(first + 1, len(lines)) if lines[i].strip() == "---"), None
    )
    if end is None:
        return text

    frontmatter = "".join(lines[first + 1 : end])
    # Flow-map metadata is used by an existing compatibility fixture.  The
    # field itself has already passed the deliberately narrow parser above.
    frontmatter = re.sub(
        r"(\{|,)\s*skills\s*:\s*\[[^\]]*\]\s*(?=,|\})",
        lambda match: "{" if match.group(1) == "{" else "",
        frontmatter,
    )
    frontmatter_lines = frontmatter.splitlines(keepends=True)
    retained: list[str] = []
    skip_block_items = False
    for line in frontmatter_lines:
        if re.fullmatch(r"skills\s*:\s*\[[^\]]*\]\s*(?:\n)?", line):
            skip_block_items = False
            continue
        if re.fullmatch(r"skills\s*:\s*(?:\n)?", line):
            skip_block_items = True
            continue
        if skip_block_items and re.fullmatch(r"\s+-\s*[^\n]+(?:\n)?", line):
            continue
        skip_block_items = False
        retained.append(line)
    return "".join(lines[: first + 1]) + "".join(retained) + "".join(lines[end:])


def _skills_dir(spec: Path) -> Path:
    if spec.parent.name == "agents" and spec.parent.parent.name == "nWave":
        return spec.parent.parent / "skills"
    if spec.parent.name == "nw" and spec.parent.parent.name == "agents":
        return spec.parent.parent.parent / "skills"
    raise ValueError(
        f"Cannot resolve skills owned by {spec}; place the role under nWave/agents or agents/nw."
    )


def _portable_reads(text: str, directory: Path) -> str:
    text = _INVOCATION.sub(
        lambda match: f"Read {directory / match[1] / 'SKILL.md'}", text
    )
    text = _COMMAND_READ.sub(lambda match: f"Run {match[1]}", text)
    text = _SKILL_ID_READ.sub(
        lambda match: (
            f"Read {directory / match[1] / 'SKILL.md'}"
            if (directory / match[1] / "SKILL.md").is_file()
            else match[0]
        ),
        text,
    )
    for prefix in _PREFIXES:
        text = text.replace(prefix, str(directory) + "/")
    return text


def _expand(spec_path: Path) -> str:
    text = _conditional_index_first(spec_path.read_text(encoding="utf-8"))
    skills = _declared_skills(text)
    if (
        not skills
        and not _INVOCATION.search(text)
        and not _COMMAND_READ.search(text)
        and not _SKILL_ID_READ.search(text)
        and not any(p in text for p in _PREFIXES)
    ):
        return text
    directory = _skills_dir(spec_path.resolve())
    sections = [_portable_reads(text, directory)]
    if skills:
        sections.append(
            "\n\nThe following skills are already loaded. Do not reload them. "
            "Apply their knowledge within this role's explicit scope and tool boundaries. "
            "Conditional references remain on demand; a general method does not expand your role.\n"
        )
    for name in skills:
        path = directory / name / "SKILL.md"
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            raise OSError(
                f"Cannot preload declared skill {name} at {path}; restore its readable SKILL.md or correct the role declaration."
            ) from error
        sections.append(
            f"\n<!-- PRELOADED SKILL START: {name}; source: {path} -->\n"
            f"Relative references in this skill resolve against {path.parent}.\n"
            f"{_portable_reads(content, directory)}\n"
            f"<!-- PRELOADED SKILL END: {name} -->\n"
        )
    return "".join(sections)


def render_installed_role(source: str | Path, deployed_skills_root: str) -> str:
    """Self-contained installed snapshot: skills preloaded, ``skills:`` removed,
    conditional reads pointing at the deployed skills root."""
    spec_path = Path(source)
    text = _expand(spec_path)
    try:
        owned = str(_skills_dir(spec_path.resolve()))
    except ValueError:
        owned = None
    if owned:
        text = text.replace(owned, deployed_skills_root)
    return _without_skills_key(text)
