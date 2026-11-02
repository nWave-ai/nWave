"""Plugin for installing nWave Skills into Codex CLI's SKILL.md format.

Codex CLI expects skills at: $HOME/.agents/skills/{skill-name}/SKILL.md
Each skill lives in its own directory with a single SKILL.md file.

This is distinct from OpenCode (~/.config/opencode/skills/) and Claude Code
(~/.claude/skills/). The Codex skills path is under $HOME/.agents/, not
under ~/.codex/ -- per official Codex CLI documentation.

A manifest file (.nwave-manifest.json) tracks which skills nWave installed,
so uninstall() can remove only nWave skills without touching user-created ones.
"""

import json
import os
import re
import shutil
from collections import Counter
from hashlib import sha256
from pathlib import Path
from stat import S_ISDIR, S_ISREG

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import detect_command_skills, load_public_agents
from scripts.shared.codex_model_wording import rewrite_claude_model_names
from scripts.shared.frontmatter import parse_frontmatter_file
from scripts.shared.platform_contracts import CODEX_SKILL_FORBIDDEN_FIELDS
from scripts.shared.skill_distribution import (
    enumerate_skills,
    filter_public_skills,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-manifest.json"
_ATTESTED_LEGACY_SKILLS_METADATA_KEY = "_nwave_codex_attested_legacy_skills"

# The first public Codex installer (manifest version 1.0) omitted these two
# command skills.  This is deliberately a closed historical set: newly added
# commands must never become implicitly adoptable merely because their name
# starts with ``nw-``.  The digests are of the Codex rendering written by that
# installer, not of the Claude source asset.
_V1_OMITTED_PUBLIC_COMMAND_SKILL_DIGESTS = {
    "nw-design": "9ff2358b5b9f27b4dcd0cbb77f9b90b91913fe6ba6614f7bfb79c6b2027875b3",
    "nw-deliver": "4b24054d706d03fc6f8d84c156f07690a7151dca35c3de054f74a89b4f64b7f0",
}

# A separate public v1 bootstrap wrote an incomplete 174-skill manifest while
# installing this exact 27-skill command profile.  These are intentionally
# pinned Codex-rendered bytes, captured from that candidate representation;
# they must never be regenerated from today's source tree.  It remains a
# separate profile from the two-skill bridge above because the historical
# renderings for their overlapping names differ.
_V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE = (
    "bc0d60b68de55abc36e8e273e729a36887f3808b4b6369ba58dbced76df2d0bb",
    "0ca4c2438ded122439db8ead2abbaf0f5522ba35e5fd091855e866476a328b55",
    "1fe801835ab0800b9e9c8fde3bef10b561aab9e84c55079acd888b526b24d86a",
    "ac8def71068d07bd072f9a18317ded0a206d77797335a38e77489d29d4ddfd8c",
    "b7b43b7189cff072c94517a8fab3e5b2688ec8386e7bbd0d4fb15b2553ded306",
    "a902b5d9b876411f2b73cf1fec3f6fb8681f70ec19155d500290eeaa8eb49f71",
    "5e4f3231f3b68ba4d1af796ff31c7fc80d6db2d7cc8f0558e2fb6a3f98d0bd98",
    "98daa12c8ffdc3dae9c3e5b3452f9afc107207e568ee495a8ea8f95bfdaa3b7f",
    "93d94f1d5a02293eab210028c0eb1fc4a143924dc7fd0e2c6331022a83d8f2fa",
    "95de6f0a9ab9235768bf902c0726d1284127796ce10e6377e71f2870bec114c3",
    "df6ddadeee36257d79806da2349a442f18c4597e39dbd2fe0f7ee8e1905e0be0",
    "12472465a632d881592b391d4665ab48231ecbc0d3527898e53c5c65527402dd",
    "3c5c450e4b1a07ff5f886c40c6cc8b4db3abfaa227acfb2a4f3c39ff46e8d68f",
    "8e92edd03e10e14b3795714fc24bcfd8ac1c87e7d4c05a7865e4008cfe21a47b",
    "019ec548e58da0640d82b989365041bfb079ada2e9396c781f7a4de500bc399a",
    "94c30ad58319bddf587a65696d269184fb5ab336584e3a4d1763a3a2e760f546",
    "9279af248efa74789f1ebf03d3ecd97bacd96c77adbd60dfe86ac30bb06fe7e9",
    "0747cf3379c1f311fa5ddfdcb4f16c62320995cca997e0c07256caa3729c75c9",
    "051b21677ae1506852393832c0903e1b9b34a658ea9fde3ad1db3ac5d3338e21",
    "87be14adc1430ddd1b042f41023799a2b2f87c57d0e08fdfb6fbad1d821902be",
    "e5233e5218bdc2d9408b81e9c0dbfd57939ad8b3ca7a280945eb9d7de7c24623",
    "f0683d0c8118c189bc6d3b2c1f5499e4dd2ae8c310fc43a2ed69b809f18f219b",
    "afbe4234a6d4c4c40a96c336e0b85528e968f258922af3021050b3dfd6c248f2",
    "3e3f460531b46c3e780cc992f81d8bb229784983a01f49c766d75e9b94b07f68",
    "51f0c0b27c941ef1f2e3613aecde8afad3db6e60c44b1f49fe2219d05598868c",
    "6fbe991edc39410df327803ceb3a1c5e48f9e55e08573de1870ff71b6378cfed",
    "c6c39bac491e1fc852c06e3e760c36ea992d62cb617f2c41a11fff3048d2060a",
)


def legacy_v1_omitted_command_skills(
    skills_dir: Path, manifest: object
) -> set[str] | None:
    """Return the exact, byte-proven v1 omissions, or refuse the witness.

    A legacy manifest is only a catalogue witness when it retains its exact
    three-field v1 shape.  Each omitted skill must be one of the closed
    historical set and its complete on-disk tree must be the single trusted
    ``SKILL.md`` asset with the pinned Codex-rendered digest.  This prevents a
    future command, an added sidecar file, a symlink, or a local edit from
    acquiring installer ownership through a name-shaped rule.
    """
    if not (
        isinstance(manifest, dict)
        and set(manifest) == {"installed_skills", "version"}
        and manifest.get("version") == "1.0"
        and isinstance(manifest.get("installed_skills"), list)
        and all(
            isinstance(name, str) and name.startswith("nw-") and Path(name).name == name
            for name in manifest["installed_skills"]
        )
        and len(manifest["installed_skills"]) == len(set(manifest["installed_skills"]))
    ):
        return None

    listed = set(manifest["installed_skills"])
    if skills_dir.is_symlink() or not skills_dir.is_dir():
        return None

    candidates = [
        candidate
        for candidate in skills_dir.glob("nw-*")
        if candidate.name not in listed
    ]

    def trusted_skill(candidate: Path, expected_digest: str) -> bool:
        skill = candidate / "SKILL.md"
        try:
            metadata, _ = parse_frontmatter_file(skill)
            return (
                candidate.name.startswith("nw-")
                and Path(candidate.name).name == candidate.name
                and not candidate.is_symlink()
                and candidate.is_dir()
                and list(candidate.iterdir()) == [skill]
                and not skill.is_symlink()
                and skill.is_file()
                and sha256(skill.read_bytes()).hexdigest() == expected_digest
                and isinstance(metadata, dict)
                and metadata.get("name") == candidate.name
            )
        except OSError:
            return False

    # Exact membership is part of the name-bound bridge fingerprint.  A small
    # test/bootstrap manifest may already list a member of the historical
    # profile, but the complete profile must still be present and byte-proven
    # before any of its remaining members are adopted.
    named_profile = _V1_OMITTED_PUBLIC_COMMAND_SKILL_DIGESTS
    named_omissions = set(named_profile) - listed
    if (
        named_omissions
        and {candidate.name for candidate in candidates} == named_omissions
    ):
        if all(
            trusted_skill(skills_dir / name, digest)
            for name, digest in named_profile.items()
        ):
            return named_omissions

    # The incomplete-manifest profile deliberately binds a *closed payload
    # multiset*, not dead historical command names.  Its content binds each
    # candidate back to its own directory through parsed frontmatter.
    # A member can already be catalogued by the incomplete manifest.  It is
    # still part of the 27-payload attestation, but only its unlisted peers
    # become omissions.  Every unlisted nw-* directory must belong to the
    # closed payload; otherwise it remains foreign.
    if (
        len(_V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE) != 27
        or len(set(_V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE)) != 27
    ):
        return None
    payload_candidates: list[tuple[Path, str]] = []
    for candidate in skills_dir.glob("nw-*"):
        skill = candidate / "SKILL.md"
        try:
            digest = sha256(skill.read_bytes()).hexdigest()
        except OSError:
            continue
        if digest in _V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE and trusted_skill(
            candidate, digest
        ):
            payload_candidates.append((candidate, digest))
    payload_names = {candidate.name for candidate, _ in payload_candidates}
    if (
        len(payload_candidates) == len(_V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE)
        and Counter(digest for _, digest in payload_candidates)
        == Counter(_V1_INCOMPLETE_MANIFEST_SKILL_DIGEST_PROFILE)
        and {candidate.name for candidate in candidates} == payload_names - listed
    ):
        return payload_names - listed
    return None


_RIGOR_MODEL_ARGUMENT = re.compile(
    r"(?m)^([ \t]*)model\s*=\s*rigor_(?:agent|reviewer)_model,?[^\n]*$"
)


def _adapt_model_dispatch_for_codex(content: str) -> str:
    """Omit nWave's rigor model argument from dispatch code for Codex.

    Codex chooses the model from its active configuration, so a dispatch line
    passing `model=rigor_agent_model` or `model=rigor_reviewer_model` would send
    a Claude-oriented alias to its runtime. Only that structural argument is
    rewritten here: prose that names a model or uses the word "inherit" keeps its
    bytes in this stage, and the wording rule of
    ``scripts.shared.codex_model_wording`` neutralises Claude model names as a
    separate stage of the install.
    """
    return _RIGOR_MODEL_ARGUMENT.sub(
        r"\1# Codex uses its configured session model; omit the model argument.",
        content,
    )


_FRONTMATTER_NAME_LINE = re.compile(r"(?m)^name:[^\n]*(?:\n|$)")


def _neutralise_claude_model_names(content: str) -> str:
    """Apply the Codex wording rule to a skill, except its frontmatter name line.

    A skill's name is its identity: a Claude tier inside it is a catalog defect
    the install scan reports, never something the installer renames.
    """
    frontmatter_end = content.find("---", 3) if content.startswith("---") else -1
    name_line = _FRONTMATTER_NAME_LINE.search(content, 0, max(frontmatter_end, 0))
    if name_line is None:
        return rewrite_claude_model_names(content)
    return (
        rewrite_claude_model_names(content[: name_line.start()])
        + name_line.group()
        + rewrite_claude_model_names(content[name_line.end() :])
    )


def _codex_skills_dir() -> Path:
    """Return the Codex CLI skills target directory.

    Codex skills live at $HOME/.agents/skills/ -- note this is NOT under
    ~/.codex/; it is a sibling of ~/.codex/ at the $HOME level.
    CODEX_HOME only overrides ~/.codex/ (config dir); it has no effect on
    the skills path.

    For testing isolation the env var NWAVE_AGENTS_HOME overrides the
    resolved $HOME in the returned path.  Production code never sets this
    variable, so production semantics are always $HOME/.agents/skills/.

    Returns:
        Path to $HOME/.agents/skills/ (or $NWAVE_AGENTS_HOME/.agents/skills/)
    """
    agents_home_override = os.environ.get("NWAVE_AGENTS_HOME")
    if agents_home_override:
        return Path(agents_home_override) / ".agents" / "skills"
    return Path.home() / ".agents" / "skills"


def _codex_config_dir() -> Path:
    """Return the Codex CLI configuration directory.

    Returns:
        Path to ~/.codex/ (or $CODEX_HOME if set)
    """
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _find_skills_source(context: InstallContext) -> Path | None:
    """Locate the skills source directory from dist or project layout.

    Args:
        context: InstallContext with framework_source and project_root

    Returns:
        Path to the skills source directory, or None if not found
    """
    dist_skills = context.framework_source / "skills" / "nw"
    if dist_skills.exists():
        return dist_skills

    project_skills = context.project_root / "nWave" / "skills"
    if project_skills.exists():
        return project_skills

    return None


def _strip_forbidden_fields(content: str) -> str:
    """Remove Claude Code-only frontmatter fields from skill content.

    Strips YAML frontmatter fields listed in CODEX_SKILL_FORBIDDEN_FIELDS.
    Only operates within the frontmatter block (between --- delimiters).
    Body content is never modified.

    Args:
        content: Full skill file content with YAML frontmatter

    Returns:
        Content with forbidden fields removed from frontmatter
    """
    if not content.startswith("---"):
        return content

    end_index = content.find("---", 3)
    if end_index == -1:
        return content

    frontmatter = content[4:end_index]
    body = content[end_index:]

    filtered_lines = [
        line
        for line in frontmatter.splitlines(keepends=True)
        if not any(
            line.startswith(f"{field}:") for field in CODEX_SKILL_FORBIDDEN_FIELDS
        )
    ]

    return "---\n" + "".join(filtered_lines) + body


def _write_manifest(target_dir: Path, installed_skill_names: list[str]) -> None:
    """Write the manifest file tracking nWave-installed skills.

    Args:
        target_dir: Codex skills directory
        installed_skill_names: List of installed skill directory names
    """
    manifest = {
        "installed_skills": sorted(installed_skill_names),
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the manifest file if it exists.

    Args:
        target_dir: Codex skills directory

    Returns:
        Parsed manifest dict, or None if not found
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _safe_skill_name(name: object) -> bool:
    """Return whether *name* is a non-traversing Codex skill basename."""
    return isinstance(name, str) and bool(name) and Path(name).name == name


def _read_owned_skill_manifest(
    target_dir: Path,
) -> tuple[bytes | None, dict | None, set[str]]:
    """Strictly read the ownership manifest before an install mutates disk.

    A manifest name is an ownership claim only after its own shape is trusted.
    This is intentionally narrower than ``_read_manifest``'s compatibility
    reader, because refresh reconciliation can delete stale directories.
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not (manifest_path.exists() or manifest_path.is_symlink()):
        return None, None, set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"unsafe Codex skills manifest: {manifest_path}")
    try:
        manifest_bytes = manifest_path.read_bytes()
        document = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable Codex skills manifest: {manifest_path}") from exc
    names = document.get("installed_skills") if isinstance(document, dict) else None
    if not (
        isinstance(document, dict)
        and set(document) == {"installed_skills", "version"}
        and document.get("version") == "1.0"
        and isinstance(names, list)
        and all(_safe_skill_name(name) for name in names)
        and len(names) == len(set(names))
    ):
        raise ValueError(f"untrusted Codex skills manifest: {manifest_path}")
    return manifest_bytes, document, set(names)


def _safe_stale_skill_dir(target_dir: Path, name: str) -> Path:
    """Validate a manifest/attestation-owned stale directory before removal."""
    if not _safe_skill_name(name):
        raise ValueError(f"unsafe stale Codex skill name: {name!r}")
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise ValueError(f"unsafe Codex skills directory: {target_dir}")
    skill_dir = target_dir / name
    if (
        skill_dir.parent != target_dir
        or skill_dir.is_symlink()
        or not skill_dir.is_dir()
    ):
        raise ValueError(f"unsafe stale Codex skill directory: {skill_dir}")
    try:
        if any(child.is_symlink() for child in skill_dir.rglob("*")):
            raise ValueError(f"unsafe stale Codex skill directory: {skill_dir}")
    except OSError as exc:
        raise ValueError(
            f"unreadable stale Codex skill directory: {skill_dir}"
        ) from exc
    return skill_dir


def _skill_tree_fingerprint(
    target_dir: Path, name: str
) -> tuple[tuple[object, ...], ...]:
    """Return a stable, identity- and byte-sensitive safe-tree fingerprint."""

    def snapshot_once() -> tuple[tuple[object, ...], ...]:
        skill_dir = _safe_stale_skill_dir(target_dir, name)
        try:
            paths = [skill_dir, *sorted(skill_dir.rglob("*"))]
            fingerprint: list[tuple[object, ...]] = []
            for path in paths:
                if path.is_symlink():
                    raise ValueError(f"unsafe Codex skill tree entry: {path}")
                before = path.stat(follow_symlinks=False)
                relative = (
                    "." if path == skill_dir else path.relative_to(skill_dir).as_posix()
                )
                if S_ISDIR(before.st_mode):
                    kind = "directory"
                    digest = ""
                elif S_ISREG(before.st_mode):
                    kind = "file"
                    digest = sha256(path.read_bytes()).hexdigest()
                else:
                    raise ValueError(f"unsafe Codex skill tree entry: {path}")
                after = path.stat(follow_symlinks=False)
                identity = (
                    before.st_dev,
                    before.st_ino,
                    before.st_mode,
                    before.st_size,
                    before.st_mtime_ns,
                )
                if identity != (
                    after.st_dev,
                    after.st_ino,
                    after.st_mode,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise ValueError(
                        f"Codex skill tree changed while inspected: {path}"
                    )
                fingerprint.append((relative, kind, *identity, digest))
            return tuple(fingerprint)
        except (OSError, ValueError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError(f"unreadable Codex skill tree: {skill_dir}") from exc

    first = snapshot_once()
    second = snapshot_once()
    if first != second:
        raise ValueError(
            f"Codex skill tree changed while inspected: {target_dir / name}"
        )
    return first


class CodexSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave Skills into Codex CLI's SKILL.md format."""

    def __init__(self) -> None:
        """Initialize Codex skills plugin with name and priority."""
        super().__init__(name="codex-skills", priority=50)

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether Codex CLI is present; skip gracefully if not.

        Detection: ~/.codex/ directory exists OR `codex` binary in PATH.
        If neither is found the plugin returns success with a skip message --
        the absence of Codex is not an error.

        Args:
            context: InstallContext (unused for detection, but required by ABC)

        Returns:
            PluginResult with success=True always (skip or proceed)
        """
        codex_dir = _codex_config_dir()
        codex_binary = shutil.which("codex") is not None
        if (
            "codex" not in context.target_platforms
            and not codex_dir.exists()
            and not codex_binary
        ):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="Codex CLI not detected, skipping skills installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="Codex CLI prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install skills from nWave/skills/ to $HOME/.agents/skills/.

        Copies each source SKILL.md to the Codex skills directory, stripping
        Claude Code-only frontmatter fields. A manifest tracks installed skill
        names for safe uninstallation.

        Walking-skeleton scope: copies ALL public skills with no name transform
        (flat namespace, no collision resolution needed for the skeleton).

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            # Check prerequisites first; skip if Codex not present
            prereq = self.validate_prerequisites(context)
            if "skip" in prereq.message.lower():
                return prereq

            context.logger.info("  Installing Codex skills...")

            skills_source = _find_skills_source(context)
            if skills_source is None:
                context.logger.info("  No skills directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to install (source directory not found)",
                )

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )

            from scripts.shared.agent_catalog import build_ownership_map

            agents_dir = context.project_root / "nWave" / "agents"
            ownership_map = (
                build_ownership_map(agents_dir) if agents_dir.exists() else {}
            )

            entries = enumerate_skills(skills_source)
            command_skills = (
                set() if context.dev_mode else detect_command_skills(skills_source)
            )
            entries = filter_public_skills(
                entries, public_agents, ownership_map, command_skills
            )

            # Snapshot the desired catalogue before looking at mutable target
            # state.  The manifest is the ownership oracle; historical
            # omissions are a separate, preflight-attested capability.
            desired_entries = tuple(entries)
            desired_names = {entry.name for entry in desired_entries}
            if len(desired_names) != len(desired_entries) or not all(
                _safe_skill_name(name) for name in desired_names
            ):
                raise ValueError("invalid desired Codex skill catalogue")

            target_dir = _codex_skills_dir()
            if target_dir.exists() or target_dir.is_symlink():
                if target_dir.is_symlink() or not target_dir.is_dir():
                    raise ValueError(f"unsafe Codex skills directory: {target_dir}")

            (
                old_manifest_bytes,
                old_manifest,
                old_manifest_names,
            ) = _read_owned_skill_manifest(target_dir)
            preflight_capability = context.metadata.get(
                _ATTESTED_LEGACY_SKILLS_METADATA_KEY, frozenset()
            )
            if not isinstance(preflight_capability, (set, frozenset)) or not all(
                _safe_skill_name(name) for name in preflight_capability
            ):
                raise ValueError("invalid Codex legacy-skill capability")
            preflight_capability = set(preflight_capability)
            reattested_omissions = (
                legacy_v1_omitted_command_skills(target_dir, old_manifest)
                if old_manifest is not None
                else None
            )
            observed_omissions = (
                set() if reattested_omissions is None else reattested_omissions
            )
            if observed_omissions != preflight_capability:
                raise ValueError(
                    "Codex legacy-skill attestation changed after preflight"
                )

            previous_owned = old_manifest_names | observed_omissions
            initial_desired_fingerprints: dict[str, tuple[tuple[object, ...], ...]] = {}
            for name in sorted(desired_names):
                desired_dir = target_dir / name
                if desired_dir.exists() or desired_dir.is_symlink():
                    if name not in previous_owned:
                        raise ValueError(
                            f"foreign or untracked Codex skill collision: {desired_dir}"
                        )
                    initial_desired_fingerprints[name] = _skill_tree_fingerprint(
                        target_dir, name
                    )
            stale_names = previous_owned - desired_names
            initial_stale_fingerprints = {
                name: _skill_tree_fingerprint(target_dir, name)
                for name in sorted(stale_names)
            }
            attested_tree_fingerprints = {
                name: _skill_tree_fingerprint(target_dir, name)
                for name in sorted(observed_omissions)
            }

            target_dir.mkdir(parents=True, exist_ok=True)

            installed_names: list[str] = []
            installed_files: list[Path] = []

            for entry in desired_entries:
                skill_target_dir = target_dir / entry.name
                if entry.name in initial_desired_fingerprints:
                    (
                        replacement_manifest_bytes,
                        replacement_manifest,
                        replacement_manifest_names,
                    ) = _read_owned_skill_manifest(target_dir)
                    if (
                        replacement_manifest_bytes != old_manifest_bytes
                        or replacement_manifest != old_manifest
                        or replacement_manifest_names != old_manifest_names
                    ):
                        raise ValueError(
                            "Codex skills manifest changed before desired replacement"
                        )
                    if (
                        _skill_tree_fingerprint(target_dir, entry.name)
                        != initial_desired_fingerprints[entry.name]
                    ):
                        raise ValueError(
                            "manifest-owned desired Codex skill changed before "
                            f"replacement: {entry.name}"
                        )
                    shutil.rmtree(skill_target_dir)
                elif skill_target_dir.exists() or skill_target_dir.is_symlink():
                    raise ValueError(
                        f"foreign or untracked Codex skill collision: {skill_target_dir}"
                    )

                if entry.source_path.is_dir():
                    shutil.copytree(entry.source_path, skill_target_dir)
                    target_file = skill_target_dir / "SKILL.md"
                else:
                    skill_target_dir.mkdir(parents=True)
                    target_file = skill_target_dir / "SKILL.md"
                    shutil.copy2(entry.source_path, target_file)

                content = target_file.read_text(encoding="utf-8")
                content = _strip_forbidden_fields(content)
                content = rewrite_host_paths(content, "codex")
                content = _adapt_model_dispatch_for_codex(content)
                content = _neutralise_claude_model_names(content)
                target_file.write_text(content, encoding="utf-8")

                installed_names.append(entry.name)
                installed_files.append(target_file)
                if entry.name in attested_tree_fingerprints:
                    # Preserve the attested chain of custody across this
                    # installer's authorized replacement of a desired legacy
                    # payload.  Final validation still reads the live tree.
                    attested_tree_fingerprints[entry.name] = _skill_tree_fingerprint(
                        target_dir, entry.name
                    )

            # Do not delete a stale owned directory until every desired skill
            # was copied and rendered.  Re-read every ownership witness from
            # the live target and require exact agreement with the initial
            # snapshot immediately before path-based deletion.
            (
                current_manifest_bytes,
                current_manifest,
                current_manifest_names,
            ) = _read_owned_skill_manifest(target_dir)
            if (
                current_manifest_bytes != old_manifest_bytes
                or current_manifest != old_manifest
                or current_manifest_names != old_manifest_names
            ):
                raise ValueError("Codex skills manifest changed during installation")

            current_attested_names: set[str] = set()
            for name, expected in attested_tree_fingerprints.items():
                if _skill_tree_fingerprint(target_dir, name) != expected:
                    raise ValueError(
                        f"attested Codex skill changed during installation: {name}"
                    )
                current_attested_names.add(name)
            if (
                current_attested_names != preflight_capability
                or current_attested_names != observed_omissions
            ):
                raise ValueError(
                    "Codex legacy-skill attestation changed before removal"
                )
            current_unlisted_non_desired = {
                path.name
                for path in target_dir.glob("nw-*")
                if path.name not in current_manifest_names
                and path.name not in desired_names
            }
            if current_unlisted_non_desired != observed_omissions - desired_names:
                raise ValueError("Codex legacy-skill candidates changed before removal")

            current_stale_names = (
                current_manifest_names | current_attested_names
            ) - desired_names
            if current_stale_names != stale_names:
                raise ValueError("Codex stale-skill set changed during installation")

            for name in sorted(current_stale_names):
                if (
                    _skill_tree_fingerprint(target_dir, name)
                    != initial_stale_fingerprints[name]
                ):
                    raise ValueError(
                        f"stale Codex skill changed during installation: {name}"
                    )
                # This last identity/content validation is immediately before
                # the destructive, path-based operation.  rmtree itself has
                # no directory-handle API, so a residual race remains between
                # this check and its first filesystem operation.
                shutil.rmtree(_safe_stale_skill_dir(target_dir, name))
            _write_manifest(target_dir, installed_names)

            context.logger.info(
                f"  Codex skills installed ({len(installed_names)} skills)"
            )

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills installed successfully ({len(installed_names)} skills)",
                installed_files=installed_files,
            )

        except Exception as e:
            context.logger.error(f"  Failed to install Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only nWave-installed Codex skills using manifest.

        Reads the manifest to determine which skills were installed by nWave,
        removes only those, and leaves user-created skills untouched.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating success or failure
        """
        try:
            context.logger.info("  Uninstalling Codex skills...")

            target_dir = _codex_skills_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                context.logger.info("  No Codex skills manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No Codex skills to uninstall (no manifest found)",
                )

            installed_skills = manifest.get("installed_skills", [])
            removed_count = 0

            for skill_name in installed_skills:
                skill_dir = target_dir / skill_name
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)
                    removed_count += 1

            manifest_path = target_dir / _MANIFEST_FILENAME
            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  Removed {removed_count} Codex skills")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills uninstalled ({removed_count} removed)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to uninstall Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify Codex skills were installed correctly.

        Checks that each skill listed in the manifest has a valid SKILL.md file.

        Args:
            context: InstallContext with shared installation utilities

        Returns:
            PluginResult indicating verification success or failure
        """
        try:
            context.logger.info("  Verifying Codex skills...")

            target_dir = _codex_skills_dir()
            manifest = _read_manifest(target_dir)

            if manifest is None:
                skills_source = _find_skills_source(context)
                if skills_source is None:
                    context.logger.info("  No Codex skills to verify (none configured)")
                    return PluginResult(
                        success=True,
                        plugin_name=self.name,
                        message="No Codex skills configured, verification skipped",
                    )

                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="Codex skills verification failed: manifest not found",
                    errors=["Manifest file .nwave-manifest.json not found"],
                )

            installed_skills = manifest.get("installed_skills", [])
            missing_skills: list[str] = []
            verified_count = 0

            for skill_name in installed_skills:
                skill_md = target_dir / skill_name / "SKILL.md"
                if not skill_md.exists():
                    missing_skills.append(f"{skill_name}/SKILL.md not found")
                else:
                    verified_count += 1

            if missing_skills:
                context.logger.error(
                    f"  Codex skills verification failed: {len(missing_skills)} missing"
                )
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=(
                        f"Codex skills verification failed: "
                        f"{len(missing_skills)} skills missing SKILL.md"
                    ),
                    errors=missing_skills,
                )

            context.logger.info(f"  Verified {verified_count} Codex skills")

            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"Codex skills verification passed ({verified_count} skills)",
            )

        except Exception as e:
            context.logger.error(f"  Failed to verify Codex skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"Codex skills verification failed: {e!s}",
                errors=[str(e)],
            )
