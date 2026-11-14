"""One read-only view of effective project settings and installed host assets."""

from __future__ import annotations

import json
import os
from pathlib import Path

import nwave_ai
from nwave_ai.doctor.checks.framework_files import FrameworkFilesCheck
from nwave_ai.doctor.context import DoctorContext
from nwave_ai.platform.activation import resolve_activation
from nwave_ai.platform.config import NWaveConfig
from nwave_ai.platform.documentation_density import resolve_density
from nwave_ai.platform.locations import NWaveLocations
from nwave_ai.platform.result import Failure
from nwdes import jev_access
from nwdes.prompts import resolved_jev
from nwdes.shell import machine_config
from scripts.shared.version import VersionResolutionError


_PROJECT_TIER = "project .nwave/config.json"
_MACHINE_TIER = "machine-wide ~/.nwave/config.json"


def jev_consent_source(repo_value: str | None, global_value: str | None) -> str:
    """Pure: the tier that decides Jev consent, in the order nwdes reads the tiers."""
    if repo_value is not None:
        return _PROJECT_TIER
    if global_value is not None:
        return _MACHINE_TIER
    return "default: nothing declared"


def jev_status_lines(
    repo_value: str | None, global_value: str | None, key_set: bool
) -> list[str]:
    """Pure: Jev consent and key state; the key's value is never part of the output."""
    consent = resolved_jev(None, repo_value, global_value)
    source = jev_consent_source(repo_value, global_value)
    access = jev_access.resolve_access(consent, key_present=key_set)
    if access is jev_access.JevAccess.UNAUTHORIZED:
        return [f"Jev: unauthorized ({source})"]
    state = "set" if key_set else "MISSING"
    lines = [f"Jev: authorized ({source}) | key: {state}"]
    warning = jev_access.warning(access)
    if warning is not None:
        lines.append(jev_access.render(warning))
    return lines


def _declared_jev(path: Path, tier: str) -> tuple[str | None, str | None]:
    """Shell: the jev value one config file declares, or the reason nwdes would refuse it."""
    if not path.is_file():
        return None, None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, f"{tier} is not readable JSON"
    if not isinstance(document, dict):
        return None, f"{tier} is not a JSON object"
    value = document.get("jev")
    if value is None or value in (jev_access.AUTHORIZED, jev_access.UNAUTHORIZED):
        return value, None
    return None, f"{tier} declares jev {value!r}, which is not a Jev choice"


def _jev_status_lines(cwd: Path) -> list[str]:
    """Shell: read the two tiers nwdes reads for Jev consent, then report them."""
    repo_value, repo_problem = _declared_jev(
        cwd / ".nwave" / "config.json", _PROJECT_TIER
    )
    global_value, global_problem = _declared_jev(
        machine_config.machine_config_path(Path.home()), _MACHINE_TIER
    )
    problems = [
        problem for problem in (repo_problem, global_problem) if problem is not None
    ]
    if problems:
        return [
            f"Jev: invalid ({'; '.join(problems)}); nwdes refuses Jev until that value is "
            "authorized or unauthorized."
        ]
    key_set = jev_access.key_is_set(os.environ.get(jev_access.KEY_VARIABLE))
    return jev_status_lines(repo_value, global_value, key_set)


def render_status(cwd: Path) -> str:
    """Describe this project's resolved state; never fetch releases or write config."""
    locations = NWaveLocations.resolve(
        home=Path.home(),
        repo_root=cwd,
        agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
        claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
        codex_config_override=os.environ.get("CODEX_HOME"),
    )
    if isinstance(locations, Failure):
        raise ValueError(locations.error)
    selected = locations.unwrap()
    config = NWaveConfig(
        cwd=cwd, global_config_path=selected.agents_home / ".nwave" / "config.json"
    )
    effective, sources = config.effective_config_with_sources()
    mode = config.activation_mode
    declared = config.enabled_for_repo
    active = resolve_activation(declared, mode)
    activation = config._global_config_data.get("activation")
    mode_source = (
        "global"
        if isinstance(activation, dict) and activation.get("mode") in ("opt-in", "all")
        else "default"
    )
    activation_source = (
        sources["enabled"] if declared is not None else f"{mode_source} mode"
    )
    try:
        version = nwave_ai.__version__
    except VersionResolutionError:
        version = "unavailable"

    claude_assets = FrameworkFilesCheck().run(DoctorContext.from_defaults()).passed
    codex_dir = selected.codex_config_dir
    codex_markers = (
        selected.agents_home / ".agents" / "skills" / ".nwave-manifest.json",
        codex_dir / "agents" / ".nwave-agents-manifest.json",
        codex_dir / ".nwave-des-manifest.json",
    )
    codex_assets = all(marker.is_file() for marker in codex_markers)

    credit = "on" if effective["attribution"] else "off"
    lines = [
        f"Global activation mode: {mode} ({mode_source})",
        f"This project is {'active' if active else 'inactive'}.",
        f"Activation source: {activation_source}.",
        f"Version: {version} (running CLI; check releases: nwave-ai update --check)",
        f"Attribution: {credit} ({sources['attribution']}); "
        f"nWave co-author credit {'applies to supported commits' if active and effective['attribution'] else 'will not be added here'}.",
        f"Verbosity: {effective['verbosity']} ({sources['verbosity']}).",
        *_jev_status_lines(cwd),
        f"Claude Code: {'framework files found' if claude_assets else 'framework files not detected'}.",
        f"Codex: {'installation manifests found' if codex_assets else 'installation manifests not detected'}.",
    ]
    if (
        "update_check" in config._global_config_data
        or "update_check" in config._config_data
    ):
        origins = ", ".join(
            origin
            for origin, data in (
                ("project", config._config_data),
                ("global", config._global_config_data),
            )
            if "update_check" in data
        )
        lines.append(
            f"Retired update_check: ignored ({origins}); no automatic update prompt."
        )
    documentation = config._global_config_data.get("documentation")
    density_config = dict(config._global_config_data)
    if isinstance(documentation, dict):
        density_config["documentation"] = {
            key: value
            for key, value in documentation.items()
            if key != "expansion_prompt"
        }
    try:
        density = resolve_density(density_config)
    except ValueError as error:
        lines.append(f"Documentation density: invalid ({error}); check global config.")
    else:
        reading = (
            "local HTML from the completed wave's DES document"
            if density.mode == "full"
            else "authoritative documents and handoffs"
        )
        lines.append(
            f"Documentation density: {density.mode} ({density.provenance}; "
            f"after an applicable completed wave: {reading})."
        )
    preference = {}
    if isinstance(documentation, dict) and "expansion_prompt" in documentation:
        preference["documentation"] = {
            "expansion_prompt": documentation["expansion_prompt"]
        }
        offer_source = "global"
    else:
        offer_source = "default"
    if "rigor" in config._global_config_data:
        preference["rigor"] = config._global_config_data["rigor"]
        if offer_source == "default":
            offer_source = "global rigor.profile"
    try:
        offer = resolve_density(preference).expansion_prompt
    except ValueError as error:
        lines.append(f"Wave-end explanation: invalid ({error}); check global config.")
    else:
        lines.append(
            f"Wave-end explanation: {offer} ({offer_source}; after completed waves only)."
        )
    if not active:
        lines.append("To activate this project: nwave-ai project enable")
    elif not effective["attribution"]:
        lines.append(
            "To credit future nWave commits: nwave-ai attribution on (machine-wide)."
        )
    lines.append(
        "Host detection is not validation; use nwave-ai doctor for Claude Code or the Codex installer's validation."
    )
    return "\n".join(lines)
