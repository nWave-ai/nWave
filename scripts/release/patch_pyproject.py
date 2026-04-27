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


if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    import tomli


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

    raw = open(input_path).read()

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
    )
    new_text, count = wheel_section.subn(replacement, text_clean)
    if count == 0:
        return text, None
    return (
        new_text,
        f'wheel config: rewritten with packages=["{pkg_name}"] + force-include',
    )


def _add_cli_entry_point(text: str, new_name: str) -> tuple[str, str | None]:
    """Add [project.scripts] CLI entry point after [project.urls] section."""
    if "[project.scripts]" in text:
        return text, None

    pkg_name = new_name.replace("-", "_")
    scripts_block = f'\n[project.scripts]\n{new_name} = "{pkg_name}.cli:main"\n'

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

    patched = len(changes) > 0

    if not dry_run:
        with open(output_path, "w") as f:
            f.write(text)

    return {
        "patched": patched,
        "changes": changes,
        "output_path": output_path,
    }


if __name__ == "__main__":
    import argparse
    import json
    import sys

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
