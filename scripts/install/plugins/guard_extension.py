"""Pure core shared by the nWave guard extensions of the hosts that load a TypeScript extension.

``render_guard_extension`` fills a guard template's two placeholders, each as a JSON string literal, in one
pass. ``manifest_text`` records the installed file name and the sha256 of its rendered bytes. The OMP and
pi.dev installers use these facts from here; each host keeps its own directory and collision rules.
"""

from __future__ import annotations

import hashlib
import json
import re

from nwave_ai.rendered_bytes import owns_digest


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


def extension_bytes(rendered: str) -> bytes:
    """Return the bytes an installer writes for a rendering: its UTF-8 encoding, with no platform line-ending translation.

    Writers store exactly these bytes and manifest_text digests exactly these bytes, so the digest of the file on disk
    equals the manifest digest on every platform.
    """
    return rendered.encode("utf-8")


def manifest_text(rendered: str) -> str:
    """Return the manifest naming the installed file and the sha256 of its rendered bytes."""
    digest = hashlib.sha256(extension_bytes(rendered)).hexdigest()
    manifest = {"installed_extensions": [EXTENSION_NAME], "sha256": digest}
    return json.dumps(manifest, indent=2) + "\n"


def owned_by_manifest(shim: bytes, manifest: bytes) -> bool:
    """Return True when the manifest's recorded digest owns the shim's bytes: its LF rendering or its full CRLF translation.

    A manifest that is not a JSON object with a string sha256 owns nothing, so the shim is kept.
    """
    try:
        recorded = json.loads(manifest).get("sha256")
    except (ValueError, AttributeError):
        return False
    return owns_digest(shim, recorded if isinstance(recorded, str) else None)
