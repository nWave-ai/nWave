"""Typed domain vocabulary for installer-orphan-sweep slice-01 acceptance tests.

SSOT-via-Types-Services-DSL mandate (criterion 1, canonical:
``nw-test-design-mandates``): every domain noun used in the Gherkin of
``des-script-manifest.feature`` is expressed here exactly once as a typed
concept. Step bodies and composition services consume these types — never
raw string literals re-spelled per step.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType


ScriptName = NewType("ScriptName", str)

#: The DES script the previous version shipped and the current version retired.
RETIRED_SCRIPT = ScriptName("retired_helper.py")

#: A user-created (non-framework) script living alongside installed scripts.
PERSONAL_SCRIPT = ScriptName("my_backup_tool.py")


# --- slice-02 additions (additive only — slice-01 definitions unchanged) ----

TemplateName = NewType("TemplateName", str)

#: Runtime-asset folder the current version ships into the templates family.
CURRENT_ASSET_DIR = TemplateName("schemas")

#: Runtime-asset folder the previous version shipped and the current one retired.
RETIRED_ASSET_DIR = TemplateName("legacy-flavors")

#: A template the user created — never installed nor tracked by the framework.
USER_TEMPLATE = TemplateName("my-team-conventions.md")

#: Utility scripts the current version ships into the shared scripts directory
#: (the utilities family — public contract of ``utilities_plugin.py``).
UTILITY_SCRIPTS: tuple[ScriptName, ...] = (
    ScriptName("install_nwave_target_hooks.py"),
    ScriptName("validate_step_file.py"),
)


# --- slice-03 additions (additive only — slice-01/02 definitions unchanged) --

SkillName = NewType("SkillName", str)

#: Stray scripts on disk that no family record tracks (orphan candidates).
ORPHAN_SCRIPT = ScriptName("superseded_tool.py")
SECOND_ORPHAN_SCRIPT = ScriptName("old_migration.py")

#: A runtime-asset folder on disk that no family record tracks.
ORPHAN_ASSET_DIR = TemplateName("stale-flavor")

#: A skill the user created — inside the framework's nw-* namespace, yet
#: never installed nor tracked (the skills preserve-rule precedent).
USER_SKILL = SkillName("nw-custom")


class AssetFamily(Enum):
    """Report families = the manifest-bearing target directories.

    The verifier's expected-vs-actual diff is keyed by the DIRECTORY that
    carries a ``.nwave-manifest.json`` (accounted = union of every family
    record in that document). The enum value is the report key — the target
    directory name the operator recognises. Directories without a manifest
    (agents) are out of report scope.
    """

    SCRIPTS = "scripts"
    RUNTIME_ASSETS = "templates"
    SKILLS = "skills"


class TargetEra(Enum):
    """Shape of the pre-existing target installation an install runs against.

    The era is the single decision-driver of the slice-01 contract:

    - ``NEVER_INSTALLED``  — fresh machine, empty target.
    - ``PRE_MANIFEST``     — 3.16.0-shaped install: DES scripts on disk but
      no manifest. Preserve-by-default is the HARD contract here: nothing
      may be deleted, and the user must be warned.
    - ``MANIFEST_TRACKED`` — install whose scripts are tracked by the shared
      ``.nwave-manifest.json`` mechanism; tracked scripts absent from the
      new source are swept on upgrade.
    """

    NEVER_INSTALLED = "never-installed"
    PRE_MANIFEST = "pre-manifest"
    MANIFEST_TRACKED = "manifest-tracked"
