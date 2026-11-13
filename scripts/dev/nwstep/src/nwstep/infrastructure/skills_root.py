"""Where the skill directories named by a schema live. Shown to the executor only; a workspace with a kit reads its own copy instead."""

from __future__ import annotations

import os
from pathlib import Path

from nwstep.infrastructure.package_paths import PackagePaths


class SkillsRoot:
    INSTALLED = Path.home() / ".omp" / "agent" / "skills"
    CHECKOUT = PackagePaths.REPOSITORY / "nWave" / "skills"
    DIRECTORY = (
        Path(os.environ["NWSTEP_SKILLS_ROOT"])
        if os.environ.get("NWSTEP_SKILLS_ROOT")
        else (INSTALLED if INSTALLED.is_dir() else CHECKOUT)
    )
