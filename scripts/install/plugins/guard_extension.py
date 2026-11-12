"""Pure core shared by the nWave guard extensions of the hosts that load a TypeScript extension.

``render_guard_extension`` fills a guard template's two placeholders, each as a JSON string literal, in one
pass. ``manifest_text`` records the installed file name and the sha256 of its rendered bytes. The OMP and
pi.dev installers use these facts from here; each host keeps its own directory and collision rules.
"""

from __future__ import annotations

import hashlib
import json
import re


EXTENSION_NAME = "nwave-hooks.ts"
MANIFEST_NAME = ".nwave-des-manifest.json"
_PLACEHOLDER = re.compile(r"\{\{(PYTHON_PATH_JSON|PYTHONPATH_JSON)\}\}")


def render_guard_extension(template: str, python: str, runtime: str) -> str:
    """Return the template with both placeholders replaced in one pass, each as a JSON string literal.

    One pass: a path that contains a placeholder is inserted verbatim and is never replaced again.
    """
    values = {
        "PYTHON_PATH_JSON": json.dumps(python),
        "PYTHONPATH_JSON": json.dumps(runtime),
    }
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def manifest_text(rendered: str) -> str:
    """Return the manifest naming the installed file and the sha256 of its rendered bytes."""
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    manifest = {"installed_extensions": [EXTENSION_NAME], "sha256": digest}
    return json.dumps(manifest, indent=2) + "\n"
