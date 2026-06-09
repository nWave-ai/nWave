"""Patch pyproject.toml for public nWave repo distribution.

Renames package, sets version, removes dev-only sections,
rewrites build targets.

CLI:
    python patch_pyproject.py --input PATH --output PATH \\
        --target-name NAME --target-version VERSION [--dry-run]

Exit codes:
    0 = success
    1 = input file not found / parse error / missing field
    2 = (reserved)
    3 = no changes needed
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    import tomli


# Ensure project root is importable for the privacy-strip dependency when this
# script is invoked standalone from a wheel-build sandbox.
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class PatchError(Exception):
    """Raised when patching fails (file not found, parse error, missing field)."""


# Dev-only TOML sections to strip from public distribution.
_DEV_SECTIONS = frozenset({"[tool.nwave]", "[tool.semantic_release]"})


def _read_and_validate(input_path: str) -> tuple[str, dict]:
    """Read raw TOML text and parse it for validation.

    Returns (raw_text, parsed_dict).
    Raises PatchError on file-not-found, parse error, or missing fields.
    """
    if not os.path.isfile(input_path):
        msg = f"Input file not found: {input_path}"
        raise PatchError(msg)

    raw = Path(input_path).read_text(encoding="utf-8")

    try:
        parsed = tomli.loads(raw)
    except tomli.TOMLDecodeError as exc:
        msg = f"TOML parse error in {input_path}: {exc}"
        raise PatchError(msg) from exc

    project = parsed.get("project", {})
    if "name" not in project:
        msg = "pyproject.toml missing required field: [project] name"
        raise PatchError(msg)

    return raw, parsed


def _patch_name(text: str, old_name: str, new_name: str) -> tuple[str, str | None]:
    """Replace the project name value (exact match inside [project] name line)."""
    pattern = re.compile(
        r'^(name\s*=\s*")' + re.escape(old_name) + r'(")', re.MULTILINE
    )
    new_text, count = pattern.subn(rf"\g<1>{new_name}\2", text)
    if count == 0:
        return text, None
    return new_text, f"name: {old_name} -> {new_name}"


def _patch_version(
    text: str, old_version: str, new_version: str
) -> tuple[str, str | None]:
    """Replace the project version value."""
    pattern = re.compile(
        r'^(version\s*=\s*")' + re.escape(old_version) + r'(")',
        re.MULTILINE,
    )
    new_text, count = pattern.subn(rf"\g<1>{new_version}\2", text)
    if count == 0:
        return text, None
    return new_text, f"version: {old_version} -> {new_version}"


def _patch_wheel_packages(text: str, new_name: str) -> tuple[str, str | None]:
    """Rewrite [tool.hatch.build.targets.wheel] packages and add force-include."""
    pkg_name = new_name.replace("-", "_")

    # Remove existing wheel section (base) and force-include subsection if present
    force_include = re.compile(
        r"^\[tool\.hatch\.build\.targets\.wheel\.force-include\]\s*\n(?:(?!\[).+\n?)*",
        re.MULTILINE,
    )
    text_clean = force_include.sub("", text)

    wheel_section = re.compile(
        r"^\[tool\.hatch\.build\.targets\.wheel\]\s*\n(?:(?!\[).+\n?)*",
        re.MULTILINE,
    )
    # Selective includes: only directories needed in the public package.
    # Avoids broken symlinks, dev-only directories, and closed-source runtime.
    #
    # Privacy note (fix-installer-private-skill-leak slice-01, 2026-05-20):
    # The `nWave/agents` + `nWave/skills` force-include below reads the tree on
    # disk verbatim. `python -m build --wheel` copies it into the .whl as-is, so
    # the tree MUST be privacy-stripped BEFORE the build. `patch_pyproject()`
    # invokes `strip_private_agents.strip()` on the tree containing this
    # pyproject.toml (see `_strip_private_artifacts`) — that is the in-place
    # half of the two-part fix; the force-include pointing at the now-stripped
    # `nWave/agents`+`nWave/skills` is the other half. build_dist.py also
    # produces a filtered dist/, but the wheel force-include bypasses dist/ and
    # reads source — so the strip has to happen on the source tree itself.
    #
    # Historical note (fix-wheel-leaks-des-config-p0, 2026-04-23):
    # Previously this block force-included broad "scripts" = "scripts" and
    # "src/des" = "src/des", which shipped 136 files of dev-only tooling
    # (release/, hooks/, framework/, validation/) and 149 files of closed-source
    # DES runtime to the public 3.11.0 wheel.  The fix:
    #   - narrows scripts to scripts/install + scripts/shared (the only subtrees
    #     imported by nwave_ai/cli.py AND scripts/install/*.py at runtime,
    #     verified by grep);
    #   - replaces raw src/des with the pre-built lib/python/des tree (which
    #     scripts/build_dist.py produces with imports rewritten src.des -> des)
    #     and places it under nWave/ so installer lookup matches.
    # The CI pypi-publish job (release-prod.yml) must run `scripts/build_dist.py`
    # and stage `dist/lib` -> `./lib` before `python -m build --wheel` for the
    # nWave/lib/python/des force-include to resolve.
    #
    # Path semantics for "lib/python/des" = "nWave/lib/python/des":
    #   LHS = source path relative to repo root -> <repo>/lib/python/des/
    #   RHS = destination inside wheel          -> site-packages/nWave/lib/python/des/
    # The installer's des_plugin.py:222 looks up
    # `context.framework_source / "lib/python/des"`.  When installed via pipx,
    # install_nwave.py sets framework_source = site-packages/nWave/, so files
    # must land at site-packages/nWave/lib/python/des/ — which only happens if
    # the force-include destination is prefixed with "nWave/".
    replacement = (
        "[tool.hatch.build.targets.wheel]\n"
        f'packages = ["{pkg_name}"]\n'
        "\n"
        "[tool.hatch.build.targets.wheel.force-include]\n"
        '"nWave/agents" = "nWave/agents"\n'
        '"nWave/scripts" = "nWave/scripts"\n'
        '"nWave/skills" = "nWave/skills"\n'
        '"nWave/tasks/nw" = "nWave/tasks/nw"\n'
        '"nWave/templates" = "nWave/templates"\n'
        '"nWave/framework-catalog.yaml" = "nWave/framework-catalog.yaml"\n'
        '"nWave/VERSION" = "nWave/VERSION"\n'
        '"nWave/README.md" = "nWave/README.md"\n'
        '"scripts/install" = "scripts/install"\n'
        '"scripts/shared" = "scripts/shared"\n'
        '"scripts/install_nwave_target_hooks.py" = "scripts/install_nwave_target_hooks.py"\n'
        '"scripts/validate_step_file.py" = "scripts/validate_step_file.py"\n'
        '"lib/python/des" = "nWave/lib/python/des"\n'
        '"schemas" = "schemas"\n'
    )
    new_text, count = wheel_section.subn(replacement, text_clean)
    if count == 0:
        return text, None
    return (
        new_text,
        f'wheel config: rewritten with packages=["{pkg_name}"] + force-include',
    )


def _add_cli_entry_point(text: str, new_name: str) -> tuple[str, str | None]:
    """Add [project.scripts] CLI entry point (merging into existing section if present).

    Behaviour per issue #41 RCA Branch A (skip->merge):
      - If [project.scripts] is absent, create the section after [project.urls]
        or before the first [tool.] section (preserves prior behaviour).
      - If [project.scripts] exists, MERGE the new entry into it (do not skip).
        Foreign entries are preserved alongside.
      - If the exact entry already exists, leave the file unchanged (idempotent).
    """
    pkg_name = new_name.replace("-", "_")
    entry_line = f'{new_name} = "{pkg_name}.cli:main"\n'

    if "[project.scripts]" in text:
        # Idempotency: bail out if the entry is already present.
        if entry_line.strip() in text:
            return text, None

        # Merge: insert the new entry on the line immediately after the
        # [project.scripts] header, preserving any foreign entries that follow.
        pattern = re.compile(r"(\[project\.scripts\]\n)")
        new_text, count = pattern.subn(rf"\1{entry_line}", text, count=1)
        if count == 0:
            return text, None
        return (
            new_text,
            f'merged [project.scripts] entry: {new_name} = "{pkg_name}.cli:main"',
        )

    scripts_block = f"\n[project.scripts]\n{entry_line}"

    # Insert after [project.urls] block (before next section)
    pattern = re.compile(r"(\[project\.urls\].*?\n)(\n\[)", re.DOTALL)
    new_text, count = pattern.subn(rf"\1{scripts_block}\2", text)
    if count == 0:
        # Fallback: append before first [tool.] section
        pattern2 = re.compile(r"(\n)(\[tool\.)")
        new_text, count = pattern2.subn(rf"\1{scripts_block}\2", text, count=1)
        if count == 0:
            return text, None
    return (
        new_text,
        f'added [project.scripts] entry point: {new_name} = "{pkg_name}.cli:main"',
    )


def _remove_section(text: str, header: str) -> tuple[str, str | None]:
    """Remove an entire TOML section (header + all lines until next section or EOF)."""
    # Match the section header and all lines up to (but not including) the next section header
    escaped = re.escape(header)
    pattern = re.compile(
        r"^" + escaped + r"\s*\n(?:(?!\[).+\n?)*",
        re.MULTILINE,
    )
    new_text, count = pattern.subn("", text)
    if count == 0:
        return text, None
    # Clean up any resulting double blank lines
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    return new_text, f"removed section: {header}"


def _strip_private_artifacts(input_path: str) -> str | None:
    """Privacy-strip the source tree the wheel force-include reads.

    The wheel ``force-include`` map points at ``nWave/agents`` +
    ``nWave/skills`` on disk. ``python -m build --wheel`` copies that tree
    verbatim, so any ``public: false`` agent or privately-owned skill present
    on disk leaks into the public ``.whl``. This strips the tree in place
    BEFORE the build runs.

    The strip preserves the ``PUBLIC_SHARED_SKILLS`` allow-list (load-bearing
    public skills with no owning public agent) — that logic lives in
    ``is_public_skill`` and is applied by ``strip()``.

    *input_path* is the pyproject.toml being patched; the tree root is its
    parent directory (the wheel-build sandbox). Returns a one-line change
    description, or ``None`` when there is no ``nWave/`` tree to strip.
    """
    tree_root = Path(input_path).resolve().parent
    if not (tree_root / "nWave" / "agents").is_dir():
        return None

    from scripts.release.strip_private_agents import strip

    removed = strip(tree_root)
    agents = len(removed["agents"])
    skills = len(removed["skills"])
    return (
        f"privacy strip: removed {agents} private agent(s) and "
        f"{skills} private skill dir(s) before wheel build"
    )


def patch_pyproject(
    input_path: str,
    output_path: str,
    target_name: str,
    target_version: str,
    dry_run: bool = False,
) -> dict:
    """Patch a pyproject.toml for public distribution.

    Returns a dict with keys: patched, changes, output_path.
    """
    raw, parsed = _read_and_validate(input_path)

    old_name = parsed["project"]["name"]
    old_version = parsed["project"].get("version", "0.0.0")

    text = raw
    changes: list[str] = []

    # 1. Name swap
    text, change = _patch_name(text, old_name, target_name)
    if change:
        changes.append(change)

    # 2. Version set
    text, change = _patch_version(text, old_version, target_version)
    if change:
        changes.append(change)

    # 3. Rewrite wheel packages + force-include
    text, change = _patch_wheel_packages(text, target_name)
    if change:
        changes.append(change)

    # 4. Add CLI entry point
    text, change = _add_cli_entry_point(text, target_name)
    if change:
        changes.append(change)

    # 5. Remove dev-only sections
    for section in sorted(_DEV_SECTIONS):
        text, change = _remove_section(text, section)
        if change:
            changes.append(change)

    # Final cleanup: collapse triple+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 6. Privacy-strip the source tree the wheel force-include reads.
    #    Mutates the filesystem, so skip under --dry-run.
    if not dry_run:
        strip_change = _strip_private_artifacts(input_path)
        if strip_change:
            changes.append(strip_change)

    patched = len(changes) > 0

    if not dry_run:
        Path(output_path).write_text(text, encoding="utf-8")

    return {
        "patched": patched,
        "changes": changes,
        "output_path": output_path,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Patch pyproject.toml for public distribution"
    )
    parser.add_argument(
        "--input", required=True, dest="input_path", help="Source pyproject.toml"
    )
    parser.add_argument(
        "--output", required=True, dest="output_path", help="Output path"
    )
    parser.add_argument("--target-name", required=True, help="Target package name")
    parser.add_argument("--target-version", required=True, help="Target version")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show diff without writing"
    )

    args = parser.parse_args()

    try:
        result = patch_pyproject(
            input_path=args.input_path,
            output_path=args.output_path,
            target_name=args.target_name,
            target_version=args.target_version,
            dry_run=args.dry_run,
        )
        print(json.dumps(result))
        sys.exit(0)
    except PatchError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
